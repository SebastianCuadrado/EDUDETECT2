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


def fetch_students(query=None, year=None, grade=None, section=None, is_admin=False):
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
        url = f"{API_URL}/students/"
        r = requests.get(url, headers=auth_headers(), params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudo cargar el listado: {e}")
        return []


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


def initials(first, last):
    return (first[:1] or "").upper() + (last[:1] or "").upper()


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


def main():
    st.set_page_config(page_title="Alumnos", page_icon="👥", layout="wide")
    ensure_auth()
    render_sidebar_nav()
    render_topbar()

    role = (st.session_state.get("user") or {}).get("role")
    is_admin = role == "ADMIN"
    st.markdown("### Lista de Alumnos" if is_admin else "### Mis alumnos")
    if is_admin:
        col_new, _ = st.columns([1, 5])
        if col_new.button("Registrar alumno"):
            try:
                if hasattr(st, "switch_page"):
                    st.switch_page("pages/04_Registrar_Estudiante.py")
            except Exception:
                pass

    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    query = c1.text_input("Buscar alumno...", placeholder="nombre, apellido o DNI")
    y = c2.number_input("Año", min_value=2000, max_value=2100, value=date.today().year, step=1)
    g = c3.number_input("Grado", min_value=1, max_value=12, value=1, step=1)
    s = c4.text_input("Sección", max_chars=2, value="A")

    col_btn, _ = st.columns([1, 5])
    do = col_btn.button("Filtrar")

    if do or "students_eval_cache" not in st.session_state:
        st.session_state.students_eval_cache = fetch_students(query, y, g, s, is_admin=is_admin)

    students = st.session_state.get("students_eval_cache", [])

    left, right = st.columns([1.6, 1])

    with left:
        for stu in students:
            st.container(border=True)
            col_a, col_b, col_c, col_d = st.columns([0.9, 3, 2, 1.2])
            init = initials(stu.get("first_name", ""), stu.get("last_name", ""))
            with col_a:
                purl = stu.get('photo')
                if purl:
                    st.image(purl, width=56)
                else:
                    st.markdown(f"**{init}**")
            with col_b:
                st.markdown(f"**{stu.get('first_name','')} {stu.get('last_name','')}**")
                st.caption(f"DNI: {stu.get('dni','-')}")
            le = stu.get("last_evaluation") or {}
            with col_c:
                st.caption(f"Fecha de evaluación: {le.get('evaluated_at','-')}")
            with col_d:
                prob = le.get("probability", None)
                st.caption(f"Probabilidad: {'No disponible' if prob in (None, '') else prob}")
                if st.button("Ver Detalle", key=f"detail_{stu.get('id')}"):
                    st.session_state.selected_student = stu
                    st.session_state.evals_cache = fetch_evaluations(stu.get("id"))
                    st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

    with right:
        sel = st.session_state.get("selected_student")
        if not sel:
            st.info("Selecciona un alumno para ver el detalle.")
        else:
            init = initials(sel.get("first_name", ""), sel.get("last_name", ""))
            st.markdown(f"### {init}  {sel.get('first_name','')} {sel.get('last_name','')}")
            st.caption(f"DNI: {sel.get('dni','-')}")

            evals = st.session_state.get("evals_cache", [])
            if evals:
                last = evals[0]
                st.write(f"Diagnóstico: {last.get('diagnosis','-')}")
                p = last.get("probability")
                st.write(f"Probabilidad: {'No disponible' if p in (None, '') else p}")
                st.write(f"Fecha de evaluación: {last.get('evaluated_at','-')}")
                st.write(f"Registrado por: {last.get('evaluated_by','-')}")
                if notes := last.get("notes"):
                    st.markdown("**Observaciones principales**")
                    st.markdown(notes)
            else:
                st.info("No hay evaluaciones registradas para este alumno.")

            st.write("")
            if "new_eval_mode" not in st.session_state:
                st.session_state.new_eval_mode = False

            if not st.session_state.new_eval_mode:
                if st.button("Nueva evaluación"):
                    st.session_state.new_eval_mode = True
                    st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
            else:
                st.markdown("#### Nueva evaluación (cuestionario 1–5)")

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
                    "Invierte letras o sílabas al escribir (ejemplo: 'pla' por 'pal').",
                    "Dificultad para copiar de la pizarra al cuaderno.",
                    "Escribe con desorden o sin separación clara de palabras.",
                    "Dificultad para escribir frases coherentes.",
                    # Sección D. Matemáticas básicas
                    "Comete errores frecuentes en operaciones básicas (suma, resta, multiplicación, división).",
                    "Confunde los signos matemáticos (+, −, ×, ÷).",
                    "Dificultad para memorizar tablas de multiplicar.",
                    "Se pierde al resolver problemas con más de un paso.",
                    "Aplica mal conceptos matemáticos en ejercicios.",
                    # Sección E. Factores asociados
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

                with st.form("new_eval_form", clear_on_submit=False):
                    eval_date = st.date_input("Fecha de observación", value=date.today())
                    st.divider()
                    st.caption("Responda del 1 (nunca) al 5 (siempre)")

                    responses = []
                    for i, q in enumerate(QUESTIONS, start=1):
                        colq1, colq2 = st.columns([3, 2])
                        with colq1:
                            st.write(f"{i}. {q}")
                        with colq2:
                            val = st.radio("", [1, 2, 3, 4, 5], index=0, key=f"q_{i}", horizontal=True)
                        responses.append(val)

                    st.divider()
                    notes = st.text_area("Observaciones del docente (opcional)", height=120)
                    submitted = st.form_submit_button("Resultado de la evaluación")

                if submitted:
                    prob = round(random.uniform(0.30, 0.95), 3)
                    if prob >= 0.80:
                        diagnosis = "DISLEXIA"
                    elif prob >= 0.60:
                        diagnosis = "RIESGO"
                    else:
                        diagnosis = "NORMAL"

                    auto_note = "Resultado simulado (sin ML)."
                    full_notes = (notes + "\n\n" if notes else "") + auto_note

                    with st.spinner("Guardando evaluación..."):
                        ok, data = create_evaluation(sel.get("id"), eval_date, diagnosis, full_notes, prob)
                        if ok:
                            st.success(f"Diagnóstico: {diagnosis} · Probabilidad: {prob}")
                            st.session_state.evals_cache = fetch_evaluations(sel.get("id"))
                            st.session_state.new_eval_mode = False
                            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
                        else:
                            if isinstance(data, dict):
                                for k, v in data.items():
                                    st.error(f"{k}: {v}")
                            else:
                                st.error(str(data))


if __name__ == "__main__":
    main()
