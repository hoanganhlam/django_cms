#!/usr/bin/python
# -*- coding: utf8 -*-


import django_filters


class CoreFilterSet(django_filters.FilterSet):

    class Meta:
        abstract = True


class NullFilter(CoreFilterSet):
    """Filter on a field set as null or not."""

    def filter(self, qs, value):
        if value is not None:
            return qs.filter(**{'%s__isnull' % self.name: value})
        return qs

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class IdInFilter(django_filters.ModelMultipleChoiceFilter):
    def filter(self, qs, value):
        if value:
            id_list = [item.id for item in value]
            return qs.filter(id__in=id_list)
        return qs
