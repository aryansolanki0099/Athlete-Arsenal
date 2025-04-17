from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('BUYER', 'Buyer'),
        ('SELLER', 'Seller'),
        ('INSTRUCTOR', 'Instructor'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    
    def is_seller(self):
        return self.user_type == 'SELLER'
        
    def is_instructor(self):
        return self.user_type == 'INSTRUCTOR'
        
    def is_buyer(self):
        return self.user_type == 'BUYER'
