import os
import time
from pathlib import Path
import streamlit as st

try:
    import requests
except Exception:
    requests = None

from ui_common import hydrate_auth_from_query, persist_auth_state

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
st.set_page_config(page_title="EduDetect - Login", page_icon="🎓", layout="wide" , initial_sidebar_state="collapsed")

hydrate_auth_from_query()

# ===================== ESTILOS =====================
st.markdown("""
<style>
[data-testid="stSidebar"] {
    display: none !important;
}

[data-testid="stSidebarNav"] {
    display: none !important;
}

[data-testid="collapsedControl"] {
    display: none !important;
}

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(30, 64, 175, 0.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.12), transparent 28%),
        linear-gradient(135deg, #020617 0%, #031225 45%, #071426 100%);
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* -------- IZQUIERDA -------- */

.hero-box {
    padding: 2rem 1rem 2rem 0.5rem;
}


.hero-title {
    color: #f8fafc;
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 1rem;
}

.hero-subtitle {
    color: #94a3b8;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}


/* -------- LOGIN -------- */
.login-card {
    background: rgba(15, 23, 42, 0.85);
    border-radius: 20px;
    padding: 2rem;
    margin-top: 3rem;
    max-width: 450px;
}

/* 🔥 TÍTULO MÁS ABAJO */
.login-title {
    color: #f8fafc;
    font-size: 2rem;
    font-weight: 800;
    margin-top: 25px;
    margin-bottom: 0.5rem;
}



/* INPUTS */
div[data-testid="InputInstructions"] {
    display: none !important;
    visibility: hidden !important;
}

div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.06) !important;
    color: white !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

/* 🔥 BOTÓN MÁS SUAVE */
.stButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%) !important;
    color: white !important;
    border-radius: 12px !important;
    min-height: 45px !important;
    font-weight: 600 !important;
    box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25);
}

/* HOVER */
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    filter: brightness(1.05);
    transform: translateY(-1px);
}

.login-footer {
    margin-top: 1rem;
    text-align: center;
    color: #64748b;
}
</style>
""", unsafe_allow_html=True)

# ===================== SESSION =====================
if "auth" not in st.session_state:
    st.session_state.auth = False

# ===================== LOGO =====================
default_logo = Path(__file__).resolve().parent / "assets" / "logo.png"
logo_path = default_logo if default_logo.exists() else None

# ===================== LAYOUT =====================
col1, col2 = st.columns([1, 1])

# -------- IZQUIERDA --------
with col1:
    st.markdown('<div class="hero-box">', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Bienvenido a EduDetect</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Plataforma inteligente de detección temprana</div>',
        unsafe_allow_html=True
    )

    if logo_path:
        st.markdown('<div class="logo-card">', unsafe_allow_html=True)
        st.image(str(logo_path), width=320)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("**Prevención temprana para un futuro brillante**")

# -------- DERECHA --------
with col2:
    st.markdown('<div class="hero-box">', unsafe_allow_html=True)

    st.markdown('<div class="login-title">Iniciar sesión</div>', unsafe_allow_html=True)


    with st.form("login_form"):
        user = st.text_input("Usuario", placeholder="Ingrese su usuario")
        pwd = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")
        submit = st.form_submit_button("Ingresar", use_container_width=True)

    # -------- LOGIN --------
    if submit:
        if not requests:
            st.error("Instala requests: pip install requests")
        else:
            with st.spinner("Verificando..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/auth/login/",
                        json={"username": user, "password": pwd},
                        timeout=10,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.auth = True
                        st.session_state.user = data.get("user", {})
                        st.session_state.token = data.get("token")

                        persist_auth_state()
                        st.success("Bienvenido")

                        time.sleep(0.5)

                        if hasattr(st, "switch_page"):
                            target = "pages/01_Lista_de_Usuarios.py" if st.session_state.user.get("role") == "ADMIN" else "pages/00_Panel_Principal.py"
                            st.switch_page(target)

                    else:
                        st.error("Credenciales incorrectas")

                except Exception as e:
                    st.error(f"Error conexión API: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# ===================== REDIRECCIÓN =====================
if st.session_state.auth:
    persist_auth_state()
    if hasattr(st, "switch_page"):
        target = "pages/01_Lista_de_Usuarios.py" if (st.session_state.get("user") or {}).get("role") == "ADMIN" else "pages/00_Panel_Principal.py"
        st.switch_page(target)