import os
import requests
import streamlit as st

from ui_common import ensure_auth, paginate_list, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def fetch_users(query: str | None = None):
    try:
        params = {"search": query} if query else None
        r = requests.get(f"{API_URL}/users/", headers=auth_headers(), params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudo cargar usuarios: {e}")
        return []


def fetch_assignments_count(user_ids: list[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for uid in user_ids:
        try:
            r = requests.get(
                f"{API_URL}/teacher-assignments/",
                headers=auth_headers(),
                params={"teacher": uid},
                timeout=12,
            )
            if r.status_code == 200:
                data = r.json()
                items = data.get("results", data)
                counts[uid] = len(items) if isinstance(items, list) else 0
            else:
                counts[uid] = 0
        except Exception:
            counts[uid] = 0
    return counts


def delete_user(user_id: int) -> bool:
    try:
        r = requests.delete(f"{API_URL}/users/{user_id}/", headers=auth_headers(), timeout=12)
        if r.status_code in (204, 200):
            st.success("Usuario eliminado")
            return True
        st.error(f"Error {r.status_code}: {r.text}")
        return False
    except Exception as e:
        st.error(f"Error de red: {e}")
        return False


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            try:
                st.experimental_rerun()
            except Exception:
                pass


def main():
    st.set_page_config(page_title="Gestión de Usuarios", page_icon="👥", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    st.title("Gestión de Usuarios")

    # Botón nuevo usuario
    col_new, _ = st.columns([1, 5])
    if col_new.button("Nuevo usuario"):
        st.session_state.selected_user_id = None
        st.session_state.user_create_mode = True
        try:
            if hasattr(st, "switch_page"):
                st.switch_page("pages/11_Editar_Usuario.py")
                return
        except Exception:
            pass
        safe_rerun()

    # Filtro
    c_search, c_btn = st.columns([4, 1])
    with c_search:
        q = st.text_input("Buscar", placeholder="username, nombre, email")
    with c_btn:
        do_search = st.button("Buscar", use_container_width=True)

    if do_search or "users_cache" not in st.session_state:
        st.session_state.users_cache = fetch_users(q)
        st.session_state["users_page"] = 1
    users = st.session_state.get("users_cache", [])

    st.markdown("### Lista de usuarios")
    if not users:
        st.info("Sin usuarios para mostrar.")
        return

    paged_users, _, _, _ = paginate_list(users, "users_page", page_size=5)

    # Cargar conteo de salones asignados por docente
    teacher_ids = [u.get("id") for u in paged_users if (u.get("role") or "").upper() in ("DOCENTE", "TEACHER", "PROFESOR")]
    assign_counts = fetch_assignments_count(teacher_ids) if teacher_ids else {}

    # Tarjetas similares al listado de alumnos
    for u in paged_users:
        uid = u.get("id")
        username = u.get("username") or ""
        nombre = ((u.get("first_name") or "") + " " + (u.get("last_name") or "")).strip()
        email = u.get("email") or "-"
        role = u.get("role") or "-"
        role_up = (role or "").upper()
        salons = assign_counts.get(uid) if role_up in ("DOCENTE", "TEACHER", "PROFESOR") else None

        with st.container(border=True):
            c1, c2, c3 = st.columns([3.2, 3.2, 2])
            c1.write(nombre or username)
            c2.caption(f"{username} · {email}")
            if salons is None:
                c3.caption(f"Rol: {role}")
            else:
                c3.caption(f"Rol: {role} · Salones: {salons}")

            btn_col = c3.columns(2)
            if btn_col[0].button("Editar", key=f"upd_{uid}", help="Editar usuario"):
                st.session_state.selected_user_id = uid
                st.session_state.user_create_mode = False
                try:
                    if hasattr(st, "switch_page"):
                        st.switch_page("pages/11_Editar_Usuario.py")
                        return
                except Exception:
                    pass
                safe_rerun()

            if btn_col[1].button("Eliminar", key=f"del_{uid}", help="Eliminar usuario"):
                if delete_user(uid):
                    st.session_state.users_cache = [
                        x for x in st.session_state.users_cache if x.get("id") != uid
                    ]
                    st.session_state["users_page"] = 1
                    safe_rerun()


if __name__ == "__main__":
    main()
