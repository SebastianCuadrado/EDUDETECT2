import os
import time
from pathlib import Path

import streamlit as st

try:
    import requests
except Exception:
    requests = None


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
st.set_page_config(page_title="EduDetect - Login", page_icon="ðŸ”", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    :root { --card-bg: #ffffff0d; }
    html, body, [class*="css"]  {
        font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans';
    }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .card { background: var(--card-bg); border: 1px solid rgba(128,128,128,0.25); border-radius: 16px; padding: 28px 24px; box-shadow: 0 10px 24px rgba(0,0,0,0.08); }
    .brand-box { background: var(--card-bg); border: 1px dashed rgba(128,128,128,0.35); border-radius: 16px; padding: 24px; text-align: center; }
    .logo-circle { width: 240px; height: 240px; margin: 24px auto 12px auto; border-radius: 999px; background: linear-gradient(180deg, rgba(180,180,180,.6), rgba(140,140,140,.6)); display: grid; place-items: center; color: #222; font-weight: 600; }
    .tagline { margin: 18px auto 0 auto; display: inline-block; padding: 12px 18px; border-radius: 10px; background: rgba(120,120,120,.25); font-weight: 600; }
    .login-title { text-align: center; letter-spacing: .06em; font-weight: 700; }
    .small-muted { color: rgba(128,128,128,.9); font-size: .9rem; }
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

col_left, col_right = st.columns([1.05, 1])

with col_left:
    st.markdown('<div class="brand-box">', unsafe_allow_html=True)
    if logo_path:
        st.image(str(logo_path), width=240)
    else:
        st.markdown('<div class="logo-circle">Logo</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tagline">PrevenciÃ³n temprana para un futuro brillante</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h3 class='login-title'>INICIAR SESIÃ“N</h3>", unsafe_allow_html=True)
    st.write("")

    with st.form("login_form", clear_on_submit=False):
        user = st.text_input("Ingrese Usuario", placeholder="tu.usuario@colegio.edu")
        pwd = st.text_input("Ingrese ContraseÃ±a", type="password", placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢")
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
                        st.success("SesiÃ³n iniciada correctamente.")
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
                        st.error(f"Error de inicio de sesiÃ³n: {detail}")
                except Exception as exc:
                    st.error(f"No se pudo conectar con la API: {exc}")

    st.markdown(
        '<p class="small-muted" style="text-align:center; margin-top:8px;">Â¿Olvidaste tu contraseÃ±a?<br><strong>Contacta al administrador</strong></p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.auth:
    try:
        if hasattr(st, "switch_page"):
            st.switch_page("pages/00_Panel_Principal.py")
    except Exception:
        pass

