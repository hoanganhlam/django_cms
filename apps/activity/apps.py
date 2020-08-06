from django.apps import AppConfig
from apps.activity.signals import action


class ActivityConfig(AppConfig):
    name = 'apps.activity'

    def ready(self):
        from apps.activity.actions import action_handler
        action.connect(action_handler, dispatch_uid='apps.activity.models')

