from apps.media import models
from rest_framework import serializers
from django.contrib.auth.models import User
from apps.authentication.models import Profile

sizes = ['200_200', '600_200']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['media', 'bio', 'nick']

    def to_representation(self, instance):
        self.fields['media'] = MediaSerializer(read_only=True)
        return super(ProfileSerializer, self).to_representation(instance)


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'profile']

    def get_profile(self, instance):
        if hasattr(instance, 'profile'):
            return ProfileSerializer(instance.profile).data
        return None


class MediaSerializer(serializers.ModelSerializer):
    sizes = serializers.SerializerMethodField()

    class Meta:
        model = models.Media
        fields = '__all__'
        extra_fields = ['sizes']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(MediaSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def get_sizes(self, instance):
        if instance.path:
            return {
                "full_size": "https://cdn.fournalist.com/images/" + instance.path.name,
                "thumb_247_247": "https://cdn.fournalist.com/247x247/images/" + instance.path.name,
                "thumb_24_24": "https://cdn.fournalist.com/24x24/images/" + instance.path.name,
            }
        else:
            return {}

    def to_representation(self, instance):
        # self.fields['user'] = UserSerializer(read_only=True)
        return super(MediaSerializer, self).to_representation(instance)
