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
        for hoja in HOJAS_REQUERIDAS:
            dfs[hoja] = pd.read_excel(archivo, sheet_name=hoja)
            st.info(f"📄 Hoja '{hoja}': {len(dfs[hoja]):,} registros")
        
        # Encontrar fecha máxima en todas las hojas
        fecha_max = datetime.now()  # Valor por defecto
        
        for hoja, df in dfs.items():
            # Buscar columnas de fecha
            for col in df.columns:
                if 'fecha' in col.lower() or 'ingreso' in col.lower() or 'factura' in col.lower():
                    try:
                        fechas = pd.to_datetime(df[col], errors='coerce')
                        if not fechas.dropna().empty:
                            max_fecha = fechas.max()
                            if fecha_max is None or max_fecha > fecha_max:
                                fecha_max = max_fecha
                    except:
                        continue
        
        return True, dfs, fecha_max
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return False, None, None

def construir_tabla_fechas(ciudad, fecha_inicio, fecha_fin):
    """CONSTRUYE SOLAMENTE LA TABLA CON LAS FECHAS - SIN CRUZAR DATOS"""
    
    # Generar todas las fechas del período
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Construir DataFrame SOLO con las fechas
    datos = []
    for fecha in fechas:
        datos.append({
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'semana': fecha.isocalendar()[1],
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': 0,  # Temporalmente en 0
            'facturado modelo': 0,  # Temporalmente en 0
            'facturado fuera modelo': 0,  # Temporalmente en 0
            'facturado total': 0,  # Temporalmente en 0
            'Novedades': 0  # Temporalmente en 0
        })
    
    df = pd.DataFrame(datos)
    return df

# Sidebar
with st.sidebar:
    st.header("📋 Información")
    st.markdown("**Fechas de inicio por ciudad:**")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"- **{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas de clasificación (pendientes):**")
    st.markdown("""
    - Próximamente: Cruce de datos con las hojas del archivo
    - Por ahora: Solo estructura de fechas
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
                st.info(f"📅 Última fecha disponible en los datos: {fecha_max.strftime('%d/%m/%Y')}")

# Selector de fecha (disponible TODO el tiempo después de cargar)
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("⚙️ Configuración del Reporte")
    
    fecha_actual = datetime.now()
    fecha_max_disponible = st.session_state.fecha_maxima
    
    if fecha_max_disponible > fecha_actual:
        fecha_max_disponible = fecha_actual
    
    # Selector de fecha - SIEMPRE visible después de cargar
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
                st.warning(f"⚠️ La fecha seleccionada ({fecha_fin.strftime('%d/%m/%Y')}) es anterior a la fecha de inicio de {ciudad} ({fecha_inicio.strftime('%d/%m/%Y')})")
                st.info(f"Por favor, selecciona una fecha posterior al {fecha_inicio.strftime('%d/%m/%Y')}")
                continue
            
            # Construir tabla SOLO con fechas (sin cruce de datos)
            df_tabla = construir_tabla_fechas(ciudad, fecha_inicio, fecha_fin)
            
            if len(df_tabla) > 0:
                # Métricas (todas en 0 por ahora)
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("📥 Total Ingresos", "0")
                with col2:
                    st.metric("✅ Facturado Modelo", "0")
                with col3:
                    st.metric("❌ Facturado Fuera", "0")
                with col4:
                    st.metric("💰 Facturado Total", "0")
                with col5:
                    st.metric("⚠️ Novedades", "0")
                
                # Mostrar tabla
                st.dataframe(
                    df_tabla,
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
                st.caption(f"📅 Mostrando {len(df_tabla)} días desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')}")
                st.info("ℹ️ Los valores numéricos están en 0 temporalmente. Próximamente se agregará el cruce con los datos del archivo.")
                
                # Exportar datos
                st.subheader("💾 Exportar Datos")
                
                col1, col2 = st.columns(2)
                
                # CSV
                csv = df_tabla.to_csv(index=False).encode('utf-8')
                col1.download_button(
                    "📥 Descargar CSV",
                    csv,
                    f"{ciudad.lower()}_estructura_fechas.csv",
                    "text/csv",
                    key=f"csv_{ciudad}"
                )
                
                # Excel
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_tabla.to_excel(writer, sheet_name='Estructura Fechas', index=False)
                    
                    # Información del período
                    info = pd.DataFrame([
                        ['Ciudad', ciudad],
                        ['Fecha Inicio', fecha_inicio.strftime('%d/%m/%Y')],
                        ['Fecha Fin', fecha_fin.strftime('%d/%m/%Y')],
                        ['Total Días', len(df_tabla)],
                        ['Nota', 'Estructura sin cruce de datos aún']
                    ], columns=['Información', 'Valor'])
                    info.to_excel(writer, sheet_name='Información', index=False)
                
                col2.download_button(
                    "📥 Descargar Excel",
                    output.getvalue(),
                    f"{ciudad.lower()}_estructura_fechas.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"excel_{ciudad}"
                )
                
            else:
                st.info(f"No hay fechas para mostrar para {ciudad}")
    
    # Botón para reiniciar (opcional)
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
st.caption("Aplicación para análisis de facturación por ciudad - Versión con estructura de fechas")
