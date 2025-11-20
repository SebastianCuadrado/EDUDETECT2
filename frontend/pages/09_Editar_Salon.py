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


def _safe_go_back():
    try:
        if hasattr(st, 'switch_page'):
            st.switch_page('pages/05_Administrar_Salones.py')
            return
    except Exception:
        pass
    st.stop()


def main():
    st.set_page_config(page_title="Editar salÃ³n", page_icon="âœï¸", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    room_id = st.session_state.get("selected_room_id")
    if not room_id:
        st.warning("No se ha seleccionado un salÃ³n.")
        _safe_go_back()

    # BotÃ³n volver
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("â† Volver"):
            _safe_go_back()

    # Cargar datos actuales
    try:
        room = api_get(f"/classrooms/{room_id}/")
    except Exception as e:
        st.error(f"No se pudo cargar el salÃ³n: {e}")
        _safe_go_back()
        return

    label = room.get('name') or f"{room.get('academic_year')} - {room.get('grade')}{room.get('section')}"
    st.title(f"Editar: {label}")
    st.caption("Modifica los campos y guarda los cambios.")

    with st.form("edit_room_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            year = st.number_input(
                "AÃ±o",
                min_value=2000,
                max_value=2100,
                value=int(room.get('academic_year') or date.today().year),
                step=1,
            )
        with c2:
            grade = st.number_input("Grado", min_value=1, max_value=12, value=int(room.get('grade') or 1), step=1)
        with c3:
            section = st.text_input("SecciÃ³n", value=room.get('section') or "", max_chars=2)
        name = st.text_input("Nombre del salÃ³n", value=room.get('name') or "")
        csave, ccancel = st.columns([1, 1])
        save = csave.form_submit_button("Guardar cambios", type="primary")
        cancel = ccancel.form_submit_button("Cancelar", type="secondary")

    if cancel:
        _safe_go_back()

    if save:
        payload = {
            "academic_year": int(year),
            "grade": int(grade),
            "section": section,
            "name": name,
        }
        with st.spinner("Guardando..."):
            ok, data = api_patch(f"/classrooms/{room_id}/", payload)
            if ok:
                st.success("SalÃ³n actualizado correctamente")
                _safe_go_back()
            else:
                if isinstance(data, dict):
                    for k, v in data.items():
                        st.error(f"{k}: {v}")
                else:
                    st.error(str(data))


if __name__ == "__main__":
    main()


