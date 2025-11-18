import os

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def _safe_nav(target: str):
    try:
        if hasattr(st, "switch_page"):
            st.switch_page(target)
            return
    except Exception:
        pass
    try:
        st.experimental_rerun()
    except Exception:
        pass


def fetch_student(student_id: int):
    try:
        r = requests.get(f"{API_URL}/students/{student_id}/", headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"No se pudo obtener la información del alumno: {e}")
        return None


def fetch_enrollments(student_id: int):
    try:
        r = requests.get(
            f"{API_URL}/enrollments/",
            headers=auth_headers(),
            params={"student": student_id},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.warning(f"No se pudo obtener la matrícula: {e}")
        return []


def fetch_classroom(classroom_id: int | None):
    if not classroom_id:
        return None
    try:
        r = requests.get(f"{API_URL}/classrooms/{classroom_id}/", headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def build_active_enrollment(student_id: int):
    enrollments = fetch_enrollments(student_id)
    if not enrollments:
        return None
    active = next((e for e in enrollments if not e.get("end_date")), None)
    if not active:
        enrollments.sort(key=lambda x: x.get("start_date") or "", reverse=True)
        active = enrollments[0]
    active["classroom_detail"] = fetch_classroom(active.get("classroom"))
    return active


def fetch_evaluations(student_id: int):
    try:
        r = requests.get(
            f"{API_URL}/evaluations/",
            headers=auth_headers(),
            params={"student": student_id},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudieron cargar las evaluaciones: {e}")
        return []


def render_header(student, enrollment):
    st.title(f"{student.get('first_name','')} {student.get('last_name','')}")
    info_cols = st.columns(4)
    info_cols[0].metric("Edad", student.get("age", "N/D"))
    info_cols[1].metric("Género", student.get("gender", "-"))
    if enrollment:
        cls = enrollment.get("classroom_detail") or {}
        classroom_label = cls.get("name") or ""
        if not classroom_label:
            grade = cls.get("grade")
            section = cls.get("section")
            parts = []
            if grade not in (None, ""):
                parts.append(f"{grade}°")
            if section:
                parts.append(section)
            classroom_label = " ".join(parts).strip()
        info_cols[2].metric("Salón", classroom_label or "No asignado")
        info_cols[3].metric("Inicio", enrollment.get("start_date") or "-")
    else:
        info_cols[2].metric("Salón", "No asignado")
        info_cols[3].metric("Inicio", "-")


def render_evaluations(evals):
    st.subheader("Historial de evaluaciones")
    if not evals:
        st.info("Este alumno aún no tiene evaluaciones registradas.")
        return
    rows = []
    for ev in sorted(evals, key=lambda x: x.get("evaluated_at") or "", reverse=True):
        rows.append(
            {
                "Fecha": ev.get("evaluated_at", "-"),
                "Probabilidad": ev.get("probability", "N/D") or "N/D",
                "Diagnóstico": ev.get("diagnosis", "-"),
            }
        )
    st.table(rows)


def main():
    st.set_page_config(page_title="Detalle del alumno", page_icon="👤", layout="wide")
    ensure_auth()
    render_sidebar_nav()
    render_topbar()

    student_id = st.session_state.get("view_student_detail_id")
    if not student_id:
        st.warning("Selecciona un alumno desde el listado para ver su detalle.")
        if st.button("Volver al listado", type="secondary"):
            _safe_nav("pages/03_Historial_Alumnos_Evaluados.py")
        st.stop()

    student = fetch_student(student_id)
    if not student:
        if st.button("Volver al listado", type="secondary"):
            _safe_nav("pages/03_Historial_Alumnos_Evaluados.py")
        st.stop()

    enrollment = build_active_enrollment(student_id)
    evaluations = fetch_evaluations(student_id)

    render_header(student, enrollment)
    st.markdown("---")
    render_evaluations(evaluations)

    st.markdown("---")
    if st.button("Volver al listado", type="secondary"):
        _safe_nav("pages/03_Historial_Alumnos_Evaluados.py")


if __name__ == "__main__":
    main()
