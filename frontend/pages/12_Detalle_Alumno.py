import os
import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def safe_nav(target: str):
    try:
        if hasattr(st, "switch_page"):
            st.switch_page(target)
            return
    except Exception:
        pass

    rerun()


def fetch_student(student_id: int):
    try:
        response = requests.get(
            f"{API_URL}/students/{student_id}/",
            headers=auth_headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        st.error(f"No se pudo obtener la información del alumno: {e}")
        return None


def fetch_enrollments(student_id: int):
    try:
        response = requests.get(
            f"{API_URL}/enrollments/",
            headers=auth_headers(),
            params={"student": student_id},
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("results", data)

    except requests.RequestException:
        return []


def fetch_classroom(classroom_id: int | None):
    if not classroom_id:
        return None

    try:
        response = requests.get(
            f"{API_URL}/classrooms/{classroom_id}/",
            headers=auth_headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        return None


def fetch_evaluations(student_id: int):
    try:
        response = requests.get(
            f"{API_URL}/evaluations/",
            headers=auth_headers(),
            params={"student": student_id},
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("results", data)

    except requests.RequestException as e:
        st.error(f"No se pudieron cargar las evaluaciones: {e}")
        return []


def build_active_enrollment(student_id: int):
    enrollments = fetch_enrollments(student_id)

    if not enrollments:
        return None

    active = next(
        (enrollment for enrollment in enrollments if not enrollment.get("end_date")),
        None,
    )

    if not active:
        enrollments.sort(
            key=lambda enrollment: enrollment.get("start_date") or "",
            reverse=True,
        )
        active = enrollments[0]

    active["classroom_detail"] = fetch_classroom(active.get("classroom"))
    return active


def get_classroom_label(enrollment):
    if not enrollment:
        return "No asignado"

    classroom = enrollment.get("classroom_detail") or {}

    classroom_name = classroom.get("name")
    if classroom_name:
        return classroom_name

    grade = classroom.get("grade")
    section = classroom.get("section")

    parts = []

    if grade not in (None, ""):
        parts.append(f"{grade}°")

    if section:
        parts.append(section)

    return " ".join(parts).strip() or "No asignado"


def get_start_date(enrollment):
    if not enrollment:
        return "-"

    return enrollment.get("start_date") or "-"


def get_last_evaluation_date(evaluations):
    if not evaluations:
        return " - "

    ordered = sorted(
        evaluations,
        key=lambda evaluation: evaluation.get("evaluated_at") or "",
        reverse=True,
    )

    return ordered[0].get("evaluated_at") or " - "


def get_diagnosis_class(diagnosis):
    diagnosis = str(diagnosis or "").lower()

    if "alto" in diagnosis:
        return "badge-high"

    if "medio" in diagnosis:
        return "badge-medium"

    if "bajo" in diagnosis:
        return "badge-low"

    return "badge-neutral"


def format_probability(value):
    if value in (None, "", "N/D"):
        return "N/D"

    try:
        value = float(value)

        if value <= 1:
            return f"{value:.2%}"

        return f"{value:.2f}%"

    except (TypeError, ValueError):
        return value


def render_styles():
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1320px;
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }
            div[data-testid="stButton"] button {
                border-radius: 10px;
                font-weight: 600;
                min-height: 42px;
            }
            .info-card {
                border: 1px solid var(--info-box-border);
                border-radius: 14px;
                padding: 16px 18px;
                background: var(--info-box-bg);
                min-height: 92px;
            }
            .info-label {
                font-size: 13px;
                font-weight: 700;
                color: var(--info-label-color);
                margin: 0 0 8px 0;
            }
            .info-value {
                font-size: 24px;
                font-weight: 800;
                color: var(--info-value-color);
                margin: 0;
            }
            .last-evaluation-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 10px 18px;
                border-radius: 999px;
                border: 1px solid rgba(96,165,250,0.65);
                background: rgba(37,99,235,0.18);
                color: #93c5fd;
                font-size: 15px;
                font-weight: 700;
                width: fit-content;
                margin-top: 16px;
            }
            .last-evaluation-badge span {
                color: var(--info-value-color);
                font-weight: 800;
            }
            .evaluation-card {
                border: 1px solid var(--info-box-border);
                border-radius: 14px;
                padding: 18px 20px;
                margin-bottom: 12px;
                background: var(--info-box-bg);
            }
            .eval-label {
                font-size: 13px;
                font-weight: 700;
                color: var(--info-label-color);
                margin: 0 0 6px 0;
            }
            .eval-value {
                font-size: 17px;
                font-weight: 800;
                color: var(--info-value-color);
                margin: 0;
            }
            .eval-grid {
                display: grid;
                grid-template-columns: 1.2fr 1.2fr 1fr;
                gap: 18px;
                align-items: center;
            }
            .badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 8px 16px;
                border-radius: 999px;
                font-size: 14px;
                font-weight: 800;
                width: fit-content;
            }
            .badge-high {
                color: #fecaca;
                border: 1px solid rgba(248,113,113,0.55);
                background: rgba(220,38,38,0.16);
            }
            .badge-medium {
                color: #fde68a;
                border: 1px solid rgba(251,191,36,0.55);
                background: rgba(217,119,6,0.16);
            }
            .badge-low {
                color: #bbf7d0;
                border: 1px solid rgba(74,222,128,0.55);
                background: rgba(22,163,74,0.16);
            }
            .badge-neutral {
                color: var(--badge-none-color);
                border: 1px solid var(--badge-none-border);
                background: var(--badge-none-bg);
            }
            @media (max-width: 900px) {
                .student-title { font-size: 60px; }
                .eval-grid { grid-template-columns: 1fr; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(student, enrollment, evaluations):
    first_name = student.get("first_name", "")
    last_name = student.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip()

    classroom_label = get_classroom_label(enrollment)
    last_evaluation = get_last_evaluation_date(evaluations)

    st.title(f"{student.get('first_name','')} {student.get('last_name','')}")

    col1, col2, col3, col4 = st.columns([1, 1, 1.4, 1])

    with col1:
        st.markdown(
            f"""
            <div class="info-card">
                <p class="info-label">Edad</p>
                <p class="info-value">{student.get("age", "N/D")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="info-card">
                <p class="info-label">Género</p>
                <p class="info-value">{student.get("gender", "-")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="info-card">
                <p class="info-label">Salón</p>
                <p class="info-value">{classroom_label}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )



    with col4:
        st.markdown(
            f"""
            <div class="info-card">
                <p class="info-label">Evaluaciones</p>
                <p class="info-value">{len(evaluations)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="last-evaluation-badge">
            Última evaluación: <span>{last_evaluation}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_evaluations(evaluations):
    st.markdown(
        '<p class="section-title">Historial de evaluaciones</p>',
        unsafe_allow_html=True,
    )

    if not evaluations:
        st.markdown(
            """
            <div class="empty-box">
                Este alumno aún no tiene evaluaciones registradas.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    ordered_evaluations = sorted(
        evaluations,
        key=lambda evaluation: evaluation.get("evaluated_at") or "",
        reverse=True,
    )

    for evaluation in ordered_evaluations:
        evaluated_at = evaluation.get("evaluated_at") or "-"
        probability = format_probability(evaluation.get("probability"))
        diagnosis = evaluation.get("diagnosis") or "-"
        badge_class = get_diagnosis_class(diagnosis)

        st.markdown(
            f"""
            <div class="evaluation-card">
                <div class="eval-grid">
                    <div>
                        <p class="eval-label">Fecha</p>
                        <p class="eval-value">{evaluated_at}</p>
                    </div>
                    <div>
                        <p class="eval-label">Probabilidad</p>
                        <p class="eval-value">{probability}</p>
                    </div>
                    <div>
                        <p class="eval-label">Diagnóstico</p>
                        <span class="badge {badge_class}">{diagnosis}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_back_button():
    if st.button("Volver al listado", type="secondary"):
        safe_nav("pages/03_Historial_Alumnos_Evaluados.py")


def main():
    st.set_page_config(
        page_title="Detalle del alumno",
        page_icon="👤",
        layout="wide",
    )

    ensure_auth()
    render_sidebar_nav()
    render_topbar()
    render_styles()

    student_id = st.session_state.get("view_student_detail_id")

    if not student_id:
        st.warning("Selecciona un alumno desde el listado para ver su detalle.")
        st.divider()
        render_back_button()
        st.stop()

    student = fetch_student(student_id)

    if not student:
        st.divider()
        render_back_button()
        st.stop()

    enrollment = build_active_enrollment(student_id)
    evaluations = fetch_evaluations(student_id)

    render_header(student, enrollment, evaluations)

    st.divider()

    render_evaluations(evaluations)

    st.divider()

    render_back_button()


if __name__ == "__main__":
    main()