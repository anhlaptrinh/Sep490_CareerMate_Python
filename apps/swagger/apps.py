from django.apps import AppConfig


class SwaggerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.swagger'

    def ready(self):
        # Ensure OpenAPI extensions are registered when the app is ready
        from . import auth_extensions  # noqa: F401
