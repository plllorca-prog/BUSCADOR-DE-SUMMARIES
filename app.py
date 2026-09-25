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

# Estilos CSS limpios
st.markdown("""

""", unsafe_allow_html=True)

# ==========================================
# BASE DE DATOS REAL (EXCEL GOP - CRUZANDO PESTAÑAS)
# ==========================================
@st.cache_data
def cargar_ofertas():
    archivo_excel = "DataBase_Offers_V02-20260924.xlsx"
    
    try:
        # 1. Leer ambas pestañas
        df_raw = pd.read_excel(archivo_excel, sheet_name="RawData_1")
        df_data = pd.read_excel(archivo_excel, sheet_name="Data")
        
        # 2. Filtrar solo las ofertas de categoría A en RawData_1
        df_raw_a = df_raw[df_raw["offer_category"] == "A"].copy()
        
        # 3. Cruzar (Merge) con la pestaña 'Data' usando nombre de proyecto y versión
        df_merged = pd.merge(
            df_raw_a[["proj_name", "version", "offer_category"]], 
            df_data, 
            on=["proj_name", "version"], 
            how="inner"
        )
        
        # 4. Adaptar los nombres de las columnas reales
        df_merged["id"] = df_merged["proj_name"] + " (v" + df_merged["version"].astype(str) + ")"
        df_merged["nombre"] = df_merged["client"]
        df_merged["tipo"] = df_merged["offer_category"] + " (" + df_merged["code"].astype(str) + ")"
        df_merged["ubicacion"] = df_merged["country"]
        
        # Extraer la ruta directamente de la pestaña Data
        df_merged["ruta_summary"] = df_merged["file_root"]
        
        # Parámetros técnicos estructurales
        df_merged["viento_ms"] = df_merged["wind_spd"]
        df_merged["clearance_mm"] = df_merged["min_clearance"]
        
        # Limpieza de datos (sin strings ni módulos)
        df_merged = df_merged.fillna({
            "viento_ms": 0, "clearance_mm": 0, 
            "ubicacion": "Desconocido",
            "ruta_summary": "Sin ruta disponible"
        })
        
        return df_merged
    except Exception as e:
        st.error(f"Error al leer el Excel: {e}")
        return pd.DataFrame()

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
        st.caption("Filtro de cálculos estructurales sincronizado con Excel GOP")
    with col_m1:
        st.metric(label="Ofertas Base", value=len(df_ofertas))
    with col_m2:
        st.metric(label="Estado BBDD", value="Conectado")

    st.divider()

    # INPUTS
    st.markdown("##### 1. Parámetros de la nueva oferta")
    c1, c2 = st.columns(2)
    with c1:
        viento_in = st.number_input("Viento (m/s) *", value=26.0, step=0.5)
    with c2:
        clearance_in = st.number_input("Clearance (mm) *", value=500, step=50)

    c_sub1, c_sub2 = st.columns([2, 2])
    with c_sub1:
        ubicacion_in = st.text_input("Ubicación", value="Kuwait")
    with c_sub2:
        regla_viento = st.radio("Criterio de Viento", ["Exacto (100%)", "Permitir Superior"], horizontal=True)

    # RESULTADOS
    st.divider()
    st.markdown("##### 2. Resultados compatibles")
    
    if df_ofertas.empty:
        st.warning("No se ha cargado la base de datos o el archivo no está disponible.")
    else:
        # Filtrado estricto por viento
        if "Exacto" in regla_viento:
            df_res = df_ofertas[df_ofertas["viento_ms"] == viento_in].copy()
        else:
            df_res = df_ofertas[df_ofertas["viento_ms"] >= viento_in].copy()

        if df_res.empty:
            st.warning("No se encontraron ofertas que cumplan con la condición de viento.")
        else:
            def scoring(row):
                # Puntuación basada solo en el Clearance (100% si coincide, 75% si no)
                return 100.0 if row["clearance_mm"] == clearance_in else 75.0

            df_res["pct"] = df_res.apply(scoring, axis=1)
            df_res = df_res.sort_values(by="pct", ascending=False)

            for _, row in df_res.iterrows():
                with st.container():
                    r1, r2, r3, r4 = st.columns([2.5, 3, 2, 1])
                    with r1:
                        st.markdown(f"**{row['id']}**")
                        st.caption(f"Cliente: {row['nombre']} | Ubicación: {row['ubicacion']}")
                    with r2:
                        st.markdown(f"Viento: **{row['viento_ms']} m/s** | Clearance: **{row['clearance_mm']} mm**")
                        st.caption(f"Tipo: {row['tipo']}")
                    with r3:
                        st.markdown(f"{row['pct']:.0f}% Coincidencia", unsafe_allow_html=True)
                        if row['viento_ms'] == viento_in and row['clearance_mm'] == clearance_in:
                            st.markdown(" Geometría Exacta", unsafe_allow_html=True)
                    with r4:
                        # Al hacer clic, muestra la ruta extraída de la BBDD
                        if st.button("Ver Ruta", key=f"btn_{row['proj_name']}_{row['version']}"):
                            st.info(f"📁 {row['ruta_summary']}")
                    st.divider()

# VISOR DE CÓDIGO FUENTE
with tab_code:
    st.subheader("Código fuente de la aplicación (`app.py`)")
    st.caption("Puedes revisar o copiar el código que está corriendo en producción:")
    with open(__file__, "r", encoding="utf-8") as f:
        code_text = f.read()
    st.code(code_text, language="python")