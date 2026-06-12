import os
from datetime import date
import io
import pandas as pd
from openpyxl.utils import get_column_letter

import requests
import streamlit as st

from ui_common import ensure_auth, paginate_list, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


LECTURA_QUESTIONS = [
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
]


ESCRITURA_QUESTIONS = [
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


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def render_styles():
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1320px;
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }
            div[data-testid="stButton"] button,
            div[data-testid="stDownloadButton"] button {
                border-radius: 10px;
                font-weight: 700;
                min-height: 42px;
            }
            .summary-card {
                border: 1px solid var(--info-box-border);
                border-radius: 14px;
                padding: 14px 18px;
                background: var(--info-box-bg);
                min-height: 78px;
            }
            .summary-label {
                font-size: 13px;
                font-weight: 700;
                color: var(--info-label-color);
                margin: 0 0 8px 0;
            }
            .summary-value {
                font-size: 24px;
                font-weight: 800;
                color: var(--info-value-color);
                margin: 0;
            }
            .evaluation-card {
                border: 1px solid var(--info-box-border);
                border-radius: 14px;
                padding: 18px 20px;
                margin-bottom: 14px;
                background: var(--info-box-bg);
            }
            .eval-label {
                font-size: 13px;
                font-weight: 700;
                color: var(--info-label-color);
                margin: 0 0 0px 0;
            }
            .eval-value {
                font-size: 16px;
                font-weight: 800;
                color: var(--info-value-color);
                margin: 0;
            }
            .badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 5px 15px;
                border-radius: 999px;
                font-size: 13px;
                font-weight: 800;
                width: fit-content;
            }
            .badge-high  { color: #fecaca; }
            .badge-medium { color: #fde68a; }
            .badge-low   { color: #bbf7d0; }
            .badge-neutral { color: var(--badge-none-color); }
            .scale-box {
                border: 1px solid var(--summary-border);
                border-radius: 14px;
                padding: 16px 18px;
                background: var(--summary-bg);
                color: var(--summary-color);
                font-size: 14px;
                font-weight: 700;
                margin-bottom: 24px;
            }
            .question-row {
                border-bottom: 1px solid var(--border-color);
                padding: 6px 0 4px 0;
            }
            .question-text {
                font-size: 15px;
                font-weight: 650;
                color: var(--text-primary);
                margin: 0;
            }
            .result-box {
                border: 1px solid var(--summary-border);
                border-radius: 14px;
                padding: 18px 20px;
                background: var(--summary-bg);
                margin-top: 20px;
            }
            .result-title {
                font-size: 18px;
                font-weight: 800;
                color: var(--info-value-color);
                margin: 0 0 8px 0;
            }
            .result-text {
                font-size: 15px;
                font-weight: 700;
                color: var(--summary-color);
                margin: 0;
            }
            div[data-testid="stDownloadButton"] button {
                margin-top: 22px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        r = requests.get(
            f"{API_URL}/students/",
            headers=auth_headers(),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", data)
    except Exception as e:
        st.error(f"No se pudieron cargar los alumnos: {e}")
        return []


def fetch_student_grade(student_id: int):
    cache = st.session_state.setdefault("student_grade_cache", {})

    if student_id in cache:
        return cache[student_id]

    try:
        r = requests.get(
            f"{API_URL}/students/{student_id}/",
            headers=auth_headers(),
            timeout=12,
        )

        if r.status_code == 200:
            data = r.json()
            grade = data.get("current_grade")
            cache[student_id] = grade
            return grade

    except Exception:
        pass

    cache[student_id] = None
    return None


def create_evaluation(
    student_id: int,
    evaluated_at: date,
    diagnosis: str,
    notes: str,
    probability=None,
    answers=None,
    model_version=None,
    student_grade=None,
    student_age=None,
):
    payload = {
        "student": student_id,
        "evaluated_at": evaluated_at.isoformat()
        if hasattr(evaluated_at, "isoformat")
        else str(evaluated_at),
        "diagnosis": diagnosis,
        "notes": notes or "",
    }

    if probability is not None and probability != "":
        payload["probability"] = probability

    if answers is not None:
        payload["answers"] = answers

    if model_version:
        payload["model_version"] = model_version

    if student_grade is not None:
        payload["student_grade"] = student_grade

    if student_age is not None:
        payload["student_age"] = student_age

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
    payload = {
        "student": student_id,
        "answers": answers,
    }

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


def get_probability_value(probability):
    if probability in (None, ""):
        return None

    try:
        return float(probability)
    except (TypeError, ValueError):
        return None


def format_probability(probability):
    value = get_probability_value(probability)

    if value is None:
        return "N/D"

    if value <= 1:
        return f"{value:.2%}"

    return f"{value:.2f}%"


def bucket_label(probability) -> str:
    value = get_probability_value(probability)

    if value is None:
        return "Sin diagnóstico"

    if value < 0.60:
        return "Nivel bajo"

    if value <= 0.85:
        return "Nivel medio"

    return "Nivel alto"


def diagnosis_class(probability=None, diagnosis=None):
    text = str(diagnosis or "").lower()
    value = get_probability_value(probability)

    if "alto" in text:
        return "badge-high"

    if "medio" in text:
        return "badge-medium"

    if "bajo" in text:
        return "badge-low"

    if value is not None:
        if value < 0.60:
            return "badge-low"

        if value <= 0.85:
            return "badge-medium"

        return "badge-high"

    return "badge-neutral"


def evals_to_excel(evals: list[dict]) -> bytes:
    rows = []
    
    # Crear lista combinada de todas las preguntas (30 total)
    all_questions = LECTURA_QUESTIONS + ESCRITURA_QUESTIONS

    for ev in evals:
        probability = ev.get("probability")
        diagnosis = ev.get("diagnosis") or bucket_label(probability)

        row = {
            "Fecha": ev.get("evaluated_at", "-"),
            "Alumno": ev.get("student_name") or f"Alumno #{ev.get('student')}",
            "Diagnóstico": diagnosis,
            "Probabilidad": format_probability(probability),
            "Docente": ev.get("evaluated_by_name") or "Yo",
        }
        
        # Agregar las 30 columnas de respuestas
        answers = ev.get("answers") or []
        for idx in range(30):
            question_num = f"P{idx + 1}"
            
            if idx < len(answers):
                answer_value = answers[idx]
                # Si la respuesta es un string de texto, convertir a número
                if isinstance(answer_value, str):
                    answer_num = {
                        "NUNCA": 1,
                        "RARA VEZ": 2,
                        "A VECES": 3,
                        "FRECUENTEMENTE": 4,
                        "SIEMPRE": 5,
                    }.get(answer_value, None)
                    row[question_num] = answer_num
                else:
                    row[question_num] = answer_value
            else:
                row[question_num] = None

        rows.append(row)

    df = pd.DataFrame(rows)

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Escribir hoja de evaluaciones
        df.to_excel(writer, index=False, sheet_name="Evaluaciones")

        worksheet = writer.sheets["Evaluaciones"]

        # Ajustar ancho de columnas
        worksheet.column_dimensions["A"].width = 16
        worksheet.column_dimensions["B"].width = 28
        worksheet.column_dimensions["C"].width = 22
        worksheet.column_dimensions["D"].width = 18
        worksheet.column_dimensions["E"].width = 22
        
        # Ajustar ancho para las columnas de preguntas (P1-P30)
        for idx in range(30):
            col_letter = get_column_letter(6 + idx)  # Columna F es la 6ta (índice 6)
            worksheet.column_dimensions[col_letter].width = 6
        
        # Crear hoja de Preguntas
        questions_data = []
        for idx, question_text in enumerate(all_questions, start=1):
            questions_data.append({
                "Pregunta": f"P{idx}",
                "Texto": question_text
            })
        
        df_questions = pd.DataFrame(questions_data)
        df_questions.to_excel(writer, index=False, sheet_name="Preguntas")
        
        worksheet_questions = writer.sheets["Preguntas"]
        worksheet_questions.column_dimensions["A"].width = 12
        worksheet_questions.column_dimensions["B"].width = 80

    output.seek(0)
    return output.getvalue()

def go_to_new_evaluation():
    st.session_state.eval_mode = "new"
    st.session_state.pop("predicted", None)
    rerun()


def go_to_list():
    st.session_state.eval_mode = "list"
    st.session_state.pop("predicted", None)
    rerun()


def render_summary(evals):
    total = len(evals)
    high = sum(1 for ev in evals if diagnosis_class(ev.get("probability"), ev.get("diagnosis")) == "badge-high")
    medium = sum(1 for ev in evals if diagnosis_class(ev.get("probability"), ev.get("diagnosis")) == "badge-medium")
    low = sum(1 for ev in evals if diagnosis_class(ev.get("probability"), ev.get("diagnosis")) == "badge-low")

    col1, col2, col3, col4 = st.columns(4)

    items = [
        ("Total", total),
        ("Nivel alto", high),
        ("Nivel medio", medium),
        ("Nivel bajo", low),
    ]

    for col, (label, value) in zip([col1, col2, col3, col4], items):
        with col:
            st.markdown(
                f"""
                <div class="summary-card">
                    <p class="summary-label">{label}</p>
                    <p class="summary-value">{value}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def page_list():
    #st.markdown('<p class="page-title">Mis evaluaciones</p>', unsafe_allow_html=True)
    st.title("Mis evaluaciones")

    evals = fetch_my_evaluations()

    col1, col2 = st.columns([1.1, 6])
    with col1:
        if st.button("Nueva evaluación", type="primary", use_container_width=True):
            go_to_new_evaluation()

    if not evals:
        st.info("Aún no has registrado evaluaciones.")
        return

    render_summary(evals)

    st.divider()

    title_col, download_col = st.columns([5, 1.1], vertical_alignment="center")

    with title_col:
        st.markdown(
            '<p class="section-title">Historial de evaluaciones</p>',
            unsafe_allow_html=True,
        )

    with download_col:
        all_excel = evals_to_excel(evals)

        st.download_button(
        "Descargar Excel",
        data=all_excel or b"",
        file_name="mis_evaluaciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_all_excel",
        use_container_width=True,
        )

    paged_evals, _, _, _ = paginate_list(evals, "evals_page", page_size=10)

    for ev in paged_evals:
        probability = ev.get("probability")
        diagnosis = ev.get("diagnosis") or bucket_label(probability)
        badge_class = diagnosis_class(probability, diagnosis)
        student_name = ev.get("student_name") or f"Alumno #{ev.get('student')}"
        evaluator = ev.get("evaluated_by_name") or "Yo"
        evaluated_at = ev.get("evaluated_at", "-")
        single_excel = evals_to_excel([ev])

        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1.4, 2.5, 1.8, 1.6, 1.1])

            with c1:
                st.markdown(
                    f"""
                    <p class="eval-label">Fecha</p>
                    <p class="eval-value">{evaluated_at}</p>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <p class="eval-label">Alumno</p>
                    <p class="eval-value">{student_name}</p>
                    """,
                    unsafe_allow_html=True,
                )

            with c3:
                st.markdown(
                    f"""
                    <p class="eval-label">Diagnóstico</p>
                    <span class="badge {badge_class}">{diagnosis}</span>
                    """,
                    unsafe_allow_html=True,
                )

            with c4:
                st.markdown(
                    f"""
                    <p class="eval-label">Probabilidad</p>
                    <p class="eval-value">{format_probability(probability)}</p>
                    """,
                    unsafe_allow_html=True,
                )


            with c5:
                st.download_button(
                    "Excel",
                    data=single_excel or b"",
                    file_name=f"evaluacion_{ev.get('id', '') or 'sin_id'}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"excel_{ev.get('id')}",
                    use_container_width=True,
)


def render_question_block(questions, start_number):
    #st.markdown(f'<p class="section-title">{title}</p>', unsafe_allow_html=True)

    responses = []

    for index, question in enumerate(questions, start=start_number):
        st.markdown('<div class="question-row">', unsafe_allow_html=True)

        colq1, colq2 = st.columns([3.5, 2])

        with colq1:
            st.markdown(
                f"""
                <p class="question-text">{index}. {question}</p>
                """,
                unsafe_allow_html=True,
            )

        with colq2:
            value = st.radio(
                label=f"Pregunta {index}",
                options=SCALE_NUM,
                index=0,
                key=f"q_{index}",
                horizontal=True,
                label_visibility="collapsed",
            )

        st.markdown("</div>", unsafe_allow_html=True)
        responses.append(value)

    return responses


def page_new():
    st.title("Nueva evaluación")
    #st.markdown('<p class="page-title">Nueva evaluación</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Responde el cuestionario y obtén el diagnóstico generado por el modelo de Machine Learning.</p>',
        unsafe_allow_html=True,
    )

    students = fetch_students()

    options = [
        (
            student.get("id"),
            f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            student.get("current_grade"),
            student.get("age"),
        )
        for student in students
    ]

    if not options:
        st.warning("No hay alumnos disponibles en tu alcance.")

        if st.button("Volver al listado", key="empty_back"):
            go_to_list()

        return

    options_by_id = {student[0]: student for student in options}

    col1, col2= st.columns([3, 1.2])

    with col1:
        selected_sid = st.selectbox(
            "Selecciona al alumno",
            options=[student[0] for student in options],
            format_func=lambda sid: options_by_id[sid][1],
            key="eval_student_select",
        )

    with col2:
        eval_date = st.date_input("Fecha de evaluación", value=date.today())

    selected_student = options_by_id[selected_sid]
    grade_val = selected_student[2]

    if grade_val in (None, ""):
        grade_val = fetch_student_grade(selected_sid)



    st.write("")

    st.markdown(
        """
        <div class="scale-box">
            Escala de respuesta: 1 = Nunca / 2 = Rara vez / 3 = A veces / 4 = Frecuentemente / 5 = Siempre
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("eval_form", clear_on_submit=False):
        lectura_responses = render_question_block(
            
            LECTURA_QUESTIONS,
            start_number=1,
        )

        escritura_responses = render_question_block(
            
            ESCRITURA_QUESTIONS,
            start_number=len(LECTURA_QUESTIONS) + 1,
        )

        responses_num = lectura_responses + escritura_responses

        st.write("")
        notes = st.text_area(
            "Observaciones del docente (opcional)",
            height=100,
            placeholder="Agrega alguna observación relevante sobre el desempeño del estudiante.",
        )

        st.write("")
        c1, c2, _ = st.columns([1.4, 1, 5])

        get_diag = c1.form_submit_button("Obtener diagnóstico", type="primary")
        cancel = c2.form_submit_button("Cancelar")

    if cancel:
        go_to_list()

    if get_diag:
        answers_txt = [NUM_TO_TXT.get(value, "NUNCA") for value in responses_num]

        with st.spinner("Obteniendo diagnóstico del modelo..."):
            ok, data = ml_evaluate(selected_sid, answers_txt, grade_val)

        if not ok:
            detail = data.get("detail") if isinstance(data, dict) else str(data)
            st.error(f"No se pudo obtener el diagnóstico del modelo: {detail}")
        else:
            prob = float(data.get("probability", 0))
            diagnosis = data.get("diagnosis", "BAJO")
            model_version = data.get("model_version", "")

            st.session_state.predicted = {
                "prob": prob,
                "diagnosis": diagnosis,
                "notes": notes,
                "student_id": selected_sid,
                "evaluated_at": eval_date,
                "model_version": model_version,
                "answers_num": responses_num,
                "answers_txt": answers_txt,
                "student_grade": grade_val,
                "student_age": selected_student[3],
            }

    if st.session_state.get("predicted"):
        prediction = st.session_state.predicted
        prob = prediction.get("prob")
        diagnosis = prediction.get("diagnosis")
        badge_class = diagnosis_class(prob, diagnosis)

        st.markdown(
            f"""
            <div class="result-box">
                <p class="result-title">Resultado generado</p>
                <p class="result-text">
                    Diagnóstico:
                    <span class="badge {badge_class}">{bucket_label(prob)}</span>
                    &nbsp;&nbsp; Probabilidad: {format_probability(prob)}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        save_col, cancel_col, _ = st.columns([1.4, 1, 5])

        if save_col.button("Guardar evaluación", type="primary", key="save_prediction"):
            with st.spinner("Guardando evaluación..."):
                extra = (
                    f"\n\nModelo: {prediction.get('model_version', '')}"
                    if prediction.get("model_version")
                    else ""
                )

                ok, data = create_evaluation(
                    prediction["student_id"],
                    prediction["evaluated_at"],
                    prediction["diagnosis"],
                    (prediction.get("notes") or "") + extra,
                    prediction["prob"],
                    answers=prediction.get("answers_num") or prediction.get("answers_txt"),
                    model_version=prediction.get("model_version"),
                    student_grade=prediction.get("student_grade"),
                    student_age=prediction.get("student_age"),
                )

                if ok:
                    st.session_state.pop("predicted", None)
                    st.session_state.eval_mode = "list"
                    st.success("Evaluación registrada correctamente.")
                    rerun()
                else:
                    st.error(str(data))

        if cancel_col.button("Cancelar", key="cancel_prediction"):
            go_to_list()


def main():
    st.set_page_config(
        page_title="Evaluaciones",
        page_icon="📝",
        layout="wide",
    )

    ensure_auth()
    render_sidebar_nav()
    render_topbar()
    render_styles()

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