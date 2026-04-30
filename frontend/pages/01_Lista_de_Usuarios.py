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


def fetch_assignments_labels(user_ids: list[int]) -> dict[int, list[str]]:
    """Returns a dict mapping teacher_id -> list of classroom label strings."""
    result: dict[int, list[str]] = {}
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
                items = data.get("results", data) if isinstance(data, dict) else data
                labels = []
                for a in (items if isinstance(items, list) else []):
                    cid = a.get("classroom")
                    if not cid:
                        continue
                    try:
                        cr = requests.get(
                            f"{API_URL}/classrooms/{cid}/",
                            headers=auth_headers(),
                            timeout=10,
                        )
                        if cr.status_code == 200:
                            c = cr.json()
                            name = c.get("name")
                            grade = c.get("grade")
                            section = c.get("section", "")
                            if name:
                                labels.append(name)
                            elif grade is not None:
                                labels.append(f"{grade}°{section}")
                            else:
                                labels.append(f"Aula {cid}")
                        else:
                            labels.append(f"Aula {cid}")
                    except Exception:
                        labels.append(f"Aula {cid}")
                result[uid] = labels
            else:
                result[uid] = []
        except Exception:
            result[uid] = []
    return result


def delete_user(user_id: int) -> bool:
    try:
        r = requests.delete(f"{API_URL}/users/{user_id}/", headers=auth_headers(), timeout=12)
        if r.status_code in (204, 200):
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
            st.experimental_rerun()


def inject_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1280px;
        }

        div[data-testid="stTextInput"] {
            margin-top: 0 !important;
        }
        div[data-testid="stTextInput"] input {
            border-radius: 14px !important;
            height: 40px !important;
        }
        div[data-testid="column"] {
            display: flex;
            align-items: end;
        }
        .stButton > button {
            border-radius: 12px !important;
            min-height: 44px !important;
            font-weight: 600 !important;
        }
        .new-user-wrap .stButton > button {
            min-height: 46px !important;
            font-size: 1rem !important;
        }
        input {
            height: 40px !important;
            border-radius: 10px !important;
        }
        .mid-wrap {
            margin-top: 0.22rem;
        }
        .meta-wrap {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 0.15rem;
        }
        .actions-center {
            margin-top: 0.22rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def role_badge_html(role: str) -> str:
    role_up = (role or "").upper()
    klass = "role-admin" if role_up == "ADMIN" else "role-docente"
    return f'<span class="role-badge {klass}">Rol: {role_up or "-"}</span>'


@st.dialog("Confirmar eliminación")
def modal_confirmar_eliminar_usuario():
    uid = st.session_state.get("confirm_delete_user_id")
    nombre = st.session_state.get("confirm_delete_user_name", "este usuario")

    st.warning(f"¿Estás seguro de que deseas eliminar a **{nombre}**?")
    st.caption("Esta acción no se puede deshacer.")

    col1, col2 = st.columns(2)

    if col1.button("Eliminar de todos modos", type="primary", use_container_width=True):
        if delete_user(uid):
            st.session_state["users_cache"] = [
                x for x in st.session_state.get("users_cache", []) if x.get("id") != uid
            ]
            st.session_state["users_page"] = 1

        st.session_state.pop("confirm_delete_user_id", None)
        st.session_state.pop("confirm_delete_user_name", None)
        safe_rerun()

    if col2.button("Cancelar", use_container_width=True):
        st.session_state.pop("confirm_delete_user_id", None)
        st.session_state.pop("confirm_delete_user_name", None)
        safe_rerun()


def main():
    st.set_page_config(page_title="Gestión de Usuarios", page_icon="👥", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    if st.session_state.pop("force_refresh_users", False):
        st.session_state.pop("users_cache", None)
        safe_rerun()
        

    st.markdown('<div class="page-title">Gestión de Usuarios</div>', unsafe_allow_html=True)



    st.write(" ")
    search_col, btn_col = st.columns([5, 1.2], gap="small")
    with search_col:
        q = st.text_input(
            label="Buscar usuario",
            placeholder="Buscar por username, nombre o correo",
            label_visibility="collapsed",
        )
    with btn_col:
        do_search = st.button("Buscar", use_container_width=True)

    if do_search or "users_cache" not in st.session_state:
        st.session_state.users_cache = fetch_users(q)
        st.session_state["users_page"] = 1

    users = st.session_state.get("users_cache", [])

    title1_col, btn1_col = st.columns([4, 1])

    with title1_col:
        st.markdown('<div class="section-title">Lista de usuarios</div>', unsafe_allow_html=True)

    with btn1_col:
        st.markdown('<div class="new-user-wrap">', unsafe_allow_html=True)
        if st.button("➕ Nuevo usuario", type="primary",use_container_width=True):
            st.session_state.selected_user_id = None
            st.session_state.pop("user_create_mode", None)

            if hasattr(st, "switch_page"):
                st.switch_page("pages/02_Registrar_Usuario.py")
                return

            safe_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if not users:
        st.markdown('<div class="empty-box">No hay usuarios para mostrar.</div>', unsafe_allow_html=True)
        return

    paged_users, _, _, _ = paginate_list(users, "users_page", page_size=10)

    teacher_ids = [
        u.get("id")
        for u in paged_users
        if (u.get("role") or "").upper() in ("DOCENTE", "TEACHER", "PROFESOR")
    ]
    assign_labels = fetch_assignments_labels(teacher_ids) if teacher_ids else {}

    for u in paged_users:
        uid = u.get("id")
        username = u.get("username") or ""
        nombre = ((u.get("first_name") or "") + " " + (u.get("last_name") or "")).strip()
        email = u.get("email") or "-"
        role = u.get("role") or "-"
        role_up = role.upper() if role else ""
        salons = assign_labels.get(uid) if role_up in ("DOCENTE", "TEACHER", "PROFESOR") else None

        with st.container(border=True):
            name_col, user_col, role_col, action_col = st.columns([2.5, 2.2, 2.0, 2.1], gap="medium")

            with name_col:
                st.markdown('<div class="mid-wrap">', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="user-name">{nombre or username or "Sin nombre"}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with user_col:
                st.markdown('<div class="mid-wrap">', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="user-username">@{username if username else "-"}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="user-email">{email}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with role_col:
                st.markdown('<div class="mid-wrap">', unsafe_allow_html=True)
                meta_html = role_badge_html(role)
                if salons is not None:
                    if salons:
                        for label in salons:
                            meta_html += f' <span class="salon-pill">{label}</span>'
                    else:
                        meta_html += ' <span class="salon-pill">Sin salón</span>'
                st.markdown(f'<div class="meta-wrap">{meta_html}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with action_col:
                st.markdown('<div class="actions-center">', unsafe_allow_html=True)
                b1, b2 = st.columns(2, gap="small")

                if b1.button("Editar", key=f"upd_{uid}", use_container_width=True):
                    st.session_state.selected_user_id = uid
                    st.session_state.pop("user_create_mode", None)

                    if hasattr(st, "switch_page"):
                        st.switch_page("pages/11_Editar_Usuario.py")
                        return

                    safe_rerun()

                if b2.button("Eliminar", key=f"del_{uid}", use_container_width=True):
                    st.session_state["confirm_delete_user_id"] = uid
                    st.session_state["confirm_delete_user_name"] = nombre or username or "este usuario"

                st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

    if "confirm_delete_user_id" in st.session_state:
        modal_confirmar_eliminar_usuario()


if __name__ == "__main__":
    main()