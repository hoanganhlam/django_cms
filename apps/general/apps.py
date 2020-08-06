from django.apps import AppConfig


class GeneralConfig(AppConfig):
    name = 'apps.general'

    def ready(self):
        from apps.general import signals
