from django.apps import AppConfig
import threading


def _warmup_ml_async():
    try:
        from .services.ml_inference import _load_artifacts  # type: ignore
        _load_artifacts()
    except Exception:
        # Evitar romper el arranque; el endpoint reportará errores detallados
        pass


class AcademicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "academics"

    def ready(self):
        # precargar artefactos del modelo en segundo plano para reducir la latencia del primer request
        t = threading.Thread(target=_warmup_ml_async, daemon=True)
        t.start()
