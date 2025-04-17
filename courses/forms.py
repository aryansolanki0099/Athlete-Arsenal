from django import forms
from .models import Course, Module, Content

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'price', 'thumbnail']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'min': 0, 'step': '0.01'})
        }

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'order': forms.NumberInput(attrs={'min': 0})
        }

class ContentForm(forms.ModelForm):
    class Meta:
        model = Content
        fields = ['title', 'content_type', 'video', 'text_content', 'order']
        widgets = {
            'text_content': forms.Textarea(attrs={'rows': 5}),
            'order': forms.NumberInput(attrs={'min': 0}),
            'content_type': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Initialize content type field
        if instance:
            self.fields['content_type'].widget.attrs['readonly'] = True
            self.fields['content_type'].widget.attrs['disabled'] = True
            
            # Show only relevant fields based on content type
            if instance.content_type == 'VIDEO':
                self.fields['text_content'].widget = forms.HiddenInput()
            else:  # TEXT
                self.fields['video'].widget = forms.HiddenInput()
        
        # Add Bootstrap classes
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        video = cleaned_data.get('video')
        text_content = cleaned_data.get('text_content')
        
        if content_type == 'VIDEO' and not video and not self.instance.video:
            raise forms.ValidationError('Video file is required for video content')
        elif content_type == 'TEXT' and not text_content:
            raise forms.ValidationError('Text content is required for text content')
        
        return cleaned_data
