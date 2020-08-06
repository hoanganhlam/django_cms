#!/usr/bin/python
# -*- coding: utf8 -*-

from rest_framework import serializers


class CoreModelSerializer(serializers.ModelSerializer):

    # https://www.somesite.com/api/v1/buildings?fields=id,latitude,longitude
    # {
    #     "id": 110,
    #     "latitude": 24.706871,
    #     "longitude": -81.0611,
    # },
    def __init__(self, *args, **kwargs):
        super(CoreModelSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.query_params.get('fields'):
            fields = request.query_params.get('fields')
            if fields:
                fields = fields.split(',')
                allowed = set(fields)
                existing = set(self.fields.keys())
                for field_name in existing - allowed:
                    self.fields.pop(field_name)

    def delete_list(self):
        if self.data:
            key, ids = self.data.popitem()
            self.Meta.model.objects.filter(id__in=ids).delete()

    class Meta:
        abstract = True
