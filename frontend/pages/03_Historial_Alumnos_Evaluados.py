import os
import requests
import streamlit as st

from ui_common import ensure_auth, paginate_list, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def fetch_students(query=None, year=None, grade=None, section=None):
    params = {}

    if query:
        params["search"] = query.strip()

    if year:
        params["year"] = year

    if grade:
        params["grade"] = grade

    if section:
        params["section"] = section.strip()

    try:
        response = requests.get(
            f"{API_URL}/students/",
            headers=auth_headers(),
            params=params,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("results", data)

    except requests.RequestException as e:
        st.error(f"No se pudo cargar el listado de alumnos: {e}")
        return []


def to_int(value):
    try:
        value = str(value).strip()
        return int(value) if value else None
    except ValueError:
        return None


def go_to_student_detail(student_id):
    st.session_state.view_student_detail_id = student_id

    if hasattr(st, "switch_page"):
        st.switch_page("pages/12_Detalle_Alumno.py")
    else:
        rerun()


def render_styles():
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1280px;
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }

            div[data-testid="stTextInput"] label {
                font-weight: 600;
                color: #ffffff;
            }

            div[data-testid="stButton"] button {
                border-radius: 10px;
                font-weight: 600;
                min-height: 42px;
            }

            .student-name {
                font-size: 17px;
                font-weight: 700;
                color: #ffffff;
                margin: 0;
            }
            .student-label {
                display: inline-block;
                padding: 6px 12px;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 700;
                white-space: nowrap;
                background: rgba(234, 138, 34, 0.16);
                color: #fcb160;
                border: 1px solid rgba(234, 138, 34, 0.32);
            }

            .student-info {
                font-size: 15px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.60);
                margin: 0;
            }

            .section-title {
                margin-top: 22px;
                margin-bottom: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_filters():
    with st.form("student_filters"):
        col1, col2, col3, col4 = st.columns([3.2, 1, 1, 1])

        with col1:
            query = st.text_input(
                "Buscar alumno",
                placeholder="Nombre, apellido",
                label_visibility="visible",
            )

        with col2:
            year = st.text_input(
                "Año",
                placeholder="Ej: 2024",
            )

        with col3:
            grade = st.text_input(
                "Grado",
                placeholder="Ej: 3",
            )

        with col4:
            section = st.text_input(
                "Sección",
                placeholder="Ej: A",
                max_chars=2,
            )

        submitted = st.form_submit_button("Filtrar")

    if submitted:
        st.session_state["teacher_students_page"] = 1

    return query, to_int(year), to_int(grade), section


def get_last_evaluation_date(student):
    last_evaluation = student.get("last_evaluation") or {}

    if isinstance(last_evaluation, dict):
        return last_evaluation.get("evaluated_at") or " -"

    return " -"


def render_student_list(students):
    st.divider()

    if not students:
        st.info("Aún no tienes alumnos registrados o no se encontraron resultados.")
        return

    paged_students, _, _, _ = paginate_list(
        students,
        "teacher_students_page",
        page_size=6,
    )

    for student in paged_students:
        student_id = student.get("id")
        full_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
        last_evaluation_date = get_last_evaluation_date(student)

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1.5, 2, 1.2],
            gap="medium",
            vertical_alignment="center")

            with col1:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; height:100%;">
                        <div class="student-name" style="transform: translateY(-10px);">
                            {full_name}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f'<span class="student-label">Última evaluación: {last_evaluation_date}</span>',
                    unsafe_allow_html=True,
                )

            with col4:
                st.markdown("<div class='detail-button'>", unsafe_allow_html=True)
                if st.button("Ver detalle", key=f"teacher_detail_{student_id}"):
                    go_to_student_detail(student_id)
                st.markdown("</div>", unsafe_allow_html=True)
def _to_int(val):
    try:
        return int(str(val).strip())
    except Exception:
        return None


def main():
    st.set_page_config(
        page_title="Mis alumnos",
        page_icon="📋",
        layout="wide",
    )

    ensure_auth()
    render_sidebar_nav()
    render_topbar()
    render_styles()

    st.title("Mis alumnos")

    c1, c2, c3, c4, c5 = st.columns([3.8, 1.1, 1.1, 1.1, 1.2], gap="small")

    with c1:
        query = st.text_input(
            label="Buscar estudiante",
            placeholder="Buscar por nombre o apellido",
            label_visibility="collapsed",
            value="",
        )

    with c2:
        y_raw = st.text_input(
            label="Año",
            placeholder="Año",
            label_visibility="collapsed",
            value="",
        )

    with c3:
        g_raw = st.text_input(
            label="Grado",
            placeholder="Grado",
            label_visibility="collapsed",
            value="",
        )

    with c4:
        s = st.text_input(
            label="Sección",
            placeholder="Sección",
            label_visibility="collapsed",
            max_chars=2,
            value="",
        )

    with c5:
        do_filter = st.button("Filtrar", use_container_width=True)

    last_q = st.session_state.get("last_stu_q", "")
    last_y = st.session_state.get("last_stu_y", "")
    last_g = st.session_state.get("last_stu_g", "")
    last_s = st.session_state.get("last_stu_s", "")

    auto_refresh = False
    if query == "" and last_q != "": auto_refresh = True
    if y_raw == "" and last_y != "": auto_refresh = True
    if g_raw == "" and last_g != "": auto_refresh = True
    if s == "" and last_s != "": auto_refresh = True

    if do_filter or "admin_students_cache" not in st.session_state or auto_refresh:
        st.session_state["last_stu_q"] = query
        st.session_state["last_stu_y"] = y_raw
        st.session_state["last_stu_g"] = g_raw
        st.session_state["last_stu_s"] = s

        year = _to_int(y_raw)
        grade = _to_int(g_raw)

        st.session_state.admin_students_cache = fetch_students(query, year, grade, s)
        st.session_state["admin_students_page"] = 1
        st.session_state.pop("enrollment_cache", None)

    students = st.session_state.get("admin_students_cache", [])

    render_student_list(students)


if __name__ == "__main__":
    main()