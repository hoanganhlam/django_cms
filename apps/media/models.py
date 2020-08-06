from django.db import models
from base.interface import BaseModel, Taxonomy
import os
import datetime
from uuid import uuid4
from django.core.exceptions import ValidationError
from sorl.thumbnail import ImageField
from django.contrib.auth.models import User
from django.core.files.temp import NamedTemporaryFile
from urllib.parse import urlparse
import requests
from django.core.files import File


# Create your models here.

def validate_file_size(value):
    file_size = value.size

    if file_size > 10485760:
        raise ValidationError("The maximum file size that can be uploaded is 10MB")
    else:
        return value


def re_path(instance, filename, bucket):
    now = datetime.datetime.now()
    upload_to = '{}/guess/{}/'.format(bucket, str(now.year) + str(now.month) + str(now.day))
    ext = filename.split('.')[-1]
    filename = '{}.{}'.format(uuid4().hex, ext)
    return os.path.join(upload_to, filename)


def path_and_rename(instance, filename):
    return re_path(instance, filename, 'favdes/images')


class MediaManager(models.Manager):

    def save_url(self, url, **extra_fields):
        if url is None:
            return None
        name = urlparse(url).path.split('/')[-1]
        temp = NamedTemporaryFile(delete=True)
        try:
            req = requests.get(url=url, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
            disposition = req.headers.get("Content-Disposition")
            if disposition:
                test = disposition.split("=")
                if len(test) > 1:
                    name = test[1].replace("\"", "")
            temp.write(req.content)
            ext = name.split('.')[-1]
            if ext == '':
                ext = 'jpg'
                name = name + '.' + ext
            if ext in ['jpg', 'jpeg', 'png']:
                temp.flush()
                img = self.model(
                    title=extra_fields.get("title") if extra_fields.get("title", None) is not None else name)
                img.path.save(name, File(temp))
                return img
            return None
        except Exception as e:
            print(e)
            return None


class Media(BaseModel):
    title = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=200, blank=True)
    path = ImageField(upload_to=path_and_rename, max_length=500, validators=[validate_file_size])
    user = models.ForeignKey(User, related_name='medias', on_delete=models.SET_NULL, blank=True, null=True)

    objects = MediaManager()
