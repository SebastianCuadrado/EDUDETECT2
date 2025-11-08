import streamlit as st
from ui_common import ensure_auth, render_sidebar_nav, render_topbar


def main():
    st.set_page_config(page_title="Panel Principal", page_icon="🏠", layout="wide")
    ensure_auth()
    render_sidebar_nav()
    render_topbar()

    st.title("Panel Principal")
    st.info("Próximamente: indicadores y gráficos del colegio.")


if __name__ == "__main__":
    main()

