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
st.set_page_config(page_title="EduDetect - Login", page_icon="🔐", layout="wide")

hydrate_auth_from_query()

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    :root { --card-bg: #ffffff0d; }
    html, body, [class*="css"]  {
        font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans';
    }
    .block-container {
        padding-top: 4rem;
        padding-bottom: 4rem;
        max-width: 1000px;
    }
    .login-panel {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(120,120,120,0.18);
        border-radius: 28px;
        padding: 36px;
    }
    .card { background: var(--card-bg); border: 1px solid rgba(128,128,128,0.25); border-radius: 16px; padding: 32px 28px; box-shadow: 0 12px 28px rgba(0,0,0,0.16); }
    .brand-box { background: var(--card-bg); border: 1px dashed rgba(128,128,128,0.35); border-radius: 16px; padding: 32px 24px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 20px; }
    .brand-box img { display: block; margin: 0 auto; max-width: 260px ; padding-left:15%}
    .logo-circle { width: 220px; height: 220px; border-radius: 999px; background: linear-gradient(180deg, rgba(180,180,180,.6), rgba(140,140,140,.6)); display: grid; place-items: center; color: #222; font-weight: 600; padding-left:15%}
    .tagline { margin: 0; padding: 14px 20px; border-radius: 12px; background: rgba(120,120,120,.22); font-weight: 600; }
    .login-title { text-align: center; letter-spacing: .04em; font-weight: 700; margin-bottom: 1rem; }
    .small-muted { color: rgba(180,180,180,.9); font-size: .9rem; }
    @media (max-width: 980px) {
        .login-panel { padding: 24px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "auth" not in st.session_state:
    st.session_state.auth = False
if "username" not in st.session_state:
    st.session_state.username = ""

default_logo = Path(__file__).resolve().parent / "assets" / "logo.png"
env_logo = os.getenv("LOGO_PATH")
logo_candidates = [Path(env_logo)] if env_logo else []
logo_candidates.append(default_logo)
logo_candidates.append(Path("frontend/assets/logo.png"))
logo_candidates.append(Path("assets/logo.png"))
logo_path = next((p for p in logo_candidates if p.exists()), None)

with st.container():
    st.markdown('<div class="login-panel">', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="brand-box">', unsafe_allow_html=True)
        if logo_path:
            st.image(str(logo_path), width=260)
        else:
            st.markdown('<div class="logo-circle">Logo</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="tagline">Prevención temprana para un futuro brillante</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3 class='login-title'>INICIAR SESIÓN</h3>", unsafe_allow_html=True)
        st.write("")

        with st.form("login_form", clear_on_submit=False):
            user = st.text_input("Ingrese usuario", placeholder="tu.usuario@colegio.edu")
            pwd = st.text_input("Ingrese contraseña", type="password", placeholder="••••••••")
            submit = st.form_submit_button("Ingresar", use_container_width=True)

        if submit:
            if not requests:
                st.error("Falta instalar 'requests'. Ejecuta: pip install requests")
            else:
                with st.spinner("Verificando credenciales..."):
                    try:
                        resp = requests.post(
                            f"{API_URL}/auth/login/",
                            json={"username": user, "password": pwd},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.auth = True
                            st.session_state.username = data.get("user", {}).get("username", user)
                            st.session_state.token = data.get("token")
                            st.session_state.user = data.get("user", {})
                            persist_auth_state()
                            st.success("Sesión iniciada correctamente.")
                            time.sleep(0.3)
                            try:
                                if hasattr(st, "switch_page"):
                                    st.switch_page("pages/00_Panel_Principal.py")
                            except Exception:
                                pass
                        else:
                            try:
                                detail = resp.json().get("detail")
                            except Exception:
                                detail = resp.text
                            st.error(f"Error de inicio de sesión: {detail}")
                    except Exception as exc:
                        st.error(f"No se pudo conectar con la API: {exc}")

        st.markdown(
            '<p class="small-muted" style="text-align:center; margin-top:8px;">¿Olvidaste tu contraseña?<br><strong>Contacta al administrador</strong></p>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.auth:
    persist_auth_state()
    try:
        if hasattr(st, "switch_page"):
            st.switch_page("pages/00_Panel_Principal.py")
    except Exception:
        pass
