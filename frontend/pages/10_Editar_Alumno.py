import os
import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get(path):
    r = requests.get(f"{API_URL}{path}", headers=auth_headers(), timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_get_student(student_id):
    r = requests.get(
        f"{API_URL}/students/{student_id}/",
        headers=auth_headers(),
        timeout=20
    )
    r.raise_for_status()
    return r.json()


def api_patch_student(student_id, payload):
    r = requests.patch(
        f"{API_URL}/students/{student_id}/",
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
        page_title="Editar alumno",
        page_icon="🎓",
        layout="wide"
    )

    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    student_id = st.session_state.get("selected_student_id")

    if not student_id:
        st.warning("No se ha seleccionado un alumno.")
        if st.button("Volver"):
            go_back()
        return

    try:
        student = api_get_student(student_id)
    except Exception as e:
        st.error(f"No se pudo cargar la información del alumno: {e}")
        return

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
                step=1
            )

        with c2:
            gender = st.selectbox(
                "Género",
                options=gender_options,
                index=gender_index,
                format_func=lambda x: {
                    "": "Seleccione",
                    "M": "Masculino",
                    "F": "Femenino"
                }.get(x, x)
            )

        c_cancel, c_save = st.columns([1, 1])

        cancel = c_cancel.form_submit_button(
            "Cancelar",
            type="secondary",
            use_container_width=True
        )

        save = c_save.form_submit_button(
            "Guardar cambios",
            type="primary",
            use_container_width=True
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
            ok, data = api_patch_student(student_id, payload)

        if not ok:
            if isinstance(data, dict):
                for k, v in data.items():
                    st.error(f"{k}: {v}")
            else:
                st.error(str(data))
            return

        st.session_state.pop("admin_students_cache", None)
        st.session_state.pop("enrollment_cache", None)
        st.session_state["force_refresh_students"] = True

        st.success("Alumno actualizado correctamente.")
        go_back()


if __name__ == "__main__":
    main()