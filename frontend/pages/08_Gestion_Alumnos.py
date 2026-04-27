import os
import requests
import streamlit as st

from ui_common import ensure_auth, paginate_list, render_sidebar_nav, render_topbar

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def fetch_students(query=None, year=None, grade=None, section=None):
    try:
        params = {}
        if query:
            params["search"] = query
        if year:
            params["year"] = year
        if grade:
            params["grade"] = grade
        if section:
            params["section"] = section

        r = requests.get(
            f"{API_URL}/students/",
            headers=auth_headers(),
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudo cargar alumnos: {e}")
        return []


def fetch_classroom(classroom_id: int):
    cache = st.session_state.setdefault("classroom_cache", {})
    if classroom_id in cache:
        return cache[classroom_id]

    try:
        r = requests.get(
            f"{API_URL}/classrooms/{classroom_id}/",
            headers=auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        cache[classroom_id] = data
        return data
    except Exception:
        return None


def fetch_active_classroom(student_id: int):
    cache = st.session_state.setdefault("enrollment_cache", {})
    if student_id in cache:
        return cache[student_id]

    try:
        r = requests.get(
            f"{API_URL}/enrollments/",
            headers=auth_headers(),
            params={"student": student_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        enrollments = data.get("results", data)

        active = next((e for e in enrollments if not e.get("end_date")), None)

        if not active and enrollments:
            enrollments.sort(key=lambda x: x.get("start_date") or "", reverse=True)
            active = enrollments[0]

        if active:
            cls = fetch_classroom(active.get("classroom"))
            cache[student_id] = cls
            return cls
    except Exception:
        pass

    cache[student_id] = None
    return None


def delete_student(student_id: int):
    r = requests.delete(
        f"{API_URL}/students/{student_id}/",
        headers=auth_headers(),
        timeout=15,
    )
    return r.status_code in (204, 200), r.text


def inject_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1280px;

            
        }

        .page-title {
            font-size: 3rem;
            font-weight: 800;
            color: #f8fafc;
            line-height: 1.05;
            margin-bottom: 0.35rem;
        }

        .page-subtitle {
            color: #94a3b8;
            font-size: 1rem;
            margin-bottom: 1.2rem;
        }

        .section-title {
            font-size: 2rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 1rem;
        }

        div[data-testid="stTextInput"] {
            margin-top: 0 !important;
        }

        div[data-testid="stTextInput"] input {
            border-radius: 14px !important;
            min-height: 48px !important;
            padding-top: 6px !important;
            padding-bottom: 12px !important;
        }

        .stButton > button {
            border-radius: 12px !important;
            min-height: 44px !important;
            font-weight: 600 !important;
        }

        .new-student-wrap .stButton > button {
            min-height: 46px !important;
            font-size: 1rem !important;
        }

        .filter-btn-wrap {
            padding-top: 3px;
            margin-bottom: 5px;
        }

        .filter-btn-wrap .stButton > button {
            min-height: 48px !important;
            margin-top: 0 !important;
        }

        .empty-box {
            background: rgba(30, 64, 175, 0.18);
            border: 1px solid rgba(96,165,250,0.18);
            color: #bfdbfe;
            border-radius: 16px;
            padding: 18px;
        }

        .student-name {
            color: #f8fafc;
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.1;
            margin: 0 !important;
            padding: 0 !important;
        }

        .student-meta {
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

        .classroom-badge,
        .gender-badge,
        .no-classroom-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .classroom-badge {
            background: rgba(59, 130, 246, 0.16);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.32);
        }

        .gender-badge {
            background: rgba(16, 185, 129, 0.14);
            color: #6ee7b7;
            border: 1px solid rgba(16, 185, 129, 0.28);
        }

        .no-classroom-badge {
            background: rgba(255,255,255,0.06);
            color: #cbd5e1;
            border: 1px solid rgba(255,255,255,0.10);
        }
        
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("Confirmar eliminación")
def modal_confirmar_eliminar_alumno():
    sid = st.session_state.get("confirm_delete_student_id")
    nombre = st.session_state.get("confirm_delete_student_name", "este alumno")

    st.warning(f"¿Estás seguro de que deseas eliminar a **{nombre}**?")
    st.caption("Esta acción no se puede deshacer.")

    col1, col2 = st.columns(2)

    if col1.button("Eliminar de todos modos", type="primary", use_container_width=True):
        ok, msg = delete_student(sid)

        if ok:
            st.success("Alumno eliminado")
            st.session_state.pop("admin_students_cache", None)
            st.session_state["admin_students_page"] = 1
        else:
            st.error(msg)

        st.session_state.pop("confirm_delete_student_id", None)
        st.session_state.pop("confirm_delete_student_name", None)
        _safe_rerun()

    if col2.button("Cancelar", use_container_width=True):
        st.session_state.pop("confirm_delete_student_id", None)
        st.session_state.pop("confirm_delete_student_name", None)
        _safe_rerun()


def _to_int(val):
    try:
        return int(str(val).strip())
    except Exception:
        return None


def classroom_label(cls):
    if not cls:
        return "-"

    name = cls.get("name") or ""
    grade = cls.get("grade") or ""
    section = cls.get("section") or ""

    label = f"{name} {grade}° {section}".strip()
    return label or "-"


def main():
    st.set_page_config(page_title="Gestión de Alumnos", page_icon="📚", layout="wide")
    ensure_auth("ADMIN")
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    if st.session_state.pop("force_refresh_students", False):
        st.session_state.pop("admin_students_cache", None)
        st.session_state.pop("enrollment_cache", None)
        _safe_rerun()

    st.markdown('<div class="page-title">Gestión de Alumnos</div>', unsafe_allow_html=True)



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

    title_col, btn_col = st.columns([4, 1])

    with title_col:
        st.markdown('<div class="section-title">Lista de alumnos</div>', unsafe_allow_html=True)

    with btn_col:
        st.markdown('<div class="new-student-wrap">', unsafe_allow_html=True)
        if st.button("➕ Nuevo alumno", type="primary", use_container_width=True):
            st.session_state.selected_student_id = None
            st.session_state.pop("user_create_mode", None)

            if hasattr(st, "switch_page"):
                st.switch_page("pages/04_Registrar_Estudiante.py")
                return

            _safe_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not students:
        st.markdown('<div class="empty-box">No hay alumnos para mostrar.</div>', unsafe_allow_html=True)
        return

    paged_students, _, _, _ = paginate_list(
        students,
        "admin_students_page",
        page_size=10,
    )

    for stu in paged_students:
        sid = stu.get("id")
        first_name = stu.get("first_name") or ""
        last_name = stu.get("last_name") or ""
        full_name = f"{first_name} {last_name}".strip() or "Sin nombre"

        age = stu.get("age")
        age_text = "N/D" if age in (None, "") else str(age)

        gender = stu.get("gender") or "-"
        cls = fetch_active_classroom(sid)
        cls_label = classroom_label(cls)

        with st.container(border=True):
            name_col, age_col, gender_col, classroom_col, action_col = st.columns(
                [2.5, 1.2, 1.4, 2.2, 1.8],
                gap="medium",
                vertical_alignment="center",
            )

            with name_col:
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

            with age_col:
                st.markdown(
                    f'<span class="student-meta">Edad: {age_text}</span>',
                    unsafe_allow_html=True,
                )

            with gender_col:
                st.markdown(
                    f'<span class="gender-badge">Género: {gender}</span>',
                    unsafe_allow_html=True,
                )

            with classroom_col:
                if cls_label != "-":
                    st.markdown(
                        f'<span class="classroom-badge">Salón: {cls_label}</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span class="no-classroom-badge">Sin salón asignado</span>',
                        unsafe_allow_html=True,
                    )

            with action_col:
                st.markdown('<div class="actions-center">', unsafe_allow_html=True)
                b1, b2 = st.columns(2, gap="small")

                if b1.button("Editar", key=f"stu_edit_{sid}", use_container_width=True):
                    st.session_state.selected_student_id = sid
                    st.session_state.pop("user_create_mode", None)

                    if hasattr(st, "switch_page"):
                        st.switch_page("pages/10_Editar_Alumno.py")
                        return

                    _safe_rerun()

                if b2.button("Eliminar", key=f"stu_del_{sid}", use_container_width=True):
                    st.session_state.confirm_delete_student_id = sid
                    st.session_state.confirm_delete_student_name = full_name
                    _safe_rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.write("")

    if "confirm_delete_student_id" in st.session_state:
        modal_confirmar_eliminar_alumno()


if __name__ == "__main__":
    main()