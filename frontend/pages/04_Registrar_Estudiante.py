import os
from datetime import date, timedelta

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get(path, params=None):
    r = requests.get(
        f"{API_URL}{path}",
        headers=auth_headers(),
        params=params,
        timeout=20
    )
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def create_student(payload: dict):
    r = requests.post(
        f"{API_URL}/students/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20
    )

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
        f"{API_URL}/enrollments/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20
    )

    if r.status_code in (200, 201):
        return True, r.json()

    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def go_back():
    if hasattr(st, "switch_page"):
        st.switch_page("pages/08_Gestion_Alumnos.py")
    else:
        st.rerun()

st.markdown("""
<style>

.back-wrap .stButton > button {
    min-width: 120px;
    min-height: 46px;
    border-radius: 12px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Nuevo alumno",
        page_icon="🎓",
        layout="wide"
    )

    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    col_title, col_back = st.columns([6, 1])

    with col_title:
        st.title("Nuevo alumno")

    with col_back:
        st.markdown('<div class="back-wrap">', unsafe_allow_html=True)
        if st.button("← Volver", type="primary", use_container_width=True):
            go_back()
        st.markdown("</div>", unsafe_allow_html=True)


    classrooms = api_get("/classrooms/")
    room_opts = [
        (
            c.get("id"),
            f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}"
        )
        for c in classrooms
    ]

    with st.form("student_form", clear_on_submit=False):
        st.markdown("### Datos del alumno")

        c1, c2 = st.columns(2)

        with c1:
            first_name = st.text_input("Nombres*")
            last_name = st.text_input("Apellidos*")
            age = st.number_input(
                "Edad*",
                min_value=5,
                max_value=18,
                value=7,
                step=1
            )

        with c2:
            gender = st.selectbox(
                "Género*",
                options=["", "M", "F"],
                format_func=lambda x: {
                    "": "Seleccione",
                    "M": "Masculino",
                    "F": "Femenino"
                }.get(x, x)
            )

        st.markdown("---")
        st.markdown("### Matrícula inicial")

        selected_room_id = None

        if room_opts:
            room_options = [None] + room_opts

            selected_room = st.selectbox(
                "Salón*",
                options=room_options,
                format_func=lambda x: "Seleccione un salón" if x is None else x[1]
            )

            selected_room_id = selected_room[0] if selected_room else None
        else:
            st.error("No hay salones creados. Primero debes crear un salón.")

        start_d = st.date_input(
            "Fecha de inicio (opcional)",
            value=None
        )

        c_cancel, c_save = st.columns([1, 1])

        cancel = c_cancel.form_submit_button(
            "Cancelar",
            type="secondary",
            use_container_width=True
        )

        submitted = c_save.form_submit_button(
            "Registrar",
            type="primary",
            use_container_width=True
        )

    if cancel:
        go_back()

    if submitted:
        if not first_name.strip() or not last_name.strip() or not selected_room_id:
            st.error("Completa los campos obligatorios (*) y selecciona un salón.")
            return

        if not gender:
            st.error("Debe seleccionar el género del estudiante.")
            return

        if start_d:
            today = date.today()
            try:
                min_start = date(today.year - age - 1, today.month, today.day)
            except ValueError:
                min_start = date(today.year - age - 1, today.month, 28)
            min_start += timedelta(days=1)
            if start_d < min_start:
                st.error(
                    "La fecha de inicio de matrícula no puede ser anterior al nacimiento estimado del alumno."
                )
                return

        payload = {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "age": age,
            "gender": gender or "",
        }

        with st.spinner("Registrando alumno..."):
            ok, data = create_student(payload)

        if not ok:
            if isinstance(data, dict):
                for k, v in data.items():
                    st.error(f"{k}: {v}")
            else:
                st.error(str(data))
            return

        student_id = data.get("id")

        if student_id and selected_room_id:
            with st.spinner("Registrando matrícula..."):
                oke, _ = enroll_student(student_id, selected_room_id, start_d)

            if not oke:
                st.warning("El alumno fue creado, pero falló la matrícula inicial.")
                return

        st.session_state.pop("admin_students_cache", None)
        st.session_state.pop("enrollment_cache", None)
        st.session_state["admin_students_page"] = 1
        st.session_state["force_refresh_students"] = True

        if hasattr(st, "switch_page"):
            st.switch_page("pages/08_Gestion_Alumnos.py")
        else:
            st.rerun()


if __name__ == "__main__":
    main()