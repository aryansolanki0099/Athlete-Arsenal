from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
import os
from django.urls import reverse

class Course(models.Model):
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    # Make Course compatible with Cart system
    @property
    def name(self):
        return self.title
    
    @property
    def seller(self):
        return self.instructor
    
    @property
    def stock(self):
        # Courses are digital products, always in stock
        return 1
    
    def save(self, *args, **kwargs):
        # Delete old thumbnail if it's being replaced
        if self.pk:
            try:
                old_instance = Course.objects.get(pk=self.pk)
                if old_instance.thumbnail and self.thumbnail != old_instance.thumbnail:
                    default_storage.delete(old_instance.thumbnail.path)
            except Course.DoesNotExist:
                pass
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete thumbnail when course is deleted
        if self.thumbnail:
            default_storage.delete(self.thumbnail.path)
        super().delete(*args, **kwargs)

class Module(models.Model):
    course = models.ForeignKey(Course, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Content(models.Model):
    CONTENT_TYPES = (
        ('VIDEO', 'Video'),
        ('TEXT', 'Text'),
    )

    module = models.ForeignKey(Module, related_name='contents', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    video = models.FileField(upload_to='course_videos/', null=True, blank=True)
    text_content = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Content'
        verbose_name_plural = 'Contents'
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    def clean(self):
        if self.content_type == 'VIDEO' and not self.video:
            raise models.ValidationError('Video file is required for video content')
        elif self.content_type == 'TEXT' and not self.text_content:
            raise models.ValidationError('Text content is required for text content')
    
    def save(self, *args, **kwargs):
        # Delete old video if it's being replaced
        if self.pk and self.content_type == 'VIDEO':
            try:
                old_instance = Content.objects.get(pk=self.pk)
                if old_instance.video and self.video != old_instance.video:
                    default_storage.delete(old_instance.video.path)
            except Content.DoesNotExist:
                pass
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete video file when content is deleted
        if self.video:
            default_storage.delete(self.video.path)
        super().delete(*args, **kwargs)

    def get_video_url(self):
        """Get the streaming URL for video content."""
        if self.content_type == 'VIDEO' and self.video:
            # Extract the relative path from the full video path
            video_path = str(self.video).replace('course_videos/', '')
            return reverse('stream_video', kwargs={'path': video_path})
        return None

    @property
    def video_url(self):
        if self.content_type == 'VIDEO' and self.video:
            return self.video.url
        return None

class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'course')
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class CourseOrder(models.Model):
    PAYMENT_METHODS = (
        ('CARD', 'Credit/Debit Card'),
        ('UPI', 'UPI Payment'),
        ('COD', 'Cash on Delivery'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='CARD')
    payment_status = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'course')
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
    
    def save(self, *args, **kwargs):
        if not self.amount:
            self.amount = self.course.price
        super().save(*args, **kwargs)
