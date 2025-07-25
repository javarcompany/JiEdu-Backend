from django.apps import AppConfig #type: ignore


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Finance'
    
    def ready(self):
        import Finance.signals
