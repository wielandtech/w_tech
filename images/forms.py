from urllib import request
from django import forms
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.conf import settings
import requests
from .models import Image

class ImageCreateForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ('title', 'url', 'description')
        widgets = {
            'url': forms.HiddenInput,
        }

    def clean_url(self):
        url = self.cleaned_data['url']
        valid_extensions = ['jpg', 'jpeg', 'png']
        extension = url.rsplit('.', 1)[1].lower()
        if extension not in valid_extensions:
            raise forms.ValidationError('The given URL does not match valid image extensions.')
        return url

    def save(self, force_insert=False,
             force_update=False,
             commit=True):
        image = super().save(commit=False)

        image_url = self.cleaned_data['url']
        name = slugify(image.title)
        extension = image_url.rsplit('.', 1)[1].lower()
        image_name = f'{name}.{extension}'
        
        try:
            # Use requests with timeout instead of urllib
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Save the image
            image.image.save(image_name, ContentFile(response.content), save=False)
            if commit:
                image.save()
            return image
        except requests.exceptions.Timeout:
            raise forms.ValidationError('The image download timed out. Please try again.')
        except requests.exceptions.RequestException as e:
            raise forms.ValidationError(f'Error downloading image: {str(e)}')

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ('title', 'url', 'image', 'description')
        widgets = {
            'url': forms.URLInput(attrs={'placeholder': 'Enter image URL (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].required = False
        self.fields['image'].required = False

    def clean(self):
        cleaned_data = super().clean()
        url = cleaned_data.get('url')
        image = cleaned_data.get('image')

        if not url and not image:
            raise forms.ValidationError('Please provide either an image URL or upload an image file.')
        
        if url and image:
            raise forms.ValidationError('Please provide either a URL or upload a file, not both.')

        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            try:
                # Check file size
                if image.size > settings.MAX_UPLOAD_SIZE:
                    raise forms.ValidationError(
                        f'Image file too large. Maximum size is {settings.MAX_UPLOAD_SIZE/1024/1024}MB'
                    )
                
                # Check file type
                valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
                extension = image.name.rsplit('.', 1)[1].lower()
                if extension not in valid_extensions:
                    raise forms.ValidationError(
                        f'Invalid file type. Allowed extensions: {", ".join(valid_extensions)}'
                    )
                
                # Check if file is actually an image
                from PIL import Image as PILImage
                try:
                    img = PILImage.open(image)
                    img.verify()
                except Exception:
                    raise forms.ValidationError('Invalid image file. Please upload a valid image.')
                
            except Exception as e:
                raise forms.ValidationError(f'Error processing image: {str(e)}')
        
        return image

    def clean_url(self):
        url = self.cleaned_data.get('url')
        if url:
            try:
                valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
                extension = url.rsplit('.', 1)[1].lower()
                if extension not in valid_extensions:
                    raise forms.ValidationError(
                        f'Invalid URL extension. Allowed extensions: {", ".join(valid_extensions)}'
                    )
                
                # Check if URL is accessible
                response = requests.head(url)
                if not response.ok:
                    raise forms.ValidationError('The provided URL is not accessible.')
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise forms.ValidationError('The provided URL does not point to an image.')
                
            except Exception as e:
                raise forms.ValidationError(f'Error validating URL: {str(e)}')
        
        return url

    def save(self, force_insert=False, force_update=False, commit=True):
        image = super().save(commit=False)
        
        if self.cleaned_data.get('url'):
            try:
                image_url = self.cleaned_data['url']
                name = slugify(image.title)
                extension = image_url.rsplit('.', 1)[1].lower()
                image_name = f'{name}.{extension}'
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()  # Raise an exception for bad status codes
                image.image.save(image_name, ContentFile(response.content), save=False)
            except requests.exceptions.Timeout:
                raise forms.ValidationError('The image download timed out. Please try again.')
            except requests.exceptions.RequestException as e:
                raise forms.ValidationError(f'Error downloading image: {str(e)}')
        
        if commit:
            image.save()
        return image