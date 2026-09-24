import streamlit as st
import pandas as pd
import inspect

# ==========================================
# CONFIGURACIÓN DE PÁGINA (Menú y barra visibles)
# ==========================================
st.set_page_config(
    page_title="Buscador de Summaries",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS limpios (sin ocultar el header nativo de Streamlit)
st.markdown("""

""", unsafe_allow_html=True)

# ==========================================
# BASE DE DATOS DE PRUEBA
# ==========================================
@st.cache_data
def cargar_ofertas():
    return pd.DataFrame([
        {
            "id": "OFR-2026-001", "nombre": "Parque Solar Palma East", "tipo": "Tipo A",
            "viento_ms": 29.0, "clearance_mm": 800, "num_strings": 24, "num_modulos": 576,
            "ubicacion": "Mallorca"
        },
        {
            "id": "OFR-2025-089", "nombre": "Planta Fotovoltaica Calvia", "tipo": "Tipo A",
            "viento_ms": 29.0, "clearance_mm": 800, "num_strings": 28, "num_modulos": 640,
            "ubicacion": "Mallorca"
        },
        {
            "id": "OFR-2025-042", "nombre": "Campos Sol II", "tipo": "Tipo B",
            "viento_ms": 29.0, "clearance_mm": 900, "num_strings": 24, "num_modulos": 576,
            "ubicacion": "Mallorca"
        },
        {
            "id": "OFR-2026-015", "nombre": "Estepona Solar Park", "tipo": "Tipo A",
            "viento_ms": 32.0, "clearance_mm": 1000, "num_strings": 32, "num_modulos": 800,
            "ubicacion": "Malaga"
        }
    ])

df_ofertas = cargar_ofertas()

# ==========================================
# PESTAÑAS PRINCIPALES (Buscador vs Código Fuente)
# ==========================================
tab_app, tab_code = st.tabs(["🔍 Buscador de Summaries", "💻 Ver Código Fuente"])

with tab_app:
    # CABECERA
    col_h, col_m1, col_m2 = st.columns([3, 1, 1])
    with col_h:
        st.title("Buscador de Summaries")
        st.caption("Filtro de cálculos estructurales Tipo A y B sincronizado con GOP")
    with col_m1:
        st.metric(label="Ofertas Base", value=len(df_ofertas))
    with col_m2:
        st.metric(label="Estado GOP", value="Conectado")

    st.divider()

    # INPUTS
    st.markdown("##### 1. Parámetros de la nueva oferta")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        viento_in = st.number_input("Viento (m/s) *", value=29.0, step=0.5)
    with c2:
        clearance_in = st.number_input("Clearance (mm) *", value=800, step=50)
    with c3:
        strings_in = st.number_input("Nº de Strings", value=24, step=1)
    with c4:
        modulos_in = st.number_input("Nº de Módulos", value=576, step=12)

    c_sub1, c_sub2 = st.columns([2, 2])
    with c_sub1:
        ubicacion_in = st.text_input("Ubicación", value="Mallorca")
    with c_sub2:
        regla_viento = st.radio("Criterio de Viento", ["Exacto (100%)", "Permitir Superior"], horizontal=True)

    # RESULTADOS
    st.divider()
    st.markdown("##### 2. Resultados compatibles")

    if "Exacto" in regla_viento:
        df_res = df_ofertas[df_ofertas["viento_ms"] == viento_in].copy()
    else:
        df_res = df_ofertas[df_ofertas["viento_ms"] >= viento_in].copy()

    if df_res.empty:
        st.warning("No se encontraron ofertas que cumplan con la condición de viento.")
    else:
        def scoring(row):
            pts = 40.0 if row["clearance_mm"] == clearance_in else 20.0
            pts += 30.0 if row["num_strings"] == strings_in else 10.0
            pts += 30.0 if row["num_modulos"] == modulos_in else 10.0
            return pts

        df_res["pct"] = df_res.apply(scoring, axis=1)
        df_res = df_res.sort_values(by="pct", ascending=False)

        for _, row in df_res.iterrows():
            with st.container():
                r1, r2, r3, r4 = st.columns([2.5, 3, 2, 1])
                with r1:
                    st.markdown(f"**{row['id']}** — {row['nombre']}")
                    st.caption(f"Tipo: {row['tipo']} | Ubicación: {row['ubicacion']}")
                with r2:
                    st.markdown(f"Viento: **{row['viento_ms']} m/s** | Clearance: **{row['clearance_mm']} mm**")
                    st.caption(f"{row['num_strings']} Strings | {row['num_modulos']} Módulos")
                with r3:
                    st.markdown(f"{row['pct']:.0f}% Coincidencia", unsafe_allow_html=True)
                    if row['viento_ms'] == viento_in and row['clearance_mm'] == clearance_in:
                        st.markdown(" Geometría Exacta", unsafe_allow_html=True)
                with r4:
                    st.button("Abrir Summary", key=f"btn_{row['id']}")
                st.divider()

# VISOR DE CÓDIGO FUENTE
with tab_code:
    st.subheader("Código fuente de la aplicación (`app.py`)")
    st.caption("Puedes revisar o copiar el código que está corriendo en producción:")
    with open(__file__, "r", encoding="utf-8") as f:
        code_text = f.read()
    st.code(code_text, language="python")
    