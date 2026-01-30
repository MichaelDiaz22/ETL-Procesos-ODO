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
        
        # Crear dos selectores separados para fecha inicial y final
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            fecha_inicio = st.date_input(
                "Fecha de inicio:",
                value=fecha_minima_archivo,
                min_value=fecha_minima_archivo,
                max_value=fecha_maxima_archivo
            )
        
        with col2:
            fecha_fin = st.date_input(
                "Fecha de fin:",
                value=fecha_maxima_archivo,
                min_value=fecha_minima_archivo,
                max_value=fecha_maxima_archivo
            )
        
        # Validar que la fecha de inicio sea menor o igual a la fecha de fin
        if fecha_inicio > fecha_fin:
            st.sidebar.error("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin")
            st.sidebar.info(f"Selecciona fechas entre: **{fecha_minima_archivo}** y **{fecha_maxima_archivo}**")
        else:
            st.sidebar.success(f"✅ Rango válido: {fecha_inicio} a {fecha_fin}")

        # 2. Filtro de Centro de Atención
        centros = sorted(df["CENTRO ATENCION"].dropna().unique())
        centro_sel = st.sidebar.multiselect(
            "Centro de Atención:", 
            options=centros,
            help="Selecciona uno o más centros de atención"
        )

        # 3. Filtro de Usuario Crea Ingreso
        usuarios = sorted(df["USUARIO CREA INGRESO"].dropna().unique())
        usuario_sel = st.sidebar.multiselect(
            "Usuario que Creó Ingreso:", 
            options=usuarios,
            help="Selecciona uno o más usuarios"
        )

        # --- APLICACIÓN DE FILTROS ---
        df_filtrado = df.copy()

        # Filtrado por Rango de Fechas (solo si las fechas son válidas)
        if fecha_inicio <= fecha_fin:
            df_filtrado = df_filtrado[
                (df_filtrado["FECHA CREACION"].dt.date >= fecha_inicio) & 
                (df_filtrado["FECHA CREACION"].dt.date <= fecha_fin)
            ]
        
        # Filtrado por Centro
        if centro_sel:
            df_filtrado = df_filtrado[df_filtrado["CENTRO ATENCION"].isin(centro_sel)]
        
        # Filtrado por Usuario
        if usuario_sel:
            df_filtrado = df_filtrado[df_filtrado["USUARIO CREA INGRESO"].isin(usuario_sel)]

        # --- VISUALIZACIÓN ---
        st.info(f"📅 Rango disponible en archivo: de **{fecha_minima_archivo}** hasta **{fecha_maxima_archivo}**")
        
        if fecha_inicio <= fecha_fin:
            st.success(f"🗓️ Rango seleccionado: **{fecha_inicio}** a **{fecha_fin}**")
        else:
            st.warning("⚠️ Ajusta las fechas para ver los registros filtrados")

        # Métricas de control
        col1, col2, col3 = st.columns(3)
        col1.metric("Total en Archivo", len(df))
        col2.metric("Registros Filtrados", len(df_filtrado))
        col3.metric("Columnas", len(df.columns))

        st.divider()

        # Mostrar los primeros 10 registros de la tabla filtrada
        st.subheader("🔍 Vista Previa (Primeros 10 registros filtrados)")
        if not df_filtrado.empty and fecha_inicio <= fecha_fin:
            st.dataframe(df_filtrado.head(10), use_container_width=True)
            
            # Mostrar estadísticas
            st.caption(f"Mostrando {min(10, len(df_filtrado))} de {len(df_filtrado)} registros")
            
            # Botón para descargar el resultado actual
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar estos resultados",
                data=csv,
                file_name="registros_filtrados.csv",
                mime="text/csv",
                help="Descarga todos los registros filtrados en formato CSV"
            )
        elif fecha_inicio > fecha_fin:
            st.warning("Por favor, ajusta las fechas: la fecha de inicio debe ser menor o igual a la fecha de fin.")
        else:
            st.warning("No hay registros que coincidan con los filtros seleccionados.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
        st.info("Verifica que el archivo tenga las columnas necesarias: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
else:
    st.info("👆 Sube un archivo Excel para activar los filtros.")
    st.caption("El archivo debe contener al menos las columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
