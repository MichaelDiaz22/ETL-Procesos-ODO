import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

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
if 'fecha_inicio' not in st.session_state:
    st.session_state.fecha_inicio = None
if 'fecha_fin' not in st.session_state:
    st.session_state.fecha_fin = None

# Sección de carga de archivo - unificada en la pantalla principal
with st.container():
    st.subheader("📂 Cargar Archivo")
    archivo = st.file_uploader(
        "Selecciona un archivo Excel",
        type=['xlsx', 'xls'],
        help="El archivo debe contener los campos: Tag, Solicitado, Auditado, Sede, Doc., Paciente, Edad, Genero, Diag., Entidad, Grupo Atención, Servicio, Cups, Radicación, Radicado, Autorizado, Autorización, Vence, Entregado, Servicio, Programado, Responsable, Estado, Observación, Prioridad, idOrden, idIndigo"
    )
    
    if archivo is not None:
        try:
            # Leer el archivo Excel saltando la primera fila (título)
            df = pd.read_excel(archivo, header=1)
            
            # Eliminar columnas sin nombre (Unnamed)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            # Renombrar la segunda columna 'Servicio' a 'Servicio proceso tramita'
            cols = df.columns.tolist()
            servicio_count = 0
            for i, col in enumerate(cols):
                if col == 'Servicio':
                    servicio_count += 1
                    if servicio_count == 2:
                        cols[i] = 'Servicio proceso tramita'
            df.columns = cols
            
            # Guardar el nombre de las columnas
            st.session_state.header_row = df.columns.tolist()
            
            # Verificar que las columnas necesarias existan
            columnas_requeridas = ['Tag', 'Solicitado', 'Auditado', 'Sede', 'Doc.', 'Paciente', 
                                   'Edad', 'Genero', 'Diag.', 'Entidad', 'Grupo Atención', 
                                   'Servicio', 'Cups', 'Radicación', 'Radicado', 'Autorizado', 
                                   'Autorización', 'Vence', 'Entregado', 'Servicio proceso tramita', 
                                   'Programado', 'Responsable', 'Estado', 'Observación', 'Prioridad', 
                                   'idOrden', 'idIndigo']
            
            # Normalizar nombres de columnas para comparación
            columnas_df = [col.strip() for col in df.columns]
            columnas_requeridas_norm = [col.strip() for col in columnas_requeridas]
            
            # Verificar columnas faltantes
            columnas_faltantes = []
            for i, col in enumerate(columnas_requeridas_norm):
                if col not in columnas_df:
                    if col == 'Servicio proceso tramita':
                        continue
                    columnas_faltantes.append(columnas_requeridas[i])
            
            if 'Servicio proceso tramita' in columnas_requeridas_norm:
                servicio_count_df = sum(1 for col in columnas_df if col == 'Servicio')
                if servicio_count_df == 1 and 'Servicio proceso tramita' in columnas_faltantes:
                    columnas_faltantes.remove('Servicio proceso tramita')
            
            if columnas_faltantes:
                st.error(f"⚠️ El archivo no contiene las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
                st.info(f"📋 Columnas encontradas: {', '.join(df.columns.tolist())}")
                st.session_state.df = None
            else:
                # Limpiar datos vacíos
                df = df.dropna(how='all')
                
                # Convertir 'Solicitado' a datetime
                df['Solicitado'] = pd.to_datetime(df['Solicitado'])
                st.session_state.df = df
                
                # Actualizar fechas en el estado
                if len(df) > 0:
                    st.session_state.fecha_inicio = df['Solicitado'].min().date()
                    st.session_state.fecha_fin = df['Solicitado'].max().date()
                
                st.success(f"✅ Archivo cargado correctamente. {len(df)} registros encontrados.")
                st.info(f"📊 Rango de fechas: {df['Solicitado'].min().strftime('%Y-%m-%d')} - {df['Solicitado'].max().strftime('%Y-%m-%d')}")
                    
        except Exception as e:
            st.error(f"⚠️ Error al leer el archivo: {e}")
            st.session_state.df = None
    else:
        st.info("📌 Carga un archivo Excel para comenzar")

# Contenido principal
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    # Verificar que la columna 'Solicitado' sea datetime
    if not pd.api.types.is_datetime64_any_dtype(df['Solicitado']):
        try:
            df['Solicitado'] = pd.to_datetime(df['Solicitado'])
        except:
            st.error("⚠️ No se pudo convertir la columna 'Solicitado' a formato de fecha")
            st.stop()
    
    # Verificar que hay datos
    if len(df) == 0:
        st.warning("⚠️ El archivo no contiene datos después de la fila de título")
        st.stop()
    
    # Crear pestañas - Primero Estadística, luego Portafolio
    tab1, tab2 = st.tabs(["📈 Estadísticas", "📊 Portafolio"])
    
    with tab1:
        st.header("📈 Estadísticas del Portafolio")
        
        # Filtros de fecha dentro de Estadísticas
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        
        with col_f1:
            fecha_min = df['Solicitado'].min().date()
            fecha_max = df['Solicitado'].max().date()
            
            fecha_inicio = st.date_input(
                "📅 Fecha Inicio",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_inicio_tab1"
            )
        
        with col_f2:
            fecha_fin = st.date_input(
                "📅 Fecha Fin",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_fin_tab1"
            )
        
        with col_f3:
            st.write("")
            st.write("")
            aplicar_filtro = st.button("🔍 Aplicar Filtro", use_container_width=True, key="filtro_tab1")
        
        # Botón para limpiar filtros
        if st.button("🔄 Limpiar Filtros", key="limpiar_tab1"):
            st.session_state.df_filtrado = None
            st.rerun()
        
        # Aplicar filtro de fechas
        if aplicar_filtro or st.session_state.df_filtrado is None:
            if fecha_inicio and fecha_fin:
                if fecha_inicio > fecha_fin:
                    st.warning("⚠️ La fecha de inicio debe ser menor o igual a la fecha de fin")
                    df_filtrado = df
                else:
                    fecha_inicio_dt = pd.Timestamp(fecha_inicio)
                    fecha_fin_dt = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    df_filtrado = df[(df['Solicitado'] >= fecha_inicio_dt) & (df['Solicitado'] <= fecha_fin_dt)]
                    st.session_state.df_filtrado = df_filtrado
            else:
                df_filtrado = df
                st.session_state.df_filtrado = df_filtrado
        else:
            df_filtrado = st.session_state.df_filtrado if st.session_state.df_filtrado is not None else df
        
        # Estadísticas generales - 5 métricas en una fila
        col_stats1, col_stats2, col_stats3, col_stats4, col_stats5 = st.columns(5)
        
        # Total de registros
        total_registros = len(df_filtrado)
        with col_stats1:
            st.metric("📊 Total Registros", f"{total_registros:,}")
        
        # Entidades
        with col_stats2:
            st.metric("🏥 Entidades", f"{df_filtrado['Entidad'].nunique():,}")
        
        # Pacientes
        with col_stats3:
            st.metric("👥 Pacientes", f"{df_filtrado['Paciente'].nunique():,}")
        
        # Servicios
        with col_stats4:
            st.metric("📋 Servicios", f"{df_filtrado['Servicio'].nunique():,}")
        
        # Órdenes gestionadas (total de registros, porque todos son órdenes)
        with col_stats5:
            # Calcular el porcentaje respecto al total general (sin filtro)
            total_general = len(df)
            porcentaje = (total_registros / total_general * 100) if total_general > 0 else 0
            st.metric(
                "📋 Órdenes Gestionadas", 
                f"{total_registros:,} ({porcentaje:.1f}%)",
                help=f"Total de órdenes en el rango de fechas seleccionado. Representa el {porcentaje:.1f}% del total de órdenes ({total_general:,})"
            )
        
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
            
            # Distribución de edades (si hay datos de edad)
            if 'Edad' in df_filtrado.columns and df_filtrado['Edad'].notna().any():
                st.subheader("📊 Distribución de Edades")
                df_edad = df_filtrado['Edad'].dropna()
                if len(df_edad) > 0:
                    bins = range(0, 101, 10)
                    edad_bins = pd.cut(df_edad, bins=bins)
                    edad_counts = edad_bins.value_counts().sort_index().reset_index()
                    edad_counts.columns = ['Rango de Edad', 'Cantidad']
                    edad_counts['Rango de Edad'] = edad_counts['Rango de Edad'].astype(str)
                    st.bar_chart(edad_counts.set_index('Rango de Edad'))
    
    with tab2:
        st.header("📊 Portafolio")
        
        # Mostrar solo la tabla con los datos
        # Usar el mismo filtro que en Estadísticas
        if st.session_state.df_filtrado is not None:
            df_tabla = st.session_state.df_filtrado
        else:
            df_tabla = df
        
        # Buscador de texto
        search_term = st.text_input("🔍 Buscar en todos los campos", placeholder="Escribe el texto a buscar...")
        if search_term:
            mask = pd.Series(False, index=df_tabla.index)
            for col in df_tabla.select_dtypes(include=['object', 'string']).columns:
                try:
                    mask |= df_tabla[col].astype(str).str.contains(search_term, case=False, na=False)
                except:
                    pass
            df_tabla = df_tabla[mask]
            st.info(f"🔍 Encontrados {len(df_tabla)} registros que coinciden con '{search_term}'")
        
        # Mostrar información del filtro
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("📊 Total de registros", f"{len(df_tabla):,}")
        with col_info2:
            if len(df_tabla) > 0:
                st.metric("📅 Rango de fechas", f"{df_tabla['Solicitado'].min().strftime('%Y-%m-%d')} - {df_tabla['Solicitado'].max().strftime('%Y-%m-%d')}")
        with col_info3:
            st.metric("🏷️ Columnas", f"{len(df_tabla.columns)}")
        
        st.divider()
        
        # Mostrar la tabla
        st.dataframe(
            df_tabla,
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
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            if st.button("📥 Exportar a Excel", use_container_width=True):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_tabla.to_excel(writer, sheet_name='Portafolio', index=False)
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
                csv_data = df_tabla.to_csv(index=False)
                st.code(csv_data, language="csv", line_numbers=False)
                st.info("💡 Selecciona el texto y presiona Ctrl+C para copiar")

# Mensaje inicial si no hay archivo cargado
else:
    st.info("👈 Carga un archivo Excel para comenzar a trabajar")
