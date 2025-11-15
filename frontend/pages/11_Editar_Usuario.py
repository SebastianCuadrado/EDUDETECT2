import os
import requests
import streamlit as st
from datetime import date

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
    return (r.status_code in (200, 202)), (r.json() if r.headers.get('content-type','').startswith('application/json') else r.text)


def api_post_user(payload: dict):
    r = requests.post(
        f"{API_URL}/users/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return (r.status_code in (200, 201)), (r.json() if r.headers.get('content-type','').startswith('application/json') else r.text)


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
    r = requests.delete(f"{API_URL}/teacher-assignments/{assignment_id}/", headers=auth_headers(), timeout=15)
    return r.status_code in (204, 200)


def go_back():
    try:
        if hasattr(st, 'switch_page'):
            st.switch_page('pages/01_Lista_de_Usuarios.py')
            return
    except Exception:
        pass
    st.stop()


def main():
    st.set_page_config(page_title="Usuario", page_icon="ðŸ‘¤", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    create_mode = bool(st.session_state.get("user_create_mode"))
    uid = st.session_state.get("selected_user_id")

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("â† Volver"):
            st.session_state.user_create_mode = False
            st.session_state.selected_user_id = None
            go_back()

    user = {}
    if not create_mode:
        if not uid:
            go_back()
            return
        try:
            user = api_get_user(uid)
        except Exception as e:
            st.error(f"No se pudo cargar el usuario: {e}")
            go_back()
            return
        st.title(f"Editar: {user.get('username')}")
    else:
        st.title("Nuevo usuario")

    # staging assignments list
    if "staged_assignments" not in st.session_state:
        st.session_state.staged_assignments = []

    with st.form("user_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Usuario" + ("*" if create_mode else ""), value=user.get("username") or "")
            first_name = st.text_input("Nombres" + ("*" if create_mode else ""), value=user.get("first_name") or "")
            last_name = st.text_input("Apellidos", value=user.get("last_name") or "")
            phone = st.text_input("Telefono", value=user.get("phone") or "")
        with c2:
            email = st.text_input("Correo" + ("*" if create_mode else ""), value=user.get("email") or "")
            dni = st.text_input("DNI" + ("*" if create_mode else ""), value=user.get("dni") or "")
            role = st.selectbox("Rol", options=["ADMIN", "DOCENTE"], index=0 if (user.get("role") or "DOCENTE")=="ADMIN" else 1)
            is_active = st.checkbox("Activo", value=bool(user.get("is_active", True)))
        password = st.text_input("Contrasena" + ("*" if create_mode else " (opcional)"), type="password")

        sel_room_id = None
        teacher_role = "TITULAR"
        start_d = None
        assign_changes = {}
        assign_deletes = set()

        if role == "DOCENTE":
            st.markdown("---")
            st.subheader("Asignacion a salon")

            # Existing assignments (edit): allow change or delete
            if not create_mode and uid:
                try:
                    current = api_get_assignments(uid)
                except Exception:
                    current = []
                if current:
                    st.caption("Asignaciones existentes:")
                    for a in current:
                        aid = a.get('id')
                        with st.container(border=True):
                            cc1, cc2, cc3, cc4 = st.columns([2, 1.2, 1.2, 1])
                            cc1.write(f"Aula ID {a.get('classroom')}")
                            new_role = cc2.selectbox("Rol", ["TITULAR", "APOYO"], index=0 if a.get('role')=='TITULAR' else 1, key=f"ass_role_{aid}")
                            try:
                                sdate = a.get('start_date')
                                parsed = date.fromisoformat(sdate) if sdate else None
                            except Exception:
                                parsed = None
                            new_start = cc3.date_input("Inicio", value=parsed, key=f"ass_start_{aid}")
                            to_del = cc4.checkbox("Eliminar", key=f"ass_del_{aid}")
                            assign_changes[aid] = {"role": new_role, "start_date": new_start}
                            if to_del:
                                assign_deletes.add(aid)

            # Staged adds
            staged = st.session_state.get("staged_assignments", [])
            if staged:
                st.caption("Nuevas asignaciones (pendientes de guardar):")
                for i, a in enumerate(staged, start=1):
                    st.write(f"{i}. Aula ID {a['classroom']} Â· Rol {a['role']} Â· Inicio {a.get('start_date') or '-'}")

            rooms = api_get_classrooms()
            room_opts = [(c.get("id"), f"{c.get('academic_year')} - {c.get('grade')}{c.get('section')}") for c in rooms]
            if room_opts:
                ridx = st.selectbox("Salon", options=list(range(len(room_opts))), format_func=lambda i: room_opts[i][1])
                sel_room_id = room_opts[ridx][0]
            teacher_role = st.selectbox("Rol en el salon", options=["TITULAR", "APOYO"], index=0)
            start_d = st.date_input("Inicio (opcional)", value=None)
            add_btn = st.form_submit_button("Asignar")
            if add_btn and sel_room_id:
                staged.append({
                    "classroom": sel_room_id,
                    "role": teacher_role,
                    "start_date": start_d.isoformat() if start_d else None,
                })
                st.session_state.staged_assignments = staged
                try:
                    st.rerun()
                except Exception:
                    pass

        csave, ccancel = st.columns([1, 1])
        save = csave.form_submit_button("Registrar" if create_mode else "Guardar cambios")
        cancel = ccancel.form_submit_button("Cancelar")

    if cancel:
        st.session_state.user_create_mode = False
        st.session_state.selected_user_id = None
        st.session_state.staged_assignments = []
        go_back()

    if save:
        if create_mode and not all([username, first_name, email, dni, password]):
            st.error("Completa los campos obligatorios (*)")
        else:
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

            if create_mode:
                ok, data = api_post_user(payload)
                if ok:
                    new_uid = data.get("id")
                    if new_uid and role == "DOCENTE":
                        for a in st.session_state.get("staged_assignments", []):
                            api_post_assignment(new_uid, a["classroom"], a.get("role", "TITULAR"), date.fromisoformat(a["start_date"]) if a.get("start_date") else None)
                    st.success("Usuario creado")
                    st.session_state.user_create_mode = False
                    st.session_state.selected_user_id = None
                    st.session_state.staged_assignments = []
                    go_back()
                else:
                    st.error(str(data))
            else:
                ok, data = api_patch_user(uid, payload)
                if ok:
                    if role == "DOCENTE":
                        # apply deletes / updates
                        try:
                            current = api_get_assignments(uid)
                        except Exception:
                            current = []
                        for a in current:
                            aid = a.get('id')
                            if st.session_state.get(f"ass_del_{aid}"):
                                api_delete_assignment(aid)
                            else:
                                new_role = st.session_state.get(f"ass_role_{aid}") or a.get('role')
                                new_start = st.session_state.get(f"ass_start_{aid}")
                                if hasattr(new_start, 'isoformat'):
                                    new_start = new_start.isoformat()
                                if new_role != a.get('role') or (new_start or None) != (a.get('start_date') or None):
                                    api_patch_assignment(aid, {"role": new_role, "start_date": new_start})
                        # create staged
                        for a in st.session_state.get("staged_assignments", []):
                            api_post_assignment(uid, a["classroom"], a.get("role", "TITULAR"), date.fromisoformat(a["start_date"]) if a.get("start_date") else None)
                    st.success("Usuario actualizado")
                    st.session_state.staged_assignments = []
                    go_back()
                else:
                    st.error(str(data))


if __name__ == "__main__":
    main()


