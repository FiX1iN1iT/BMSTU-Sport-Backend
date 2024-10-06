from django.conf import settings
from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.response import *

def process_file_upload(file_object: InMemoryUploadedFile, client, image_name):
    try:
        client.put_object('bmstu-sport', image_name, file_object, file_object.size)
        return f"http://localhost:9000/bmstu-sport/{image_name}"
    except Exception as e:
        return {"error": str(e)}

def add_pic(new_section, image):
    client = Minio(           
            endpoint=settings.AWS_S3_ENDPOINT_URL,
           access_key=settings.AWS_ACCESS_KEY_ID,
           secret_key=settings.AWS_SECRET_ACCESS_KEY,
           secure=settings.MINIO_USE_SSL
    )
    i = new_section.id
    img_obj_name = f"{i}.png"

    if not image:
        return Response({"error": "Нет файла для изображения секции."})
    result = process_file_upload(image, client, img_obj_name)

    if 'error' in result:
        return Response(result)

    new_section.imageUrl = result
    new_section.save()

    return Response({"message": "success"})

def delete_pic(section_id):
    client = Minio(           
        endpoint=settings.AWS_S3_ENDPOINT_URL,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )
    
    img_obj_name = f"{section_id}.png"

    try:
        client.remove_object('bmstu-sport', img_obj_name)
        return Response({"message": "Image deleted successfully."})
    except Exception as e:
        return Response({"error": str(e)})