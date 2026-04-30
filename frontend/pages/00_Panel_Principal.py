import os
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from ui_common import ensure_auth, render_sidebar_nav, render_topbar


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Token {token}"} if token else {}


def fetch_all_evaluations(mine: bool = False):
    url = f"{API_URL}/evaluations/"
    params = {"mine": 1} if mine else {}
    out: list[dict] = []

    while url:
        r = requests.get(
            url,
            headers=auth_headers(),
            params=params if url.endswith("/evaluations/") else None,
            timeout=20,
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


def fetch_students_map(student_ids):
    m: dict[int, dict] = {}

    for sid in sorted(set(map(int, student_ids))):
        try:
            r = requests.get(
                f"{API_URL}/students/{sid}/",
                headers=auth_headers(),
                timeout=15,
            )
            if r.status_code == 200:
                m[sid] = r.json()
        except Exception:
            pass

    return m


def to_df(evals: list[dict]) -> pd.DataFrame:
    if not evals:
        return pd.DataFrame(columns=["evaluated_at", "diagnosis", "probability", "student"])

    df = pd.DataFrame(evals)
    df["evaluated_at"] = pd.to_datetime(df["evaluated_at"], errors="coerce")
    return df


def inject_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1280px !important;
            padding-top: 0.5rem !important;
            padding-bottom: 2rem !important;
        }
        .filter-card {
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px 16px 6px 16px;
            margin-bottom: 18px;
            background: var(--bg-card);
        }
        div[data-testid="stSelectbox"] label,
        div[data-testid="stCheckbox"] label {
            color: var(--text-primary) !important;
            font-weight: 700 !important;
        }
        div[data-testid="stSelectbox"] div {
            border-radius: 12px !important;
        }
        [data-testid="stMetric"] {
            background: transparent !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, helper: str = ""):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-helper">{helper}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Panel",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    ensure_auth()
    render_sidebar_nav()
    render_topbar()
    inject_styles()

    role = (st.session_state.get("user") or {}).get("role", "")
    if role == "ADMIN":
        st.warning("El rol Administrador no tiene acceso a este panel. Utiliza el menú lateral para navegar a Alumnos, Usuarios o Salones.")
        st.stop()

    st.markdown('<div class="page-title">Panel de Evaluaciones</div>', unsafe_allow_html=True)


    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1, 1], gap="medium")

    with c1:
        mine = st.toggle("Solo mis evaluaciones", value=(role != "ADMIN"))

    with c2:
        days = st.selectbox(
            "Rango",
            options=[7, 30, 90, 180, 9999],
            index=1,
            format_func=lambda x: "Todo" if x == 9999 else f"Últimos {x} días",
        )

    with c3:
        prob_bucket = st.selectbox(
            "Probabilidad",
            options=["Todas", ">= 0.8", "0.6–0.79", "< 0.6"],
            index=0,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    try:
        evals = fetch_all_evaluations(mine=mine)
    except Exception as e:
        st.error(f"No se pudo cargar evaluaciones: {e}")
        return

    df = to_df(evals)

    if df.empty:
        st.markdown(
            '<div class="empty-box">No hay evaluaciones registradas para los filtros seleccionados.</div>',
            unsafe_allow_html=True,
        )
        return

    if days != 9999:
        start_dt = pd.Timestamp(datetime.today() - timedelta(days=days))
        df = df[df["evaluated_at"] >= start_dt]

    if prob_bucket != "Todas":
        if prob_bucket == ">= 0.8":
            df = df[df["probability"].fillna(0) >= 0.8]
        elif prob_bucket == "0.6–0.79":
            df = df[
                (df["probability"].fillna(0) >= 0.6)
                & (df["probability"].fillna(0) < 0.8)
            ]
        else:
            df = df[df["probability"].fillna(0) < 0.6]

    if df.empty:
        st.markdown(
            '<div class="empty-box">No hay evaluaciones para los filtros aplicados.</div>',
            unsafe_allow_html=True,
        )
        return

    total = int(len(df))
    by_diag = df["diagnosis"].value_counts()

    n_alto = int(by_diag.get("ALTO", 0))
    n_medio = int(by_diag.get("MEDIO", 0))
    n_bajo = int(by_diag.get("BAJO", 0))

    avg_prob = float(df["probability"].dropna().mean()) if df["probability"].notna().any() else 0.0
    last_date = df["evaluated_at"].max()
    last_text = "-" if pd.isna(last_date) else last_date.date().isoformat()

    k1, k2, k3, k4 = st.columns(4, gap="medium")

    with k1:
        kpi_card("Evaluaciones", str(total), "Total según filtros")

    with k2:
        kpi_card("Alto / Medio / Bajo", f"{n_alto} / {n_medio} / {n_bajo}", "Distribución por nivel")

    with k3:
        kpi_card("Prob. promedio", f"{avg_prob:.3f}", "Promedio de probabilidad")

    with k4:
        kpi_card("Última evaluación", last_text, "Fecha más reciente")

    nivel_predominante = by_diag.idxmax() if not by_diag.empty else "N/D"
    st.markdown(
        f"""
        <div class="summary-box">
            Actualmente se muestran <b>{total}</b> evaluaciones. 
            El nivel predominante es <b>{nivel_predominante}</b> y la probabilidad promedio es <b>{avg_prob:.3f}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_left, c_right = st.columns(2, gap="medium")

    with c_left:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Distribución por nivel</div>', unsafe_allow_html=True)

        level_counts = df["diagnosis"].value_counts()
        if not level_counts.empty:
            st.bar_chart(level_counts, height=240)
        else:
            st.caption("Sin datos para mostrar.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Evolución de evaluaciones</div>', unsafe_allow_html=True)

        df_evo = df.copy()
        df_evo["fecha"] = df_evo["evaluated_at"].dt.date

        evo = (
            df_evo.groupby("fecha")
            .size()
            .reset_index(name="Evaluaciones")
        )

        evo["fecha"] = pd.to_datetime(evo["fecha"]).dt.strftime("%d/%m/%Y")

        if not evo.empty:
            st.line_chart(evo.set_index("fecha")["Evaluaciones"], height=240)
        else:
            st.caption("Sin datos en el rango seleccionado.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Distribución de probabilidad</div>', unsafe_allow_html=True)

    try:
        st.histogram(df, x="probability", bins=20, height=240)
    except Exception:
        cuts = pd.cut(
            df["probability"].fillna(0),
            bins=[0.00, 0.20, 0.40, 0.60, 0.80, 1.00],
            include_lowest=True,
        )
        counts = cuts.value_counts().sort_index()
        chart_df = counts.rename_axis("bin").reset_index(name="count")
        chart_df["bin"] = chart_df["bin"].astype(str)
        st.bar_chart(chart_df.set_index("bin")["count"], height=240)

    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Ver análisis por edad"):
        st.caption("Se usa la edad registrada del alumno.")

        stu_map = fetch_students_map(df["student"].unique())

        def age_from_map(sid):
            try:
                return (stu_map.get(int(sid)) or {}).get("age")
            except Exception:
                return None

        df["age"] = df["student"].apply(age_from_map)

        bins = [0, 6, 8, 10, 20]
        labels = ["≤6", "7–8", "9–10", "≥11"]

        df["age_group"] = pd.cut(
            df["age"].fillna(-1),
            bins=[-1] + bins,
            labels=["N/D"] + labels,
        )

        age_col1, age_col2 = st.columns(2, gap="medium")

        with age_col1:
            st.markdown("#### Evaluaciones por grupo de edad")
            st.bar_chart(df["age_group"].value_counts().sort_index(), height=240)

        with age_col2:
            st.markdown("#### Nivel por grupo de edad")
            st.bar_chart(
                df.groupby(["age_group", "diagnosis"], observed=False)
                .size()
                .unstack(fill_value=0),
                height=240,
            )


if __name__ == "__main__":
    main()