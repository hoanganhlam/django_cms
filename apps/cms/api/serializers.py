from apps.cms import models
from rest_framework import serializers
from apps.media.api.serializers import MediaSerializer
from apps.media.models import Media


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Publication
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {
            'user': {'read_only': True},
            'slug': {'read_only': True},
            'medias': {'read_only': True},
        }

    def to_representation(self, instance):
        return super(PublicationSerializer, self).to_representation(instance)


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Post
        fields = '__all__'
        extra_fields = [],
        extra_kwargs = {
            'user': {'read_only': True},
            'created': {'read_only': True},
            'updated': {'read_only': True},
            'post_related': {'read_only': True},
        }

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(PostSerializer, self).get_field_names(declared_fields, info)
        if getattr(self.Meta, 'extra_fields', None) and len(self.Meta.extra_fields) > 0:
            return expanded_fields + list(self.Meta.extra_fields[0])
        else:
            return expanded_fields

    def to_representation(self, instance):
        return super(PostSerializer, self).to_representation(instance)


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Term
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True}
        }


class PubTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PublicationTerm
        fields = '__all__'
        extra_kwargs = {
            'created': {'read_only': True},
            'updated': {'read_only': True},
        }
        extra_fields = ['entities'],

    def to_representation(self, instance):
        self.fields['term'] = TermSerializer(read_only=True)
        self.fields['media'] = MediaSerializer()
        return super(PubTermSerializer, self).to_representation(instance)


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Theme
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {
            'user': {'read_only': True},
            'created': {'read_only': True},
            'updated': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['media'] = MediaSerializer()
        return super(ThemeSerializer, self).to_representation(instance)


class PThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PublicationTheme
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {}

    def to_representation(self, instance):
        self.fields['theme'] = ThemeSerializer()
        return super(PThemeSerializer, self).to_representation(instance)


class CooperateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PublicationCooperation
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {
            'user': {'read_only': True},
        }

    def to_representation(self, instance):
        self.fields['publication'] = PublicationSerializer()
        self.fields['cooperation'] = PublicationSerializer()
        return super(CooperateSerializer, self).to_representation(instance)
