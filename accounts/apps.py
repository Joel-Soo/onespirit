from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Account Management'

    def ready(self):
        """
        Initialize account utilities when the app is ready.
        """
        # Import signals to ensure they are registered
        # (Add signal imports here when signal handlers are implemented)
        pass
