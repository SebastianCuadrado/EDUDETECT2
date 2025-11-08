import os
from datetime import date
import streamlit as st
import requests
from ui_common import ensure_auth, render_sidebar_nav, render_topbar

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", headers=auth_headers(), params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def create_user(payload: dict):
    r = requests.post(
        f"{API_URL}/users/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def assign_teacher(teacher_id: int, classroom_id: int, role: str = "TITULAR", start_date: date | None = None):
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
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def main():
    st.set_page_config(page_title="Registrar Usuario", page_icon="👤", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    st.title("Registrar Usuario")

    classrooms = api_get("/classrooms/")
    room_opts = [(c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}") for c in classrooms]

    with st.form("reg_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            dni = st.text_input("DNI*", max_chars=15)
            username = st.text_input("Usuario*", max_chars=150)
            password = st.text_input("Contraseña*", type="password")
            role = st.selectbox("Tipo de Usuario*", options=["ADMIN", "DOCENTE"], index=1)
        with col2:
            first_name = st.text_input("Nombre*")
            email = st.text_input("Correo*", placeholder="email@gmail.com")
            phone = st.text_input("Teléfono", placeholder="")

        selected_room_id = None
        teacher_role = "TITULAR"
        start_d = None
        if role == "DOCENTE":
            st.markdown("---")
            st.subheader("Asignación a salón")
            if room_opts:
                idx = st.selectbox(
                    "Salón*", options=list(range(len(room_opts))), format_func=lambda i: room_opts[i][1]
                )
                selected_room_id = room_opts[idx][0]
            else:
                st.error("No hay salones creados. Ve a 'Salones' y crea uno primero.")
            teacher_role = st.selectbox("Rol en el salón", options=["TITULAR", "APOYO"], index=0)
            start_d = st.date_input("Inicio (opcional)", value=None)

        submitted = st.form_submit_button("Registrar", use_container_width=True)

    if submitted:
        if not all([dni, username, first_name, email, password]) or (role == "DOCENTE" and not selected_room_id):
            st.error("Completa los campos obligatorios (*) y selecciona un salón para docentes")
            return
        payload = {
            "username": username,
            "first_name": first_name,
            "last_name": "",
            "email": email,
            "phone": phone,
            "dni": dni,
            "role": role,
            "password": password,
            "is_active": True,
        }
        with st.spinner("Creando usuario..."):
            ok, data = create_user(payload)
            if ok:
                st.success(f"Usuario '{data.get('username')}' creado correctamente")
                if role == "DOCENTE" and selected_room_id:
                    ok2, info = assign_teacher(data.get("id"), selected_room_id, teacher_role, start_d)
                    if ok2:
                        st.success("Docente asignado al salón")
                    else:
                        st.warning(f"Usuario creado pero falló la asignación: {info}")
                st.balloons()
            else:
                if isinstance(data, dict):
                    for k, v in data.items():
                        st.error(f"{k}: {v}")
                else:
                    st.error(str(data))

    st.markdown("---")
    st.caption(
        "Solo ADMIN puede registrar nuevos usuarios. Si el usuario es DOCENTE, la asignación a salón es obligatoria."
    )


if __name__ == "__main__":
    main()
