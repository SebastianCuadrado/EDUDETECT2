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


def reset_state_if_user_changed():
    user = st.session_state.get("user") or {}
    user_id = user.get("id") or user.get("username")

    if not user_id:
        return

    previous_user_id = st.session_state.get("current_user_id")

    if previous_user_id != user_id:
        keys_to_clear = [
            "admin_students_cache",
            "students_eval_cache",
            "teacher_students_page",
            "admin_students_page",
            "last_stu_q",
            "last_stu_y",
            "last_stu_g",
            "last_stu_s",
            "view_student_detail_id",
            "enrollment_cache",
            "student_grade_cache",
        ]

        for key in keys_to_clear:
            st.session_state.pop(key, None)

        st.session_state["current_user_id"] = user_id


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

            .detail-button {
                display: flex;
                justify-content: flex-end;
                align-items: center;
                height: 100%;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_last_evaluation_date(student):
    last_evaluation = student.get("last_evaluation") or {}

    if isinstance(last_evaluation, dict):
        return last_evaluation.get("evaluated_at") or "-"

    return "-"


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
            col1, col2, col3 = st.columns(
                [3, 2, 1.2],
                gap="medium",
                vertical_alignment="center",
            )

            with col1:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; height:100%;">
                        <div class="student-name">
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

            with col3:
                st.markdown("<div class='detail-button'>", unsafe_allow_html=True)
                if st.button("Ver detalle", key=f"teacher_detail_{student_id}"):
                    go_to_student_detail(student_id)
                st.markdown("</div>", unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Mis alumnos",
        page_icon="📋",
        layout="wide",
    )

    ensure_auth()
    reset_state_if_user_changed()
    render_sidebar_nav()
    render_topbar()
    render_styles()

    st.title("Mis alumnos")

    c1, c2, c3, c4, c5 = st.columns(
        [3.8, 1.1, 1.1, 1.1, 1.2],
        gap="small",
    )

    with c1:
        query = st.text_input(
            label="Buscar estudiante",
            placeholder="Buscar por nombre o apellido",
            label_visibility="collapsed",
            value=st.session_state.get("last_stu_q", ""),
        )

    with c2:
        y_raw = st.text_input(
            label="Año",
            placeholder="Año",
            label_visibility="collapsed",
            value=st.session_state.get("last_stu_y", ""),
        )

    with c3:
        g_raw = st.text_input(
            label="Grado",
            placeholder="Grado",
            label_visibility="collapsed",
            value=st.session_state.get("last_stu_g", ""),
        )

    with c4:
        s = st.text_input(
            label="Sección",
            placeholder="Sección",
            label_visibility="collapsed",
            max_chars=2,
            value=st.session_state.get("last_stu_s", ""),
        )

    with c5:
        do_filter = st.button("Filtrar", use_container_width=True)

    if do_filter:
        st.session_state["last_stu_q"] = query
        st.session_state["last_stu_y"] = y_raw
        st.session_state["last_stu_g"] = g_raw
        st.session_state["last_stu_s"] = s
        st.session_state["teacher_students_page"] = 1

    year = to_int(query and y_raw or y_raw)
    grade = to_int(g_raw)

    students = fetch_students(
        query=query,
        year=year,
        grade=grade,
        section=s,
    )

    render_student_list(students)


if __name__ == "__main__":
    main()