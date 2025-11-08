import time
import streamlit as st


def logout():
    for k in ("auth", "username", "token", "user"):
        if k in st.session_state:
            del st.session_state[k]
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
        sr = (st.session_state.get("user") or {}).get("role")
        if sr != role:
            st.warning("Acceso restringido: solo usuarios con permisos pueden ver esta página.")
            st.stop()


def render_sidebar_nav():
    # Ocultar el navegador de páginas nativo de Streamlit para evitar duplicados
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
    uname = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")

    with st.sidebar:
        st.markdown("### EduDetect")
        st.caption(f"Conectado como {uname} · {role}")

        link_fn = getattr(st, "page_link", None)
        if link_fn:
            st.page_link("pages/00_Panel_Principal.py", label="Panel", icon="🏠")
            if role == "ADMIN":
                st.page_link("pages/08_Gestion_Alumnos.py", label="Alumnos", icon="👥")
            else:
                st.page_link("pages/03_Historial_Alumnos_Evaluados.py", label="Alumnos", icon="👥")
            if role != "ADMIN":
                st.page_link("pages/07_Evaluaciones.py", label="Evaluaciones", icon="📝")
            if role == "ADMIN":
                st.page_link("pages/01_Lista_de_Usuarios.py", label="Usuarios", icon="👤")
                st.page_link("pages/05_Administrar_Salones.py", label="Salones", icon="🏫")
        else:
            st.markdown("- [Panel](pages/00_Panel_Principal.py)")
            if role == "ADMIN":
                st.markdown("- [Alumnos](pages/08_Gestion_Alumnos.py)")
            else:
                st.markdown("- [Alumnos](pages/03_Historial_Alumnos_Evaluados.py)")
            if role != "ADMIN":
                st.markdown("- [Evaluaciones](pages/07_Evaluaciones.py)")
            if role == "ADMIN":
                st.markdown("- [Usuarios](pages/01_Lista_de_Usuarios.py)")
                st.markdown("- [Salones](pages/05_Administrar_Salones.py)")

        st.divider()
        if st.button("Cerrar sesión", type="primary"):
            logout()


def render_topbar():
    if not st.session_state.get("auth"):
        return
    user = st.session_state.get("user") or {}
    uname = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")
    st.caption(f"Conectado: {uname} · {role}")

