#!/usr/bin/python
# -*- coding: utf8 -*-

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_file_size(value):
    file_size = value.size

    if file_size > 2048576000:
        raise ValidationError("The maximum file size that can be uploaded is 1MB")
    else:
        return value


class CoreValidator(object):
    VALID_ALPHA = _('attribute is required')

    def __init__(self):
        pass

    @staticmethod
    def __raiseError(msg):
        raise ValidationError(msg)

    @staticmethod
    def __regxMatch(value, pattern=r'.*'):
        # prog = re.compile(pattern)
        # result = prog.match(value)
        result = re.match(pattern, value)
        return result

    @staticmethod
    def v_required(value):
        if value:
            if isinstance(value, str):
                if value.strip() == '':
                    return CoreValidator.__raiseError(CoreValidator.VALID_ALPHA)
        else:
            return CoreValidator.__raiseError(CoreValidator.VALID_ALPHA)

    @staticmethod
    def v_alpha(value):
        pass

    @staticmethod
    def v_alpha_number(value):
        pass

    @staticmethod
    def v_digits(value, min=None, max=None):
        pass

    @staticmethod
    def v_min(value, min=None):
        pass

    @staticmethod
    def v_max(value, max=None):
        pass

    @staticmethod
    def v_regex(value, pattern=None):
        pass

    @staticmethod
    def v_notregex(value, pattern=None):
        pass
