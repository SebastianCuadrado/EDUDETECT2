import time
import streamlit as st


def logout():
    for key in ("auth", "username", "token", "user"):
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
    if not st.session_state.get("auth") or not st.session_state.get("token"):
        st.error("Inicia sesión primero en la página principal.")
        st.stop()
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
                page_link("pages/08_Gestion_Alumnos.py", label="Alumnos", icon="🧒")
                page_link("pages/01_Lista_de_Usuarios.py", label="Usuarios", icon="👤")
                page_link("pages/05_Administrar_Salones.py", label="Salones", icon="🏫")
            else:
                page_link("pages/03_Historial_Alumnos_Evaluados.py", label="Alumnos", icon="🧒")
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
    if not st.session_state.get("auth"):
        return
    user = st.session_state.get("user") or {}
    username = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")
    st.caption(f"Conectado: {username} · {role}")
