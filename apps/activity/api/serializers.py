from apps.activity import models
from rest_framework import serializers
from apps.authentication.api.serializers import UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Comment
        fields = ['content', 'activity', 'user', 'created']
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['user'] = UserSerializer(read_only=True)
        return super(CommentSerializer, self).to_representation(instance)


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Action
        fields = ['id', 'verb', 'created', 'message',
                  'actor_content_type', 'actor_object_id',
                  'target_content_type', 'target_object_id',
                  'user_mention', 'hash_tags']
        extra_kwargs = {
            'actor_content_type': {'read_only': True},
            'verb': {'read_only': True},
            'actor_object_id': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['user_mention'] = UserSerializer(read_only=True, many=True)
        return super(ActivitySerializer, self).to_representation(instance)
