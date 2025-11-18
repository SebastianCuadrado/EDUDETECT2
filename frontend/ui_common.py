import time
import uuid
from typing import Any, Dict

import streamlit as st


@st.cache_resource
def _auth_store() -> Dict[str, Dict[str, Any]]:
    """Simple in-memory store that survives reruns to keep tokens per session id."""
    return {}


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


def hydrate_auth_from_query():
    if st.session_state.get("auth"):
        return
    params = _get_query_params()
    raw = params.get("session")
    if isinstance(raw, list):
        raw = raw[0]
    session_id = raw or st.session_state.get("session_id")
    if not session_id:
        return
    data = _auth_store().get(session_id)
    if not data:
        return
    for key, value in data.items():
        st.session_state[key] = value
    st.session_state["session_id"] = session_id


def persist_auth_state():
    if not st.session_state.get("auth"):
        return
    session_id = st.session_state.get("session_id") or uuid.uuid4().hex
    st.session_state["session_id"] = session_id
    payload = {key: st.session_state.get(key) for key in ("auth", "username", "token", "user")}
    _auth_store()[session_id] = payload
    params = _get_query_params()
    params["session"] = session_id
    _set_query_params(params)


def clear_persisted_auth():
    session_id = st.session_state.get("session_id")
    if session_id:
        _auth_store().pop(session_id, None)
    params = _get_query_params()
    if "session" in params:
        params.pop("session")
        _set_query_params(params)


def logout():
    clear_persisted_auth()
    for key in ("auth", "username", "token", "user", "session_id"):
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
