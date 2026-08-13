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

# Datos estáticos del portafolio base (para referencia)
PORTAFOLIO_BASE = [
    # CUPS, codIPS, descrCodIPS, codREPS, A, UNIDAD EJECUTORA, Codigo unidad
    ("221401", "221401", "NASOSINUSCOPIA", "209_CIRUGÍA OTORRINOLARINGOLOGÍA", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("311401", "311401", "PUNCIÓN (ASPIRACIÓN) TRANSTRÁQUEAL VÍA PERCUTÁNEA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("311402", "311402", "PUNCIÓN (ASPIRACIÓN) TRANSTRÁQUEAL VÍA ENDOSCÓPICA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332201", "332201", "BRONCOSCOPIA CON LAVADO BRONQUIAL", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332202", "332202", "BRONCOSCOPIA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332203", "332203", "BRONCOSCOPIA CON LAVADO BRONCOALVEOLAR", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332204", "332204", "BRONCOSCOPIA CON CEPILLADO", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332601", "332601", "BIOPSIA CERRADA DE PULMÓN VÍA PERCUTÁNEA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("441302", "441302", "ESOFAGOGASTRODUODENOSCOPIA [EGD] CON O SIN BIOPSIA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("452301", "452301", "COLONOSCOPIA TOTAL", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("452305", "452305", "COLONOSCOPIA TOTAL CON O SIN BIOPSIA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("452401", "452401", "SIGMOIDOSCOPIA FLEXIBLE O RIGIDA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("7DS004", "7DS004", "DERECHOS DE SALA DE PROCEDIMIENTOS ENDOSCOPICOS", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882112", "882112", "ECOGRAFÍA DOPPLER DE VASOS DEL CUELLO", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882132", "882132", "ECOGRAFÍA DOPPLER DE OTROS VASOS PERIFÉRICOS DEL CUELLO", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882308", "882308", "ECOGRAFÍA DOPPLER DE VASOS ARTERIALES DE MIEMBROS INFERIORES", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882309", "882309", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBROS SUPERIORES", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882316", "882316", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBRO SUPERIOR", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882317", "882317", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBROS INFERIORES", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882318", "882318", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBRO INFERIOR", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("895003", "895003", "PRUEBA DE MESA BASCULANTE", "742_DIAGNÓSTICO VASCULAR", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("895004", "895004", "MONITOREO AMBULATORIO DE PRESIÓN ARTERIAL SISTÉMICA", "742_DIAGNÓSTICO VASCULAR", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("463201", "463201", "YEYUNOSTOMÍA PERCUTÁNEA (ENDOSCÓPICA)", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("422003", "422003", "ESOFAGOSCOPIA VÍA ORAL EXPLORATORIA O DIAGNÓSTICA SIN BIOPSIA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("422602", "422602", "BIOPSIA DE ESÓFAGO VÍA ENDOSCÓPICA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("423302", "423302", "CONTROL DE HEMORRAGIA DE ESÓFAGO VÍA ENDOSCÓPICA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("423304", "423304", "INYECCIÓN (ESCLEROSIS) DE VÁRICES ESOFÁGICAS VÍA ENDOSCÓPICA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("434101", "434101", "LIGADURA ENDOSCÓPICA DE VÁRICES GÁSTRICAS", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("441201", "441201", "GASTROSCOPIA A TRAVÉS DE ESTOMA ARTIFICIAL", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    # Agregar algunos registros de la segunda parte del archivo para tener más variedad
    ("010201", "010201", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR A TRAVÉS DE CATÉTER PREVIAMENTE IMPLANTADO", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010202", "010202", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR POR TREPANACIÓN (SIN CATÉTER)", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010203", "010203", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR A TRAVÉS DE UN RESERVORIO", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010204", "010204", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR, VÍA TRANSFONTANELAR", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010205", "010205", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010901", "010901", "PUNCIÓN SUBDURAL", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010902", "010902", "OTRA PUNCIÓN CRANEAL", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
]

# Crear DataFrame del portafolio base
df_portafolio_base = pd.DataFrame(PORTAFOLIO_BASE, columns=['CUPS', 'codIPS', 'descrCodIPS', 'codREPS', 'A', 'UNIDAD EJECUTORA', 'Codigo unidad'])

# Inicializar el estado de la sesión para el DataFrame
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_filtrado' not in st.session_state:
    st.session_state.df_filtrado = None
if 'fecha_inicio' not in st.session_state:
    st.session_state.fecha_inicio = None
if 'fecha_fin' not in st.session_state:
    st.session_state.fecha_fin = None

# Sección de carga de archivo
with st.container():
    st.subheader("📂 Cargar Archivo de Solicitudes")
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
        st.info("📌 Carga un archivo Excel para comenzar a trabajar")

# Crear pestañas - Portafolio (siempre visible), Solicitudes (solo si hay archivo), Estadísticas (solo si hay archivo)
if st.session_state.df is not None:
    tab1, tab2, tab3 = st.tabs(["📚 Portafolio", "📊 Solicitudes", "📈 Estadísticas"])
else:
    tab1, tab2, tab3 = st.tabs(["📚 Portafolio", "📊 Solicitudes (carga archivo)", "📈 Estadísticas (carga archivo)"])

# ======================== TAB 1: PORTAFOLIO ========================
with tab1:
    st.header("📚 Portafolio de Servicios")
    st.caption("Esta tabla muestra los servicios disponibles en el portafolio")
    
    # Filtros para el portafolio
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        unidades = ["Todas"] + sorted(df_portafolio_base['UNIDAD EJECUTORA'].unique().tolist())
        unidad_seleccionada = st.selectbox("🏢 Unidad Ejecutora", unidades, key="portafolio_unidad")
    
    with col_f2:
        codigos = ["Todos"] + sorted(df_portafolio_base['codREPS'].unique().tolist())
        codigo_seleccionado = st.selectbox("📋 Código REPS", codigos, key="portafolio_codigo")
    
    with col_f3:
        busqueda_portafolio = st.text_input("🔍 Buscar por descripción", placeholder="Escribe texto...", key="portafolio_busqueda")
    
    with col_f4:
        mostrar_solo_activos = st.checkbox("✅ Mostrar solo Activos (A=True)", value=False, key="portafolio_activos")
    
    # Aplicar filtros al portafolio
    df_portafolio_filtrado = df_portafolio_base.copy()
    
    if unidad_seleccionada != "Todas":
        df_portafolio_filtrado = df_portafolio_filtrado[df_portafolio_filtrado['UNIDAD EJECUTORA'] == unidad_seleccionada]
    
    if codigo_seleccionado != "Todos":
        df_portafolio_filtrado = df_portafolio_filtrado[df_portafolio_filtrado['codREPS'] == codigo_seleccionado]
    
    if busqueda_portafolio:
        df_portafolio_filtrado = df_portafolio_filtrado[df_portafolio_filtrado['descrCodIPS'].str.contains(busqueda_portafolio, case=False, na=False)]
    
    if mostrar_solo_activos:
        df_portafolio_filtrado = df_portafolio_filtrado[df_portafolio_filtrado['A'] == True]
    
    # Mostrar información del portafolio
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    with col_info1:
        st.metric("📊 Total Registros", f"{len(df_portafolio_filtrado):,}")
    with col_info2:
        st.metric("🏢 Unidades Ejecutoras", df_portafolio_filtrado['UNIDAD EJECUTORA'].nunique())
    with col_info3:
        st.metric("📋 Códigos REPS", df_portafolio_filtrado['codREPS'].nunique())
    with col_info4:
        activos = df_portafolio_filtrado[df_portafolio_filtrado['A'] == True].shape[0]
        st.metric("✅ Activos (A=True)", f"{activos:,}")
    
    st.divider()
    
    # Mostrar tabla del portafolio
    st.dataframe(
        df_portafolio_filtrado,
        use_container_width=True,
        height=500,
        column_config={
            "CUPS": st.column_config.TextColumn("CUPS", width="small"),
            "codIPS": st.column_config.TextColumn("Código IPS", width="small"),
            "descrCodIPS": st.column_config.TextColumn("Descripción", width="large"),
            "codREPS": st.column_config.TextColumn("Código REPS", width="medium"),
            "A": st.column_config.CheckboxColumn("Activo", width="small"),
            "UNIDAD EJECUTORA": st.column_config.TextColumn("Unidad Ejecutora", width="medium"),
            "Codigo unidad": st.column_config.TextColumn("Código Unidad", width="small"),
        }
    )
    
    # Exportar portafolio
    st.divider()
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if st.button("📥 Exportar Portafolio a Excel", use_container_width=True):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_portafolio_filtrado.to_excel(writer, sheet_name='Portafolio', index=False)
            output.seek(0)
            
            st.download_button(
                label="⬇️ Descargar Excel",
                data=output,
                file_name=f"Portafolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_portafolio_excel"
            )
    
    with col_exp2:
        if st.button("📋 Ver CSV del Portafolio", use_container_width=True):
            csv_data = df_portafolio_filtrado.to_csv(index=False)
            st.code(csv_data, language="csv", line_numbers=False)
            st.info("💡 Selecciona el texto y presiona Ctrl+C para copiar")

# ======================== TAB 2: SOLICITUDES ========================
if st.session_state.df is not None:
    with tab2:
        st.header("📊 Solicitudes Cargadas")
        
        df = st.session_state.df.copy()
        
        # Mostrar la tabla con los datos
        if st.session_state.df_filtrado is not None:
            df_tabla = st.session_state.df_filtrado
        else:
            df_tabla = df
        
        # Buscador de texto
        search_term = st.text_input("🔍 Buscar en todos los campos", placeholder="Escribe el texto a buscar...", key="solicitudes_busqueda")
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
            if st.button("📥 Exportar Solicitudes a Excel", use_container_width=True):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_tabla.to_excel(writer, sheet_name='Solicitudes', index=False)
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Descargar Excel",
                    data=output,
                    file_name=f"Solicitudes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_solicitudes_excel"
                )
        
        with col_exp2:
            if st.button("📋 Copiar al portapapeles", use_container_width=True):
                csv_data = df_tabla.to_csv(index=False)
                st.code(csv_data, language="csv", line_numbers=False)
                st.info("💡 Selecciona el texto y presiona Ctrl+C para copiar")
else:
    with tab2:
        st.info("📌 Carga un archivo Excel para ver las solicitudes")
        st.info("El archivo debe contener las columnas: Tag, Solicitado, Auditado, Sede, Doc., Paciente, Edad, Genero, Diag., Entidad, Grupo Atención, Servicio, Cups, Radicación, Radicado, Autorizado, Autorización, Vence, Entregado, Servicio proceso tramita, Programado, Responsable, Estado, Observación, Prioridad, idOrden, idIndigo")

# ======================== TAB 3: ESTADÍSTICAS ========================
if st.session_state.df is not None:
    with tab3:
        st.header("📈 Estadísticas del Portafolio")
        
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
        
        # Filtros de fecha
        col_f1, col_f2 = st.columns([2, 2])
        
        with col_f1:
            fecha_min = df['Solicitado'].min().date()
            fecha_max = df['Solicitado'].max().date()
            
            fecha_inicio = st.date_input(
                "📅 Fecha Inicio",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_inicio_estadisticas"
            )
        
        with col_f2:
            fecha_fin = st.date_input(
                "📅 Fecha Fin",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_fin_estadisticas"
            )
        
        # Filtros de Estado y Entidad (selección múltiple)
        st.divider()
        st.subheader("🔍 Filtros Adicionales")
        
        col_f3, col_f4 = st.columns(2)
        
        with col_f3:
            # Obtener valores únicos de Estado
            estados_disponibles = sorted(df['Estado'].dropna().unique().tolist())
            # Selección múltiple con todos seleccionados por defecto
            estados_seleccionados = st.multiselect(
                "📌 Estado",
                options=estados_disponibles,
                default=estados_disponibles,
                key="estados_filtro"
            )
        
        with col_f4:
            # Obtener valores únicos de Entidad
            entidades_disponibles = sorted(df['Entidad'].dropna().unique().tolist())
            # Selección múltiple con todos seleccionados por defecto
            entidades_seleccionadas = st.multiselect(
                "🏥 Entidad",
                options=entidades_disponibles,
                default=entidades_disponibles,
                key="entidades_filtro"
            )
        
        # Botón para aplicar filtros
        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            aplicar_filtro = st.button("🔍 Aplicar Filtros", use_container_width=True, key="filtro_estadisticas")
        
        # Botón para limpiar filtros
        with col_btn2:
            if st.button("🔄 Restablecer Filtros", use_container_width=True, key="reset_estadisticas"):
                st.session_state.df_filtrado = None
                st.rerun()
        
        # Aplicar todos los filtros
        if aplicar_filtro or st.session_state.df_filtrado is None:
            # Iniciar con el DataFrame completo
            df_filtrado = df.copy()
            
            # Aplicar filtro de fechas
            if fecha_inicio and fecha_fin:
                if fecha_inicio <= fecha_fin:
                    fecha_inicio_dt = pd.Timestamp(fecha_inicio)
                    fecha_fin_dt = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    df_filtrado = df_filtrado[(df_filtrado['Solicitado'] >= fecha_inicio_dt) & (df_filtrado['Solicitado'] <= fecha_fin_dt)]
                else:
                    st.warning("⚠️ La fecha de inicio debe ser menor o igual a la fecha de fin")
            
            # Aplicar filtro de Estado (si hay selecciones)
            if estados_seleccionados:
                df_filtrado = df_filtrado[df_filtrado['Estado'].isin(estados_seleccionados)]
            
            # Aplicar filtro de Entidad (si hay selecciones)
            if entidades_seleccionadas:
                df_filtrado = df_filtrado[df_filtrado['Entidad'].isin(entidades_seleccionadas)]
            
            st.session_state.df_filtrado = df_filtrado
        else:
            df_filtrado = st.session_state.df_filtrado if st.session_state.df_filtrado is not None else df
        
        # Mostrar estadísticas generales
        st.divider()
        st.subheader("📊 Resumen")
        
        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        with col_stats1:
            st.metric("📊 Total Registros", f"{len(df_filtrado):,}")
        with col_stats2:
            st.metric("🏥 Entidades", f"{df_filtrado['Entidad'].nunique():,}")
        with col_stats3:
            st.metric("👥 Pacientes", f"{df_filtrado['Paciente'].nunique():,}")
        with col_stats4:
            st.metric("📋 Servicios", f"{df_filtrado['Servicio'].nunique():,}")
        
        # Mostrar tabla de resumen de estados
        if len(df_filtrado) > 0:
            st.divider()
            st.subheader("📊 Distribución por Estado")
            
            # Tabla de conteo por estado
            estado_counts = df_filtrado['Estado'].value_counts().reset_index()
            estado_counts.columns = ['Estado', 'Cantidad']
            
            # Calcular porcentajes
            total = estado_counts['Cantidad'].sum()
            estado_counts['Porcentaje'] = (estado_counts['Cantidad'] / total * 100).round(2)
            estado_counts['Porcentaje'] = estado_counts['Porcentaje'].astype(str) + '%'
            
            st.dataframe(
                estado_counts,
                use_container_width=True,
                column_config={
                    "Estado": "Estado",
                    "Cantidad": "Cantidad",
                    "Porcentaje": "% del Total"
                }
            )
            
            # Tabla de conteo por entidad (top 10)
            st.divider()
            st.subheader("🏥 Top 10 Entidades")
            
            entidad_counts = df_filtrado['Entidad'].value_counts().head(10).reset_index()
            entidad_counts.columns = ['Entidad', 'Cantidad']
            
            # Calcular porcentajes
            total_entidades = entidad_counts['Cantidad'].sum()
            entidad_counts['Porcentaje'] = (entidad_counts['Cantidad'] / total_entidades * 100).round(2)
            entidad_counts['Porcentaje'] = entidad_counts['Porcentaje'].astype(str) + '%'
            
            st.dataframe(
                entidad_counts,
                use_container_width=True,
                column_config={
                    "Entidad": "Entidad",
                    "Cantidad": "Cantidad",
                    "Porcentaje": "% del Total"
                }
            )
            
            # Mostrar información de filtros aplicados
            st.divider()
            st.caption(f"🔍 Filtros aplicados: {len(estados_seleccionados)} estados, {len(entidades_seleccionadas)} entidades")
            st.caption(f"📅 Rango de fechas: {fecha_inicio} - {fecha_fin}")
            
else:
    with tab3:
        st.info("📌 Carga un archivo Excel para ver las estadísticas")

# Mensaje de pie de página
st.divider()
st.caption("💡 Gestor de Portafolio - Los datos del portafolio base son estáticos y siempre están disponibles")
