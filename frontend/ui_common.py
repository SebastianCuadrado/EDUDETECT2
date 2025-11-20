import base64
import json
import time
from typing import Any, Dict

import streamlit as st


def _get_query_params() -> Dict[str, Any]:
    try:
        return dict(st.query_params)
    except Exception:
        getter = getattr(st, "experimental_get_query_params", None)
        if getter:
            return getter()
        return {}


def _set_query_params(params: Dict[str, Any]):
    try:
        qp = st.query_params
        qp.clear()
        for key, value in params.items():
            qp[key] = value
        return
    except Exception:
        setter = getattr(st, "experimental_set_query_params", None)
        if setter:
            setter(**params)


def _encode_payload(data: Dict[str, Any]) -> str | None:
    try:
        raw = json.dumps(data).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")
    except Exception:
        return None


def _decode_payload(raw: str):
    try:
        data = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
        return json.loads(data)
    except Exception:
        return None


def hydrate_auth_from_query():
    if st.session_state.get("auth"):
        return
    params = _get_query_params()
    raw = params.get("auth")
    if isinstance(raw, list):
        raw = raw[0]
    if not raw:
        raw = st.session_state.get("_auth_payload")
        if raw:
            params["auth"] = raw
            _set_query_params(params)
    if not raw:
        return
    data = _decode_payload(raw)
    if not data or not data.get("token"):
        return
    for key in ("auth", "username", "token", "user"):
        if key in data:
            st.session_state[key] = data[key]
    st.session_state["_auth_payload"] = raw


def persist_auth_state():
    if not st.session_state.get("auth"):
        return
    payload = {
        "auth": True,
        "username": st.session_state.get("username"),
        "token": st.session_state.get("token"),
        "user": st.session_state.get("user"),
    }
    encoded = _encode_payload(payload)
    if not encoded:
        return
    params = _get_query_params()
    params["auth"] = encoded
    _set_query_params(params)
    st.session_state["_auth_payload"] = encoded


def clear_persisted_auth():
    params = _get_query_params()
    if "auth" in params:
        params.pop("auth")
        _set_query_params(params)
    if "_auth_payload" in st.session_state:
        del st.session_state["_auth_payload"]


def logout():
    clear_persisted_auth()
    for key in ("auth", "username", "token", "user", "_auth_payload"):
        if key in st.session_state:
            del st.session_state[key]
    st.success("Sesión cerrada")
    time.sleep(0.2)
    try:
        if hasattr(st, "switch_page"):
            st.switch_page("app_login.py")
            return
    except Exception:
        pass
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


def paginate_list(items, key: str, page_size: int = 5, label: str | None = None):
    """
    Simple client-side paginator returning the current slice and page info.
    """
    total = len(items)
    if page_size <= 0:
        return items, 1, 1, total

    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.session_state.get(key, 1)
    if page < 1 or page > total_pages:
        page = 1

    if total_pages > 1:
        prev_col, info_col, next_col = st.columns([1, 4, 1])
        if prev_col.button("Anterior", key=f"{key}_prev", disabled=page <= 1):
            page = max(1, page - 1)
        if next_col.button("Siguiente", key=f"{key}_next", disabled=page >= total_pages):
            page = min(total_pages, page + 1)
        st.session_state[key] = page

        start = (page - 1) * page_size
        end = min(start + page_size, total)
        label_txt = label or "Pagina"
        info_col.caption(f"{label_txt} {page} de {total_pages} · {start + 1}-{end} de {total}")
    else:
        st.session_state[key] = 1

    page = st.session_state.get(key, 1)
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    return items[start:end], page, total_pages, total


def ensure_auth(role: str | None = None):
    hydrate_auth_from_query()
    if not st.session_state.get("auth") or not st.session_state.get("token"):
        st.error("Inicia sesión primero en la página principal.")
        st.stop()
    persist_auth_state()
    if role:
        user_role = (st.session_state.get("user") or {}).get("role")
        if user_role != role:
            st.warning("Acceso restringido: solo usuarios con permisos pueden ver esta página.")
            st.stop()


def render_sidebar_nav():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    hydrate_auth_from_query()
    if not st.session_state.get("auth"):
        return

    user = st.session_state.get("user") or {}
    username = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")
    is_admin = role == "ADMIN"

    with st.sidebar:
        st.markdown("### EduDetect")
        st.caption(f"Conectado como {username} · {role}")

        page_link = getattr(st, "page_link", None)
        if page_link:
            page_link("pages/00_Panel_Principal.py", label="Panel", icon="📊")
            if is_admin:
                page_link("pages/08_Gestion_Alumnos.py", label="Alumnos", icon="🎓")
                page_link("pages/01_Lista_de_Usuarios.py", label="Usuarios", icon="🧑‍💼")
                page_link("pages/05_Administrar_Salones.py", label="Salones", icon="🏫")
            else:
                page_link("pages/03_Historial_Alumnos_Evaluados.py", label="Alumnos", icon="🎓")
                page_link("pages/07_Evaluaciones.py", label="Evaluaciones", icon="📝")
        else:
            st.markdown("- [Panel](pages/00_Panel_Principal.py)")
            if is_admin:
                st.markdown("- [Alumnos](pages/08_Gestion_Alumnos.py)")
                st.markdown("- [Usuarios](pages/01_Lista_de_Usuarios.py)")
                st.markdown("- [Salones](pages/05_Administrar_Salones.py)")
            else:
                st.markdown("- [Alumnos](pages/03_Historial_Alumnos_Evaluados.py)")
                st.markdown("- [Evaluaciones](pages/07_Evaluaciones.py)")

        st.divider()
        if st.button("Cerrar sesión", type="primary"):
            logout()


def render_topbar():
    hydrate_auth_from_query()
    if not st.session_state.get("auth"):
        return
    user = st.session_state.get("user") or {}
    username = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")
    st.caption(f"Conectado: {username} · {role}")
