import streamlit as st
import pandas as pd

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Buscador de Summaries",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS
st.markdown("""

""", unsafe_allow_html=True)

# Función auxiliar para convertir números con coma a float
def convertir_a_float(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace(',', '.', regex=False).str.strip(),
        errors='coerce'
    ).fillna(0.0)

# ==========================================
# BASE DE DATOS REAL (PESTAÑA RawData_1)
# ==========================================
@st.cache_data
def cargar_ofertas():
    archivo_excel = "DataBase_Offers_V02-20260924.xlsx"
    
    try:
        df_raw = pd.read_excel(archivo_excel, sheet_name="RawData_1")
        
        # Limpiar espacios en blanco en los nombres de las columnas
        df_raw.columns = df_raw.columns.str.strip()
        
        # Filtrar ofertas que contengan "A" en offer_category (ej: "1 A", "A")
        if "offer_category" in df_raw.columns:
            es_cat_a = df_raw["offer_category"].astype(str).str.contains("A", case=False, na=False)
            df_ofertas = df_raw[es_cat_a].copy()
        else:
            df_ofertas = df_raw.copy()
            
        # Mapeo general
        df_ofertas["id"] = df_ofertas["proj_name"].astype(str) + " (v" + df_ofertas["version"].astype(str) + ")"
        df_ofertas["nombre"] = df_ofertas["client"] if "client" in df_ofertas.columns else "Cliente no especificado"
        df_ofertas["tipo"] = df_ofertas["offer_category"].astype(str) + " (" + df_ofertas["code"].astype(str) + ")" if "code" in df_ofertas.columns else df_ofertas["offer_category"].astype(str)
        df_ofertas["ubicacion"] = df_ofertas["country"] if "country" in df_ofertas.columns else "Desconocido"
        df_ofertas["ruta_summary"] = df_ofertas["file_root"] if "file_root" in df_ofertas.columns else "Sin ruta disponible"
        
        # Conversión segura de números procesando comas decimales
        df_ofertas["viento_ms"] = convertir_a_float(df_ofertas["wind_spd"]) if "wind_spd" in df_ofertas.columns else 0.0
        df_ofertas["max_clearance_mm"] = convertir_a_float(df_ofertas["max_clearance"]) if "max_clearance" in df_ofertas.columns else 0.0
        df_ofertas["longitud_tr1"] = convertir_a_float(df_ofertas["length_Tr1"]) if "length_Tr1" in df_ofertas.columns else 0.0
        
        # Deduplicación inteligente por parámetros clave
        columnas_filtro_duplicados = ["proj_name", "version", "viento_ms", "max_clearance_mm", "longitud_tr1"]
        cols_existentes = [c for c in columnas_filtro_duplicados if c in df_ofertas.columns]
        
        if cols_existentes:
            df_ofertas = df_ofertas.drop_duplicates(subset=cols_existentes)
        
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
# PESTAÑAS PRINCIPALES
# ==========================================
tab_app, tab_code = st.tabs(["🔍 Buscador de Summaries", "💻 Ver Código Fuente"])

with tab_app:
    col_h, col_m1, col_m2 = st.columns([3, 1, 1])
    with col_h:
        st.title("Buscador de Summaries")
        st.caption("Filtro de cálculos estructurales sincronizado con Excel GOP")
    with col_m1:
        st.metric(label="Ofertas Base", value=len(df_ofertas))
    with col_m2:
        st.metric(label="Estado BBDD", value="Conectado")

    st.divider()

    st.markdown("##### 1. Parámetros de la nueva oferta")
    c1, c2, c3 = st.columns(3)
    with c1:
        viento_in = st.number_input("Viento (wind_spd) *", value=55.5, step=0.5)
    with c2:
        clearance_in = st.number_input("Max Clearance (mm) *", value=900, step=50)
    with c3:
        # Input Opcional: Si se deja vacío (None), no se usa como filtro
        longitud_in = st.number_input("Longitud Tr1 (Opcional)", value=None, placeholder="Ej: 139.2", step=1.0)

    c_sub1, c_sub2 = st.columns([2, 2])
    with c_sub1:
        ubicacion_in = st.text_input("Ubicación", value="Saudi Arabia")
    with c_sub2:
        regla_viento = st.radio("Criterio de Viento", ["Exacto (100%)", "Permitir Superior"], horizontal=True)

    st.divider()
    st.markdown("##### 2. Resultados compatibles")
    
    if df_ofertas.empty:
        st.warning("No se ha cargado la base de datos o el archivo no está disponible.")
    else:
        # Filtrado obligatorio por viento
        if "Exacto" in regla_viento:
            df_res = df_ofertas[abs(df_ofertas["viento_ms"] - viento_in) <= 0.1].copy()
        else:
            df_res = df_ofertas[df_ofertas["viento_ms"] >= (viento_in - 0.1)].copy()

        if df_res.empty:
            st.warning("No se encontraron ofertas que cumplan con la condición de viento.")
        else:
            # Puntuación según si Longitud Tr1 se ha especificado o no
            def scoring(row):
                if longitud_in is not None and longitud_in > 0:
                    pts = 0.0
                    if abs(row["max_clearance_mm"] - clearance_in) <= 1.0:
                        pts += 50.0
                    if abs(row["longitud_tr1"] - longitud_in) <= 0.2:
                        pts += 50.0
                    return pts
                else:
                    # Si no se especifica longitud, la coincidencia depende únicamente del clearance
                    return 100.0 if abs(row["max_clearance_mm"] - clearance_in) <= 1.0 else 50.0

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
                        st.caption(f"Longitud Tr1: **{row['longitud_tr1']}** | Tipo: {row['tipo']}")
                    with r3:
                        st.markdown(f"{row['pct']:.0f}% Coincidencia", unsafe_allow_html=True)
                        
                        # Comprobar si es Geometría Exacta
                        viento_ok = abs(row['viento_ms'] - viento_in) <= 0.1
                        clearance_ok = abs(row['max_clearance_mm'] - clearance_in) <= 1.0
                        
                        if longitud_in is not None and longitud_in > 0:
                            longitud_ok = abs(row['longitud_tr1'] - longitud_in) <= 0.2
                            exacta = viento_ok and clearance_ok and longitud_ok
                        else:
                            exacta = viento_ok and clearance_ok
                            
                        if exacta:
                            st.markdown(" Geometría Exacta", unsafe_allow_html=True)
                    with r4:
                        if st.button("Ver Ruta", key=f"btn_{idx}_{row['id']}"):
                            st.info(f"📁 {row['ruta_summary']}")
                    st.divider()

with tab_code:
    st.subheader("Código fuente de la aplicación (`app.py`)")
    with open(__file__, "r", encoding="utf-8") as f:
        code_text = f.read()
    st.code(code_text, language="python")
    