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


def paginate_list(items, key: str, page_size: int = 10, label: str | None = None):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)

    if key not in st.session_state:
        st.session_state[key] = 1

    if st.session_state[key] > total_pages:
        st.session_state[key] = total_pages
    if st.session_state[key] < 1:
        st.session_state[key] = 1

    page = st.session_state[key]

    if total_pages > 1:
        st.markdown('<div class="pagination-wrap">', unsafe_allow_html=True)

        prev_col, info_col, next_col = st.columns([1, 2, 1])

        with prev_col:
            if st.button("Anterior", key=f"{key}_prev", disabled=page <= 1, use_container_width=True):
                st.session_state[key] = page - 1
                st.rerun()

        start = (page - 1) * page_size
        end = min(start + page_size, total)

        texto = f"Página <b>{page}</b> de <b>{total_pages}</b> · Mostrando <b>{start+1}-{end}</b> de <b>{total}</b>"
        if label:
            texto = f"{label} · {texto}"

        with info_col:
            st.markdown(
                f"""
                <div style="text-align:center; padding-top:0.45rem; font-size:0.95rem; color:#b8bcc8;">
                    {texto}
                </div>
                """,
                unsafe_allow_html=True
            )

        with next_col:
            if st.button("Siguiente", key=f"{key}_next", disabled=page >= total_pages, use_container_width=True):
                st.session_state[key] = page + 1
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.session_state[key] = 1
        page = 1

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
    import streamlit as st
    from ui_common import hydrate_auth_from_query, logout

    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }

        /* Sidebar fondo */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #252733 0%, #222430 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }

        /* Padding */
        section[data-testid="stSidebar"] > div {
            padding-top: 1.2rem;
            padding-bottom: 1rem;
        }

        /* Header */
        .sidebar-title {
            color: #f8fafc;
            font-size: 1.9rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .sidebar-user {
            color: #b8c0cc;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

        .sidebar-divider {
            border: none;
            border-top: 1px solid rgba(255,255,255,0.10);
            margin: 0.8rem 0 1rem 0;
        }

        /* Links */
        section[data-testid="stSidebar"] .stPageLink a {
            position: relative;
            width: 100%;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.45rem;
            border-radius: 12px;
            color: #f8fafc !important;
            text-decoration: none !important;
            font-weight: 600;
            transition: all 0.18s ease;
        }

        /* Hover */
        section[data-testid="stSidebar"] .stPageLink a:hover:not([aria-current="page"]) {
            background: rgba(255,255,255,0.07);
        }

        /* 🔥 ACTIVO */
        section[data-testid="stSidebar"] .stPageLink a[aria-current="page"] {
            background: rgba(255,255,255,0.12) !important;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 12px;
        }

        /* 🔥 BARRA IZQUIERDA */
        section[data-testid="stSidebar"] .stPageLink a[aria-current="page"]::before {
            content: "";
            position: absolute;
            left: 0;
            top: 8px;
            bottom: 8px;
            width: 4px;
            border-radius: 4px;
            background: #4f8cff;
        }

        /* Botón logout */
        .logout-wrap {
            margin-top: 1.2rem;
        }

        .logout-wrap .stButton > button {
            width: 100%;
            min-height: 48px;
            border-radius: 12px;
            font-weight: 700;
            border: none;
            background: linear-gradient(180deg, #ff5a5f 0%, #ff4d4f 100%);
            color: white;
            box-shadow: 0 10px 24px rgba(255, 77, 79, 0.18);
        }

        .logout-wrap .stButton > button:hover {
            filter: brightness(1.03);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Validación de sesión
    hydrate_auth_from_query()
    if not st.session_state.get("auth"):
        return

    user = st.session_state.get("user") or {}
    username = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")
    is_admin = role == "ADMIN"

    # Sidebar
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-title">EduDetect</div>
            <div class="sidebar-user">Conectado como {username} · {role}</div>
            <hr class="sidebar-divider">
            """,
            unsafe_allow_html=True,
        )

        page_link = getattr(st, "page_link", None)

        if page_link:
            if not is_admin:
                page_link("pages/00_Panel_Principal.py", label="Panel", icon="📊")

            if is_admin:
                page_link("pages/01_Lista_de_Usuarios.py", label="Usuarios", icon="🧑‍💼")
                page_link("pages/08_Gestion_Alumnos.py", label="Alumnos", icon="🎓")
                page_link("pages/05_Administrar_Salones.py", label="Salones", icon="🏫")
            else:
                page_link("pages/03_Historial_Alumnos_Evaluados.py", label="Alumnos", icon="🎓")
                page_link("pages/07_Evaluaciones.py", label="Evaluaciones", icon="📝")

        # Logout
        st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
        if st.button("Cerrar sesión", type="primary"):
            logout()
        st.markdown("</div>", unsafe_allow_html=True)

def render_topbar():
     hydrate_auth_from_query()
     if not st.session_state.get("auth"):
        return
        user = st.session_state.get("user") or {}
        username = user.get("username") or st.session_state.get("username", "")
        role = user.get("role", "")
        st.caption(f"Conectado: {username} · {role}")
