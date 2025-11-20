import os
from glob import glob
import threading
from typing import List, Tuple, Optional

import numpy as np
import warnings
try:
    from sklearn.exceptions import InconsistentVersionWarning  # type: ignore
except Exception:  # pragma: no cover
    InconsistentVersionWarning = None

try:
    import joblib
except Exception:  # pragma: no cover
    joblib = None


_lock = threading.Lock()
_model = None
_scaler = None
_version = None


SCALE = ["NUNCA", "RARA VEZ", "A VECES", "FRECUENTEMENTE", "SIEMPRE"]


def _load_artifacts():
    global _model, _scaler, _version
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        # Resolve candidate paths (env var wins). Default to backend/ml, then academics/ml
        if joblib is None:
            raise RuntimeError("joblib no está instalado. Agrega 'joblib' a requirements.")
        # Silenciar warning por versiones distintas de scikit-learn al deserializar
        if InconsistentVersionWarning is not None:
            warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
        base_backend = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # .../backend
        base_academics = os.path.dirname(os.path.dirname(__file__))                 # .../backend/academics

        model_path_env = os.getenv("MODEL_PATH")
        scaler_path_env = os.getenv("SCALER_PATH")

        model_candidates = [
            model_path_env,
            os.path.join(base_backend, "ml", "modelo_mg.pkl"),
            os.path.join(base_academics, "ml", "modelo_mg.pkl"),
        ]
        scaler_candidates = [
            scaler_path_env,
            os.path.join(base_backend, "ml", "minmax_scaler.pkl"),
            os.path.join(base_backend, "ml", "minmax_scaler_f.pkl"),
            os.path.join(base_academics, "ml", "minmax_scaler.pkl"),
            os.path.join(base_academics, "ml", "minmax_scaler_f.pkl"),
        ]

        model_path = next((p for p in model_candidates if p and os.path.exists(p)), None)
        scaler_path = next((p for p in scaler_candidates if p and os.path.exists(p)), None)
        if not scaler_path:
            # intento flexible: cualquier pkl que contenga 'scaler' en backend/ml
            cand = glob(os.path.join(base_backend, "ml", "*scaler*.pkl"))
            if cand:
                scaler_path = cand[0]

        if not model_path:
            raise FileNotFoundError("No se encontró el modelo. Define MODEL_PATH o coloca 'modelo_mg.pkl' en backend/ml/ (o academics/ml/)")

        _model = joblib.load(model_path)
        _scaler = joblib.load(scaler_path) if scaler_path else None
        _version = os.getenv("MODEL_VERSION", os.path.basename(model_path))


def _build_features(age: Optional[int], grade: Optional[int], answers: List[str]) -> np.ndarray:
    base = int(os.getenv("ML_LIKERT_BASE", "1"))  # 0 → [0..4], 1 → [1..5]
    default_age = int(os.getenv("ML_DEFAULT_AGE", "8"))
    default_grade = int(os.getenv("ML_DEFAULT_GRADE", "1"))
    age_val = float(age if age is not None else default_age)
    grade_val = float(grade if grade is not None else default_grade)
    idxs = [SCALE.index(a) for a in answers]
    likert_vals = [base + i for i in idxs]
    feats = np.array([age_val, grade_val] + likert_vals, dtype=float).reshape(1, -1)
    return feats


def _to_probability(model, X: np.ndarray) -> float:
    # Try predict_proba
    if hasattr(model, "predict_proba"):
        proba = float(model.predict_proba(X)[0, -1])
        return max(0.0, min(1.0, proba))
    # Fallback to decision_function with sigmoid
    if hasattr(model, "decision_function"):
        z = float(model.decision_function(X)[0])
        sig = 1.0 / (1.0 + np.exp(-z))
        return max(0.0, min(1.0, float(sig)))
    # As a last resort, use predict (0/1)
    pred = int(model.predict(X)[0])
    return 0.9 if pred == 1 else 0.1


def predict(answers: List[str], age: Optional[int] = None, grade: Optional[int] = None) -> Tuple[str, float, str]:
    _load_artifacts()
    X = _build_features(age, grade, answers)
    if _scaler is not None:
        try:
            X = _scaler.transform(X)
        except Exception:
            # Si falla el escalado por desajuste de dimensiones, continuar sin escalar
            pass
    p = _to_probability(_model, X)
    # Regla de negocio para diagnóstico (temporal hasta calibración)
    if p < 0.60:
        diag = "BAJO"
    elif p <= 0.85:
        diag = "MEDIO"
    else:
        diag = "ALTO"
    return diag, float(p), _version or "unknown"
