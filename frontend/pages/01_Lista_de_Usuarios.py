import os
import requests
import streamlit as st
from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def fetch_users(query: str | None = None):
    try:
        params = {"search": query} if query else None
        r = requests.get(f"{API_URL}/users/", headers=auth_headers(), params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudo cargar usuarios: {e}")
        return []


def delete_user(user_id: int):
    try:
        r = requests.delete(f"{API_URL}/users/{user_id}/", headers=auth_headers(), timeout=10)
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
        if hasattr(st, 'experimental_rerun'):
            try:
                st.experimental_rerun()
            except Exception:
                pass


def main():
    st.set_page_config(page_title="Usuarios", page_icon="👤", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()

    st.title("Usuarios")
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

    c_search, c_btn = st.columns([4, 1])
    with c_search:
        q = st.text_input("Buscar usuario", placeholder="username, nombre, email, DNI, teléfono")
    with c_btn:
        do_search = st.button("Buscar", use_container_width=True)

    if do_search or "users_cache" not in st.session_state:
        st.session_state.users_cache = fetch_users(q)

    users = st.session_state.get("users_cache", [])
    st.markdown("#### Resultados")
    if not users:
        st.info("Sin usuarios para mostrar.")
        return

    header_cols = ["ID", "Username", "Nombre", "Correo", "Teléfono", "DNI", "Rol", "Editar", "Eliminar"]
    st.markdown(" | ".join(header_cols))
    st.markdown(":-" * len(header_cols))

    for u in users:
        uid = u.get("id")
        username = u.get("username")
        nombre = (u.get("first_name") or "") + (" " + u.get("last_name") if u.get("last_name") else "")
        email = u.get("email")
        phone = u.get("phone")
        dni = u.get("dni")
        role = u.get("role")

        c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.6, 1.2, 1.8, 2.5, 1.5, 1.5, 1.2, 1.0, 1.0])
        c1.write(uid)
        c2.write(username)
        c3.write(nombre.strip() or "-")
        c4.write(email)
        c5.write(phone or "-")
        c6.write(dni)
        c7.write(role)
        upd = c8.button("Editar", key=f"upd_{uid}")
        rem = c9.button("Eliminar", key=f"del_{uid}")
        if rem:
            if delete_user(uid):
                st.session_state.users_cache = [x for x in st.session_state.users_cache if x.get("id") != uid]
                safe_rerun()
        if upd:
            st.session_state.selected_user_id = uid
            st.session_state.user_create_mode = False
            try:
                if hasattr(st, "switch_page"):
                    st.switch_page("pages/11_Editar_Usuario.py")
                    return
            except Exception:
                pass
            safe_rerun()


if __name__ == "__main__":
    main()

