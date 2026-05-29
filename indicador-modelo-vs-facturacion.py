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
        
        # Cargar datos y preprocesar fechas
        dfs = {}
        for hoja in HOJAS_REQUERIDAS:
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            # Identificar y convertir columna de fecha ingreso
            col_fecha = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'fecha ingreso' in col_lower or 'fecha_ingreso' in col_lower or 'fechaing' in col_lower or 'ingreso' in col_lower:
                    col_fecha = col
                    break
            
            if col_fecha:
                # Convertir a datetime con dayfirst=True para formato DD/MM/YYYY
                df['_fecha_ingreso'] = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True)
            else:
                df['_fecha_ingreso'] = pd.NaT
            
            # Identificar columna de unidad operativa (para EVENTO y PGP)
            if hoja in ['EVENTO', 'PGP']:
                col_unidad = None
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if 'unidad operativa' in col_lower or 'unidad' in col_lower or 'operativa' in col_lower or 'ciudad' in col_lower:
                        col_unidad = col
                        break
                df['_unidad_operativa'] = df[col_unidad].astype(str).str.upper() if col_unidad else ''
            
            # Identificar columna de centro de atención (para PDTE EVENTO y PDTE PGP)
            if hoja in ['PDTE EVENTO', 'PDTE PGP']:
                col_centro = None
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if 'centro de atencion' in col_lower or 'centro' in col_lower or 'atencion' in col_lower:
                        col_centro = col
                        break
                df['_centro_atencion'] = df[col_centro].astype(str).str.upper() if col_centro else ''
            
            dfs[hoja] = df
            st.info(f"📄 Hoja '{hoja}': {len(df):,} registros")
        
        # Encontrar fecha máxima
        fecha_max = datetime.now()
        for df in dfs.values():
            fechas_validas = df['_fecha_ingreso'].dropna()
            if not fechas_validas.empty:
                max_fecha = fechas_validas.max()
                if max_fecha > fecha_max:
                    fecha_max = max_fecha
        
        return True, dfs, fecha_max
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return False, None, None

def procesar_ingresos_ciudad(dfs, ciudad, fecha_inicio, fecha_fin):
    """Procesa ingresos para una ciudad de manera vectorizada"""
    
    # Generar diccionario de ingresos por fecha
    ingresos_dict = {}
    
    # Procesar hojas EVENTO y PGP (filtro por unidad operativa)
    for hoja in ['EVENTO', 'PGP']:
        if hoja in dfs:
            df = dfs[hoja]
            
            # Filtrar por unidad operativa
            mask_unidad = df['_unidad_operativa'].str.contains(ciudad.upper(), na=False)
            df_filtrado = df[mask_unidad]
            
            # Filtrar por rango de fechas
            mask_fecha = (df_filtrado['_fecha_ingreso'] >= fecha_inicio) & (df_filtrado['_fecha_ingreso'] <= fecha_fin)
            fechas = df_filtrado.loc[mask_fecha, '_fecha_ingreso'].dt.date
            
            # Contar
            for fecha in fechas:
                ingresos_dict[fecha] = ingresos_dict.get(fecha, 0) + 1
    
    # Procesar hojas PDTE EVENTO y PDTE PGP (filtro por centro de atención SAN MARCEL)
    for hoja in ['PDTE EVENTO', 'PDTE PGP']:
        if hoja in dfs:
            df = dfs[hoja]
            
            # Filtrar por centro de atención SAN MARCEL
            mask_centro = df['_centro_atencion'].str.contains('SAN MARCEL', na=False)
            df_filtrado = df[mask_centro]
            
            # Filtrar por rango de fechas
            mask_fecha = (df_filtrado['_fecha_ingreso'] >= fecha_inicio) & (df_filtrado['_fecha_ingreso'] <= fecha_fin)
            fechas = df_filtrado.loc[mask_fecha, '_fecha_ingreso'].dt.date
            
            # Contar
            for fecha in fechas:
                ingresos_dict[fecha] = ingresos_dict.get(fecha, 0) + 1
    
    return ingresos_dict

def construir_tabla(ciudad, fecha_inicio, fecha_fin, dfs):
    """Construye la tabla con las fechas y calcula los ingresos"""
    
    # Procesar ingresos de manera vectorizada
    ingresos_dict = procesar_ingresos_ciudad(dfs, ciudad, fecha_inicio, fecha_fin)
    
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
        ingresos = ingresos_dict.get(fecha_key, 0)
        
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
    **Ingresos = Conteo de registros donde:**
    - EVENTO/PGP: unidad operativa = ciudad
    - PDTE EVENTO/PDTE PGP: centro atención = SAN MARCEL
    - Fecha ingreso está en el período
    """)

# Carga de archivo
st.header("📁 Cargar Archivo")

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
                
                # Establecer fecha inicial por defecto
                fecha_actual = datetime.now()
                if fecha_max > fecha_actual:
                    fecha_max = fecha_actual
                st.session_state.fecha_hasta = fecha_max
                
                st.success("✅ Archivo procesado correctamente!")

# Selector de fecha (disponible después de cargar)
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("⚙️ Configuración del Reporte")
    
    fecha_actual = datetime.now()
    fecha_max_disponible = st.session_state.fecha_maxima
    
    if fecha_max_disponible > fecha_actual:
        fecha_max_disponible = fecha_actual
    
    # Selector de fecha
    fecha_hasta = st.date_input(
        "📅 Seleccionar fecha final del reporte:",
        value=st.session_state.fecha_hasta.date() if st.session_state.fecha_hasta else fecha_max_disponible.date(),
        min_value=datetime(2025, 9, 16).date(),
        max_value=fecha_actual.date(),
        help="La tabla mostrará datos desde la fecha de inicio de cada ciudad hasta esta fecha"
    )
    
    # Actualizar fecha en session state
    st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
    
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    # Crear pestañas por ciudad
    tabs = st.tabs(list(CIUDADES.keys()))
    
    for tab, ciudad in zip(tabs, CIUDADES.keys()):
        with tab:
            fecha_inicio = CIUDADES[ciudad]['fecha_inicio']
            fecha_fin = st.session_state.fecha_hasta
            
            # Validar que fecha_fin sea mayor que fecha_inicio
            if fecha_fin < fecha_inicio:
                st.warning(f"⚠️ La fecha seleccionada ({fecha_fin.strftime('%d/%m/%Y')}) es anterior a la fecha de inicio de {ciudad}")
                continue
            
            with st.spinner(f"Procesando {ciudad}..."):
                # Construir tabla con ingresos
                df_completa, df_filtrado = construir_tabla(
                    ciudad,
                    fecha_inicio,
                    fecha_fin,
                    st.session_state.dfs
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
                    st.caption(f"📅 Mostrando {len(df_filtrado)} días con ingresos")
                    
                    # Gráfico de ingresos
                    if len(df_filtrado) > 1:
                        st.subheader("📈 Evolución de Ingresos")
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
                        f"{ciudad.lower()}_ingresos.csv",
                        "text/csv",
                        key=f"csv_{ciudad}"
                    )
                    
                    # Excel
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_completa.to_excel(writer, sheet_name='Todos los días', index=False)
                        df_filtrado.to_excel(writer, sheet_name='Días con ingresos', index=False)
                    
                    col2.download_button(
                        "📥 Descargar Excel",
                        output.getvalue(),
                        f"{ciudad.lower()}_ingresos.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{ciudad}"
                    )
                    
                else:
                    st.info(f"No hay ingresos para {ciudad} en el período seleccionado")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Reiniciar - Cargar otro archivo", use_container_width=True):
        for key in ['datos_cargados', 'dfs', 'fecha_maxima', 'fecha_hasta']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 1. Carga un archivo Excel\n\n👆 2. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para cargar los datos")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
