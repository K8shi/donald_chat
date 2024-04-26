from __future__ import absolute_import, unicode_literals
from celery import shared_task
from project.celeryapp import celery_app
from django.core.serializers import deserialize
from django.conf import settings
from .utils import make_chroma_db
import zipfile
import os
import json
import time


@shared_task
def add(x, y): 
    return x+y

@shared_task
def process_zip(UPZ):
    from .models import (UploadedZipFile, )
    obj = UploadedZipFile.objects.get(id = UPZ)
    zip_file_path = obj.uploaded_zip_file.path
    # try:
    extract_path = os.path.join(settings.MEDIA_ROOT, "extracted", obj.user.username)
    
    
    os.makedirs(extract_path, exist_ok=True)

    if not os.path.exists(zip_file_path):
        time.sleep(15)   
        
        
    os.chmod(zip_file_path, 0o777)
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    if not obj.user.chroma_db_path:
        chroma_db_path = f"vector_db/{obj.user.username}"
        obj.user.chroma_db_path = chroma_db_path
        obj.user.save()
    else:
        chroma_db_path = obj.user.chroma_db_path
    obj.progress = "starting_text_processing" 
    obj.save_field()
    make_chroma_db(obj.user, extract_path, chroma_db_path, obj, extract_path)
    try:
        os.remove(zip_file_path)
    except:
        pass
    # except Exception as e:
    #     print(f"=====================>{e}")
    #     obj.progress = "error"
    #     obj.save()