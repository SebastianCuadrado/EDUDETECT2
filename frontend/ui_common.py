import base64
import json
import time
from typing import Any, Dict

import streamlit as st


def _get_query_params() -> Dict[str, Any]:
    try:
        return dict(st.query_params)
    except Exception:
        getter = getattr(st, "experimental_get_query_params", None)
        if getter:
            return getter()
        return {}


def _set_query_params(params: Dict[str, Any]):
    try:
        qp = st.query_params
        qp.clear()
        for key, value in params.items():
            qp[key] = value
        return
    except Exception:
        setter = getattr(st, "experimental_set_query_params", None)
        if setter:
            setter(**params)


def _encode_payload(data: Dict[str, Any]) -> str | None:
    try:
        raw = json.dumps(data).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")
    except Exception:
        return None


def _decode_payload(raw: str):
    try:
        data = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
        return json.loads(data)
    except Exception:
        return None


def hydrate_auth_from_query():
    if st.session_state.get("auth"):
        # Ya hidratado — solo asegura que el ?auth no sea visible
        try:
            if "auth" in st.query_params:
                st.query_params.clear()
        except Exception:
            pass
        return
    params = _get_query_params()
    raw = params.get("auth")
    if isinstance(raw, list):
        raw = raw[0]
    if not raw:
        raw = st.session_state.get("_auth_payload")
    if not raw:
        return
    data = _decode_payload(raw)
    if not data or not data.get("token"):
        return
    for key in ("auth", "username", "token", "user"):
        if key in data:
            st.session_state[key] = data[key]
    st.session_state["_auth_payload"] = raw
    # Limpia el ?auth del URL para que no sea visible ni quede en el historial
    try:
        if "auth" in st.query_params:
            st.query_params.clear()
    except Exception:
        pass


def persist_auth_state():
    """Persiste el token en session_state._auth_payload (NO en el URL).
    El URL se limpia en hydrate_auth_from_query al navegar.
    Solo escribe en el URL si _auth_payload aún no existe para la navegación actual.
    """
    if not st.session_state.get("auth"):
        return
    payload = {
        "auth": True,
        "username": st.session_state.get("username"),
        "token": st.session_state.get("token"),
        "user": st.session_state.get("user"),
    }
    encoded = _encode_payload(payload)
    if not encoded:
        return
    st.session_state["_auth_payload"] = encoded
    # Escribe en el URL SOLO si aún no se ha hidratado esta sesión
    # (es decir, es la primera vez que se navega a esta página)
    try:
        current_params = dict(st.query_params)
        if "auth" not in current_params:
            st.query_params["auth"] = encoded
    except Exception:
        params = _get_query_params()
        params["auth"] = encoded
        _set_query_params(params)


def clear_persisted_auth():
    params = _get_query_params()
    if "auth" in params:
        params.pop("auth")
        _set_query_params(params)
    if "_auth_payload" in st.session_state:
        del st.session_state["_auth_payload"]


def logout():
    clear_persisted_auth()

    keys_to_clear = [
        "auth",
        "username",
        "token",
        "user",
        "_auth_payload",

        # Datos temporales por usuario
        "students_eval_cache",
        "teacher_students_page",
        "admin_students_page",
        "admin_eval_students_page",
        "evals_page",
        "eval_mode",
        "predicted",
        "view_student_detail_id",
        "student_grade_cache",
        "current_user_id",
        "selected_student",
        "evals_cache",
        "new_eval_mode",
        "eval_student_select",
    ]

    for key in keys_to_clear:
        st.session_state.pop(key, None)

    st.success("Sesión cerrada")
    time.sleep(0.2)

    try:
        if hasattr(st, "query_params"):
            st.query_params.clear()
    except Exception:
        pass

    try:
        if hasattr(st, "switch_page"):
            st.switch_page("app_login.py")
            return
    except Exception:
        pass

    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()

def paginate_list(items, key: str, page_size: int = 10, label: str | None = None):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)

    if key not in st.session_state:
        st.session_state[key] = 1

    if st.session_state[key] > total_pages:
        st.session_state[key] = total_pages
    if st.session_state[key] < 1:
        st.session_state[key] = 1

    page = st.session_state[key]

    if total_pages > 1:
        st.markdown('<div class="pagination-wrap">', unsafe_allow_html=True)

        prev_col, info_col, next_col = st.columns([1, 2, 1])

        with prev_col:
            if st.button("Anterior", key=f"{key}_prev", disabled=page <= 1, use_container_width=True):
                st.session_state[key] = page - 1
                st.rerun()

        start = (page - 1) * page_size
        end = min(start + page_size, total)

        texto = f"Página <b>{page}</b> de <b>{total_pages}</b> · Mostrando <b>{start+1}-{end}</b> de <b>{total}</b>"
        if label:
            texto = f"{label} · {texto}"

        with info_col:
            st.markdown(
                f"""
                <div style="text-align:center; padding-top:0.45rem; font-size:0.95rem; color:#b8bcc8;">
                    {texto}
                </div>
                """,
                unsafe_allow_html=True
            )

        with next_col:
            if st.button("Siguiente", key=f"{key}_next", disabled=page >= total_pages, use_container_width=True):
                st.session_state[key] = page + 1
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.session_state[key] = 1
        page = 1

    start = (page - 1) * page_size
    end = min(start + page_size, total)

    return items[start:end], page, total_pages, total


def ensure_auth(role: str | None = None):
    hydrate_auth_from_query()
    if not st.session_state.get("auth") or not st.session_state.get("token"):
        st.error("Inicia sesión primero en la página principal.")
        st.stop()
    persist_auth_state()
    if role:
        user_role = (st.session_state.get("user") or {}).get("role")
        if user_role != role:
            st.warning("Acceso restringido: solo usuarios con permisos pueden ver esta página.")
            st.stop()


def render_sidebar_nav():
    import streamlit as st
    from ui_common import hydrate_auth_from_query, logout

    st.markdown(
        """
        <style>
        /* =====================================================
           VARIABLES DE TEMA — Dark por defecto, Light override
           ===================================================== */
        :root {
            --bg-primary:        #0f172a;
            --bg-secondary:      #1e293b;
            --bg-sidebar:        linear-gradient(180deg, #252733 0%, #222430 100%);
            --bg-card:           rgba(255,255,255,0.025);
            --bg-input:          rgba(255,255,255,0.06);
            --border-color:      rgba(255,255,255,0.08);
            --border-sidebar:    rgba(255,255,255,0.06);
            --border-divider:    rgba(255,255,255,0.10);

            --text-primary:      #f8fafc;
            --text-secondary:    #94a3b8;
            --text-muted:        #64748b;
            --text-sidebar-user: #b8c0cc;
            --text-link:         #f8fafc;
            --text-pagination:   #b8bcc8;
            --text-input:        #f8fafc;

            --badge-admin-bg:    rgba(59,130,246,0.16);
            --badge-admin-color: #93c5fd;
            --badge-admin-border:rgba(59,130,246,0.32);
            --badge-doc-bg:      rgba(16,185,129,0.14);
            --badge-doc-color:   #6ee7b7;
            --badge-doc-border:  rgba(16,185,129,0.28);
            --badge-pill-bg:     rgba(255,255,255,0.06);
            --badge-pill-color:  #cbd5e1;
            --badge-pill-border: rgba(255,255,255,0.10);
            --badge-cls-bg:      rgba(59,130,246,0.16);
            --badge-cls-color:   #93c5fd;
            --badge-cls-border:  rgba(59,130,246,0.32);
            --badge-gen-bg:      rgba(16,185,129,0.14);
            --badge-gen-color:   #6ee7b7;
            --badge-gen-border:  rgba(16,185,129,0.28);
            --badge-none-bg:     rgba(255,255,255,0.06);
            --badge-none-color:  #cbd5e1;
            --badge-none-border: rgba(255,255,255,0.10);

            --empty-box-bg:      rgba(30,64,175,0.18);
            --empty-box-border:  rgba(96,165,250,0.18);
            --empty-box-color:   #bfdbfe;

            --hover-link-bg:     rgba(255,255,255,0.07);
            --active-link-bg:    rgba(255,255,255,0.12);
            --active-link-border:rgba(255,255,255,0.15);

            --info-label-color:  rgba(255,255,255,0.55);
            --info-value-color:  #ffffff;
            --info-box-bg:       rgba(255,255,255,0.025);
            --info-box-border:   rgba(255,255,255,0.14);

            --kpi-label-color:   #94a3b8;
            --kpi-value-color:   #f8fafc;
            --kpi-helper-color:  #64748b;
            --summary-bg:        rgba(30,64,175,0.12);
            --summary-border:    rgba(96,165,250,0.18);
            --summary-color:     #bfdbfe;
            --chart-title-color: #f8fafc;

            --student-name-color:#f8fafc;
            --student-meta-bg:   rgba(234,138,34,0.16);
            --student-meta-color:#fcb160;
            --student-meta-border:rgba(234,138,34,0.32);

            --user-name-color:   #f8fafc;
            --user-user-color:   #cbd5e1;
            --user-email-color:  #60a5fa;
        }

        /* =====================================================
           OVERRIDES PARA TEMA CLARO
           ===================================================== */
        @media (prefers-color-scheme: light) {
            :root {
                --bg-primary:        #f1f5f9;
                --bg-secondary:      #e2e8f0;
                --bg-sidebar:        linear-gradient(180deg, #1e2433 0%, #1a1f2e 100%);
                --bg-card:           rgba(0,0,0,0.03);
                --bg-input:          rgba(0,0,0,0.04);
                --border-color:      rgba(0,0,0,0.10);

                --text-primary:      #0f172a;
                --text-secondary:    #475569;
                --text-muted:        #64748b;
                --text-sidebar-user: #b8c0cc;
                --text-link:         #f8fafc;
                --text-pagination:   #334155;
                --text-input:        #0f172a;

                --badge-admin-bg:    rgba(59,130,246,0.12);
                --badge-admin-color: #1d4ed8;
                --badge-admin-border:rgba(59,130,246,0.30);
                --badge-doc-bg:      rgba(16,185,129,0.12);
                --badge-doc-color:   #047857;
                --badge-doc-border:  rgba(16,185,129,0.30);
                --badge-pill-bg:     rgba(0,0,0,0.06);
                --badge-pill-color:  #334155;
                --badge-pill-border: rgba(0,0,0,0.12);
                --badge-cls-bg:      rgba(59,130,246,0.12);
                --badge-cls-color:   #1d4ed8;
                --badge-cls-border:  rgba(59,130,246,0.30);
                --badge-gen-bg:      rgba(16,185,129,0.12);
                --badge-gen-color:   #047857;
                --badge-gen-border:  rgba(16,185,129,0.30);
                --badge-none-bg:     rgba(0,0,0,0.06);
                --badge-none-color:  #475569;
                --badge-none-border: rgba(0,0,0,0.12);

                --empty-box-bg:      rgba(59,130,246,0.08);
                --empty-box-border:  rgba(59,130,246,0.20);
                --empty-box-color:   #1e40af;

                --hover-link-bg:     rgba(255,255,255,0.07);
                --active-link-bg:    rgba(255,255,255,0.15);
                --active-link-border:rgba(255,255,255,0.20);

                --info-label-color:  #64748b;
                --info-value-color:  #0f172a;
                --info-box-bg:       rgba(0,0,0,0.03);
                --info-box-border:   rgba(0,0,0,0.10);

                --kpi-label-color:   #475569;
                --kpi-value-color:   #0f172a;
                --kpi-helper-color:  #94a3b8;
                --summary-bg:        rgba(59,130,246,0.07);
                --summary-border:    rgba(59,130,246,0.20);
                --summary-color:     #1e3a8a;
                --chart-title-color: #0f172a;

                --student-name-color:#0f172a;
                --student-meta-bg:   rgba(234,138,34,0.10);
                --student-meta-color:#92400e;
                --student-meta-border:rgba(234,138,34,0.25);

                --user-name-color:   #0f172a;
                --user-user-color:   #334155;
                --user-email-color:  #1d4ed8;
            }
        }

        /* =====================================================
           ESTILOS GLOBALES QUE USAN LAS VARIABLES
           ===================================================== */
        [data-testid="stSidebarNav"] { display: none; }

        div[data-testid="InputInstructions"] {
            display: none !important;
            visibility: hidden !important;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        }

        /* ===== SIDEBAR SIEMPRE OSCURO (independiente del tema) ===== */
        section[data-testid="stSidebar"] {
            width: 280px !important;
            background: linear-gradient(180deg, #1e2433 0%, #1a1f2e 100%) !important;
            border-right: 1px solid rgba(255,255,255,0.06) !important;
        }

        /* Fuerza fondo oscuro en todos los divs internos del sidebar */
        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] > div > div {
            background: transparent !important;
        }

        /* Links del sidebar — siempre blancos */
        section[data-testid="stSidebar"] .stPageLink a,
        section[data-testid="stSidebar"] .stPageLink a:visited,
        section[data-testid="stSidebar"] .stPageLink a:hover,
        section[data-testid="stSidebar"] .stPageLink a:active,
        section[data-testid="stSidebar"] .stPageLink a * {
            color: #f8fafc !important;
            text-decoration: none !important;
        }

        section[data-testid="stSidebar"] .stPageLink a {
            position: relative;
            width: 100%;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.45rem;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.18s ease;
            background: transparent;
        }

        section[data-testid="stSidebar"] .stPageLink a:hover:not([aria-current="page"]) {
            background: rgba(255,255,255,0.08) !important;
        }

        section[data-testid="stSidebar"] .stPageLink a[aria-current="page"] {
            background: rgba(255,255,255,0.14) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 12px !important;
        }

        section[data-testid="stSidebar"] .stPageLink a[aria-current="page"]::before {
            content: "";
            position: absolute;
            left: 0;
            top: 8px;
            bottom: 8px;
            width: 4px;
            border-radius: 4px;
            background: #4f8cff;
        }

        .logout-wrap {
            margin-top: 1.2rem;
        }

        .logout-wrap .stButton > button {
            width: 100%;
            min-height: 48px;
            border-radius: 12px;
            font-weight: 700;
            border: none;
            background: linear-gradient(180deg, #ff5a5f 0%, #ff4d4f 100%);
            color: white;
            box-shadow: 0 10px 24px rgba(255,77,79,0.18);
        }
        .logout-wrap .stButton > button:hover {
            filter: brightness(1.03);
        }

        /* Padding interno del sidebar */
        section[data-testid="stSidebar"] > div {
            padding-top: 1.2rem;
            padding-bottom: 1rem;
        }

        /* Fuerza blanco en TODOS los textos del sidebar */
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] label {
            color: #f8fafc !important;
        }
        /* Excepto el email que va en azul */
        section[data-testid="stSidebar"] .user-email {
            color: #60a5fa !important;
        }
        section[data-testid="stSidebar"] .sidebar-user {
            color: #b8c0cc !important;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

        .sidebar-title {
            color: #f8fafc !important;
            font-size: 1.9rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .sidebar-divider {
            border: none;
            border-top: 1px solid rgba(255,255,255,0.10);
            margin: 0.8rem 0 1rem 0;
        }

        /* Paginacion */
        .pagination-wrap {
            margin: 0.3rem 0 0.6rem 0;
            padding: 0;
        }
        .pagination-wrap .stButton > button {
            min-height: 36px !important;
            padding: 0.3rem 0.6rem !important;
            font-size: 0.85rem !important;
        }
        .pagination-info {
            color: var(--text-pagination) !important;
        }

        /* ------- Títulos y textos de contenido ------- */
        .page-title {
            font-size: 3rem;
            font-weight: 800;
            color: var(--text-primary);
            line-height: 1.05;
            margin-bottom: 0.35rem;
        }

        .section-title {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }

        .page-subtitle {
            color: var(--text-secondary);
            font-size: 1rem;
            margin-bottom: 1.2rem;
        }

        /* ------- Badges comunes ------- */
        .role-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .role-admin {
            background: var(--badge-admin-bg);
            color: var(--badge-admin-color);
            border-color: var(--badge-admin-border);
        }
        .role-docente {
            background: var(--badge-doc-bg);
            color: var(--badge-doc-color);
            border-color: var(--badge-doc-border);
        }
        .salon-pill {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 0.80rem;
            font-weight: 600;
            background: var(--badge-pill-bg);
            color: var(--badge-pill-color);
            border: 1px solid var(--badge-pill-border);
        }

        /* student badges */
        .classroom-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
            background: var(--badge-cls-bg);
            color: var(--badge-cls-color);
            border: 1px solid var(--badge-cls-border);
        }
        .gender-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
            background: var(--badge-gen-bg);
            color: var(--badge-gen-color);
            border: 1px solid var(--badge-gen-border);
        }
        .no-classroom-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
            background: var(--badge-none-bg);
            color: var(--badge-none-color);
            border: 1px solid var(--badge-none-border);
        }
        .student-meta {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
            background: var(--student-meta-bg);
            color: var(--student-meta-color);
            border: 1px solid var(--student-meta-border);
        }

        /* ------- Textos de usuario/alumno ------- */
        .user-name, .student-name {
            color: var(--user-name-color);
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
        }
        .student-name {
            font-size: 1.35rem;
        }
        .user-username {
            color: var(--user-user-color);
            font-size: 0.98rem;
            font-weight: 600;
            line-height: 1.35;
            margin: 0;
        }
        .user-email {
            color: var(--user-email-color);
            font-size: 0.98rem;
            word-break: break-word;
            margin-top: 0.22rem;
        }

        /* ------- Cajas vacías / info ------- */
        .empty-box {
            background: var(--empty-box-bg);
            border: 1px solid var(--empty-box-border);
            color: var(--empty-box-color);
            border-radius: 16px;
            padding: 18px;
        }

        /* ------- Info box (editar alumno) ------- */
        .info-box {
            border: 1px solid var(--info-box-border);
            border-radius: 14px;
            padding: 16px 18px;
            background: var(--info-box-bg);
            margin-bottom: 16px;
        }
        .info-label {
            font-size: 13px;
            font-weight: 700;
            color: var(--info-label-color);
            margin: 0 0 6px 0;
        }
        .info-value {
            font-size: 18px;
            font-weight: 800;
            color: var(--info-value-color);
            margin: 0;
        }

        /* ------- KPI cards (panel) ------- */
        .kpi-card {
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 18px 18px 16px 18px;
            background: var(--bg-card);
            min-height: 110px;
        }
        .kpi-label {
            color: var(--kpi-label-color);
            font-size: 0.88rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }
        .kpi-value {
            color: var(--kpi-value-color);
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.05;
        }
        .kpi-helper {
            color: var(--kpi-helper-color);
            font-size: 0.85rem;
            margin-top: 0.35rem;
        }
        .summary-box {
            border: 1px solid var(--summary-border);
            background: var(--summary-bg);
            color: var(--summary-color);
            border-radius: 16px;
            padding: 14px 16px;
            margin: 18px 0;
            font-size: 0.98rem;
        }
        .chart-card {
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px 16px 10px 16px;
            background: var(--bg-card);
            margin-bottom: 18px;
        }
        .chart-title {
            color: var(--chart-title-color);
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 0.65rem;
        }

        /* ------- Ocultar elementos de Streamlit ------- */
        [data-testid="stAppDeployButton"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden; }
        [data-testid="stToolbar"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Validación de sesión
    hydrate_auth_from_query()
    if not st.session_state.get("auth"):
        return

    user = st.session_state.get("user") or {}
    username = user.get("username") or st.session_state.get("username", "")
    role = user.get("role", "")
    is_admin = role == "ADMIN"

    # Sidebar
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-title">EduDetect</div>
            <div class="sidebar-user">Conectado como {username} · {role}</div>
            <hr class="sidebar-divider">
            """,
            unsafe_allow_html=True,
        )

        page_link = getattr(st, "page_link", None)

        if page_link:
            if not is_admin:
                page_link("pages/00_Panel_Principal.py", label="Panel", icon="📊")

            if is_admin:
                page_link("pages/01_Lista_de_Usuarios.py", label="Usuarios", icon="🧑‍💼")
                page_link("pages/08_Gestion_Alumnos.py", label="Alumnos", icon="🎓")
                page_link("pages/05_Administrar_Salones.py", label="Salones", icon="🏫")
            else:
                page_link("pages/03_Historial_Alumnos_Evaluados.py", label="Alumnos", icon="🎓")
                page_link("pages/07_Evaluaciones.py", label="Evaluaciones", icon="📝")

        # Logout
        st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
        if st.button("Cerrar sesión", type="primary"):
            logout()
        st.markdown("</div>", unsafe_allow_html=True)

def render_topbar():
     hydrate_auth_from_query()
     if not st.session_state.get("auth"):
        return
        user = st.session_state.get("user") or {}
        username = user.get("username") or st.session_state.get("username", "")
        role = user.get("role", "")
        st.caption(f"Conectado: {username} · {role}")