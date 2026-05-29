import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import calendar

# Configuración de la página
st.set_page_config(
    page_title="Tabla Resumen por Ciudad",
    page_icon="📊",
    layout="wide"
)

# Definición de ciudades con sus fechas de inicio
CIUDADES = {
    "MANIZALES": {
        "nombre": "Manizales",
        "fecha_inicio": datetime(2025, 9, 16)
    },
    "ARMENIA": {
        "nombre": "Armenia", 
        "fecha_inicio": datetime(2025, 11, 20)
    },
    "PEREIRA": {
        "nombre": "Pereira",
        "fecha_inicio": datetime(2026, 4, 15)
    }
}

HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']

# Inicializar session state
if 'datos_procesados' not in st.session_state:
    st.session_state.datos_procesados = None

def identificar_columna(df, posibles_nombres):
    """Identifica una columna basada en posibles nombres"""
    for col in df.columns:
        col_lower = col.lower().strip()
        for nombre in posibles_nombres:
            if nombre in col_lower:
                return col
    return None

def procesar_ciudad(dfs, ciudad, fecha_inicio_ciudad, fecha_fin):
    """Procesa los datos para una ciudad específica"""
    
    # Diccionarios para almacenar los resultados
    ingresos_dict = {}
    facturado_modelo_dict = {}
    facturado_fuera_dict = {}
    
    # 1. Procesar INGRESOS de todas las hojas (PDTE EVENTO, PDTE PGP, EVENTO, PGP)
    for hoja in ['PDTE EVENTO', 'PDTE PGP', 'EVENTO', 'PGP']:
        if hoja not in dfs:
            continue
        
        df = dfs[hoja]
        
        # Identificar columna de fecha de ingreso
        col_fecha_ingreso = identificar_columna(df, ['ingreso', 'fechaing', 'fecha ingreso'])
        
        if col_fecha_ingreso is None:
            continue
        
        # Convertir a datetime
        fechas_ingreso = pd.to_datetime(df[col_fecha_ingreso], errors='coerce')
        
        # Filtrar por rango de fechas
        mask = (fechas_ingreso >= fecha_inicio_ciudad) & (fechas_ingreso <= fecha_fin)
        
        # Contar ingresos por fecha
        for fecha in fechas_ingreso[mask]:
            fecha_key = fecha.date()
            ingresos_dict[fecha_key] = ingresos_dict.get(fecha_key, 0) + 1
    
    # 2. Procesar FACTURACIÓN de hojas EVENTO y PGP
    for hoja in ['EVENTO', 'PGP']:
        if hoja not in dfs:
            continue
        
        df = dfs[hoja]
        
        # Identificar columnas necesarias
        col_ciudad = identificar_columna(df, ['ciudad', 'unidad', 'ciiu', 'operativa'])
        col_fecha_ingreso = identificar_columna(df, ['ingreso', 'fechaing', 'fecha ingreso'])
        col_fecha_factura = identificar_columna(df, ['factura', 'fechafac', 'fecha factura'])
        
        if any(x is None for x in [col_ciudad, col_fecha_ingreso, col_fecha_factura]):
            continue
        
        # Filtrar por ciudad
        df_ciudad = df[df[col_ciudad].astype(str).str.upper().str.contains(ciudad, na=False)]
        
        if len(df_ciudad) == 0:
            continue
        
        # Convertir fechas
        fechas_ingreso = pd.to_datetime(df_ciudad[col_fecha_ingreso], errors='coerce')
        fechas_factura = pd.to_datetime(df_ciudad[col_fecha_factura], errors='coerce')
        
        # Procesar cada registro
        for idx in range(len(df_ciudad)):
            fecha_ingreso = fechas_ingreso.iloc[idx]
            fecha_factura = fechas_factura.iloc[idx]
            
            if pd.isna(fecha_ingreso) or pd.isna(fecha_factura):
                continue
            
            # Verificar rango de fecha de factura
            if fecha_factura < fecha_inicio_ciudad or fecha_factura > fecha_fin:
                continue
            
            fecha_key = fecha_factura.date()
            
            # Clasificar según las fechas
            if fecha_ingreso >= fecha_inicio_ciudad and fecha_factura >= fecha_inicio_ciudad:
                # Facturado modelo
                facturado_modelo_dict[fecha_key] = facturado_modelo_dict.get(fecha_key, 0) + 1
            elif fecha_ingreso < fecha_inicio_ciudad and fecha_factura < fecha_inicio_ciudad:
                # Facturado fuera modelo
                facturado_fuera_dict[fecha_key] = facturado_fuera_dict.get(fecha_key, 0) + 1
    
    return ingresos_dict, facturado_modelo_dict, facturado_fuera_dict

def construir_tabla_resumen(ciudad, config, dfs, fecha_hasta):
    """Construye la tabla resumen para una ciudad"""
    
    fecha_inicio = config['fecha_inicio']
    
    # Generar todas las fechas desde inicio hasta fecha_hasta
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_hasta:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Procesar datos de la ciudad
    ingresos_dict, modelo_dict, fuera_dict = procesar_ciudad(
        dfs, ciudad, fecha_inicio, fecha_hasta
    )
    
    # Construir tabla
    tabla = []
    for fecha in fechas:
        fecha_key = fecha.date()
        
        ingresos = ingresos_dict.get(fecha_key, 0)
        facturado_modelo = modelo_dict.get(fecha_key, 0)
        facturado_fuera = fuera_dict.get(fecha_key, 0)
        facturado_total = facturado_modelo + facturado_fuera
        novedades = max(0, ingresos - facturado_total)
        
        tabla.append({
            'semana': fecha.isocalendar()[1],
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos,
            'facturado modelo': facturado_modelo,
            'facturado fuera modelo': facturado_fuera,
            'facturado total': facturado_total,
            'Novedades': novedades
        })
    
    df_tabla = pd.DataFrame(tabla)
    
    # Filtrar solo días con actividad (opcional, pero mejora visualización)
    df_tabla_filtrada = df_tabla[
        (df_tabla['ingresos'] > 0) | 
        (df_tabla['facturado modelo'] > 0) | 
        (df_tabla['facturado fuera modelo'] > 0)
    ]
    
    return df_tabla, df_tabla_filtrada

def obtener_fecha_maxima(dfs):
    """Obtiene la fecha máxima disponible en todas las hojas"""
    fechas_maximas = []
    
    for hoja, df in dfs.items():
        # Buscar columnas de fecha
        for col in df.columns:
            if 'fecha' in col.lower() or 'ingreso' in col.lower() or 'factura' in col.lower():
                try:
                    fechas = pd.to_datetime(df[col], errors='coerce')
                    fecha_max = fechas.max()
                    if pd.notna(fecha_max):
                        fechas_maximas.append(fecha_max)
                except:
                    continue
    
    if fechas_maximas:
        return max(fechas_maximas)
    return datetime.now()

# Interfaz de usuario
st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📋 Configuración")
    st.markdown("**Fechas de inicio por ciudad:**")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"- **{config['nombre']}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas de clasificación:**")
    st.markdown("""
    **Facturado Modelo:**
    - Fecha Ingreso ≥ Fecha Inicio Ciudad
    - Fecha Factura ≥ Fecha Inicio Ciudad
    
    **Facturado Fuera Modelo:**
    - Fecha Ingreso < Fecha Inicio Ciudad
    - Fecha Factura < Fecha Inicio Ciudad
    """)

# Carga de archivo
st.header("📁 Cargar Archivo")

archivo = st.file_uploader(
    "Selecciona archivo Excel",
    type=['xlsx', 'xls']
)

if archivo:
    if st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
        with st.spinner("Cargando y procesando archivo..."):
            try:
                # Leer todas las hojas
                excel_file = pd.ExcelFile(archivo)
                hojas_existentes = excel_file.sheet_names
                
                # Verificar hojas requeridas
                hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_existentes]
                
                if hojas_faltantes:
                    st.error(f"❌ Faltan las siguientes hojas: {', '.join(hojas_faltantes)}")
                else:
                    # Cargar datos
                    dfs = {}
                    for hoja in HOJAS_REQUERIDAS:
                        dfs[hoja] = pd.read_excel(archivo, sheet_name=hoja)
                        st.info(f"📄 {hoja}: {len(dfs[hoja]):,} registros")
                    
                    # Obtener fecha máxima
                    fecha_maxima = obtener_fecha_maxima(dfs)
                    
                    # Guardar en session state
                    st.session_state.datos_procesados = {
                        'dfs': dfs,
                        'fecha_maxima': fecha_maxima
                    }
                    
                    st.success("✅ Archivo procesado correctamente!")
                    st.info(f"📅 Fecha máxima encontrada: {fecha_maxima.strftime('%d/%m/%Y')}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Mostrar resultados
if st.session_state.datos_procesados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    dfs = st.session_state.datos_procesados['dfs']
    fecha_maxima = st.session_state.datos_procesados['fecha_maxima']
    
    # Selector de fecha final
    col1, col2 = st.columns([2, 1])
    with col1:
        fecha_hasta = st.date_input(
            "Fecha final del resumen:",
            value=fecha_maxima.date(),
            min_value=datetime(2025, 9, 16).date(),
            max_value=fecha_maxima.date()
        )
    
    fecha_hasta_dt = datetime.combine(fecha_hasta, datetime.min.time())
    
    # Crear tabs para cada ciudad
    tabs = st.tabs([CIUDADES[ciudad]['nombre'] for ciudad in CIUDADES.keys()])
    
    for tab, ciudad in zip(tabs, CIUDADES.keys()):
        with tab:
            with st.spinner(f"Procesando {CIUDADES[ciudad]['nombre']}..."):
                # Construir tabla
                df_completa, df_filtrada = construir_tabla_resumen(
                    ciudad,
                    CIUDADES[ciudad],
                    dfs,
                    fecha_hasta_dt
                )
                
                if len(df_filtrada) > 0:
                    # Métricas
                    st.subheader(f"📈 Métricas - {CIUDADES[ciudad]['nombre']}")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Total Ingresos", f"{df_completa['ingresos'].sum():,}")
                    with col2:
                        st.metric("Facturado Modelo", f"{df_completa['facturado modelo'].sum():,}")
                    with col3:
                        st.metric("Facturado Fuera", f"{df_completa['facturado fuera modelo'].sum():,}")
                    with col4:
                        st.metric("Facturado Total", f"{df_completa['facturado total'].sum():,}")
                    with col5:
                        st.metric("Novedades", f"{df_completa['Novedades'].sum():,}")
                    
                    # Mostrar tabla
                    st.subheader("📋 Detalle por Fecha")
                    st.dataframe(
                        df_filtrada,
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
                    
                    # Mostrar estadísticas de fechas
                    st.caption(f"📅 Mostrando {len(df_filtrada)} días con actividad del {df_filtrada['Fecha'].min()} al {df_filtrada['Fecha'].max()}")
                    
                    # Gráfico
                    if len(df_filtrada) > 1:
                        st.subheader("📈 Evolución Temporal")
                        chart_data = df_filtrada[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
                        chart_data.index = pd.to_datetime(df_filtrada['Fecha'])
                        st.line_chart(chart_data)
                    
                    # Descargas
                    st.subheader("💾 Exportar Datos")
                    col1, col2 = st.columns(2)
                    
                    # CSV
                    csv_data = df_completa.to_csv(index=False).encode('utf-8')
                    col1.download_button(
                        f"📥 Descargar CSV Completo",
                        csv_data,
                        f"{ciudad.lower()}_resumen_completo.csv",
                        "text/csv",
                        key=f"csv_{ciudad}"
                    )
                    
                    # Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_completa.to_excel(writer, sheet_name='Detalle Completo', index=False)
                        df_filtrada.to_excel(writer, sheet_name='Días con Actividad', index=False)
                        
                        # Agregar métricas
                        metrics = pd.DataFrame([
                            ['Ciudad', CIUDADES[ciudad]['nombre']],
                            ['Fecha Inicio', CIUDADES[ciudad]['fecha_inicio'].strftime('%d/%m/%Y')],
                            ['Fecha Fin', fecha_hasta.strftime('%d/%m/%Y')],
                            ['Total Ingresos', df_completa['ingresos'].sum()],
                            ['Facturado Modelo', df_completa['facturado modelo'].sum()],
                            ['Facturado Fuera Modelo', df_completa['facturado fuera modelo'].sum()],
                            ['Facturado Total', df_completa['facturado total'].sum()],
                            ['Novedades', df_completa['Novedades'].sum()]
                        ], columns=['Métrica', 'Valor'])
                        metrics.to_excel(writer, sheet_name='Métricas', index=False)
                    
                    col2.download_button(
                        f"📥 Descargar Excel Completo",
                        output.getvalue(),
                        f"{ciudad.lower()}_resumen_completo.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{ciudad}"
                    )
                    
                else:
                    st.warning(f"No hay datos para {CIUDADES[ciudad]['nombre']} en el período seleccionado")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Cargar otro archivo", use_container_width=True):
        st.session_state.datos_procesados = None
        st.rerun()

else:
    if archivo is None:
        st.info("👆 Carga un archivo Excel y presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para comenzar")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
