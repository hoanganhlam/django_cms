from __future__ import unicode_literals
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from django.utils.timesince import timesince as django_timesince
from django.utils.timezone import now
from base import interface


class Follow(models.Model):
    """
    Lets a user follow the activities of any specific actor
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_index=True
    )
    object_id = models.CharField(max_length=255, db_index=True)
    follow_object = GenericForeignKey()
    actor_only = models.BooleanField(
        "Only follow actions where "
        "the object is the target.",
        default=True
    )
    flag = models.CharField(max_length=255, blank=True, db_index=True, default='')
    started = models.DateTimeField(default=now, db_index=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id', 'flag')

    def __str__(self):
        return '{} -> {} : {}'.format(self.user, self.follow_object, self.flag)


class Action(models.Model):
    actor_content_type = models.ForeignKey(
        ContentType, related_name='actor',
        on_delete=models.CASCADE, db_index=True
    )
    actor_object_id = models.CharField(max_length=255, db_index=True)
    actor = GenericForeignKey('actor_content_type', 'actor_object_id')

    verb = models.CharField(max_length=255, db_index=True)

    target_content_type = models.ForeignKey(
        ContentType, blank=True, null=True,
        related_name='target',
        on_delete=models.CASCADE, db_index=True
    )
    target_object_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    target = GenericForeignKey(
        'target_content_type',
        'target_object_id'
    )

    action_object_content_type = models.ForeignKey(
        ContentType, blank=True, null=True,
        related_name='action_object',
        on_delete=models.CASCADE, db_index=True
    )
    action_object_object_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    action_object = GenericForeignKey(
        'action_object_content_type',
        'action_object_object_id'
    )

    message = models.TextField(null=True, blank=True)
    created = models.DateTimeField(default=now, db_index=True)
    public = models.BooleanField(default=True, db_index=True)
    voters = models.ManyToManyField(User, blank=True, related_name='voted_actions')
    user_mention = models.ManyToManyField(User, blank=True, related_name='mentioned_actions')
    user_seen = models.ManyToManyField(User, blank=True, related_name='seen_actions')
    user_deleted = models.ManyToManyField(User, blank=True, related_name='deleted_actions')
    is_activity = models.BooleanField(default=True)
    is_notify = models.BooleanField(default=True)
    measure = JSONField(null=True, blank=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        ctx = {
            'actor': self.actor,
            'verb': self.verb,
            'action_object': self.action_object,
            'target': self.target,
            'timesince': self.timesince()
        }
        if self.target:
            if self.action_object:
                return _('%(actor)s %(verb)s %(action_object)s on %(target)s %(timesince)s ago') % ctx
            return _('%(actor)s %(verb)s %(target)s %(timesince)s ago') % ctx
        if self.action_object:
            return _('%(actor)s %(verb)s %(action_object)s %(timesince)s ago') % ctx
        return _('%(actor)s %(verb)s %(timesince)s ago') % ctx

    def timesince(self, now_param=None):
        return django_timesince(self.created, now_param).encode('utf8').replace(b'\xc2\xa0', b' ').decode('utf8')


class Comment(interface.BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    activity = models.ForeignKey(Action, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField(max_length=500)
    parent_comment = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    voters = models.ManyToManyField(User, blank=True, related_name='voted_comments')
