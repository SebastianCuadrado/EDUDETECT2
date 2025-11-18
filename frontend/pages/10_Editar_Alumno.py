import os
from datetime import date, timedelta

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get_student(student_id: int):
    r = requests.get(f"{API_URL}/students/{student_id}/", headers=auth_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def api_get_classrooms():
    r = requests.get(f"{API_URL}/classrooms/", headers=auth_headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_patch_student(student_id: int, payload: dict):
    url = f"{API_URL}/students/{student_id}/"
    r = requests.patch(url, headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20)
    if r.status_code in (200, 202):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def api_post_student(payload: dict):
    url = f"{API_URL}/students/"
    r = requests.post(url, headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20)
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def api_post_enrollment(student_id: int, classroom_id: int, start_date: date | None = None):
    payload = {
        "student": student_id,
        "classroom": classroom_id,
        "start_date": start_date.isoformat() if start_date else None,
    }
    r = requests.post(
        f"{API_URL}/enrollments/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    return r.status_code in (200, 201)


def api_get_enrollments(student_id: int):
    r = requests.get(
        f"{API_URL}/enrollments/",
        headers=auth_headers(),
        params={"student": student_id},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_patch_enrollment(enrollment_id: int, payload: dict):
    r = requests.patch(
        f"{API_URL}/enrollments/{enrollment_id}/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return r.status_code in (200, 202)


def go_back():
    try:
        if hasattr(st, 'switch_page'):
            st.switch_page('pages/08_Gestion_Alumnos.py')
            return
    except Exception:
        pass
    st.stop()


def main():
    st.set_page_config(page_title="Alumno", page_icon="°¸§¢", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    create_mode = bool(st.session_state.get("create_mode"))
    sid = st.session_state.get("selected_student_id")

    # Barra superior con volver
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("¢¢  Volver"):
            go_back()

    stu = {}
    age_val = None
    active_classroom_id = None
    if not create_mode:
        if not sid:
            st.warning("No se ha seleccionado un alumno.")
            go_back()
            return
        try:
            stu = api_get_student(sid)
        except Exception as e:
            st.error(f"No se pudo cargar el alumno: {e}")
            go_back()
            return
        st.title(f"Editar: {stu.get('first_name','')} {stu.get('last_name','')}")
        age_val = stu.get("age")
        # Mostrar matr­cula activa actual
        try:
            enrolls = api_get_enrollments(sid)
        except Exception:
            enrolls = []
        active = None
        for e in enrolls:
            if not e.get("end_date"):
                active = e
                break
        if active:
            active_classroom_id = active.get('classroom')
            st.caption(f"Sal³n actual (activo): ID {active_classroom_id} · Inicio: {active.get('start_date') or '-'}")
    else:
        st.title("Nuevo alumno")

    with st.form("student_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Nombres" + ("*" if create_mode else ""), value=stu.get("first_name") or "")
            last_name = st.text_input("Apellidos" + ("*" if create_mode else ""), value=stu.get("last_name") or "")
            age = st.number_input("Edad" + ("*" if create_mode else ""), min_value=1, max_value=120, value=int(age_val or 7))
        with col2:
            gender = st.selectbox(
                "G©nero",
                options=["", "M", "F", "O"],
                index=["", "M", "F", "O"].index(stu.get("gender") or ""),
            )

        # Matr­cula inicial (crear) o cambio de sal³n (editar)
        selected_room_id = None
        start_d = None
        classrooms = api_get_classrooms()
        room_opts = [(c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}") for c in classrooms]
        if create_mode:
            st.markdown("---")
            st.subheader("Matr­cula inicial")
            if room_opts:
                ridx = st.selectbox("Sal³n*", options=list(range(len(room_opts))), format_func=lambda i: room_opts[i][1])
                selected_room_id = room_opts[ridx][0]
            else:
                st.error("No hay salones creados")
            start_d = st.date_input("Fecha de inicio (opcional)", value=None)
        else:
            # Cambio de sal³n opcional (solo uno activo)
            st.markdown("---")
            st.subheader("Cambio de sal³n (opcional)")
            if room_opts:
                ridx2 = st.selectbox(
                    "Nuevo sal³n (opcional)",
                    options=[-1] + list(range(len(room_opts))),
                    format_func=lambda i: ("-- mantener --" if i == -1 else room_opts[i][1]),
                )
                if ridx2 != -1:
                    selected_room_id = room_opts[ridx2][0]
                    start_d = st.date_input("Fecha de inicio en nuevo sal³n", value=date.today())

        csave, ccancel = st.columns([1, 1])
        save = csave.form_submit_button("Registrar" if create_mode else "Guardar cambios")
        cancel = ccancel.form_submit_button("Cancelar")

    if cancel:
        st.session_state.create_mode = False
        st.session_state.selected_student_id = None
        go_back()

    if save:
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "age": int(age),
            "gender": gender,
        }
        if create_mode and not all([first_name, last_name, age, selected_room_id]):
            st.error("Completa los campos obligatorios (*)")
        else:
            with st.spinner("Guardando..."):
                if create_mode:
                    ok, data = api_post_student(payload)
                    if ok:
                        new_id = data.get("id")
                        if new_id and selected_room_id:
                            api_post_enrollment(new_id, selected_room_id, start_d)
                        st.success("Alumno creado")
                        # limpiar caches para que el listado recargue y muestre el nuevo alumno
                        try:
                            if 'admin_students_cache' in st.session_state:
                                del st.session_state['admin_students_cache']
                        except Exception:
                            pass
                        st.session_state.create_mode = False
                        st.session_state.selected_student_id = None
                        go_back()
                    else:
                        st.error(str(data))
                else:
                    ok, data = api_patch_student(sid, payload)
                    if ok:
                        # si se seleccion³ nuevo sal³n, validar y migrar matr­cula
                        if selected_room_id:
                            if active_classroom_id and int(selected_room_id) == int(active_classroom_id):
                                st.warning("El sal³n seleccionado es el mismo que el actual. No se realizaron cambios de matr­cula.")
                            else:
                                try:
                                    enrolls = api_get_enrollments(sid)
                                except Exception:
                                    enrolls = []
                                active = None
                                for e in enrolls:
                                    if not e.get("end_date"):
                                        active = e
                                        break
                                if active:
                                    # cerrar matr­cula activa un d­a antes del nuevo inicio
                                    end_day = (start_d or date.today()) - timedelta(days=1)
                                    api_patch_enrollment(active.get("id"), {"end_date": end_day.isoformat()})
                                api_post_enrollment(sid, selected_room_id, start_d)
                        st.success("Alumno actualizado")
                        # limpiar cache para reflejar cambios al volver
                        try:
                            if 'admin_students_cache' in st.session_state:
                                del st.session_state['admin_students_cache']
                        except Exception:
                            pass
                        go_back()
                    else:
                        st.error(str(data))


if __name__ == "__main__":
    main()


