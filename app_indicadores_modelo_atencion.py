import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos", layout="wide")

st.title("📊 Visualizador de Registros con Filtros Dinámicos")

# 1. Carga de archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Leer el archivo
        df = pd.read_excel(uploaded_file)
        
        # --- PROCESAMIENTO DE FECHAS ---
        # Convertimos la columna a datetime para poder operar
        df["FECHA CREACION"] = pd.to_datetime(df["FECHA CREACION"], errors='coerce')
        
        # Eliminamos filas con fechas nulas para evitar errores en el selector
        df = df.dropna(subset=["FECHA CREACION"])

        # Identificamos los límites reales del archivo
        fecha_minima_archivo = df["FECHA CREACION"].min().date()
        fecha_maxima_archivo = df["FECHA CREACION"].max().date()

        # --- SECCIÓN DE FILTROS EN SIDEBAR ---
        st.sidebar.header("⚙️ Filtros de Búsqueda")

        # 1. Filtro de Fechas (Rango basado en el archivo)
        st.sidebar.subheader("Rango de Evaluación")
        rango_fechas = st.sidebar.date_input(
            "Selecciona el periodo:",
            value=(fecha_minima_archivo, fecha_maxima_archivo), # Valor inicial: todo el rango
            min_value=fecha_minima_archivo,                   # Límite mínimo permitido
            max_value=fecha_maxima_archivo                    # Límite máximo permitido
        )

        # 2. Filtro de Centro de Atención
        centros = sorted(df["CENTRO ATENCION"].dropna().unique())
        centro_sel = st.sidebar.multiselect(
            "Centro de Atención:", 
            options=centros
        )

        # 3. Filtro de Usuario Crea Ingreso
        usuarios = sorted(df["USUARIO CREA INGRESO"].dropna().unique())
        usuario_sel = st.sidebar.multiselect(
            "Usuario que Creó Ingreso:", 
            options=usuarios
        )

        # --- APLICACIÓN DE FILTROS ---
        df_filtrado = df.copy()

        # Filtrado por Rango de Fechas (Controlando que se hayan seleccionado ambas fechas)
        if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
            f_inicio, f_fin = rango_fechas
            df_filtrado = df_filtrado[
                (df_filtrado["FECHA CREACION"].dt.date >= f_inicio) & 
                (df_filtrado["FECHA CREACION"].dt.date <= f_fin)
            ]
        
        # Filtrado por Centro
        if centro_sel:
            df_filtrado = df_filtrado[df_filtrado["CENTRO ATENCION"].isin(centro_sel)]
        
        # Filtrado por Usuario
        if usuario_sel:
            df_filtrado = df_filtrado[df_filtrado["USUARIO CREA INGRESO"].isin(usuario_sel)]

        # --- VISUALIZACIÓN ---
        st.info(f"📅 Rango disponible en archivo: de **{fecha_minima_archivo}** hasta **{fecha_maxima_archivo}**")

        # Métricas de control
        col1, col2, col3 = st.columns(3)
        col1.metric("Total en Archivo", len(df))
        col2.metric("Registros Filtrados", len(df_filtrado))
        col3.metric("Columnas", len(df.columns))

        st.divider()

        # Mostrar los primeros 10 registros de la tabla filtrada
        st.subheader("🔍 Vista Previa (Primeros 10 registros filtrados)")
        if not df_filtrado.empty:
            st.dataframe(df_filtrado.head(10), use_container_width=True)
            
            # Botón para descargar el resultado actual
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar estos resultados",
                data=csv,
                file_name="registros_filtrados.csv",
                mime="text/csv",
            )
        else:
            st.warning("No hay registros que coincidan con los filtros seleccionados.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
else:
    st.info("Sube un archivo Excel para activar los filtros.")
