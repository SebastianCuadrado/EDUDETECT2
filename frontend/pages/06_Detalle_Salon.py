import os
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
    return r.json()


def api_get_all(path, params=None):
    url = f"{API_URL}{path}"
    out = []
    while url:
        r = requests.get(url, headers=auth_headers(), params=params if url.endswith(path) else None, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "results" in data:
            out.extend(data["results"])
            url = data.get("next")
        else:
            out.extend(data)
            url = None
    return out


def main():
    st.set_page_config(page_title="Detalle del salón", page_icon="🏫", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    room_id = st.session_state.get("selected_room_id")
    if not room_id:
        st.warning("No se ha seleccionado un salón. Volviendo...")
        try:
            if hasattr(st, 'switch_page'):
                st.switch_page('pages/05_Administrar_Salones.py')
                return
        except Exception:
            pass
        st.stop()

    # Botón volver (arriba a la derecha)
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button(" Volver"):
            try:
                if hasattr(st, 'switch_page'):
                    st.switch_page('pages/05_Administrar_Salones.py')
                    return
            except Exception:
                pass
            st.stop()

    # Cargar info
    room = api_get(f"/classrooms/{room_id}/")
    label = room.get('name') or f"{room.get('academic_year')} - {room.get('grade')}{room.get('section')}"
    st.title(label)
    st.caption(f"Año: {room.get('academic_year')} · Grado: {room.get('grade')} · Sección: {room.get('section')}")

    assigns = api_get_all("/teacher-assignments/", params={"classroom": room_id})
    enrolls = api_get_all("/enrollments/", params={"classroom": room_id})

    # Bloques lado a lado
    left, right = st.columns(2)

    with left:
        st.subheader("Profesores")
        if not assigns:
            st.write("Sin profesores asignados")
        else:
            for a in assigns:
                try:
                    u = api_get(f"/users/{a.get('teacher')}/")
                    st.write(f"- {u.get('username')} ({u.get('first_name','')} {u.get('last_name','')}) · {a.get('role')}")
                except Exception:
                    st.write(f"- ID {a.get('teacher')} · {a.get('role')}")

    with right:
        st.subheader("Alumnos")
        if not enrolls:
            st.write("Sin alumnos matriculados")
        else:
            for e in enrolls[:50]:
                try:
                    s = api_get(f"/students/{e.get('student')}/")
                    st.write(f"- {s.get('first_name','')} {s.get('last_name','')} (DNI {s.get('dni','')})")
                except Exception:
                    st.write(f"- ID {e.get('student')}")
            if len(enrolls) > 50:
                st.caption(f" y {len(enrolls)-50} más")


if __name__ == "__main__":
    main()

