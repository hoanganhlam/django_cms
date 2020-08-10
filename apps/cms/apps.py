from django.apps import AppConfig


class CmsConfig(AppConfig):
    name = 'apps.cms'

    def ready(self):
        from django.contrib.auth.models import User
        from apps.activity import registry
        registry.register(self.get_model('post'))
        registry.register(self.get_model('publication'))
        registry.register(User)
        from apps.cms import signals
