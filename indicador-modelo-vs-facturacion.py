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

def identificar_columnas(df):
    """Identifica las columnas necesarias en cada DataFrame"""
    columnas = {
        'ciudad': None,
        'fecha_ingreso': None,
        'fecha_factura': None
    }
    
    for col in df.columns:
        col_lower = col.lower().strip()
        
        if 'ciudad' in col_lower or 'unidad' in col_lower or 'operativa' in col_lower or 'ciiu' in col_lower:
            if columnas['ciudad'] is None:
                columnas['ciudad'] = col
        
        if 'ingreso' in col_lower or 'fechaing' in col_lower or 'fecha_ingreso' in col_lower:
            if columnas['fecha_ingreso'] is None:
                columnas['fecha_ingreso'] = col
        
        if 'factura' in col_lower or 'fechafac' in col_lower or 'fecha_factura' in col_lower:
            if columnas['fecha_factura'] is None:
                columnas['fecha_factura'] = col
    
    return columnas

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
        for hoja in HOJAS_REQUERIDAS:
            dfs[hoja] = pd.read_excel(archivo, sheet_name=hoja)
            st.info(f"📄 Hoja '{hoja}': {len(dfs[hoja]):,} registros")
        
        # Encontrar fecha máxima en todas las hojas
        fecha_max = None
        for hoja, df in dfs.items():
            columnas = identificar_columnas(df)
            
            # Buscar en fecha ingreso
            if columnas['fecha_ingreso']:
                fechas = pd.to_datetime(df[columnas['fecha_ingreso']], errors='coerce')
                if not fechas.dropna().empty:
                    max_fecha = fechas.max()
                    if fecha_max is None or max_fecha > fecha_max:
                        fecha_max = max_fecha
            
            # Buscar en fecha factura
            if columnas['fecha_factura']:
                fechas = pd.to_datetime(df[columnas['fecha_factura']], errors='coerce')
                if not fechas.dropna().empty:
                    max_fecha = fechas.max()
                    if fecha_max is None or max_fecha > fecha_max:
                        fecha_max = max_fecha
        
        return True, dfs, fecha_max
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return False, None, None

def procesar_ingresos(dfs, fecha_inicio, fecha_fin):
    """Calcula los ingresos por fecha desde todas las hojas"""
    ingresos = {}
    
    for hoja in ['PDTE EVENTO', 'PDTE PGP', 'EVENTO', 'PGP']:
        if hoja not in dfs:
            continue
        
        df = dfs[hoja]
        columnas = identificar_columnas(df)
        
        if columnas['fecha_ingreso'] is None:
            continue
        
        # Convertir fechas
        fechas = pd.to_datetime(df[columnas['fecha_ingreso']], errors='coerce')
        
        # Filtrar por rango
        mask = (fechas >= fecha_inicio) & (fechas <= fecha_fin)
        
        # Contar por fecha
        for fecha in fechas[mask]:
            fecha_key = fecha.date()
            ingresos[fecha_key] = ingresos.get(fecha_key, 0) + 1
    
    return ingresos

def procesar_facturacion(dfs, ciudad, fecha_inicio, fecha_fin):
    """Calcula facturado modelo y fuera modelo"""
    facturado_modelo = {}
    facturado_fuera = {}
    
    for hoja in ['EVENTO', 'PGP']:
        if hoja not in dfs:
            continue
        
        df = dfs[hoja]
        columnas = identificar_columnas(df)
        
        # Verificar que existan todas las columnas necesarias
        if any(x is None for x in [columnas['ciudad'], columnas['fecha_ingreso'], columnas['fecha_factura']]):
            continue
        
        # Filtrar por ciudad
        mask_ciudad = df[columnas['ciudad']].astype(str).str.upper().str.contains(ciudad.upper(), na=False)
        df_ciudad = df[mask_ciudad]
        
        if len(df_ciudad) == 0:
            continue
        
        # Convertir fechas
        fechas_ingreso = pd.to_datetime(df_ciudad[columnas['fecha_ingreso']], errors='coerce')
        fechas_factura = pd.to_datetime(df_ciudad[columnas['fecha_factura']], errors='coerce')
        
        # Procesar cada registro
        for idx in range(len(df_ciudad)):
            fecha_ingreso = fechas_ingreso.iloc[idx]
            fecha_factura = fechas_factura.iloc[idx]
            
            if pd.isna(fecha_ingreso) or pd.isna(fecha_factura):
                continue
            
            # Verificar rango de factura
            if fecha_factura < fecha_inicio or fecha_factura > fecha_fin:
                continue
            
            fecha_key = fecha_factura.date()
            
            # Clasificar
            if fecha_ingreso >= fecha_inicio and fecha_factura >= fecha_inicio:
                facturado_modelo[fecha_key] = facturado_modelo.get(fecha_key, 0) + 1
            elif fecha_ingreso < fecha_inicio and fecha_factura < fecha_inicio:
                facturado_fuera[fecha_key] = facturado_fuera.get(fecha_key, 0) + 1
    
    return facturado_modelo, facturado_fuera

def construir_tabla(ciudad, fecha_inicio, fecha_fin, dfs):
    """Construye la tabla resumen para una ciudad"""
    
    # Generar todas las fechas del período
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Procesar datos
    ingresos_dict = procesar_ingresos(dfs, fecha_inicio, fecha_fin)
    modelo_dict, fuera_dict = procesar_facturacion(dfs, ciudad, fecha_inicio, fecha_fin)
    
    # Construir DataFrame
    datos = []
    for fecha in fechas:
        fecha_key = fecha.date()
        
        ingresos = ingresos_dict.get(fecha_key, 0)
        fact_modelo = modelo_dict.get(fecha_key, 0)
        fact_fuera = fuera_dict.get(fecha_key, 0)
        fact_total = fact_modelo + fact_fuera
        novedades = max(0, ingresos - fact_total)
        
        datos.append({
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'semana': fecha.isocalendar()[1],
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos,
            'facturado modelo': fact_modelo,
            'facturado fuera modelo': fact_fuera,
            'facturado total': fact_total,
            'Novedades': novedades
        })
    
    df = pd.DataFrame(datos)
    
    # Filtrar solo días con actividad
    df_filtrado = df[
        (df['ingresos'] > 0) | 
        (df['facturado modelo'] > 0) | 
        (df['facturado fuera modelo'] > 0)
    ]
    
    return df, df_filtrado

# Sidebar
with st.sidebar:
    st.header("📋 Información")
    st.markdown("**Fechas de inicio por ciudad:**")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"- **{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas de clasificación:**")
    st.markdown("""
    **Facturado Modelo:**
    - Ingreso ≥ Fecha inicio
    - Factura ≥ Fecha inicio
    
    **Facturado Fuera Modelo:**
    - Ingreso < Fecha inicio
    - Factura < Fecha inicio
    """)
    
    st.markdown("---")
    st.markdown("**Hojas requeridas:**")
    for hoja in HOJAS_REQUERIDAS:
        st.markdown(f"- {hoja}")

# Carga de archivo
st.header("📁 Cargar Archivo")

archivo = st.file_uploader(
    "Selecciona el archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: EVENTO, PGP, PDTE EVENTO, PDTE PGP"
)

if archivo:
    if st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
        with st.spinner("Cargando y procesando archivo..."):
            exito, dfs, fecha_max = cargar_archivo(archivo)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_maxima = fecha_max
                st.success("✅ Archivo procesado correctamente!")
                st.info(f"📅 Última fecha disponible: {fecha_max.strftime('%d/%m/%Y')}")

# Mostrar resultados
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen")
    
    # Selector de fecha final
    fecha_actual = datetime.now()
    fecha_max = st.session_state.fecha_maxima
    
    if fecha_max > fecha_actual:
        fecha_max = fecha_actual
    
    fecha_hasta = st.date_input(
        "📅 Seleccionar fecha final del reporte:",
        value=fecha_max.date(),
        min_value=datetime(2025, 9, 16).date(),
        max_value=fecha_actual.date(),
        help="La tabla mostrará datos desde la fecha de inicio de cada ciudad hasta esta fecha"
    )
    
    fecha_hasta_dt = datetime.combine(fecha_hasta, datetime.min.time())
    
    # Crear pestañas por ciudad
    tabs = st.tabs(list(CIUDADES.keys()))
    
    for tab, ciudad in zip(tabs, CIUDADES.keys()):
        with tab:
            fecha_inicio = CIUDADES[ciudad]['fecha_inicio']
            
            # Validar que fecha_hasta sea mayor que fecha_inicio
            if fecha_hasta_dt < fecha_inicio:
                st.warning(f"⚠️ La fecha seleccionada ({fecha_hasta_dt.strftime('%d/%m/%Y')}) es anterior a la fecha de inicio de {ciudad} ({fecha_inicio.strftime('%d/%m/%Y')})")
                st.info(f"Por favor, selecciona una fecha posterior al {fecha_inicio.strftime('%d/%m/%Y')}")
                continue
            
            with st.spinner(f"Procesando {ciudad}..."):
                # Construir tablas
                df_completa, df_filtrado = construir_tabla(
                    ciudad,
                    fecha_inicio,
                    fecha_hasta_dt,
                    st.session_state.dfs
                )
                
                if len(df_filtrado) > 0:
                    # Métricas
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("📥 Total Ingresos", f"{df_completa['ingresos'].sum():,}")
                    with col2:
                        st.metric("✅ Facturado Modelo", f"{df_completa['facturado modelo'].sum():,}")
                    with col3:
                        st.metric("❌ Facturado Fuera", f"{df_completa['facturado fuera modelo'].sum():,}")
                    with col4:
                        st.metric("💰 Facturado Total", f"{df_completa['facturado total'].sum():,}")
                    with col5:
                        st.metric("⚠️ Novedades", f"{df_completa['Novedades'].sum():,}")
                    
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
                    st.caption(f"📅 Mostrando {len(df_filtrado)} días con actividad del {df_filtrado['Fecha'].min()} al {df_filtrado['Fecha'].max()}")
                    
                    # Gráfico de evolución
                    if len(df_filtrado) > 1:
                        st.subheader("📈 Evolución Temporal")
                        chart_data = df_filtrado[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
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
                        f"{ciudad.lower()}_resumen.csv",
                        "text/csv",
                        key=f"csv_{ciudad}"
                    )
                    
                    # Excel
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_completa.to_excel(writer, sheet_name='Todos los días', index=False)
                        df_filtrado.to_excel(writer, sheet_name='Días con actividad', index=False)
                        
                        # Métricas
                        metrics = pd.DataFrame([
                            ['Ciudad', ciudad],
                            ['Fecha Inicio', fecha_inicio.strftime('%d/%m/%Y')],
                            ['Fecha Fin', fecha_hasta.strftime('%d/%m/%Y')],
                            ['Total Ingresos', df_completa['ingresos'].sum()],
                            ['Facturado Modelo', df_completa['facturado modelo'].sum()],
                            ['Facturado Fuera', df_completa['facturado fuera modelo'].sum()],
                            ['Facturado Total', df_completa['facturado total'].sum()],
                            ['Novedades', df_completa['Novedades'].sum()]
                        ], columns=['Métrica', 'Valor'])
                        metrics.to_excel(writer, sheet_name='Métricas', index=False)
                    
                    col2.download_button(
                        "📥 Descargar Excel",
                        output.getvalue(),
                        f"{ciudad.lower()}_resumen.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{ciudad}"
                    )
                    
                else:
                    st.info(f"No hay datos para {ciudad} en el período seleccionado")
                    st.caption(f"Período analizado: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Cargar otro archivo", use_container_width=True):
        for key in ['datos_cargados', 'dfs', 'fecha_maxima']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 1. Carga un archivo Excel\n\n👆 2. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para comenzar")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
