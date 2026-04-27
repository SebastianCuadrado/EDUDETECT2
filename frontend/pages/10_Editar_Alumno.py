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
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_get_student(student_id):
    r = requests.get(
        f"{API_URL}/students/{student_id}/",
        headers=auth_headers(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def api_patch_student(student_id, payload):
    r = requests.patch(
        f"{API_URL}/students/{student_id}/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if r.status_code in (200, 201, 202):
        return True, r.json()

    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def api_get_classrooms():
    return api_get("/classrooms/")


def api_get_enrollments(student_id):
    return api_get(
        "/enrollments/",
        params={"student": student_id},
    )


def api_patch_enrollment(enrollment_id, payload):
    r = requests.patch(
        f"{API_URL}/enrollments/{enrollment_id}/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if r.status_code in (200, 201, 202):
        return True, r.json()

    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def api_post_enrollment(student_id, classroom_id, start_date_value):
    payload = {
        "student": student_id,
        "classroom": classroom_id,
        "start_date": start_date_value.isoformat(),
        "end_date": None,
    }

    r = requests.post(
        f"{API_URL}/enrollments/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if r.status_code in (200, 201, 202):
        return True, r.json()

    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def get_active_enrollment(enrollments):
    for enrollment in enrollments:
        if not enrollment.get("end_date"):
            return enrollment

    return None


def get_classroom_label(classroom):
    if not classroom:
        return "No asignado"

    name = classroom.get("name")
    academic_year = classroom.get("academic_year")
    grade = classroom.get("grade")
    section = classroom.get("section")

    if name and grade and section:
        return f"{name} - {grade}° {section}"

    if name:
        return name

    parts = []

    if academic_year:
        parts.append(str(academic_year))

    if grade not in (None, ""):
        parts.append(f"{grade}°")

    if section:
        parts.append(str(section))

    return " ".join(parts).strip() or f"Salón #{classroom.get('id')}"


def get_classroom_by_id(classrooms, classroom_id):
    if not classroom_id:
        return None

    for classroom in classrooms:
        if str(classroom.get("id")) == str(classroom_id):
            return classroom

    return None


def go_back():
    if hasattr(st, "switch_page"):
        st.switch_page("pages/08_Gestion_Alumnos.py")
    else:
        st.rerun()


def clear_students_cache():
    keys = [
        "admin_students_cache",
        "students_eval_cache",
        "enrollment_cache",
        "force_refresh_students",
    ]

    for key in keys:
        st.session_state.pop(key, None)

    st.session_state["force_refresh_students"] = True


def render_styles():
    st.markdown(
        """
        <style>
            .back-wrap .stButton > button {
                min-width: 120px;
                min-height: 46px;
                border-radius: 12px;
                font-weight: 700;
            }

            .info-box {
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 14px;
                padding: 16px 18px;
                background: rgba(255, 255, 255, 0.025);
                margin-bottom: 16px;
            }

            .info-label {
                font-size: 13px;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.55);
                margin: 0 0 6px 0;
            }

            .info-value {
                font-size: 18px;
                font-weight: 800;
                color: #ffffff;
                margin: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Editar alumno",
        page_icon="🎓",
        layout="wide",
    )

    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    render_styles()

    student_id = st.session_state.get("selected_student_id")

    if not student_id:
        st.warning("No se ha seleccionado un alumno.")
        if st.button("Volver"):
            go_back()
        return

    try:
        student = api_get_student(student_id)
        classrooms = api_get_classrooms()
        enrollments = api_get_enrollments(student_id)
    except Exception as e:
        st.error(f"No se pudo cargar la información del alumno: {e}")
        return

    active_enrollment = get_active_enrollment(enrollments)
    active_classroom_id = active_enrollment.get("classroom") if active_enrollment else None
    active_classroom = get_classroom_by_id(classrooms, active_classroom_id)
    current_classroom_label = get_classroom_label(active_classroom)

    col_title, col_back = st.columns([6, 1])

    with col_title:
        st.title("Editar alumno")

    with col_back:
        st.markdown('<div class="back-wrap">', unsafe_allow_html=True)
        if st.button("← Volver", type="primary", use_container_width=True):
            go_back()
        st.markdown("</div>", unsafe_allow_html=True)

    first_name_default = student.get("first_name", "")
    last_name_default = student.get("last_name", "")
    age_default = student.get("age") or 7
    gender_default = student.get("gender") or ""

    gender_options = ["", "M", "F"]
    gender_index = gender_options.index(gender_default) if gender_default in gender_options else 0

    classroom_options = [
        classroom for classroom in classrooms
        if classroom.get("id") is not None
    ]

    with st.form("edit_student_form", clear_on_submit=False):
        st.markdown("### Datos del alumno")

        c1, c2 = st.columns(2)

        with c1:
            first_name = st.text_input("Nombres*", value=first_name_default)
            last_name = st.text_input("Apellidos*", value=last_name_default)
            age = st.number_input(
                "Edad*",
                min_value=5,
                max_value=18,
                value=int(age_default),
                step=1,
            )

        with c2:
            gender = st.selectbox(
                "Género",
                options=gender_options,
                index=gender_index,
                format_func=lambda x: {
                    "": "Seleccione",
                    "M": "Masculino",
                    "F": "Femenino",
                }.get(x, x),
            )

        st.divider()

        st.markdown("### Asignación de salón")

        st.markdown(
            f"""
            <div class="info-box">
                <p class="info-label">Salón actual</p>
                <p class="info-value">{current_classroom_label}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_classroom_id = None
        start_date_value = None

        classroom_select_options = [None] + classroom_options

        selected_classroom = st.selectbox(
            "Nuevo salón",
            options=classroom_select_options,
            format_func=lambda classroom: "Mantener salón actual"
            if classroom is None
            else get_classroom_label(classroom),
        )

        if selected_classroom is not None:
            selected_classroom_id = selected_classroom.get("id")
            start_date_value = st.date_input(
                "Fecha de inicio en el nuevo salón",
                value=date.today(),
            )

        c_cancel, c_save = st.columns([1, 1])

        cancel = c_cancel.form_submit_button(
            "Cancelar",
            type="secondary",
            use_container_width=True,
        )

        save = c_save.form_submit_button(
            "Guardar cambios",
            type="primary",
            use_container_width=True,
        )

    if cancel:
        go_back()

    if save:
        if not first_name.strip() or not last_name.strip():
            st.error("Completa los campos obligatorios (*).")
            return

        payload = {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "age": int(age),
            "gender": gender or "",
        }

        with st.spinner("Guardando cambios..."):
            ok_student, student_response = api_patch_student(student_id, payload)

        if not ok_student:
            if isinstance(student_response, dict):
                for key, value in student_response.items():
                    st.error(f"{key}: {value}")
            else:
                st.error(str(student_response))
            return

        if selected_classroom_id:
            if active_classroom_id and str(selected_classroom_id) == str(active_classroom_id):
                st.warning("Los datos del alumno fueron actualizados. El salón seleccionado es el mismo que el actual.")
                clear_students_cache()
                return

            with st.spinner("Actualizando asignación de salón..."):
                if active_enrollment:
                    enrollment_id = active_enrollment.get("id")
                    end_date_value = start_date_value - timedelta(days=1)

                    ok_close, close_response = api_patch_enrollment(
                        enrollment_id,
                        {"end_date": end_date_value.isoformat()},
                    )

                    if not ok_close:
                        st.error(f"No se pudo cerrar la asignación anterior: {close_response}")
                        return

                ok_enrollment, enrollment_response = api_post_enrollment(
                    student_id,
                    selected_classroom_id,
                    start_date_value,
                )

                if not ok_enrollment:
                    st.error(f"No se pudo crear la nueva asignación de salón: {enrollment_response}")
                    return

        clear_students_cache()
        st.success("Alumno actualizado correctamente.")
        go_back()


if __name__ == "__main__":
    main()