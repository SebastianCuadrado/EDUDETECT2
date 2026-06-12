import os
import re
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
        r = requests.get(
            url,
            headers=auth_headers(),
            params=params if url.endswith(path) else None,
            timeout=20,
        )
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
        f"{API_URL}{path}",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if r.status_code in (200, 201):
        return True, r.json()

    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


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


def api_delete(path):
    r = requests.delete(
        f"{API_URL}{path}",
        headers=auth_headers(),
        timeout=20,
    )

    return r.status_code in (204, 200), (
        r.text if r.status_code not in (204, 200) else ""
    )


def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


def inject_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1280px;
            padding-top: 1.5rem;
            padding-bottom: 1rem;
        }
        div[data-testid="stTextInput"] input {
            border-radius: 14px !important;
            min-height: 48px !important;
        }
        .stButton > button {
            border-radius: 12px !important;
            min-height: 44px !important;
            font-weight: 600 !important;
        }
        .new-room-wrap .stButton > button {
            min-height: 46px !important;
            font-size: 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("Confirmar eliminación")
def modal_confirmar_eliminar_salon():
    rid = st.session_state.get("confirm_delete_room_id")
    nombre = st.session_state.get("confirm_delete_room_name", "este salón")

    st.warning(f"¿Estás seguro de que deseas eliminar **{nombre}**?")
    st.caption("Esta acción no se puede deshacer.")

    col1, col2 = st.columns(2)

    if col1.button("Eliminar de todos modos", type="primary", use_container_width=True):
        ok, msg = api_delete(f"/classrooms/{rid}/")

        if ok:
            st.success("Salón eliminado")
        else:
            st.error(msg)

        st.session_state.pop("confirm_delete_room_id", None)
        st.session_state.pop("confirm_delete_room_name", None)
        _safe_rerun()

    if col2.button("Cancelar", use_container_width=True):
        st.session_state.pop("confirm_delete_room_id", None)
        st.session_state.pop("confirm_delete_room_name", None)
        _safe_rerun()


@st.dialog("Nuevo salón")
def modal_crear_salon():
    c1, c2, c3 = st.columns(3)

    with c1:
        year = st.number_input(
            "Año *",
            min_value=2000,
            max_value=2100,
            value=None,
            step=1,
            placeholder="Ej: 2025",
        )

    with c2:
        grade = st.number_input(
            "Grado *",
            min_value=1,
            max_value=12,
            value=None,
            step=1,
            placeholder="1 – 12",
        )

    with c3:
        section = st.text_input("Sección *", value="", max_chars=2, placeholder="Ej: A")

    name = st.text_input("Nombre del salón *", value="", max_chars=100, placeholder="Ej: Aula 3A")

    col_crear, col_cancelar = st.columns(2)

    if col_crear.button("Crear", type="primary", use_container_width=True):
        errors = []
        if year is None:
            errors.append("El campo **Año** no puede estar vacío.")
        elif int(year) < date.today().year:
            errors.append("El año académico no puede ser anterior al año actual.")
        if grade is None:
            errors.append("El campo **Grado** no puede estar vacío.")

        if not section.strip():
            errors.append("El campo **Sección** no puede estar vacío.")
        elif not re.match(r"^[a-zA-Z0-9]+$", section.strip()):
            errors.append("La sección solo debe contener letras y números.")

        if not name.strip():
            errors.append("El campo **Nombre del salón** no puede estar vacío.")
        elif not re.search(r"[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]", name.strip()):
            errors.append(
                "El nombre del salón debe contener al menos una letra y no puede estar compuesto solo por números o caracteres especiales."
            )

        if errors:
            for err in errors:
                st.error(err)
            return

        ok, data = api_post(
            "/classrooms/",
            {
                "name": name.strip(),
                "academic_year": int(year),
                "grade": int(grade),
                "section": section.strip().upper(),
                "school": SCHOOL_NAME,
            },
        )

        if ok:
            st.success("Salón creado correctamente")
            st.session_state.show_create_room = False
            st.session_state["rooms_page"] = 1
            _safe_rerun()
        else:
            st.error(str(data))

    if col_cancelar.button("Cancelar", use_container_width=True):
        st.session_state.show_create_room = False
        _safe_rerun()


def main():
    st.set_page_config(
        page_title="Salones",
        page_icon="🏫",
        layout="wide",
    )

    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    st.markdown(
        '<div class="page-title">Administrar salones</div>',
        unsafe_allow_html=True,
    )

    search_col, btn_col = st.columns([5, 1], gap="small")

    with search_col:
        q = st.text_input(
            label="",
            placeholder="Buscar por sección, grado o año",
            label_visibility="collapsed",
        )

    with btn_col:
        st.button("Buscar", use_container_width=True)

    prev_q = st.session_state.get("last_rooms_query")

    if prev_q != q:
        st.session_state["last_rooms_query"] = q
        st.session_state["rooms_page"] = 1

    rooms = api_get_all("/classrooms/", params={"search": q or None})

    if "show_create_room" not in st.session_state:
        st.session_state.show_create_room = False

    if "edit_room" not in st.session_state:
        st.session_state.edit_room = None

    title_col, new_col = st.columns([4, 1])

    with title_col:
        st.markdown(
            '<div class="section-title">Lista de salones</div>',
            unsafe_allow_html=True,
        )

    with new_col:
        st.markdown('<div class="new-room-wrap">', unsafe_allow_html=True)

        if st.button("➕ Nuevo salón", type="primary", use_container_width=True):
            modal_crear_salon()

        st.markdown("</div>", unsafe_allow_html=True)

    if not rooms:
        st.info("No hay salones para mostrar.")
        return

    paged_rooms, _, _, _ = paginate_list(
        rooms,
        "rooms_page",
        page_size=6,
    )

    cols = st.columns(3, gap="large")
    idx = 0

    for r in paged_rooms:
        with cols[idx]:
            with st.container(border=True):
                rid = r.get("id")
                name = (r.get("name") or "").strip()
                computed_label = f"{r.get('academic_year')} - {r.get('grade')}{r.get('section')}"

                if name:
                    st.markdown(f"### {name}")
                else:
                    st.markdown("### Nombre del salón")

                st.markdown(f"**{computed_label}**")
                st.caption(f"Grado: {r.get('grade')} | Sección: {r.get('section')}")

                c1, c2, c3 = st.columns(3)

                if c1.button("Detalle", key=f"room_detail_{rid}", use_container_width=True):
                    st.session_state.selected_room_id = rid

                    try:
                        import streamlit as _st

                        if hasattr(_st, "switch_page"):
                            _st.switch_page("pages/06_Detalle_Salon.py")
                        else:
                            _safe_rerun()
                    except Exception:
                        _safe_rerun()

                if c2.button("Editar", key=f"room_edit_{rid}", use_container_width=True):
                    st.session_state.selected_room_id = rid

                    try:
                        import streamlit as _st

                        if hasattr(_st, "switch_page"):
                            _st.switch_page("pages/09_Editar_Salon.py")
                        else:
                            _safe_rerun()
                    except Exception:
                        _safe_rerun()

                if c3.button("Eliminar", key=f"room_del_{rid}", use_container_width=True):
                    st.session_state.confirm_delete_room_id = rid
                    nombre_salon = (
                        (r.get("name") or "").strip()
                        or f"{r.get('academic_year')} - {r.get('grade')}{r.get('section')}"
                    )
                    st.session_state.confirm_delete_room_name = nombre_salon
                    _safe_rerun()

        idx = (idx + 1) % 3

    if "confirm_delete_room_id" in st.session_state:
        modal_confirmar_eliminar_salon()

    edit_data = st.session_state.get("edit_room")

    if edit_data:
        st.markdown("---")
        st.subheader("Editar salón")

        with st.form("edit_room_form", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)

            with c1:
                year = st.number_input(
                    "Año",
                    min_value=2000,
                    max_value=2100,
                    value=int(edit_data.get("academic_year") or date.today().year),
                    step=1,
                )

            with c2:
                grade = st.number_input(
                    "Grado",
                    min_value=1,
                    max_value=12,
                    value=int(edit_data.get("grade") or 1),
                    step=1,
                )

            with c3:
                section = st.text_input(
                    "Sección",
                    value=edit_data.get("section") or "",
                    max_chars=2,
                )

            name = st.text_input("Nombre", value=edit_data.get("name") or "")

            csave, ccancel = st.columns([1, 1])

            save = csave.form_submit_button("Guardar cambios")
            cancel = ccancel.form_submit_button("Cancelar")

        if cancel:
            st.session_state.pop("edit_room", None)
            _safe_rerun()

        if save:
            errors = []
            if int(year) < date.today().year:
                errors.append("El año académico no puede ser anterior al año actual.")

            if not section.strip():
                errors.append("El campo **Sección** no puede estar vacío.")
            elif not re.match(r"^[a-zA-Z0-9]+$", section.strip()):
                errors.append("La sección solo debe contener letras y números.")

            if not name.strip():
                errors.append("El campo **Nombre del salón** no puede estar vacío.")
            elif not re.search(r"[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]", name.strip()):
                errors.append(
                    "El nombre del salón debe contener al menos una letra y no puede estar compuesto solo por números o caracteres especiales."
                )

            if errors:
                for err in errors:
                    st.error(err)
            else:
                payload = {
                    "academic_year": int(year),
                    "grade": int(grade),
                    "section": section.strip().upper(),
                    "name": name.strip(),
                }

                ok, data = api_patch(f"/classrooms/{edit_data.get('id')}/", payload)

                if ok:
                    st.success("Salón actualizado")
                    st.session_state.pop("edit_room", None)
                    _safe_rerun()
                else:
                    st.error(str(data))


if __name__ == "__main__":
    main()