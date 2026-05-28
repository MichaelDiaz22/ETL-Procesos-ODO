import streamlit as st
import pandas as pd
from datetime import datetime
import io
import calendar

# Configuración de la página
st.set_page_config(
    page_title="Tabla Resumen por Ciudad",
    page_icon="📊",
    layout="wide"
)

# Título de la aplicación
st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# Definición de ciudades con sus fechas de corte
CIUDADES_CONFIG = {
    "MANIZALES": {
        "fecha_inicio": datetime(2025, 9, 16),
        "nombre_completo": "Manizales"
    },
    "ARMENIA": {
        "fecha_inicio": datetime(2025, 11, 20),
        "nombre_completo": "Armenia"
    },
    "PEREIRA": {
        "fecha_inicio": datetime(2026, 4, 15),
        "nombre_completo": "Pereira"
    }
}

# Hojas requeridas
HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']

# Inicializar session state
if 'archivo_procesado' not in st.session_state:
    st.session_state.archivo_procesado = False
if 'datos_hojas' not in st.session_state:
    st.session_state.datos_hojas = {}
if 'fecha_maxima' not in st.session_state:
    st.session_state.fecha_maxima = None
if 'fecha_hasta' not in st.session_state:
    st.session_state.fecha_hasta = None

def limpiar_fecha(fecha):
    """Convierte diferentes formatos de fecha a datetime"""
    if pd.isna(fecha):
        return None
    try:
        return pd.to_datetime(fecha, errors='coerce')
    except:
        return None

def normalizar_ciudad(ciudad):
    """Normaliza el nombre de la ciudad"""
    if pd.isna(ciudad):
        return None
    ciudad_str = str(ciudad).upper().strip()
    
    if 'MANIZALES' in ciudad_str:
        return 'MANIZALES'
    elif 'ARMENIA' in ciudad_str:
        return 'ARMENIA'
    elif 'PEREIRA' in ciudad_str:
        return 'PEREIRA'
    return None

def obtener_fecha_maxima(dfs_hojas):
    """Obtiene la fecha máxima disponible en todas las hojas"""
    fechas_maximas = []
    
    for hoja_nombre, df in dfs_hojas.items():
        # Buscar columnas de fecha
        for col in df.columns:
            col_lower = col.lower()
            if 'fecha' in col_lower or 'ingreso' in col_lower or 'factura' in col_lower:
                try:
                    # Intentar convertir a datetime
                    fechas_temp = pd.to_datetime(df[col], errors='coerce')
                    fechas_validas = fechas_temp.dropna()
                    if len(fechas_validas) > 0:
                        fechas_maximas.append(fechas_validas.max())
                except:
                    continue
    
    if fechas_maximas:
        return max(fechas_maximas)
    return datetime.now()

def procesar_datos_ingresos(dfs_hojas, fecha_inicio, fecha_fin):
    """Procesa los ingresos desde todas las hojas"""
    ingresos_por_fecha = {}
    
    for hoja_nombre in ['PDTE EVENTO', 'PDTE PGP', 'EVENTO', 'PGP']:
        if hoja_nombre not in dfs_hojas:
            continue
            
        df = dfs_hojas[hoja_nombre]
        
        # Buscar columna de fecha de ingreso
        col_fecha_ingreso = None
        for col in df.columns:
            col_lower = col.lower()
            if 'ingreso' in col_lower or 'fechaing' in col_lower:
                col_fecha_ingreso = col
                break
        
        if col_fecha_ingreso is None:
            continue
        
        # Convertir la columna a datetime
        fechas = pd.to_datetime(df[col_fecha_ingreso], errors='coerce')
        
        # Filtrar por rango de fechas
        mask = (fechas >= fecha_inicio) & (fechas <= fecha_fin)
        fechas_filtradas = fechas[mask]
        
        # Contar ingresos por fecha
        for fecha in fechas_filtradas.dt.date.unique():
            count = (fechas_filtradas.dt.date == fecha).sum()
            ingresos_por_fecha[fecha] = ingresos_por_fecha.get(fecha, 0) + count
    
    return ingresos_por_fecha

def procesar_datos_facturacion(dfs_hojas, ciudad, fecha_inicio, fecha_fin):
    """Procesa la facturación desde las hojas EVENTO y PGP"""
    facturado_modelo = {}
    facturado_fuera_modelo = {}
    
    for hoja_nombre in ['EVENTO', 'PGP']:
        if hoja_nombre not in dfs_hojas:
            continue
            
        df = dfs_hojas[hoja_nombre]
        
        # Buscar columnas necesarias
        col_ciudad = None
        col_fecha_ingreso = None
        col_fecha_factura = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'ciudad' in col_lower or 'unidad' in col_lower:
                if col_ciudad is None:
                    col_ciudad = col
            elif 'ingreso' in col_lower:
                if col_fecha_ingreso is None:
                    col_fecha_ingreso = col
            elif 'factura' in col_lower:
                if col_fecha_factura is None:
                    col_fecha_factura = col
        
        if col_ciudad is None or col_fecha_ingreso is None or col_fecha_factura is None:
            continue
        
        # Convertir fechas
        fechas_ingreso = pd.to_datetime(df[col_fecha_ingreso], errors='coerce')
        fechas_factura = pd.to_datetime(df[col_fecha_factura], errors='coerce')
        ciudades = df[col_ciudad].apply(normalizar_ciudad)
        
        # Filtrar por ciudad y fechas válidas
        mask = (ciudades == ciudad) & fechas_factura.notna() & fechas_ingreso.notna()
        
        for idx in df[mask].index:
            fecha_ingreso = fechas_ingreso[idx]
            fecha_factura = fechas_factura[idx]
            
            # Verificar rango de fechas
            if fecha_factura < fecha_inicio or fecha_factura > fecha_fin:
                continue
            
            fecha_key = fecha_factura.date()
            
            # Determinar si es modelo o fuera modelo
            if fecha_ingreso >= fecha_inicio and fecha_factura >= fecha_inicio:
                facturado_modelo[fecha_key] = facturado_modelo.get(fecha_key, 0) + 1
            elif fecha_ingreso < fecha_inicio and fecha_factura < fecha_inicio:
                facturado_fuera_modelo[fecha_key] = facturado_fuera_modelo.get(fecha_key, 0) + 1
    
    return facturado_modelo, facturado_fuera_modelo

def construir_tabla_resumen(ciudad, config, dfs_hojas, fecha_hasta):
    """Construye la tabla resumen para una ciudad específica"""
    fecha_inicio = config['fecha_inicio']
    
    # Generar rango de fechas
    fechas = pd.date_range(start=fecha_inicio, end=fecha_hasta, freq='D')
    
    # Procesar datos
    ingresos_dict = procesar_datos_ingresos(dfs_hojas, fecha_inicio, fecha_hasta)
    facturado_modelo_dict, facturado_fuera_modelo_dict = procesar_datos_facturacion(
        dfs_hojas, ciudad, fecha_inicio, fecha_hasta
    )
    
    # Construir DataFrame
    datos_resumen = []
    
    for fecha in fechas:
        fecha_key = fecha.date()
        
        ingresos = ingresos_dict.get(fecha_key, 0)
        facturado_modelo = facturado_modelo_dict.get(fecha_key, 0)
        facturado_fuera_modelo = facturado_fuera_modelo_dict.get(fecha_key, 0)
        facturado_total = facturado_modelo + facturado_fuera_modelo
        novedades = max(0, ingresos - facturado_total)
        
        # Solo agregar si hay algún valor relevante
        if ingresos > 0 or facturado_total > 0:
            datos_resumen.append({
                'semana': fecha.isocalendar()[1],
                'Fecha': fecha.strftime('%Y-%m-%d'),
                'año': fecha.year,
                'mes': calendar.month_name[fecha.month],
                'ingresos': ingresos,
                'facturado modelo': facturado_modelo,
                'facturado fuera modelo': facturado_fuera_modelo,
                'facturado total': facturado_total,
                'Novedades': novedades
            })
    
    return pd.DataFrame(datos_resumen)

# Sidebar
with st.sidebar:
    st.header("📋 Configuración")
    st.markdown("**Fechas de inicio:**")
    for ciudad, config in CIUDADES_CONFIG.items():
        st.markdown(f"- **{config['nombre_completo']}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas:**")
    st.markdown("""
    **Modelo:** Ingreso ≥ inicio y Factura ≥ inicio
    **Fuera modelo:** Ingreso < inicio y Factura < inicio
    """)
    
    st.markdown("---")
    st.markdown("**Hojas requeridas:**")
    for hoja in HOJAS_REQUERIDAS:
        st.markdown(f"- {hoja}")

# Área principal
st.header("📁 Carga de Archivo")

archivo_subido = st.file_uploader(
    "Selecciona un archivo Excel",
    type=['xlsx', 'xls'],
    key="file_uploader"
)

if archivo_subido is not None:
    # Procesar archivo si es nuevo
    if not st.session_state.archivo_procesado:
        with st.spinner("Cargando y procesando archivo..."):
            try:
                # Leer todas las hojas
                excel_file = pd.ExcelFile(archivo_subido)
                hojas_disponibles = excel_file.sheet_names
                
                # Verificar hojas requeridas
                hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_disponibles]
                
                if hojas_faltantes:
                    st.error(f"❌ Faltan hojas: {', '.join(hojas_faltantes)}")
                else:
                    # Cargar datos
                    for hoja in HOJAS_REQUERIDAS:
                        st.session_state.datos_hojas[hoja] = pd.read_excel(archivo_subido, sheet_name=hoja)
                    
                    # Calcular fecha máxima
                    st.session_state.fecha_maxima = obtener_fecha_maxima(st.session_state.datos_hojas)
                    st.session_state.fecha_hasta = st.session_state.fecha_maxima.date()
                    st.session_state.archivo_procesado = True
                    
                    st.success("✅ Archivo cargado correctamente")
                    
                    # Mostrar resumen de carga
                    for hoja in HOJAS_REQUERIDAS:
                        st.info(f"📄 {hoja}: {len(st.session_state.datos_hojas[hoja]):,} registros")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state.archivo_procesado = False
    
    # Mostrar resultados si el archivo está procesado
    if st.session_state.archivo_procesado and st.session_state.datos_hojas:
        st.markdown("---")
        st.header("📊 Tablas Resumen")
        
        # Selector de fecha
        fecha_max_date = st.session_state.fecha_maxima.date()
        fecha_min_date = datetime(2025, 9, 16).date()
        
        fecha_hasta = st.date_input(
            "Fecha final:",
            value=st.session_state.fecha_hasta,
            min_value=fecha_min_date,
            max_value=fecha_max_date,
            key="fecha_selector"
        )
        
        # Actualizar fecha si cambió
        if fecha_hasta != st.session_state.fecha_hasta:
            st.session_state.fecha_hasta = fecha_hasta
        
        # Convertir a datetime
        fecha_hasta_dt = datetime.combine(st.session_state.fecha_hasta, datetime.min.time())
        
        # Crear pestañas para cada ciudad
        tabs = st.tabs([CIUDADES_CONFIG[ciudad]['nombre_completo'] for ciudad in CIUDADES_CONFIG.keys()])
        
        for tab, ciudad in zip(tabs, CIUDADES_CONFIG.keys()):
            with tab:
                with st.spinner(f"Procesando {CIUDADES_CONFIG[ciudad]['nombre_completo']}..."):
                    try:
                        # Construir tabla
                        df_resumen = construir_tabla_resumen(
                            ciudad,
                            CIUDADES_CONFIG[ciudad],
                            st.session_state.datos_hojas,
                            fecha_hasta_dt
                        )
                        
                        if len(df_resumen) > 0:
                            # Métricas
                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("Total Ingresos", f"{df_resumen['ingresos'].sum():,}")
                            with col2:
                                st.metric("Facturado Modelo", f"{df_resumen['facturado modelo'].sum():,}")
                            with col3:
                                st.metric("Facturado Fuera", f"{df_resumen['facturado fuera modelo'].sum():,}")
                            with col4:
                                st.metric("Facturado Total", f"{df_resumen['facturado total'].sum():,}")
                            with col5:
                                st.metric("Novedades", f"{df_resumen['Novedades'].sum():,}")
                            
                            # Tabla
                            st.dataframe(
                                df_resumen,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "semana": "Semana",
                                    "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                                    "año": "Año",
                                    "mes": "Mes",
                                    "ingresos": st.column_config.NumberColumn("Ingresos", format="%d"),
                                    "facturado modelo": st.column_config.NumberColumn("Fact. Modelo", format="%d"),
                                    "facturado fuera modelo": st.column_config.NumberColumn("Fact. Fuera", format="%d"),
                                    "facturado total": st.column_config.NumberColumn("Fact. Total", format="%d"),
                                    "Novedades": st.column_config.NumberColumn("Novedades", format="%d")
                                }
                            )
                            
                            # Gráfico
                            if len(df_resumen) > 1:
                                chart_data = df_resumen[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
                                chart_data.index = pd.to_datetime(df_resumen['Fecha'])
                                st.line_chart(chart_data)
                            
                            # Descargas
                            col1, col2 = st.columns(2)
                            with col1:
                                csv = df_resumen.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    f"📥 CSV {CIUDADES_CONFIG[ciudad]['nombre_completo']}",
                                    csv,
                                    f"resumen_{ciudad.lower()}.csv",
                                    "text/csv"
                                )
                            with col2:
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    df_resumen.to_excel(writer, sheet_name=ciudad, index=False)
                                st.download_button(
                                    f"📥 Excel {CIUDADES_CONFIG[ciudad]['nombre_completo']}",
                                    output.getvalue(),
                                    f"resumen_{ciudad.lower()}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.info("No hay datos en el rango seleccionado")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

else:
    # Reset al cargar nuevo archivo
    st.session_state.archivo_procesado = False
    st.session_state.datos_hojas = {}
    st.info("👆 Carga un archivo Excel para comenzar")
    
    with st.expander("📋 Ver ejemplo"):
        st.markdown("""
        **Hojas requeridas:** EVENTO, PGP, PDTE EVENTO, PDTE PGP
        
        **Columnas necesarias:**
        - Ciudad / Unidad Operativa
        - Fecha Ingreso
        - Fecha Factura (para EVENTO y PGP)
        """)

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
