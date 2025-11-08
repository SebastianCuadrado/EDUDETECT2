import os
import random
from datetime import date

import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def fetch_my_evaluations():
    try:
        r = requests.get(
            f"{API_URL}/evaluations/",
            headers=auth_headers(),
            params={"mine": 1},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudieron cargar las evaluaciones: {e}")
        return []


def fetch_students():
    try:
        r = requests.get(f"{API_URL}/students/", headers=auth_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudieron cargar los alumnos: {e}")
        return []


def create_evaluation(student_id: int, evaluated_at: date, diagnosis: str, notes: str, probability=None):
    payload = {
        "student": student_id,
        "evaluated_at": evaluated_at.isoformat() if hasattr(evaluated_at, "isoformat") else str(evaluated_at),
        "diagnosis": diagnosis,
        "notes": notes or "",
    }
    if probability is not None and probability != "":
        payload["probability"] = probability
    r = requests.post(
        f"{API_URL}/evaluations/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def page_list():
    st.markdown("### Mis evaluaciones")
    col_btn, _ = st.columns([1, 6])
    if col_btn.button("Nueva evaluación", type="primary"):
        st.session_state.eval_mode = "new"
        st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

    evals = fetch_my_evaluations()
    if not evals:
        st.info("Aún no has registrado evaluaciones.")
        return

    for ev in evals:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 2])
            c1.caption(str(ev.get("evaluated_at", "-")))
            c2.write(ev.get("student_name") or f"Alumno #{ev.get('student')}")
            c3.write(ev.get("diagnosis", "-"))
            p = ev.get("probability")
            c4.write("-" if p in (None, "") else p)
            c5.caption(ev.get("evaluated_by_name") or "Yo")


def page_new():
    st.markdown("### Nueva evaluación")
    st.caption("Responde el cuestionario y obtén el diagnóstico simulado.")

    # Datos del alumno a evaluar
    students = fetch_students()
    options = [
        (
            s.get("id"),
            f"{s.get('first_name','')} {s.get('last_name','')} - DNI {s.get('dni','')}".strip(),
        )
        for s in students
    ]
    if not options:
        st.warning("No hay alumnos disponibles en tu alcance.")
        if st.button("Volver al listado"):
            st.session_state.eval_mode = "list"
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
        return

    with st.form("eval_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            student_idx = st.selectbox(
                "Selecciona al alumno",
                options=list(range(len(options))),
                format_func=lambda i: options[i][1],
            )
        with col2:
            eval_date = st.date_input("Fecha de evaluación", value=date.today())

        st.divider()
        st.caption("Escala: 1 (nunca) → 5 (siempre)")

        QUESTIONS = [
            # Sección A. Lectura y decodificación
            "Confunde letras con sonidos similares (p/b, d/t, m/n).",
            "Omite o añade sílabas al leer.",
            "Lee lentamente o con baja precisión.",
            "Necesita leer en voz alta para comprender un texto.",
            "Se salta palabras al leer.",
            # Sección B. Comprensión lectora
            "Tiene dificultad para recordar lo que acaba de leer.",
            "Requiere releer varias veces para entender un texto corto.",
            "No identifica la idea principal de un texto corto.",
            "Mezcla personajes o eventos en un relato o cuento breve.",
            "Necesita ayuda frecuente para comprender instrucciones escritas.",
            # Sección C. Escritura y ortografía
            "Comete errores ortográficos repetidos en palabras conocidas.",
            "Invierte letras o sílabas al escribir (ejemplo: ‘pla’ por ‘pal’).",
            "Dificultad para copiar de la pizarra al cuaderno.",
            "Escribe con desorden o sin separación clara de palabras.",
            "Dificultad para escribir frases coherentes.",
            # Sección D. Matemáticas básicas
            "Comete errores frecuentes en operaciones básicas (suma, resta, multiplicación, división).",
            "Confunde los signos matemáticos (+, −, ×, ÷).",
            "Dificultad para memorizar tablas de multiplicar.",
            "Se pierde al resolver problemas con más de un paso.",
            "Aplica mal conceptos matemáticos en ejercicios.",
            # Sección E. Factores asociados: atención, memoria y autorregulación
            "Se distrae con facilidad durante la clase.",
            "Le cuesta seguir instrucciones de más de dos pasos.",
            "Olvida con frecuencia lo que se le acaba de indicar.",
            "Se frustra con facilidad ante errores o tareas largas.",
            "Necesita recordatorios constantes para terminar sus tareas.",
            # Sección F. Factores contextuales y conductuales
            "Muestra poco interés por leer o escribir.",
            "Evita leer en público.",
            "Su avance académico es más lento que el de sus compañeros.",
            "Ha repetido grado o ha sido derivado a apoyo psicopedagógico.",
            "Manifiesta ansiedad o rechazo cuando se le pide leer o escribir en público.",
        ]

        responses = []
        for i, q in enumerate(QUESTIONS, start=1):
            colq1, colq2 = st.columns([3, 2])
            with colq1:
                st.write(f"{i}. {q}")
            with colq2:
                val = st.radio("", [1, 2, 3, 4, 5], index=0, key=f"q_{i}", horizontal=True)
            responses.append(val)

        st.divider()
        notes = st.text_area("Observaciones del docente (opcional)", height=100)

        c1, c2, c3 = st.columns([1, 1, 5])
        get_diag = c1.form_submit_button("Obtener diagnóstico")
        cancel = c2.form_submit_button("Cancelar")

    if cancel:
        st.session_state.eval_mode = "list"
        st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

    if get_diag:
        prob = round(random.uniform(0.30, 0.95), 3)
        if prob >= 0.80:
            diagnosis = "DISLEXIA"
        elif prob >= 0.60:
            diagnosis = "RIESGO"
        else:
            diagnosis = "NORMAL"

        st.session_state.predicted = {
            "prob": prob,
            "diagnosis": diagnosis,
            "notes": notes,
            "student_id": options[student_idx][0],
            "evaluated_at": eval_date,
        }

    if st.session_state.get("predicted"):
        pr = st.session_state.predicted
        st.success(f"Diagnóstico: {pr['diagnosis']} · Probabilidad: {pr['prob']}")
        save_col, cancel_col, _ = st.columns([1, 1, 6])
        if save_col.button("Guardar evaluación"):
            with st.spinner("Guardando evaluación..."):
                ok, data = create_evaluation(
                    pr["student_id"], pr["evaluated_at"], pr["diagnosis"],
                    (pr.get("notes") or "") + "\n\nResultado simulado (sin ML).",
                    pr["prob"],
                )
                if ok:
                    st.session_state.pop("predicted", None)
                    st.session_state.eval_mode = "list"
                    st.success("Evaluación registrada")
                    st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
                else:
                    st.error(str(data))
        if cancel_col.button("Cancelar"):
            st.session_state.pop("predicted", None)
            st.session_state.eval_mode = "list"
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()


def main():
    st.set_page_config(page_title="Evaluaciones", page_icon="📝", layout="wide")
    ensure_auth()
    render_sidebar_nav()
    render_topbar()

    role = (st.session_state.get("user") or {}).get("role")
    if role == "ADMIN":
        st.warning("Esta sección es exclusiva para docentes.")
        return

    if "eval_mode" not in st.session_state:
        st.session_state.eval_mode = "list"

    if st.session_state.eval_mode == "new":
        page_new()
    else:
        page_list()


if __name__ == "__main__":
    main()
