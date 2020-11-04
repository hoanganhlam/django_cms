from django.db import models
from base.interface import Taxonomy, BaseModel
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey


# Create your models here.

class Task(BaseModel, Taxonomy):
    user = models.ForeignKey(User, related_name="list_task", on_delete=models.CASCADE)
    assignee = models.ManyToManyField(User, related_name="list_task_assigned", blank=True)
    meta = JSONField(null=True, blank=True)
    time_start = models.DateTimeField(blank=True, null=True)
    time_end = models.DateTimeField(blank=True, null=True)
    time_dead = models.DateTimeField(blank=True, null=True)

    target_content_type = models.ForeignKey(
        ContentType, blank=True, null=True,
        related_name='task_target',
        on_delete=models.CASCADE, db_index=True
    )
    target_object_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    target = GenericForeignKey(
        'target_content_type',
        'target_object_id'
    )
