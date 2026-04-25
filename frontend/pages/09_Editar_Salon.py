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
    r = requests.get(f"{API_URL}{path}", headers=auth_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def api_patch(path, payload):
    r = requests.patch(
        f"{API_URL}{path}",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if r.status_code in (200, 202):
        return True, r.json()

    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def go_back():
    st.session_state.pop("classrooms_cache", None)

    if hasattr(st, "switch_page"):
        st.switch_page("pages/05_Administrar_Salones.py")
    else:
        st.rerun()


def inject_styles():
    st.markdown("""
    <style>
    .main .block-container {
        max-width: 1280px;
        padding-top: 1.2rem;
        padding-bottom: 1rem;
    }

    .page-title {
        font-size: 2.6rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .page-caption {
        color: #a7adb8;
        font-size: 1rem;
        margin-bottom: 1.2rem;
    }

    .form-card {
        border: 1px solid #343946;
        border-radius: 14px;
        padding: 1.2rem;
        background-color: #0f131b;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        border-radius: 12px !important;
        min-height: 46px !important;
    }

    .stButton > button {
        min-height: 42px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
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
        page_title="Editar salón",
        page_icon="✏️",
        layout="wide"
    )

    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    room_id = st.session_state.get("selected_room_id")

    if not room_id:
        st.warning("No se ha seleccionado un salón.")
        if st.button("Volver"):
            go_back()
        return

    top_left, top_right = st.columns([6, 1])
    with top_left:
        st.title("Editar salón")

    with top_right:
        st.markdown('<div class="back-wrap">', unsafe_allow_html=True)
        if st.button("← Volver", type="primary", use_container_width=True):
            go_back()
        st.markdown("</div>", unsafe_allow_html=True)

    try:
        room = api_get(f"/classrooms/{room_id}/")
    except Exception as e:
        st.error(f"No se pudo cargar el salón: {e}")
        return

    label = room.get("name") or f"{room.get('academic_year')} - {room.get('grade')}{room.get('section')}"



    with st.form("edit_room_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)

        with c1:
            year = st.number_input(
                "Año",
                min_value=2000,
                max_value=2100,
                value=int(room.get("academic_year") or date.today().year),
                step=1,
            )

        with c2:
            grade = st.number_input(
                "Grado",
                min_value=1,
                max_value=12,
                value=int(room.get("grade") or 1),
                step=1
            )

        with c3:
            section = st.text_input(
                "Sección",
                value=room.get("section") or "",
                max_chars=2
            )

        name = st.text_input(
            "Nombre del salón",
            value=room.get("name") or ""
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
        if not section.strip():
            st.error("La sección es obligatoria.")
            return

        if not name.strip():
            st.error("El nombre del salón es obligatorio.")
            return

        payload = {
            "academic_year": int(year),
            "grade": int(grade),
            "section": section.strip().upper(),
            "name": name.strip(),
        }

        with st.spinner("Guardando cambios..."):
            ok, data = api_patch(f"/classrooms/{room_id}/", payload)

        if ok:
            st.session_state.pop("classrooms_cache", None)
            st.success("Salón actualizado correctamente.")
            go_back()
        else:
            if isinstance(data, dict):
                for k, v in data.items():
                    st.error(f"{k}: {v}")
            else:
                st.error(str(data))


if __name__ == "__main__":
    main()