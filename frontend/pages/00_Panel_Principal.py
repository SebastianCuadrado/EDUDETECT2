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
            r = requests.get(f"{API_URL}/students/{sid}/", headers=auth_headers(), timeout=15)
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


def main():
    st.set_page_config(page_title="Panel", page_icon="📊", layout="wide")
    ensure_auth()
    render_sidebar_nav()
    render_topbar()

    role = (st.session_state.get("user") or {}).get("role", "")
    if role == "ADMIN":
        st.warning("El rol Adminstrador no tiene acceso a este panel. Utiliza el menú lateral para navegar a Alumnos, Usuarios o Salones.")
        st.stop()

    st.title("Panel de Evaluaciones")

    c1, c2, c3 = st.columns([1.2, 1, 1])
    mine = c1.toggle("Solo mis evaluaciones", value=(role != "ADMIN"))
    days = c2.selectbox(
        "Rango",
        options=[7, 30, 90, 180, 365, 9999],
        index=1,
        format_func=lambda x: "Todo" if x == 9999 else f"Últimos {x} días",
    )
    prob_bucket = c3.selectbox("Probabilidad", options=["Todas", ">= 0.8", "0.6–0.79", "< 0.6"], index=0)

    try:
        evals = fetch_all_evaluations(mine=mine)
    except Exception as e:
        st.error(f"No se pudo cargar evaluaciones: {e}")
        return

    df = to_df(evals)
    if df.empty:
        st.info("No hay evaluaciones registradas para los filtros seleccionados.")
        return

    if days != 9999:
        start_dt = pd.Timestamp(datetime.today() - timedelta(days=days))
        df = df[df["evaluated_at"] >= start_dt]

    if prob_bucket != "Todas":
        if prob_bucket == ">= 0.8":
            df = df[df["probability"].fillna(0) >= 0.8]
        elif prob_bucket == "0.6–0.79":
            df = df[(df["probability"].fillna(0) >= 0.6) & (df["probability"].fillna(0) < 0.8)]
        else:
            df = df[df["probability"].fillna(0) < 0.6]

    total = int(len(df))
    by_diag = df["diagnosis"].value_counts()
    n_alto = int(by_diag.get("ALTO", 0))
    n_medio = int(by_diag.get("MEDIO", 0))
    n_bajo = int(by_diag.get("BAJO", 0))
    avg_prob = float(df["probability"].dropna().mean()) if df["probability"].notna().any() else 0.0
    last_date = df["evaluated_at"].max()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Evaluaciones", f"{total}")
    k2.metric("Alto / Medio / Bajo", f"{n_alto} / {n_medio} / {n_bajo}")
    k3.metric("Prob. promedio", f"{avg_prob:.3f}")
    k4.metric("Última eval.", "-" if pd.isna(last_date) else last_date.date().isoformat())

    st.markdown("---")

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Distribución por nivel")
        st.bar_chart(df["diagnosis"].value_counts(), height=260)

    with c_right:
        st.subheader("Evolución de evaluaciones")
        ts = df.set_index("evaluated_at").resample("W").size().rename("Evaluaciones")
        if not ts.empty:
            st.line_chart(ts, height=260)
        else:
            st.caption("Sin datos en el rango seleccionado")

    st.subheader("Distribución de probabilidad")
    try:
        st.histogram(df, x="probability", bins=20, height=260)
    except Exception:
        cuts = pd.cut(df["probability"].fillna(0), bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], include_lowest=True)
        counts = cuts.value_counts().sort_index()
        chart_df = counts.rename_axis("bin").reset_index(name="count")
        chart_df["bin"] = chart_df["bin"].astype(str)
        st.bar_chart(chart_df.set_index("bin")["count"], height=260)

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
        df["age_group"] = pd.cut(df["age"].fillna(-1), bins=[-1] + bins, labels=["N/D"] + labels)
        c1, c2 = st.columns(2)
        with c1:
            st.bar_chart(df["age_group"].value_counts().sort_index())
        with c2:
            st.bar_chart(df.groupby(["age_group", "diagnosis"], observed=False).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()

