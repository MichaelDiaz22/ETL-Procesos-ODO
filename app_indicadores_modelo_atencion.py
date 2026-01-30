import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos - Salud", layout="wide")

st.title("📊 Monitor de Ingresos de Pacientes")

# 1. Carga de archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Leer el archivo
        df = pd.read_excel(uploaded_file)
        
        # --- PREPROCESAMIENTO ---
        # Convertir FECHA CREACION a formato datetime (asegurando que sea fecha)
        if "FECHA CREACION" in df.columns:
            df["FECHA CREACION"] = pd.to_datetime(df["FECHA CREACION"], errors='coerce')
            # Eliminamos filas donde la fecha no se pudo convertir si es necesario, 
            # o simplemente trabajamos con las válidas.
            df = df.dropna(subset=["FECHA CREACION"])

        # --- SECCIÓN DE FILTROS EN SIDEBAR ---
        st.sidebar.header("Filtros de Búsqueda")

        # Filtro de Centro de Atención (Multiselección)
        centros = sorted(df["CENTRO ATENCION"].dropna().unique())
        centro_sel = st.sidebar.multiselect(
            "Seleccione Centro(s) de Atención:", 
            options=centros, 
            default=[]
        )

        # Filtro de Usuario Crea Ingreso (Multiselección)
        usuarios = sorted(df["USUARIO CREA INGRESO"].dropna().unique())
        usuario_sel = st.sidebar.multiselect(
            "Seleccione Usuario(s):", 
            options=usuarios, 
            default=[]
        )

        # Filtro de Rango de Fechas (FECHA CREACION)
        min_date = df["FECHA CREACION"].min().date()
        max_date = df["FECHA CREACION"].max().date()
        
        date_range = st.sidebar.date_input(
            "Rango de Fecha Creación:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # --- LÓGICA DE FILTRADO ---
        df_filtrado = df.copy()

        # Filtrar por Centro
        if centro_sel:
            df_filtrado = df_filtrado[df_filtrado["CENTRO ATENCION"].isin(centro_sel)]
        
        # Filtrar por Usuario
        if usuario_sel:
            df_filtrado = df_filtrado[df_filtrado["USUARIO CREA INGRESO"].isin(usuario_sel)]

        # Filtrar por Rango de Fechas
        if isinstance(date_range, tuple) and len(date_range) == 2:
            inicio, fin = date_range
            df_filtrado = df_filtrado[
                (df_filtrado["FECHA CREACION"].dt.date >= inicio) & 
                (df_filtrado["FECHA CREACION"].dt.date <= fin)
            ]

        # --- MOSTRAR RESULTADOS ---
        st.subheader(f"📋 Registros Encontrados: {len(df_filtrado)}")
        
        # Métricas rápidas
        m1, m2, m3 = st.columns(3)
        m1.metric("Registros Filtrados", len(df_filtrado))
        m2.metric("Centros Seleccionados", len(centro_sel) if centro_sel else "Todos")
        m3.metric("Rango Días", (df_filtrado["FECHA CREACION"].max() - df_filtrado["FECHA CREACION"].min()).days if not df_filtrado.empty else 0)

        st.markdown("### Primeros 10 registros del filtro aplicado:")
        st.dataframe(df_filtrado.head(10), use_container_width=True)

        # Opción para descargar los datos filtrados (extra útil)
        if not df_filtrado.empty:
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar datos filtrados (CSV)",
                data=csv,
                file_name="datos_filtrados.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        st.info("Asegúrate de que el archivo tenga las columnas: 'CENTRO ATENCION', 'USUARIO CREA INGRESO' y 'FECHA CREACION'.")

else:
    st.info("👋 Bienvenido. Por favor, carga un archivo Excel para comenzar.")
