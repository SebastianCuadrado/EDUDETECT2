import os
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            try:
                st.experimental_rerun()
            except Exception:
                pass


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def fetch_students(query=None, year=None, grade=None, section=None):
    try:
        params = {}
        if query:
            params["search"] = query
        if year:
            params["year"] = year
        if grade:
            params["grade"] = grade
        if section:
            params["section"] = section
        r = requests.get(f"{API_URL}/students/", headers=auth_headers(), params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudo cargar alumnos: {e}")
        return []


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", headers=auth_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def create_student(payload: dict, photo_file=None):
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


def update_student(student_id: int, payload: dict, photo_file=None):
    url = f"{API_URL}/students/{student_id}/"
    if photo_file is not None:
        files = {
            "photo": (
                getattr(photo_file, "name", "photo.jpg"),
                photo_file.getvalue(),
                getattr(photo_file, "type", "application/octet-stream"),
            )
        }
        data = {k: v for k, v in payload.items() if v is not None}
        r = requests.patch(url, headers=auth_headers(), data=data, files=files, timeout=20)
    else:
        r = requests.patch(url, headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20)
    if r.status_code in (200, 202):
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
        timeout=15,
    )
    return r.status_code in (200, 201)


def delete_student(student_id: int):
    r = requests.delete(f"{API_URL}/students/{student_id}/", headers=auth_headers(), timeout=15)
    return r.status_code in (204, 200), r.text


def main():
    st.set_page_config(page_title="Gestión de Alumnos", page_icon="📚", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    st.title("Gestión de Alumnos")

    # Filtros
    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
    query = c1.text_input("Buscar", placeholder="nombre, apellido, DNI, email")
    y = c2.number_input("Año", min_value=2000, max_value=2100, value=date.today().year, step=1)
    g = c3.number_input("Grado", min_value=1, max_value=12, value=1, step=1)
    s = c4.text_input("Sección", max_chars=2, value="A")
    do = c5.button("Filtrar")

    if do or "admin_students_cache" not in st.session_state:
        st.session_state.admin_students_cache = fetch_students(query, y, g, s)
    students = st.session_state.get("admin_students_cache", [])

    # Botón crear
    st.markdown("---")
    if "show_create_student" not in st.session_state:
        st.session_state.show_create_student = False
    new_col, _ = st.columns([1, 6])
    if new_col.button("Nuevo alumno"):
        st.session_state.selected_student_id = None
        st.session_state.create_mode = True
        try:
            import streamlit as _st
            if hasattr(_st, 'switch_page'):
                _st.switch_page('pages/10_Editar_Alumno.py')
            else:
                _safe_rerun()
        except Exception:
            _safe_rerun()

    if st.session_state.show_create_student:
        classrooms = api_get("/classrooms/")
        room_opts = [(c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}") for c in classrooms]
        st.subheader("Registrar nuevo alumno")
        with st.form("create_student_form", clear_on_submit=False):
            a1, a2 = st.columns(2)
            with a1:
                dni = st.text_input("DNI*", max_chars=15)
                first_name = st.text_input("Nombres*")
                birth_date = st.date_input("Fecha de nacimiento", value=None)
                phone = st.text_input("Teléfono")
            with a2:
                last_name = st.text_input("Apellidos*")
                gender = st.selectbox("Género", options=["", "M", "F", "O"], index=0)
                email = st.text_input("Correo")
            st.caption("Foto (opcional)")
            photo = st.file_uploader("Selecciona una imagen", type=["png", "jpg", "jpeg"], accept_multiple_files=False)
            st.markdown("---")
            if room_opts:
                ridx = st.selectbox("Salón*", options=list(range(len(room_opts))), format_func=lambda i: room_opts[i][1])
                selected_room_id = room_opts[ridx][0]
            else:
                st.error("No hay salones creados")
                selected_room_id = None
            start_d = st.date_input("Fecha de inicio (opcional)", value=None)
            csave, ccancel = st.columns([1, 1])
            create_submit = csave.form_submit_button("Registrar")
            cancel_create = ccancel.form_submit_button("Cancelar")
        if cancel_create:
            st.session_state.show_create_student = False
            _safe_rerun()
        if create_submit:
            if not all([dni, first_name, last_name, selected_room_id]):
                st.error("Completa los campos obligatorios (*) y salón")
            else:
                payload = {
                    "dni": dni,
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": birth_date.isoformat() if birth_date else None,
                    "gender": gender or "",
                    "email": email or "",
                    "phone": phone or "",
                }
                with st.spinner("Creando alumno..."):
                    ok, data = create_student(payload, photo)
                    if ok:
                        sid = data.get("id")
                        if sid and selected_room_id:
                            enroll_student(sid, selected_room_id, start_d)
                        st.success("Alumno creado")
                        st.session_state.show_create_student = False
                        st.session_state.admin_students_cache = fetch_students(query, y, g, s)
                        _safe_rerun()
                    else:
                        st.error(str(data))

    # Listado
    st.markdown("### Lista de alumnos")
    for stu in students:
        with st.container(border=True):
            cimg, c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 1, 1])
            photo_url = stu.get("photo")
            if photo_url:
                cimg.image(photo_url, width=64)
            else:
                cimg.write("")
            c1.write(f"{stu.get('first_name','')} {stu.get('last_name','')}")
            c2.caption(f"DNI: {stu.get('dni','-')}")
            c3.caption(f"Email: {stu.get('email','-')} · Tel: {stu.get('phone','-')}")
            if c4.button("Editar", key=f"stu_edit_{stu.get('id')}"):
                st.session_state.selected_student_id = stu.get('id')
                st.session_state.create_mode = False
                try:
                    import streamlit as _st
                    if hasattr(_st, 'switch_page'):
                        _st.switch_page('pages/10_Editar_Alumno.py')
                    else:
                        _safe_rerun()
                except Exception:
                    _safe_rerun()
            if c5.button("Eliminar", key=f"stu_del_{stu.get('id')}"):
                ok, msg = delete_student(stu.get('id'))
                if ok:
                    st.success("Alumno eliminado")
                    st.session_state.admin_students_cache = [x for x in students if x.get('id') != stu.get('id')]
                    _safe_rerun()
                else:
                    st.error(msg)

    # La edición se realiza en pages/10_Editar_Alumno.py


if __name__ == "__main__":
    main()
