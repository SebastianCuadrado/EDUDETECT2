import os
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get_user(user_id: int):
    r = requests.get(f"{API_URL}/users/{user_id}/", headers=auth_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def api_patch_user(user_id: int, payload: dict):
    r = requests.patch(
        f"{API_URL}/users/{user_id}/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return (
        r.status_code in (200, 202),
        r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
    )


def api_get_classrooms():
    r = requests.get(f"{API_URL}/classrooms/", headers=auth_headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_get_assignments(teacher_id: int):
    r = requests.get(
        f"{API_URL}/teacher-assignments/",
        headers=auth_headers(),
        params={"teacher": teacher_id},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)


def api_post_assignment(teacher_id: int, classroom_id: int, role: str = "TITULAR", start_date: date | None = None):
    payload = {
        "teacher": teacher_id,
        "classroom": classroom_id,
        "role": role,
        "start_date": start_date.isoformat() if start_date else None,
    }
    r = requests.post(
        f"{API_URL}/teacher-assignments/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return r.status_code in (200, 201)


def api_patch_assignment(assignment_id: int, payload: dict):
    r = requests.patch(
        f"{API_URL}/teacher-assignments/{assignment_id}/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return r.status_code in (200, 202)


def api_delete_assignment(assignment_id: int):
    r = requests.delete(
        f"{API_URL}/teacher-assignments/{assignment_id}/",
        headers=auth_headers(),
        timeout=15,
    )
    return r.status_code in (204, 200)


def go_back():
    st.session_state.pop("edit_user_role", None)
    st.session_state.pop("edit_user_active", None)
    st.session_state["staged_assignments"] = []
    try:
        if hasattr(st, "switch_page"):
            st.switch_page("pages/01_Lista_de_Usuarios.py")
            return
    except Exception:
        pass
    st.stop()


def inject_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1320px;
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }

        .section-card {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 16px 16px 8px 16px;
            margin-bottom: 18px;
            background: rgba(255,255,255,0.01);
        }

        .section-title {
            font-size: 1.6rem;
            font-weight: 800;
            color: #f8fafc;
            margin: 0 0 0.75rem 0;
        }

        .section-subtitle {
            color: #94a3b8;
            font-size: 0.96rem;
            margin-bottom: 0.9rem;
        }

        .mini-title {
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 700;
            margin: 0.3rem 0 0.7rem 0;
        }

        .footer-actions {
            margin-top: 0.8rem;
        }

        .footer-actions .stButton > button,
        .footer-actions .stFormSubmitButton > button {
            min-height: 46px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }

        div[data-testid="stCheckbox"] {
            margin-top: 1.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Editar usuario", page_icon="👤", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    uid = st.session_state.get("selected_user_id")
    if not uid:
        st.error("No se encontró un usuario seleccionado para editar.")
        go_back()
        return

    try:
        user = api_get_user(uid)
    except Exception as e:
        st.error(f"No se pudo cargar el usuario: {e}")
        go_back()
        return

    if "staged_assignments" not in st.session_state:
        st.session_state.staged_assignments = []

    if "edit_user_role" not in st.session_state:
        st.session_state.edit_user_role = user.get("role") or "DOCENTE"

    if "edit_user_active" not in st.session_state:
        st.session_state.edit_user_active = bool(user.get("is_active", True))

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Volver",type="primary"):
            go_back()

    st.title(f"Editar: {user.get('username')}")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Rol y estado</div>', unsafe_allow_html=True)

    rc1, rc2 = st.columns([2, 1])

    with rc1:
        role = st.selectbox(
            "Rol",
            options=["ADMIN", "DOCENTE"],
            key="edit_user_role",
        )

    with rc2:
        is_active = st.checkbox("Activo", key="edit_user_active")

    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("edit_user_form", clear_on_submit=False):
        st.markdown('<div class="section-title">Información del usuario</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        with c1:
            username = st.text_input("Usuario", value=user.get("username") or "")
            first_name = st.text_input("Nombres", value=user.get("first_name") or "")
            last_name = st.text_input("Apellidos", value=user.get("last_name") or "")

        with c2:
            email = st.text_input("Correo", value=user.get("email") or "")
            dni = st.text_input("DNI", value=user.get("dni") or "")
            phone = st.text_input("Telefono", value=user.get("phone") or "")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">Acceso</div>', unsafe_allow_html=True)
        password = st.text_input("Contrasena (opcional)", type="password")
        st.markdown("</div>", unsafe_allow_html=True)

        sel_room_id = None
        teacher_role = "TITULAR"
        start_d = None

        if role == "DOCENTE":
            st.markdown("---")
            st.markdown('<div class="section-title">Asignacion a salon</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-subtitle">Gestiona las asignaciones actuales y agrega nuevas asignaciones para este docente.</div>',
                unsafe_allow_html=True,
            )

            try:
                rooms = api_get_classrooms()
            except Exception as e:
                rooms = []
                st.error(f"No se pudieron cargar los salones: {e}")

            room_map = {}
            for c in rooms:
                rid = c.get("id")
                label = f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}"
                if c.get("name"):
                    label = f"{c.get('name')} ({label})"
                room_map[rid] = label

            try:
                current = api_get_assignments(uid)
            except Exception:
                current = []

            if current:
                st.markdown('<div class="mini-title">Asignaciones existentes</div>', unsafe_allow_html=True)

                for a in current:
                    aid = a.get("id")
                    with st.container(border=True):
                        cc1, cc2, cc3, cc4 = st.columns([2.3, 1.3, 1.3, 1])
                        cid = a.get("classroom")

                        cc1.markdown(f"**{room_map.get(cid) or f'Aula ID {cid}'}**")

                        cc2.selectbox(
                            "Rol",
                            ["TITULAR", "APOYO"],
                            index=0 if a.get("role") == "TITULAR" else 1,
                            key=f"ass_role_{aid}",
                        )

                        try:
                            sdate = a.get("start_date")
                            parsed = date.fromisoformat(sdate) if sdate else None
                        except Exception:
                            parsed = None

                        st_key = f"ass_start_{aid}"
                        current_val = st.session_state.get(st_key, parsed)
                        cc3.date_input("Inicio", value=current_val, key=st_key)
                        cc4.checkbox("Eliminar", key=f"ass_del_{aid}")

            staged = st.session_state.get("staged_assignments", [])
            if staged:
                st.markdown('<div class="mini-title">Nuevas asignaciones pendientes</div>', unsafe_allow_html=True)
                for i, a in enumerate(staged, start=1):
                    room_label = room_map.get(a["classroom"], f"Aula ID {a['classroom']}")
                    st.caption(f"{i}. {room_label} · Rol {a['role']} · Inicio {a.get('start_date') or '-'}")

            st.markdown('<div class="mini-title">Agregar asignación</div>', unsafe_allow_html=True)

            room_opts = [
                (c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}")
                for c in rooms
            ]

            a1, a2, a3, a4 = st.columns([2.2, 1.5, 1.5, 0.8])

            with a1:
                if room_opts:
                    ridx = st.selectbox(
                        "Salon",
                        options=list(range(len(room_opts))),
                        format_func=lambda i: room_opts[i][1],
                    )
                    sel_room_id = room_opts[ridx][0]
                else:
                    st.selectbox("Salon", options=[], disabled=True)

            with a2:
                teacher_role = st.selectbox("Rol en el salon", options=["TITULAR", "APOYO"], index=0)

            with a3:
                start_d = st.date_input("Inicio (opcional)", value=None)

            with a4:
                st.write("")
                st.write("")
                add_btn = st.form_submit_button("Asignar", use_container_width=True)

            if add_btn and sel_room_id:
                staged.append(
                    {
                        "classroom": sel_room_id,
                        "role": teacher_role,
                        "start_date": start_d.isoformat() if start_d else None,
                    }
                )
                st.session_state.staged_assignments = staged
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="footer-actions">', unsafe_allow_html=True)
        ccancel, csave = st.columns([1, 1])

        cancel = ccancel.form_submit_button("Cancelar", type="secondary", use_container_width=True)
        save = csave.form_submit_button("Guardar cambios", type="primary", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    if cancel:
        go_back()

    if save:
        payload = {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "dni": dni,
            "role": role,
            "is_active": is_active,
        }

        if password:
            payload["password"] = password

        ok, data = api_patch_user(uid, payload)

        if not ok:
            st.error(str(data))
            return

        if role == "DOCENTE":
            try:
                current = api_get_assignments(uid)
            except Exception:
                current = []

            for a in current:
                aid = a.get("id")

                if st.session_state.get(f"ass_del_{aid}"):
                    api_delete_assignment(aid)
                else:
                    new_role = st.session_state.get(f"ass_role_{aid}") or a.get("role")
                    new_start = st.session_state.get(f"ass_start_{aid}")
                    if hasattr(new_start, "isoformat"):
                        new_start = new_start.isoformat()

                    if new_role != a.get("role") or (new_start or None) != (a.get("start_date") or None):
                        api_patch_assignment(aid, {"role": new_role, "start_date": new_start})

            for a in st.session_state.get("staged_assignments", []):
                api_post_assignment(
                    uid,
                    a["classroom"],
                    a.get("role", "TITULAR"),
                    date.fromisoformat(a["start_date"]) if a.get("start_date") else None,
                )

        st.success("Usuario actualizado")
        st.session_state["force_refresh_users"] = True
        go_back()


if __name__ == "__main__":
    main()