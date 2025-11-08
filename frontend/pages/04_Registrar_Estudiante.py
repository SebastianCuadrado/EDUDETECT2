import os
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", headers=auth_headers(), params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def create_student(payload: dict, photo_file):
    url = f"{API_URL}/students/"
    if photo_file is not None:
        files = {
            "photo": (
                getattr(photo_file, "name", "photo.jpg"),
                photo_file.getvalue(),
                getattr(photo_file, "type", "application/octet-stream"),
            )
        }
        data = {k: v for k, v in payload.items() if v is not None}
        r = requests.post(url, headers=auth_headers(), data=data, files=files, timeout=20)
    else:
        r = requests.post(url, headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20)
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def enroll_student(student_id: int, classroom_id: int, start_date: date | None = None):
    payload = {
        "student": student_id,
        "classroom": classroom_id,
        "start_date": start_date.isoformat() if start_date else None,
    }
    r = requests.post(
        f"{API_URL}/enrollments/", headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20
    )
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def main():
    st.set_page_config(page_title="Registrar Estudiante", page_icon="🧑‍🎓", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    st.title("Registrar Estudiante")

    classrooms = api_get("/classrooms/")
    room_opts = [(c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}") for c in classrooms]

    with st.form("student_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            dni = st.text_input("DNI*", max_chars=15)
            first_name = st.text_input("Nombres*")
            birth_date = st.date_input("Fecha de nacimiento", value=None)
            phone = st.text_input("Teléfono")
        with c2:
            last_name = st.text_input("Apellidos*")
            gender = st.selectbox("Género", options=["", "M", "F", "O"], index=0)
            email = st.text_input("Correo")

        st.markdown("---")
        st.caption("Foto del alumno (opcional)")
        photo = st.file_uploader("Selecciona una imagen", type=["png", "jpg", "jpeg"], accept_multiple_files=False)

        st.markdown("---")
        st.subheader("Matrícula")
        if room_opts:
            idx = st.selectbox("Salón*", options=list(range(len(room_opts))), format_func=lambda i: room_opts[i][1])
            selected_room_id = room_opts[idx][0]
        else:
            st.error("No hay salones creados. Ve a 'Salones' y crea uno primero.")
            selected_room_id = None
        start_d = st.date_input("Fecha de inicio (opcional)", value=None)

        submitted = st.form_submit_button("Registrar", use_container_width=True)

    if submitted:
        if not all([dni, first_name, last_name, selected_room_id]):
            st.error("Completa los campos obligatorios (*) y selecciona un salón")
            return
        payload = {
            "dni": dni,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date.isoformat() if birth_date else None,
            "gender": gender or "",
            "email": email or "",
            "phone": phone or "",
        }
        with st.spinner("Creando estudiante..."):
            ok, data = create_student(payload, photo)
            if not ok:
                if isinstance(data, dict):
                    for k, v in data.items():
                        st.error(f"{k}: {v}")
                else:
                    st.error(str(data))
                return
            st.success(f"Estudiante '{first_name} {last_name}' creado correctamente")
            student_id = data.get("id")

        if student_id and selected_room_id:
            with st.spinner("Matriculando estudiante..."):
                oke, _ = enroll_student(student_id, selected_room_id, start_d)
                if oke:
                    st.success("Matrícula registrada")
                else:
                    st.warning("Estudiante creado. Falló la matrícula")


if __name__ == "__main__":
    main()

