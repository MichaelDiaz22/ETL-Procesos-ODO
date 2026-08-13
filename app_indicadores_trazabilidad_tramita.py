import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Gestor de Portafolio",
    page_icon="📋",
    layout="wide"
)

# Título principal
st.title("📋 Gestor de Portafolio")

# Inicializar el estado de la sesión para el DataFrame
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_filtrado' not in st.session_state:
    st.session_state.df_filtrado = None

# Sidebar para la carga del archivo
with st.sidebar:
    st.header("📂 Cargar Archivo")
    
    # Cargar archivo Excel
    archivo = st.file_uploader(
        "Selecciona un archivo Excel",
        type=['xlsx', 'xls'],
        help="El archivo debe contener los campos: Tag, Solicitado, Auditado, Sede, Doc., Paciente, Edad, Genero, Diag., Entidad, Grupo Atención, Servicio, Cups, Radicación, Radicado, Autorizado, Autorización, Vence, Entregado, Servicio2, Programado, Responsable, Estado, Observación, Prioridad, idOrden, idIndigo"
    )
    
    if archivo is not None:
        try:
            # Leer el archivo Excel
            df = pd.read_excel(archivo)
            st.session_state.df = df
            
            # Verificar que las columnas necesarias existan
            columnas_requeridas = ['Tag', 'Solicitado', 'Auditado', 'Sede', 'Doc.', 'Paciente', 
                                   'Edad', 'Genero', 'Diag.', 'Entidad', 'Grupo Atención', 
                                   'Servicio', 'Cups', 'Radicación', 'Radicado', 'Autorizado', 
                                   'Autorización', 'Vence', 'Entregado', 'Servicio2', 'Programado', 
                                   'Responsable', 'Estado', 'Observación', 'Prioridad', 'idOrden', 'idIndigo']
            
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            if columnas_faltantes:
                st.error(f"⚠️ El archivo no contiene las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
                st.session_state.df = None
            else:
                # Convertir la columna 'Solicitado' a datetime
                try:
                    df['Solicitado'] = pd.to_datetime(df['Solicitado'])
                    st.success(f"✅ Archivo cargado correctamente. {len(df)} registros encontrados.")
                    
                    # Mostrar información del archivo
                    st.info(f"📊 Rango de fechas: {df['Solicitado'].min().strftime('%Y-%m-%d')} - {df['Solicitado'].max().strftime('%Y-%m-%d')}")
                except Exception as e:
                    st.error(f"⚠️ Error al procesar la columna 'Solicitado': {e}")
                    st.session_state.df = None
                    
        except Exception as e:
            st.error(f"⚠️ Error al leer el archivo: {e}")
            st.session_state.df = None
    else:
        st.info("📌 Carga un archivo Excel para comenzar")

# Contenido principal
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Verificar que la columna 'Solicitado' sea datetime
    if not pd.api.types.is_datetime64_any_dtype(df['Solicitado']):
        df['Solicitado'] = pd.to_datetime(df['Solicitado'])
    
    # Crear pestañas
    tab1, tab2 = st.tabs(["📊 Portafolio", "📈 Estadísticas"])
    
    with tab1:
        st.header("📊 Portafolio")
        
        # Filtros de fecha
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Obtener fecha mínima y máxima
            fecha_min = df['Solicitado'].min().date()
            fecha_max = df['Solicitado'].max().date()
            
            fecha_inicio = st.date_input(
                "📅 Fecha Inicio",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_inicio"
            )
        
        with col2:
            fecha_fin = st.date_input(
                "📅 Fecha Fin",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_fin"
            )
        
        with col3:
            st.write("")
            st.write("")
            aplicar_filtro = st.button("🔍 Aplicar Filtro", use_container_width=True)
        
        # Botón para limpiar filtros
        if st.button("🔄 Limpiar Filtros"):
            st.session_state.df_filtrado = None
            st.rerun()
        
        # Aplicar filtro de fechas
        if aplicar_filtro or st.session_state.df_filtrado is None:
            if fecha_inicio and fecha_fin:
                # Validar que fecha_inicio <= fecha_fin
                if fecha_inicio > fecha_fin:
                    st.warning("⚠️ La fecha de inicio debe ser menor o igual a la fecha de fin")
                    df_filtrado = df
                else:
                    # Convertir a datetime para la comparación
                    fecha_inicio_dt = pd.Timestamp(fecha_inicio)
                    fecha_fin_dt = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    
                    df_filtrado = df[(df['Solicitado'] >= fecha_inicio_dt) & (df['Solicitado'] <= fecha_fin_dt)]
                    st.session_state.df_filtrado = df_filtrado
            else:
                df_filtrado = df
                st.session_state.df_filtrado = df_filtrado
        else:
            df_filtrado = st.session_state.df_filtrado if st.session_state.df_filtrado is not None else df
        
        # Mostrar información del filtro
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("📊 Total de registros", f"{len(df_filtrado):,}")
        with col_info2:
            if fecha_inicio and fecha_fin:
                st.metric("📅 Rango de fechas", f"{fecha_inicio} - {fecha_fin}")
        with col_info3:
            st.metric("🏷️ Columnas", f"{len(df_filtrado.columns)}")
        
        st.divider()
        
        # Mostrar la tabla
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            height=500,
            column_config={
                "Solicitado": st.column_config.DatetimeColumn(
                    "Solicitado",
                    format="YYYY-MM-DD HH:mm",
                ),
                "Auditado": st.column_config.DatetimeColumn(
                    "Auditado",
                    format="YYYY-MM-DD HH:mm",
                ),
                "Autorización": st.column_config.DatetimeColumn(
                    "Autorización",
                    format="YYYY-MM-DD HH:mm",
                ),
                "Vence": st.column_config.DatetimeColumn(
                    "Vence",
                    format="YYYY-MM-DD HH:mm",
                ),
                "Entregado": st.column_config.DatetimeColumn(
                    "Entregado",
                    format="YYYY-MM-DD HH:mm",
                ),
                "Programado": st.column_config.DatetimeColumn(
                    "Programado",
                    format="YYYY-MM-DD HH:mm",
                ),
                "Edad": st.column_config.NumberColumn(
                    "Edad",
                    format="%d",
                ),
            }
        )
        
        # Opciones de exportación
        st.divider()
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            if st.button("📥 Exportar a Excel", use_container_width=True):
                # Crear archivo Excel en memoria
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_filtrado.to_excel(writer, sheet_name='Portafolio', index=False)
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Descargar Excel",
                    data=output,
                    file_name=f"Portafolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel"
                )
        
        with col_exp2:
            if st.button("📋 Copiar al portapapeles", use_container_width=True):
                # Convertir a CSV y mostrar en un text_area para copiar
                csv_data = df_filtrado.to_csv(index=False)
                st.code(csv_data, language="csv", line_numbers=False)
                st.info("💡 Selecciona el texto y presiona Ctrl+C para copiar")
    
    with tab2:
        st.header("📈 Estadísticas del Portafolio")
        
        # Estadísticas generales
        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        with col_stats1:
            st.metric("📊 Total Registros", f"{len(df_filtrado):,}")
        with col_stats2:
            st.metric("🏥 Entidades", f"{df_filtrado['Entidad'].nunique():,}")
        with col_stats3:
            st.metric("👥 Pacientes", f"{df_filtrado['Paciente'].nunique():,}")
        with col_stats4:
            st.metric("📋 Servicios", f"{df_filtrado['Servicio'].nunique():,}")
        
        st.divider()
        
        # Gráficos (si hay datos)
        if len(df_filtrado) > 0:
            # Distribución por estado
            st.subheader("📊 Distribución por Estado")
            estado_counts = df_filtrado['Estado'].value_counts().reset_index()
            estado_counts.columns = ['Estado', 'Cantidad']
            st.bar_chart(estado_counts.set_index('Estado'))
            
            # Distribución por entidad (top 10)
            st.subheader("🏥 Top 10 Entidades")
            entidad_counts = df_filtrado['Entidad'].value_counts().head(10).reset_index()
            entidad_counts.columns = ['Entidad', 'Cantidad']
            st.bar_chart(entidad_counts.set_index('Entidad'))
            
            # Distribución por servicio (top 10)
            st.subheader("📋 Top 10 Servicios")
            servicio_counts = df_filtrado['Servicio'].value_counts().head(10).reset_index()
            servicio_counts.columns = ['Servicio', 'Cantidad']
            st.bar_chart(servicio_counts.set_index('Servicio'))
            
            # Distribución por género
            st.subheader("👤 Distribución por Género")
            genero_counts = df_filtrado['Genero'].value_counts().reset_index()
            genero_counts.columns = ['Género', 'Cantidad']
            st.bar_chart(genero_counts.set_index('Género'))
            
            # Series temporales
            st.subheader("📈 Solicitudes por Día")
            solicitudes_por_dia = df_filtrado.groupby(df_filtrado['Solicitado'].dt.date).size().reset_index()
            solicitudes_por_dia.columns = ['Fecha', 'Cantidad']
            st.line_chart(solicitudes_por_dia.set_index('Fecha'))

# Mensaje inicial si no hay archivo cargado
else:
    st.info("👈 Carga un archivo Excel en el panel lateral para comenzar a trabajar")
