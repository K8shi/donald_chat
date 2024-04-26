import os
import zipfile
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.conf import settings
from .tasks import process_zip
from .utils import make_chroma_db
from django.core.serializers import serialize

def validate_file_size(value):
    limit = 90 * 1024 * 1024  # 90 MB
    if value.size > limit:
        raise ValidationError("File size cannot exceed 90 MB.")


def validate_zip_file_size(value):
    max_size = 90 * 1024 * 1024  # 90 MB
    if value.size > max_size:
        raise ValidationError('The file size exceeds the maximum allowed 90 MB')


# Create your models here.
class User(AbstractUser):
    collection = models.CharField(max_length=255, null=False, default="my_collection")
    chromadb = models.FileField(
        upload_to=f"vector_db/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["sqlite3"]),
            validate_file_size,
        ],
    )
    chroma_db_path = models.CharField(max_length=255, blank=True, null=True)
    profile_photo = models.ImageField(upload_to="uploads/images/", null=True, blank=True)
    bot_icon = models.ImageField(upload_to="uploads/images/", null=True, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
    
    def save(self, *args, **kwargs):
        self.chroma_db_path = f"vector_db/{self.username}"
        super().save(*args, **kwargs)


class UserAPIKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_key')
    api_key = models.CharField(max_length=255)
    pinecone_api_key = models.CharField(max_length=255, null=True, blank=True)
    pinecone_index_name = models.CharField(max_length=255, null=True, blank=True) 

    def __str__(self):
        return self.user.username


class UploadedZipFile(models.Model):
    PROGRESS_CHOICES = (
        ('starting_text_processing', 'Starting Text Processing'),
        ('text_processing_complete', 'Text Processing Complete'),
        ('starting_embedding', 'Starting Embedding'),
        ('embedding_complete', 'Embedding Complete'),
        ('error', 'error'),
        ('complete', 'complete'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='uploaded_zip')
    uploaded_zip_file = models.FileField(upload_to="files/", validators=[validate_zip_file_size])
    progress = models.CharField(max_length=50, choices=PROGRESS_CHOICES, default='starting_text_processing')

    
    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        process_zip.delay(self.id)
        
    def save_field(self, *args, **kwargs):
        super().save(*args, **kwargs) 

class AllowedUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="allowed_user")
    created_at = models.DateTimeField(auto_now_add=True, editable=True)
    updated_at = models.DateTimeField(auto_now=True, editable=True)
    
    # def process_zip(self):
    #     zip_file_path = self.uploaded_zip_file.path
    #     print("zip path :" + zip_file_path)
    #     #extract_path = os.path.join(os.path.dirname(zip_file_path), "extracted", self.user.username)
    #     extract_path = os.path.join(settings.MEDIA_ROOT, "extracted", self.user.username)
        
    #     # Create the extracted directory if it doesn't exist
    #     os.makedirs(extract_path, exist_ok=True)

    #     # Extract the zip file
    #     with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
    #         zip_ref.extractall(extract_path)

    #     # Parse documents and create vector database
    #     if not self.user.chroma_db_path:
    #         chroma_db_path = f"vector_db/{self.user.username}"
    #         self.user.chroma_db_path = chroma_db_path
    #         self.user.save()
    #     else:
    #         chroma_db_path = self.user.chroma_db_path
    #     self.progress = "starting_text_processing" 
    #     self.save_field()
    #     make_chroma_db(self.user, extract_path, chroma_db_path, self)

    #     # Clean up: Remove the zip file
    #     try:
    #         os.remove(zip_file_path)
    #     except:
    #         pass
