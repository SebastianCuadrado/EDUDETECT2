import os
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, paginate_list, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
SCHOOL_NAME = os.getenv("SCHOOL_NAME", "COLEGIO")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get_all(path, params=None):
    url = f"{API_URL}{path}"
    out = []
    while url:
        r = requests.get(url, headers=auth_headers(), params=params if url.endswith(path) else None, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "results" in data:
            out.extend(data["results"])
            url = data.get("next")
        else:
            out.extend(data)
            url = None
    return out


def api_post(path, payload):
    r = requests.post(
        f"{API_URL}{path}", headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20
    )
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def api_patch(path, payload):
    r = requests.patch(
        f"{API_URL}{path}", headers=auth_headers() | {"Content-Type": "application/json"}, json=payload, timeout=20
    )
    if r.status_code in (200, 202):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def api_delete(path):
    r = requests.delete(f"{API_URL}{path}", headers=auth_headers(), timeout=20)
    return r.status_code in (204, 200), (r.text if r.status_code not in (204, 200) else "")


def _safe_rerun():
    try:
        # Streamlit >= 1.27
        st.rerun()
    except Exception:
        try:
            # Compatibilidad con versiones anteriores
            if hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        except Exception:
            pass


def main():
    st.set_page_config(page_title="Salones", page_icon="🏫", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    st.markdown("### Administrar salones")

    q = st.text_input("Buscar salón...", placeholder="Sección, grado o año")
    prev_q = st.session_state.get("last_rooms_query")
    if prev_q != q:
        st.session_state["last_rooms_query"] = q
        st.session_state["rooms_page"] = 1
    rooms = api_get_all("/classrooms/", params={"search": q or None})
    paged_rooms, _, _, _ = paginate_list(rooms, "rooms_page", page_size=10)

    if "show_create_room" not in st.session_state:
        st.session_state.show_create_room = False
    if "edit_room" not in st.session_state:
        st.session_state.edit_room = None

    cols = st.columns(3, gap="large")
    idx = 0
    with cols[idx]:
        with st.container(border=True):
            st.markdown("### ")
            st.markdown("**Agregar salón**")
            if st.button("Nuevo salón"):
                st.session_state.show_create_room = True
                _safe_rerun()
    idx = (idx + 1) % 3

    for r in paged_rooms:
        with cols[idx]:
            with st.container(border=True):
                rid = r.get('id')
                name = (r.get('name') or "").strip()
                computed_label = f"{r.get('academic_year')} - {r.get('grade')}{r.get('section')}"
                if name:
                    st.markdown(f"**{name}**")
                    st.write(computed_label)
                else:
                    st.markdown("**Nombre del salón**")
                    st.write(computed_label)
                st.caption(f"Grado: {r.get('grade')}  |  Sección: {r.get('section')}")
                c1, c2, c3 = st.columns(3)
                if c1.button("Ver detalle", key=f"room_detail_{rid}"):
                    st.session_state.selected_room_id = rid
                    try:
                        import streamlit as _st
                        if hasattr(_st, 'switch_page'):
                            _st.switch_page('pages/06_Detalle_Salon.py')
                        else:
                            _safe_rerun()
                    except Exception:
                        _safe_rerun()
                if c2.button("Editar", key=f"room_edit_{rid}"):
                    st.session_state.selected_room_id = rid
                    try:
                        import streamlit as _st
                        if hasattr(_st, 'switch_page'):
                            _st.switch_page('pages/09_Editar_Salon.py')
                        else:
                            _safe_rerun()
                    except Exception:
                        _safe_rerun()
                if c3.button("Eliminar", key=f"room_del_{rid}"):
                    ok, msg = api_delete(f"/classrooms/{rid}/")
                    if ok:
                        st.success("Salón eliminado")
                        _safe_rerun()
                    else:
                        st.error(msg)
        idx = (idx + 1) % 3

    if st.session_state.show_create_room:
        st.markdown("---")
        st.subheader("Nuevo salón")
        c1, c2, c3 = st.columns(3)
        with c1:
            year = st.number_input("Año", min_value=2000, max_value=2100, value=date.today().year, step=1)
        with c2:
            grade = st.number_input("Grado", min_value=1, max_value=12, value=1, step=1)
        with c3:
            section = st.text_input("Sección", value="A", max_chars=2)
        name = st.text_input("Nombre del salón*", max_chars=100)
        if st.button("Guardar salón"):
            if not name.strip():
                st.error("El nombre del salón es obligatorio")
            else:
                ok, data = api_post(
                    "/classrooms/",
                    {"name": name.strip(), "academic_year": int(year), "grade": int(grade), "section": section, "school": SCHOOL_NAME},
                )
                if ok:
                    st.success("Salón creado")
                    st.session_state.show_create_room = False
                    _safe_rerun()
                else:
                    st.error(str(data))

    edit_data = st.session_state.get("edit_room")
    if edit_data:
        st.markdown("---")
        st.subheader("Editar salón")
        with st.form("edit_room_form", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                year = st.number_input("Año", min_value=2000, max_value=2100, value=int(edit_data.get('academic_year') or date.today().year), step=1)
            with c2:
                grade = st.number_input("Grado", min_value=1, max_value=12, value=int(edit_data.get('grade') or 1), step=1)
            with c3:
                section = st.text_input("Sección", value=edit_data.get('section') or "", max_chars=2)
            name = st.text_input("Nombre", value=edit_data.get('name') or "")
            csave, ccancel = st.columns([1,1])
            save = csave.form_submit_button("Guardar cambios")
            cancel = ccancel.form_submit_button("Cancelar")
        if cancel:
            st.session_state.pop("edit_room", None)
            _safe_rerun()
        if save:
            payload = {"academic_year": int(year), "grade": int(grade), "section": section, "name": name}
            ok, data = api_patch(f"/classrooms/{edit_data.get('id')}/", payload)
            if ok:
                st.success("Salón actualizado")
                st.session_state.pop("edit_room", None)
                _safe_rerun()
            else:
                st.error(str(data))


if __name__ == "__main__":
    main()
