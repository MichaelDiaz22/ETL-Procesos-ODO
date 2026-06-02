import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Configuración de la página
st.set_page_config(
    page_title="Tabla Resumen por Ciudad",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# Definición de ciudades con sus fechas de inicio
CIUDADES = {
    "Manizales": {"fecha_inicio": datetime(2025, 9, 16)},
    "Armenia": {"fecha_inicio": datetime(2025, 11, 20)},
    "Pereira": {"fecha_inicio": datetime(2026, 4, 15)}
}

# Hojas requeridas
HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']

# Inicializar session state
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'dfs' not in st.session_state:
    st.session_state.dfs = {}
if 'fecha_maxima' not in st.session_state:
    st.session_state.fecha_maxima = None
if 'fecha_hasta' not in st.session_state:
    st.session_state.fecha_hasta = None

def cargar_archivo(archivo):
    """Carga el archivo Excel y valida las hojas"""
    try:
        excel_file = pd.ExcelFile(archivo)
        hojas_disponibles = excel_file.sheet_names
        
        # Verificar hojas requeridas
        hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_disponibles]
        
        if hojas_faltantes:
            st.error(f"❌ Faltan las siguientes hojas: {', '.join(hojas_faltantes)}")
            return False, None, None
        
        # Cargar datos
        dfs = {}
        
        # Mostrar información de columnas para depuración
        with st.expander("🔍 Ver información de columnas (Debug)"):
            for hoja in HOJAS_REQUERIDAS:
                df = pd.read_excel(archivo, sheet_name=hoja, nrows=5)
                st.write(f"**Hoja {hoja} - Columnas disponibles:**")
                st.write(list(df.columns))
                st.write("---")
        
        for hoja in HOJAS_REQUERIDAS:
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            # Para la hoja EVENTO, preprocesar datos
            if hoja == 'EVENTO':
                # Identificar columna de FECHA INGRESO
                col_fecha = None
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if 'fecha ingreso' in col_lower or 'fecha_ingreso' in col_lower or 'fechaing' in col_lower or 'ingreso' in col_lower:
                        col_fecha = col
                        break
                
                # Identificar columna de CIUDAD UNIDAD OPERATIVA
                col_ciudad = None
                for col in df.columns:
                    col_lower = col.lower().strip()
                    # Buscar específicamente "CIUDAD UNIDAD OPERATIVA" o variantes
                    if 'ciudad unidad operativa' in col_lower or 'ciudad_unidad_operativa' in col_lower or 'ciudad operativa' in col_lower or 'unidad operativa' in col_lower:
                        col_ciudad = col
                        break
                
                # Si no encuentra, buscar cualquier columna que tenga "ciudad" o "unidad"
                if col_ciudad is None:
                    for col in df.columns:
                        col_lower = col.lower().strip()
                        if 'ciudad' in col_lower or 'unidad' in col_lower:
                            col_ciudad = col
                            break
                
                st.info(f"📌 Hoja EVENTO - Columna FECHA INGRESO encontrada: {col_fecha}")
                st.info(f"📌 Hoja EVENTO - Columna CIUDAD UNIDAD OPERATIVA encontrada: {col_ciudad}")
                
                if col_fecha and col_ciudad:
                    # Mostrar ejemplos de valores para depuración
                    st.write(f"**Ejemplos de valores en {col_ciudad}:**")
                    st.write(df[col_ciudad].head(10).tolist())
                    
                    # Convertir fecha a datetime y extraer solo la fecha (sin hora)
                    df['_fecha_ingreso'] = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True).dt.date
                    # Normalizar ciudad operativa
                    df['_ciudad_operativa'] = df[col_ciudad].astype(str).str.upper().str.strip()
                    
                    # Guardar solo las columnas necesarias
                    dfs[hoja] = df[['_fecha_ingreso', '_ciudad_operativa']].copy()
                    
                    # Mostrar valores únicos de ciudades para depuración
                    ciudades_unicas = df['_ciudad_operativa'].unique()
                    st.write(f"**Valores únicos en CIUDAD UNIDAD OPERATIVA:**")
                    st.write(ciudades_unicas[:20].tolist())
                else:
                    st.warning(f"⚠️ Hoja {hoja}: No se encontraron las columnas necesarias")
                    st.write(f"Columna fecha encontrada: {col_fecha}")
                    st.write(f"Columna ciudad encontrada: {col_ciudad}")
                    dfs[hoja] = pd.DataFrame(columns=['_fecha_ingreso', '_ciudad_operativa'])
            else:
                # Para las otras hojas, solo guardamos estructura básica por ahora
                dfs[hoja] = pd.DataFrame()
            
            st.info(f"📄 Hoja '{hoja}': {len(df):,} registros")
        
        # Encontrar fecha máxima en la hoja EVENTO
        fecha_max = datetime.now()
        if 'EVENTO' in dfs and not dfs['EVENTO'].empty:
            fechas_validas = dfs['EVENTO']['_fecha_ingreso'].dropna()
            if not fechas_validas.empty:
                fecha_max = datetime.combine(fechas_validas.max(), datetime.min.time())
        
        return True, dfs, fecha_max
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return False, None, None

def contar_ingresos_evento(df_evento, ciudad, fecha_inicio, fecha_fin):
    """Cuenta los ingresos de la hoja EVENTO para una ciudad específica"""
    
    if df_evento.empty:
        st.warning("DataFrame de EVENTO está vacío")
        return {}
    
    # Normalizar nombre de ciudad
    ciudad_upper = ciudad.upper()
    
    st.write(f"**Debug - Buscando ciudad:** {ciudad_upper}")
    
    # Filtrar por ciudad
    mask_ciudad = df_evento['_ciudad_operativa'].str.contains(ciudad_upper, na=False)
    df_ciudad = df_evento[mask_ciudad]
    
    st.write(f"**Debug - Registros encontrados para {ciudad}:** {len(df_ciudad)}")
    
    if df_ciudad.empty:
        # Mostrar algunas ciudades disponibles
        ciudades_disponibles = df_evento['_ciudad_operativa'].unique()
        st.write(f"**Ciudades disponibles en los datos:** {ciudades_disponibles[:10].tolist()}")
        return {}
    
    # Filtrar por rango de fechas
    mask_fecha = (df_ciudad['_fecha_ingreso'] >= fecha_inicio.date()) & (df_ciudad['_fecha_ingreso'] <= fecha_fin.date())
    df_filtrado = df_ciudad[mask_fecha]
    
    st.write(f"**Debug - Registros después de filtrar por fechas:** {len(df_filtrado)}")
    st.write(f"**Rango de fechas:** {fecha_inicio.date()} a {fecha_fin.date()}")
    
    # Contar por fecha
    conteo = {}
    for fecha in df_filtrado['_fecha_ingreso']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def construir_tabla_con_ingresos(ciudad, fecha_inicio, fecha_fin, df_evento):
    """Construye la tabla con las fechas y los ingresos de la hoja EVENTO"""
    
    # Contar ingresos para la ciudad desde la hoja EVENTO
    conteo_ingresos = contar_ingresos_evento(df_evento, ciudad, fecha_inicio, fecha_fin)
    
    # Generar todas las fechas del período
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Construir DataFrame
    datos = []
    for fecha in fechas:
        fecha_key = fecha.date()
        ingresos = conteo_ingresos.get(fecha_key, 0)
        
        datos.append({
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'semana': fecha.isocalendar()[1],
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos,
            'facturado modelo': 0,
            'facturado fuera modelo': 0,
            'facturado total': 0,
            'Novedades': 0
        })
    
    df = pd.DataFrame(datos)
    
    # Filtrar solo días con ingresos > 0 para mostrar
    df_filtrado = df[df['ingresos'] > 0]
    
    return df, df_filtrado

# Sidebar
with st.sidebar:
    st.header("📋 Información")
    st.markdown("**Fechas de inicio por ciudad:**")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"- **{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas de Ingresos:**")
    st.markdown("""
    **Ingresos = Conteo de registros de la hoja EVENTO donde:**
    - FECHA INGRESO coincide con la fecha de la fila
    - CIUDAD UNIDAD OPERATIVA contiene el nombre de la ciudad
    """)
    
    st.markdown("---")
    st.markdown("**Hojas requeridas:**")
    for hoja in HOJAS_REQUERIDAS:
        st.markdown(f"- {hoja}")

# Carga de archivo
st.header("📁 Cargar Archivo")

# Selector de fecha (aparece ANTES del botón procesar)
st.markdown("### ⚙️ Configuración del Reporte")

fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 9, 16).date(),
    max_value=fecha_actual.date(),
    help="La tabla mostrará datos desde la fecha de inicio de cada ciudad hasta esta fecha"
)

st.markdown("---")

archivo = st.file_uploader(
    "Selecciona el archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: EVENTO, PGP, PDTE EVENTO, PDTE PGP"
)

if archivo:
    if st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
        with st.spinner("Cargando archivo..."):
            exito, dfs, fecha_max = cargar_archivo(archivo)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_maxima = fecha_max
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                
                st.success("✅ Archivo procesado correctamente!")
                st.info(f"📅 Los datos se mostrarán hasta: {fecha_hasta.strftime('%d/%m/%Y')}")

# Mostrar resultados después de procesar
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    # Obtener el DataFrame de EVENTO
    df_evento = st.session_state.dfs.get('EVENTO', pd.DataFrame())
    
    # Crear pestañas por ciudad
    tabs = st.tabs(list(CIUDADES.keys()))
    
    for tab, ciudad in zip(tabs, CIUDADES.keys()):
        with tab:
            fecha_inicio = CIUDADES[ciudad]['fecha_inicio']
            fecha_fin = st.session_state.fecha_hasta
            
            # Validar que fecha_fin sea mayor que fecha_inicio
            if fecha_fin < fecha_inicio:
                st.warning(f"⚠️ La fecha seleccionada ({fecha_fin.strftime('%d/%m/%Y')}) es anterior a la fecha de inicio de {ciudad} ({fecha_inicio.strftime('%d/%m/%Y')})")
                st.info(f"Por favor, selecciona una fecha posterior al {fecha_inicio.strftime('%d/%m/%Y')}")
                continue
            
            with st.spinner(f"Calculando ingresos para {ciudad}..."):
                # Construir tabla con ingresos de EVENTO
                df_completa, df_filtrado = construir_tabla_con_ingresos(
                    ciudad,
                    fecha_inicio,
                    fecha_fin,
                    df_evento
                )
                
                if len(df_filtrado) > 0:
                    # Métricas
                    total_ingresos = df_completa['ingresos'].sum()
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("📥 Total Ingresos", f"{total_ingresos:,}")
                    with col2:
                        st.metric("✅ Facturado Modelo", "Pendiente")
                    with col3:
                        st.metric("❌ Facturado Fuera", "Pendiente")
                    with col4:
                        st.metric("💰 Facturado Total", "Pendiente")
                    with col5:
                        st.metric("⚠️ Novedades", "Pendiente")
                    
                    # Mostrar tabla
                    st.dataframe(
                        df_filtrado,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                            "semana": "Semana",
                            "año": "Año",
                            "mes": "Mes",
                            "ingresos": st.column_config.NumberColumn("Ingresos", format="%d"),
                            "facturado modelo": st.column_config.NumberColumn("Fact. Modelo", format="%d"),
                            "facturado fuera modelo": st.column_config.NumberColumn("Fact. Fuera", format="%d"),
                            "facturado total": st.column_config.NumberColumn("Fact. Total", format="%d"),
                            "Novedades": st.column_config.NumberColumn("Novedades", format="%d")
                        }
                    )
                    
                    # Información del período
                    st.caption(f"📅 Mostrando {len(df_filtrado)} días con ingresos del {df_filtrado['Fecha'].min()} al {df_filtrado['Fecha'].max()}")
                    
                    # Gráfico de ingresos
                    if len(df_filtrado) > 1:
                        st.subheader("📈 Evolución de Ingresos (Hoja EVENTO)")
                        chart_data = df_filtrado[['ingresos']].copy()
                        chart_data.index = pd.to_datetime(df_filtrado['Fecha'])
                        st.line_chart(chart_data)
                    
                    # Exportar datos
                    st.subheader("💾 Exportar Datos")
                    
                    col1, col2 = st.columns(2)
                    
                    # CSV
                    csv = df_completa.to_csv(index=False).encode('utf-8')
                    col1.download_button(
                        "📥 Descargar CSV",
                        csv,
                        f"{ciudad.lower()}_ingresos_evento.csv",
                        "text/csv",
                        key=f"csv_{ciudad}"
                    )
                    
                    # Excel
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_completa.to_excel(writer, sheet_name='Todos los días', index=False)
                        df_filtrado.to_excel(writer, sheet_name='Días con ingresos', index=False)
                        
                        # Información del procesamiento
                        info = pd.DataFrame([
                            ['Ciudad', ciudad],
                            ['Fecha Inicio', fecha_inicio.strftime('%d/%m/%Y')],
                            ['Fecha Fin', fecha_fin.strftime('%d/%m/%Y')],
                            ['Total Días', len(df_completa)],
                            ['Días con Ingresos', len(df_filtrado)],
                            ['Total Ingresos', total_ingresos],
                            ['Fuente de datos', 'Hoja EVENTO - Campo FECHA INGRESO y CIUDAD UNIDAD OPERATIVA']
                        ], columns=['Información', 'Valor'])
                        info.to_excel(writer, sheet_name='Información', index=False)
                    
                    col2.download_button(
                        "📥 Descargar Excel",
                        output.getvalue(),
                        f"{ciudad.lower()}_ingresos_evento.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{ciudad}"
                    )
                    
                else:
                    st.info(f"No hay ingresos para {ciudad} en el período seleccionado (desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')})")
                    st.caption("Los ingresos se calculan exclusivamente de la hoja EVENTO")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Reiniciar - Cargar otro archivo", use_container_width=True):
        for key in ['datos_cargados', 'dfs', 'fecha_maxima', 'fecha_hasta']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 1. Selecciona la fecha final del reporte\n\n👆 2. Carga un archivo Excel\n\n👆 3. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para cargar los datos")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad - Ingresos desde hoja EVENTO")
