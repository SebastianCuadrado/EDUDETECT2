import os
import streamlit as st
import requests

from ui_common import ensure_auth, render_sidebar_nav, render_topbar

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", headers=auth_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def api_get_all(path, params=None):
    url = f"{API_URL}{path}"
    out = []

    while url:
        r = requests.get(
            url,
            headers=auth_headers(),
            params=params if url.endswith(path) else None,
            timeout=15
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

def get_active_enrollments(enrollments):
    return [
        enrollment
        for enrollment in enrollments
        if not enrollment.get("end_date")
    ]


def go_back():
    if hasattr(st, "switch_page"):
        st.switch_page("pages/05_Administrar_Salones.py")
    else:
        st.rerun()


def paginate_items(items, key: str, page_size: int = 8):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)

    if key not in st.session_state:
        st.session_state[key] = 1

    page = st.session_state[key]
    page = min(max(page, 1), total_pages)
    st.session_state[key] = page

    start = (page - 1) * page_size
    end = min(start + page_size, total)

    if total_pages > 1:
        c1, c2, c3 = st.columns([1, 2, 1])

        with c1:
            if st.button("Anterior", disabled=page <= 1, key=f"{key}_prev", use_container_width=True):
                st.session_state[key] = page - 1
                st.rerun()

        with c2:
            st.markdown(
                f"""
                <div style="text-align:center; padding-top:0.5rem; color:var(--text-pagination)">
                    Página <b>{page}</b> de <b>{total_pages}</b> · {start + 1}-{end} de {total}
                </div>
                """,
                unsafe_allow_html=True
            )

        with c3:
            if st.button("Siguiente", disabled=page >= total_pages, key=f"{key}_next", use_container_width=True):
                st.session_state[key] = page + 1
                st.rerun()

    return items[start:end]


def inject_styles():
    st.markdown("""
    <style>
    .main .block-container {
        max-width: 1280px;
        padding-top: 1.2rem;
        padding-bottom: 1rem;
    }
    .room-title {
        font-size: 2.7rem;
        font-weight: 800;
        color: var(--text-primary);
        margin-bottom: 0.2rem;
    }
    .room-meta {
        color: var(--text-secondary);
        font-size: 1rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        background: var(--bg-card);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text-primary);
    }
    .metric-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
    }
    .item-card {
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.65rem;
        background: var(--bg-card);
    }
    .item-title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    .item-subtitle {
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }
    .stButton > button {
        min-height: 42px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Detalle del salón",
        page_icon="🏫",
        layout="wide"
    )

    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    room_id = st.session_state.get("selected_room_id")

    if not room_id:
        st.warning("No se ha seleccionado un salón.")
        if st.button("Volver",type="primary"):
            go_back()
        return

    top_left, top_right = st.columns([5, 1])

    with top_right:
        if st.button("Volver", use_container_width=True,type="primary"):
            go_back()

    try:
        room = api_get(f"/classrooms/{room_id}/")
        assigns = api_get_all("/teacher-assignments/", params={"classroom": room_id})

        all_enrolls = api_get_all("/enrollments/", params={"classroom": room_id})
        enrolls = get_active_enrollments(all_enrolls)
    except Exception as e:
        st.error(f"No se pudo cargar el detalle del salón: {e}")
        return

    label = room.get("name") or f"{room.get('academic_year')} - {room.get('grade')}{room.get('section')}"

    st.markdown(f'<div class="room-title">{label}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="room-meta">
            Año: {room.get('academic_year')} · Grado: {room.get('grade')} · Sección: {room.get('section')}
        </div>
        """,
        unsafe_allow_html=True
    )

    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{len(assigns)}</div>
                <div class="metric-label">Profesores asignados</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{len(enrolls)}</div>
                <div class="metric-label">Alumnos matriculados</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{room.get('grade')}{room.get('section')}</div>
                <div class="metric-label">Aula</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div class="section-title">Profesores</div>', unsafe_allow_html=True)

        if not assigns:
            st.info("Sin profesores asignados.")
        else:
            for a in assigns:
                try:
                    u = api_get(f"/users/{a.get('teacher')}/")
                    username = u.get("username", "")
                    full_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
                    role = a.get("role") or "Sin rol"

                    st.markdown(
                        f"""
                        <div class="item-card">
                            <div class="item-title">{full_name or username}</div>
                            <div class="item-subtitle">@{username} · Rol: {role}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                except Exception:
                    st.markdown(
                        f"""
                        <div class="item-card">
                            <div class="item-title">Docente ID {a.get('teacher')}</div>
                            <div class="item-subtitle">Rol: {a.get('role') or 'Sin rol'}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with right:
        st.markdown('<div class="section-title">Alumnos</div>', unsafe_allow_html=True)

        if not enrolls:
            st.info("Sin alumnos matriculados.")
        else:
            paged_enrolls = paginate_items(enrolls, "room_students_page", page_size=8)

            for e in paged_enrolls:
                try:
                    s = api_get(f"/students/{e.get('student')}/")
                    full_name = f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
                    age = s.get("age")
                    gender = s.get("gender") or "-"

                    subtitle_parts = []

                    if age:
                        subtitle_parts.append(f"Edad: {age}")

                    if gender != "-":
                        subtitle_parts.append(f"Género: {gender}")

                    subtitle = " · ".join(subtitle_parts) if subtitle_parts else "Sin datos adicionales"

                    st.markdown(
                        f"""
                        <div class="item-card">
                            <div class="item-title">{full_name or f"Alumno ID {e.get('student')}"}</div>
                            <div class="item-subtitle">{subtitle}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                except Exception:
                    st.markdown(
                        f"""
                        <div class="item-card">
                            <div class="item-title">Alumno ID {e.get('student')}</div>
                            <div class="item-subtitle">No se pudo cargar información adicional</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


if __name__ == "__main__":
    main()