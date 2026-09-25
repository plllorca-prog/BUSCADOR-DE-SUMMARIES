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
# BASE DE DATOS REAL (SOLO PESTAÑA RawData_1)
# ==========================================
@st.cache_data
def cargar_ofertas():
    archivo_excel = "DataBase_Offers_V02-20260924.xlsx"
    
    try:
        # 1. Leer SOLO la pestaña RawData_1
        df_raw = pd.read_excel(archivo_excel, sheet_name="RawData_1")
        
        # 2. Filtrar ofertas que contengan "A" en offer_category (ej: "1 A", "A", "A ")
        es_categoria_a = df_raw["offer_category"].astype(str).str.contains("A", case=False, na=False)
        df_ofertas = df_raw[es_categoria_a].copy()
        
        # 3. Eliminar duplicados por proyecto y versión
        df_ofertas = df_ofertas.drop_duplicates(subset=["proj_name", "version"])
        
        # 4. Adaptar columnas generales
        df_ofertas["id"] = df_ofertas["proj_name"].astype(str) + " (v" + df_ofertas["version"].astype(str) + ")"
        df_ofertas["nombre"] = df_ofertas["client"]
        df_ofertas["tipo"] = df_ofertas["offer_category"].astype(str) + " (" + df_ofertas["code"].astype(str) + ")"
        df_ofertas["ubicacion"] = df_ofertas["country"]
        
        # Extraer ruta del archivo
        df_ofertas["ruta_summary"] = df_ofertas["file_root"] if "file_root" in df_ofertas.columns else "Sin ruta disponible"
        
        # 5. Convertir valores numéricos asegurando float
        df_ofertas["viento_ms"] = pd.to_numeric(df_ofertas["wind_spd"], errors="coerce").fillna(0.0)
        df_ofertas["max_clearance_mm"] = pd.to_numeric(df_ofertas["max_clearance"], errors="coerce").fillna(0.0)
        df_ofertas["longitud_tr1"] = pd.to_numeric(df_ofertas["length_Tr1"], errors="coerce").fillna(0.0)
        
        # Limpieza de nulos en textos
        df_ofertas = df_ofertas.fillna({
            "ubicacion": "Desconocido",
            "ruta_summary": "Sin ruta disponible"
        })
        
        return df_ofertas
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
    c1, c2, c3 = st.columns(3)
    with c1:
        viento_in = st.number_input("Viento (wind_spd) *", value=55.5, step=0.5)
    with c2:
        clearance_in = st.number_input("Max Clearance (mm) *", value=900, step=50)
    with c3:
        longitud_in = st.number_input("Longitud Tr1 *", value=139.2, step=1.0)

    c_sub1, c_sub2 = st.columns([2, 2])
    with c_sub1:
        ubicacion_in = st.text_input("Ubicación", value="Saudi Arabia")
    with c_sub2:
        regla_viento = st.radio("Criterio de Viento", ["Exacto (100%)", "Permitir Superior"], horizontal=True)

    # RESULTADOS
    st.divider()
    st.markdown("##### 2. Resultados compatibles")
    
    if df_ofertas.empty:
        st.warning("No se ha cargado la base de datos o el archivo no está disponible.")
    else:
        # Filtrado por viento con un pequeño margen para imprecisiones decimales
        if "Exacto" in regla_viento:
            df_res = df_ofertas[abs(df_ofertas["viento_ms"] - viento_in) < 0.1].copy()
        else:
            df_res = df_ofertas[df_ofertas["viento_ms"] >= (viento_in - 0.1)].copy()

        if df_res.empty:
            st.warning("No se encontraron ofertas que cumplan con la condición de viento.")
        else:
            def scoring(row):
                pts = 0.0
                if abs(row["max_clearance_mm"] - clearance_in) < 1.0:
                    pts += 50.0
                if abs(row["longitud_tr1"] - longitud_in) < 0.1:
                    pts += 50.0
                return pts

            df_res["pct"] = df_res.apply(scoring, axis=1)
            df_res = df_res.sort_values(by="pct", ascending=False)

            for idx, (_, row) in enumerate(df_res.iterrows()):
                with st.container():
                    r1, r2, r3, r4 = st.columns([2.5, 3, 2, 1])
                    with r1:
                        st.markdown(f"**{row['id']}**")
                        st.caption(f"Cliente: {row['nombre']} | Ubicación: {row['ubicacion']}")
                    with r2:
                        st.markdown(f"Viento: **{row['viento_ms']} m/s** | Max Clearance: **{row['max_clearance_mm']} mm**")
                        st.caption(f"Longitud Tr1: {row['longitud_tr1']} | Tipo: {row['tipo']}")
                    with r3:
                        st.markdown(f"{row['pct']:.0f}% Coincidencia", unsafe_allow_html=True)
                        if abs(row['viento_ms'] - viento_in) < 0.1 and abs(row['max_clearance_mm'] - clearance_in) < 1.0 and abs(row['longitud_tr1'] - longitud_in) < 0.1:
                            st.markdown(" Geometría Exacta", unsafe_allow_html=True)
                    with r4:
                        if st.button("Ver Ruta", key=f"btn_{idx}_{row['proj_name']}_{row['version']}"):
                            st.info(f"📁 {row['ruta_summary']}")
                    st.divider()

# VISOR DE CÓDIGO FUENTE
with tab_code:
    st.subheader("Código fuente de la aplicación (`app.py`)")
    st.caption("Puedes revisar o copiar el código que está corriendo en producción:")
    with open(__file__, "r", encoding="utf-8") as f:
        code_text = f.read()
    st.code(code_text, language="python")