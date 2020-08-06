from apps.cms import models
from rest_framework import serializers


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Publication
        fields = '__all__'
        extra_fields = []

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(PublicationSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def to_representation(self, instance):
        return super(PublicationSerializer, self).to_representation(instance)


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Post
        fields = '__all__'
        extra_fields = []

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(PostSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def to_representation(self, instance):
        return super(PostSerializer, self).to_representation(instance)


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Term
        fields = '__all__'


class TermTaxonomySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TermTaxonomy
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {
            'term': {'read_only': True}
        }

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(TermTaxonomySerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def to_representation(self, instance):
        self.fields["term"] = TermSerializer(read_only=True)
        return super(TermTaxonomySerializer, self).to_representation(instance)
