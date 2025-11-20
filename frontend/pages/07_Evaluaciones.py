import os
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


def ml_evaluate(student_id: int, answers: list[str], grade: int | None = None):
    payload = {"student": student_id, "answers": answers}
    if grade is not None:
        payload["grade"] = grade
    r = requests.post(
        f"{API_URL}/ml/evaluate/",
        headers=auth_headers() | {"Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if r.status_code in (200, 201):
        return True, r.json()
    try:
        return False, r.json()
    except Exception:
        return False, {"detail": r.text}


def bucket_label(prob: float | None) -> str:
    if prob is None:
        return "-"
    if prob < 0.60:
        return "Menos del 60% (Nivel Bajo)"
    if prob <= 0.85:
        return "Entre 60% - 85% (Nivel Medio)"
    return "Más del 85% (Nivel Alto)"


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
            p = ev.get("probability")
            c3.write(bucket_label(p if p not in (None, "") else None))
            c4.write("-" if p in (None, "") else f"{float(p):.3f}")
            c5.caption(ev.get("evaluated_by_name") or "Yo")


def page_new():
    st.markdown("### Nueva evaluación")
    st.caption("Responde el cuestionario y obtén el diagnóstico generado por el modelo (ML).")

    students = fetch_students()
    options = [
        (
            s.get("id"),
            f"{s.get('first_name','')} {s.get('last_name','')}".strip(),
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
        col1, col2, col3 = st.columns([3, 1.2, 1])
        with col1:
            student_idx = st.selectbox(
                "Selecciona al alumno",
                options=list(range(len(options))),
                format_func=lambda i: options[i][1],
            )
        with col2:
            eval_date = st.date_input("Fecha de evaluación", value=date.today())
        with col3:
            grade_val = st.number_input("Grado", min_value=1, max_value=12, value=1, step=1)

        st.divider()
        st.caption("Escala: 1=NUNCA, 2=RARA VEZ, 3=A VECES, 4=FRECUENTEMENTE, 5=SIEMPRE")

        QUESTIONS = [
            # SECCIÓN A · LECTURA
            "Presenta dificultad para dividir las palabras en sílabas.",
            "Tiene dificultad para relacionar letras con sus sonidos (conversión grafema-fonema).",
            "Omite o añade letras o sílabas al leer palabras o textos.",
            "Sustituye letras o sílabas con sonidos parecidos (p/b, d/t, m/n).",
            "Invierte letras o sílabas durante la lectura (por ejemplo, “sol” por “los”).",
            "Une o separa palabras de forma incorrecta al leer.",
            "Lee lentamente o con poca precisión.",
            "Necesita leer en voz alta para comprender un texto.",
            "Pierde el renglón o se salta palabras al leer.",
            "Tiene dificultad para comprender el contenido general de lo leído.",
            "No respeta signos de puntuación al leer (coma, punto, interrogación).",
            "Lee sin entonación o de manera monótona.",
            "Señala con el dedo mientras lee para no perderse.",
            "Presenta rectificaciones o repeticiones constantes al leer.",
            "Tiene dificultad para pronunciar palabras nuevas o largas.",
            # SECCIÓN B · ESCRITURA
            "Sustituye letras o sílabas al escribir (por ejemplo, “p” por “b”).",
            "Omite letras o sílabas al escribir palabras.",
            "Invierte letras al escribir (por ejemplo, escribe “b” en lugar de “d”).",
            "Une o separa palabras de manera incorrecta al escribir.",
            "Presenta errores de ortografía frecuentes (reglas básicas).",
            "Alterna el uso de mayúsculas y minúsculas dentro de una misma palabra.",
            "Escribe con letras de tamaño irregular o ilegible.",
            "Muestra dificultad para mantener el orden en la escritura dentro de la línea.",
            "Tiene pobreza de vocabulario al expresarse por escrito.",
            "Le cuesta elaborar oraciones con sentido completo.",
            "No utiliza conectores (como “y”, “pero”, “porque”) al redactar frases.",
            "Presenta dificultades para organizar sus ideas por escrito.",
            "Escribe oraciones muy cortas o sin coherencia.",
            "Comete errores ortográficos arbitrarios o sin seguir reglas.",
            "Muestra dificultad para redactar textos o composiciones por sí mismo(a).",
        ]

        SCALE = ["NUNCA", "RARA VEZ", "A VECES", "FRECUENTEMENTE", "SIEMPRE"]
        SCALE_NUM = [1, 2, 3, 4, 5]
        NUM_TO_TXT = {i + 1: SCALE[i] for i in range(5)}

        responses_num: list[int] = []
        for i, question in enumerate(QUESTIONS, start=1):
            colq1, colq2 = st.columns([3, 2])
            with colq1:
                st.write(f"{i}. {question}")
            with colq2:
                value = st.radio("", SCALE_NUM, index=0, key=f"q_{i}", horizontal=True)
            responses_num.append(value)

        st.divider()
        notes = st.text_area("Observaciones del docente (opcional)", height=100)

        c1, c2, _ = st.columns([1, 1, 5])
        get_diag = c1.form_submit_button("Obtener diagnóstico")
        cancel = c2.form_submit_button("Cancelar")

    if cancel:
        st.session_state.eval_mode = "list"
        st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

    if get_diag:
        sid = options[student_idx][0]
        answers_txt = [NUM_TO_TXT.get(v, "NUNCA") for v in responses_num]
        ok, data = ml_evaluate(sid, answers_txt, grade_val)
        if not ok:
            detail = data.get("detail") if isinstance(data, dict) else str(data)
            st.error(f"No se pudo obtener diagnóstico del modelo: {detail}")
        else:
            prob = float(data.get("probability", 0))
            diagnosis = data.get("diagnosis", "BAJO")
            model_version = data.get("model_version", "")
            st.session_state.predicted = {
                "prob": prob,
                "diagnosis": diagnosis,
                "notes": notes,
                "student_id": sid,
                "evaluated_at": eval_date,
                "model_version": model_version,
            }

    if st.session_state.get("predicted"):
        pr = st.session_state.predicted
        st.success(f"Resultado: {bucket_label(float(pr['prob']))} · Probabilidad: {float(pr['prob']):.3f}")
        save_col, cancel_col, _ = st.columns([1, 1, 6])
        if save_col.button("Guardar evaluación"):
            with st.spinner("Guardando evaluación..."):
                extra = f"\n\nModelo: {pr.get('model_version','')}" if pr.get("model_version") else ""
                ok, data = create_evaluation(
                    pr["student_id"],
                    pr["evaluated_at"],
                    pr["diagnosis"],
                    (pr.get("notes") or "") + extra,
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
