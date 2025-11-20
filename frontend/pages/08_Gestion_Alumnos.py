import os
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, paginate_list, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

page_size = 10
page = st.session_state.get("page_students", 1)  # o page_users en el otro listado


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


def fetch_classroom(classroom_id: int):
    cache = st.session_state.setdefault("classroom_cache", {})
    if classroom_id in cache:
        return cache[classroom_id]
    try:
        r = requests.get(f"{API_URL}/classrooms/{classroom_id}/", headers=auth_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()
        cache[classroom_id] = data
        return data
    except Exception:
        return None


def fetch_active_classroom(student_id: int):
    cache = st.session_state.setdefault("enrollment_cache", {})
    if student_id in cache:
        return cache[student_id]
    try:
        r = requests.get(
            f"{API_URL}/enrollments/",
            headers=auth_headers(),
            params={"student": student_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        enrollments = data.get("results", data)
        active = next((e for e in enrollments if not e.get("end_date")), None)
        if not active and enrollments:
            enrollments.sort(key=lambda x: x.get("start_date") or "", reverse=True)
            active = enrollments[0]
        if active:
            cls = fetch_classroom(active.get("classroom"))
            cache[student_id] = cls
            return cls
    except Exception:
        pass
    cache[student_id] = None
    return None


def delete_student(student_id: int):
    r = requests.delete(f"{API_URL}/students/{student_id}/", headers=auth_headers(), timeout=15)
    return r.status_code in (204, 200), r.text


def main():
    st.set_page_config(page_title="Gesti\u00f3n de Alumnos", page_icon="\U0001F4DA", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    if st.session_state.pop("force_refresh_students", False):
        st.session_state.pop("admin_students_cache", None)
        _safe_rerun()

    st.title("Gesti\u00f3n de Alumnos")

    # Filtros
    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
    query = c1.text_input("Buscar", placeholder="nombre o apellido", value="")
    y = c2.number_input("A\u00f1o", min_value=2000, max_value=2100, value=date.today().year, step=1)
    g = c3.number_input("Grado", min_value=1, max_value=12, value=1, step=1)
    s = c4.text_input("Secci\u00f3n", max_chars=2, value="")
    do = c5.button("Filtrar")

    if do or "admin_students_cache" not in st.session_state:
        st.session_state.admin_students_cache = fetch_students(query, y, g, s)
        st.session_state["admin_students_page"] = 1
    students = st.session_state.get("admin_students_cache", [])

    # Crear nuevo alumno: navega a la p\u00e1gina unificada de edici\u00f3n/creaci\u00f3n
    st.markdown("---")
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

    # Listado
    st.markdown("### Lista de alumnos")
    paged_students, _, _, _ = paginate_list(students, "admin_students_page", page_size=10)
    if not students:
        st.info("No hay alumnos para mostrar.")
    for stu in paged_students:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2.5, 2.5, 1.5])
            c1.write(f"{stu.get('first_name','')} {stu.get('last_name','')}")
            age = stu.get("age")
            c2.caption(f"Edad: {'N/D' if age in (None, '') else age}  |  Género: {stu.get('gender','') or '-'}")

            cls = fetch_active_classroom(stu.get("id"))
            if cls:
                label = f"{cls.get('name','')} {cls.get('grade','')}° {cls.get('section','')}".strip()
                c3.caption(f"Salón: {label}")
            else:
                c3.caption("Salón: -")

            b1, b2 = c4.columns(2)
            if b1.button("Editar", key=f"stu_edit_{stu.get('id')}"):
                st.session_state.selected_student_id = stu.get("id")
                st.session_state.create_mode = False
                try:
                    import streamlit as _st
                    if hasattr(_st, "switch_page"):
                        _st.switch_page("pages/10_Editar_Alumno.py")
                    else:
                        _safe_rerun()
                except Exception:
                    _safe_rerun()

            if b2.button("Eliminar", key=f"stu_del_{stu.get('id')}"):
                ok, msg = delete_student(stu.get("id"))
                if ok:
                    st.success("Alumno eliminado")
                    st.session_state["force_refresh_students"] = True
                    st.session_state["admin_students_page"] = 1
                    st.session_state.pop("admin_students_cache", None)
                    _safe_rerun()
                else:
                    st.error(msg)


if __name__ == "__main__":
    main()
