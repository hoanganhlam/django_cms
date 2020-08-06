from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from apps.media.models import Media


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    nick = models.CharField(max_length=200, null=True, blank=True)
    bio = models.CharField(max_length=500, null=True, blank=True)
    medals = ArrayField(models.CharField(max_length=80), null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles")
    extra = JSONField(blank=True, null=True)
    options = JSONField(blank=True, null=True)
