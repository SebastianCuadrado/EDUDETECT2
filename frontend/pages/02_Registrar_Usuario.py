import os
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_post_user(payload: dict):
    r = requests.post(
        f"{API_URL}/users/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return (
        r.status_code in (200, 201),
        r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
    )


def api_get_classrooms():
    r = requests.get(f"{API_URL}/classrooms/", headers=auth_headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_post_assignment(teacher_id: int, classroom_id: int, role: str = "TITULAR", start_date: date | None = None):
    payload = {
        "teacher": teacher_id,
        "classroom": classroom_id,
        "role": role,
        "start_date": start_date.isoformat() if start_date else None,
    }
    r = requests.post(
        f"{API_URL}/teacher-assignments/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return r.status_code in (200, 201)


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


def reset_create_state():
    st.session_state.pop("new_user_role", None)
    st.session_state.pop("new_user_active", None)
    st.session_state["staged_assignments"] = []


def go_back():
    reset_create_state()
    try:
        if hasattr(st, "switch_page"):
            st.switch_page("pages/01_Lista_de_Usuarios.py")
            return
    except Exception:
        pass
    st.stop()


def inject_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1320px;
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }

        .section-card {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 16px 16px 8px 16px;
            margin-bottom: 18px;
            background: rgba(255,255,255,0.01);
        }

        .section-title {
            font-size: 1.6rem;
            font-weight: 800;
            color: #f8fafc;
            margin: 0 0 0.75rem 0;
        }

        .section-subtitle {
            color: #94a3b8;
            font-size: 0.96rem;
            margin-bottom: 0.9rem;
        }

        .mini-title {
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 700;
            margin: 0.3rem 0 0.7rem 0;
        }

        .pending-card {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: rgba(255,255,255,0.015);
        }

        .pending-text {
            color: #e2e8f0;
            font-size: 0.95rem;
            margin: 0;
        }

        .admin-note {
            color: #cbd5e1;
            font-size: 0.96rem;
            margin-bottom: 0.8rem;
        }

        .footer-actions {
            margin-top: 0.8rem;
        }

        .footer-actions .stButton > button,
        .footer-actions .stFormSubmitButton > button {
            min-height: 46px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }

        .assign-btn-wrap .stFormSubmitButton > button {
            min-height: 46px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            background-color: #FF9800 !important;
            
        }

        div[data-testid="stCheckbox"] {
            margin-top: 1.9rem;
        }

        div[data-testid="InputInstructions"] {
            display: none !important;
            visibility: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def validate_required(username: str, first_name: str, email: str, dni: str, password: str):
    missing = []

    if not username.strip():
        missing.append("Usuario")
    if not first_name.strip():
        missing.append("Nombres")
    if not email.strip():
        missing.append("Correo")
    if not dni.strip():
        missing.append("DNI")
    elif not dni.strip().isdigit() or len(dni.strip()) != 8:
        missing.append("DNI (debe tener exactamente 8 dígitos numéricos)")
    if not password.strip():
        missing.append("Contraseña")

    return missing


def main():
    st.set_page_config(page_title="Nuevo usuario", page_icon="👤", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    if "staged_assignments" not in st.session_state:
        st.session_state["staged_assignments"] = []

    if "new_user_role" not in st.session_state:
        st.session_state["new_user_role"] = "DOCENTE"

    if "new_user_active" not in st.session_state:
        st.session_state["new_user_active"] = True

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Volver",type="primary"):
            go_back()

    st.title("Nuevo usuario")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Rol y estado</div>', unsafe_allow_html=True)

    rc1, rc2 = st.columns([2, 1])

    with rc1:
        role = st.selectbox(
            "Rol",
            options=["ADMIN", "DOCENTE"],
            key="new_user_role",
        )

    with rc2:
        is_active = st.checkbox("Activo", key="new_user_active")

    st.markdown("</div>", unsafe_allow_html=True)

    if role == "ADMIN":
        st.session_state["staged_assignments"] = []

    with st.form("new_user_form", clear_on_submit=False):
        st.markdown('<div class="section-title">Información del usuario</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        with c1:
            username = st.text_input("Usuario *")
            first_name = st.text_input("Nombres *")
            last_name = st.text_input("Apellidos")

        with c2:
            email = st.text_input("Correo *")
            dni = st.text_input("DNI *", max_chars=8)
            phone = st.text_input("Telefono", max_chars=9)

        password = st.text_input("Contrasena *", type="password")

        sel_room_id = None
        teacher_role = "TITULAR"
        start_d = None

        if role == "ADMIN":
            st.markdown("---")
            st.markdown('<div class="section-title">Permisos administrativos</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="admin-note">Los usuarios con rol ADMIN no requieren asignación a salón.</div>',
                unsafe_allow_html=True,
            )
            st.info("Continúa con el registro del usuario.")
            st.markdown("</div>", unsafe_allow_html=True)

        if role == "DOCENTE":
            st.markdown("---")
            st.markdown('<div class="section-title">Asignacion a salon</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-subtitle">Agrega asignaciones iniciales para este docente antes de registrarlo.</div>',
                unsafe_allow_html=True,
            )

            try:
                rooms = api_get_classrooms()
            except Exception as e:
                rooms = []
                st.error(f"No se pudieron cargar los salones: {e}")

            room_map = {}
            for c in rooms:
                rid = c.get("id")
                label = f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}"
                if c.get("name"):
                    label = f"{c.get('name')} ({label})"
                room_map[rid] = label

            staged = st.session_state.get("staged_assignments", [])
            if staged:
                st.markdown('<div class="mini-title">Asignaciones pendientes</div>', unsafe_allow_html=True)
                for i, a in enumerate(staged, start=1):
                    room_label = room_map.get(a["classroom"], f"Aula ID {a['classroom']}")
                    st.markdown(
                        f'<div class="pending-card"><p class="pending-text">{i}. {room_label} · Rol {a["role"]} · Inicio {a.get("start_date") or "-"}</p></div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div class="mini-title">Agregar asignación</div>', unsafe_allow_html=True)

            room_opts = [
                (None, "Seleccione un salón")
                ]+[
                (c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}")
                for c in rooms
            ]

            a1, a2, a3, a4 = st.columns([2.2, 1.5, 1.5, 0.9])

            with a1:
                ridx = st.selectbox(
                    "Salon",
                    options=list(range(len(room_opts))),
                    format_func=lambda i: room_opts[i][1],
                    index=0
                )
                sel_room_id = room_opts[ridx][0]

            with a2:
                teacher_role = st.selectbox("Rol en el salon", options=["TITULAR", "APOYO"], index=0)

            with a3:
                start_d = st.date_input("Inicio (opcional)", value=None)

            with a4:
                st.markdown('<div class="assign-btn-wrap">', unsafe_allow_html=True)
                st.write("")
                add_btn = st.form_submit_button("Asignar salón", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if add_btn:
                if sel_room_id is None:
                    st.warning("Selecciona un salón antes de asignar.")
                else:
                    staged.append(
                        {
                            "classroom": sel_room_id,
                            "role": teacher_role,
                            "start_date": start_d.isoformat() if start_d else None,
                        }
                    )
                    st.session_state["staged_assignments"] = staged
                    safe_rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="footer-actions">', unsafe_allow_html=True)
        ccancel, csave = st.columns([1, 1])

        cancel = ccancel.form_submit_button("Cancelar", type="secondary", use_container_width=True)
        save = csave.form_submit_button("Registrar", type="primary", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    if cancel:
        go_back()

    if save:
        missing = validate_required(username, first_name, email, dni, password)
        if missing:
            st.error("Completa los campos obligatorios: " + ", ".join(missing))
            return

        payload = {
            "username": username.strip(),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "dni": dni.strip(),
            "role": role,
            "is_active": is_active,
            "password": password,
        }

        ok, data = api_post_user(payload)

        if not ok:
            st.error(str(data))
            return

        new_uid = data.get("id")
        if new_uid and role == "DOCENTE":
            for a in st.session_state.get("staged_assignments", []):
                api_post_assignment(
                    new_uid,
                    a["classroom"],
                    a.get("role", "TITULAR"),
                    date.fromisoformat(a["start_date"]) if a.get("start_date") else None,
                )

        st.success("Usuario creado correctamente.")
        st.session_state["force_refresh_users"] = True
        go_back()


if __name__ == "__main__":
    main()