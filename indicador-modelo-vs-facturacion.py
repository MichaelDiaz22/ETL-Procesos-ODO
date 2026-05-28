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
if 'archivo_cargado' not in st.session_state:
    st.session_state.archivo_cargado = None
if 'datos_hojas' not in st.session_state:
    st.session_state.datos_hojas = {}
if 'tablas_resumen' not in st.session_state:
    st.session_state.tablas_resumen = {}

def limpiar_fecha(fecha):
    """Convierte diferentes formatos de fecha a datetime"""
    if pd.isna(fecha):
        return None
    try:
        return pd.to_datetime(fecha)
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

def procesar_datos_ingresos(dfs_hojas, fecha_inicio, fecha_fin):
    """
    Procesa los ingresos desde las hojas PDTE EVENTO, PDTE PGP, EVENTO, PGP
    """
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
        
        # Procesar cada registro
        for idx, row in df.iterrows():
            fecha_ingreso = limpiar_fecha(row[col_fecha_ingreso])
            
            if fecha_ingreso is None:
                continue
            
            # Filtrar por rango de fechas
            if fecha_inicio <= fecha_ingreso <= fecha_fin:
                fecha_key = fecha_ingreso.date()
                ingresos_por_fecha[fecha_key] = ingresos_por_fecha.get(fecha_key, 0) + 1
    
    return ingresos_por_fecha

def procesar_datos_facturacion(dfs_hojas, ciudad, fecha_inicio, fecha_fin):
    """
    Procesa la facturación desde las hojas EVENTO y PGP
    Retorna diccionarios con facturado modelo y fuera modelo por fecha
    """
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
            if 'ciudad' in col_lower or 'unidad' in col_lower or 'operativa' in col_lower:
                if col_ciudad is None:
                    col_ciudad = col
            elif 'ingreso' in col_lower or 'fechaing' in col_lower:
                if col_fecha_ingreso is None:
                    col_fecha_ingreso = col
            elif 'factura' in col_lower or 'fechafac' in col_lower:
                if col_fecha_factura is None:
                    col_fecha_factura = col
        
        if col_ciudad is None or col_fecha_ingreso is None or col_fecha_factura is None:
            continue
        
        # Procesar cada registro
        for idx, row in df.iterrows():
            ciudad_registro = normalizar_ciudad(row[col_ciudad])
            
            # Filtrar por ciudad
            if ciudad_registro != ciudad:
                continue
            
            fecha_ingreso = limpiar_fecha(row[col_fecha_ingreso])
            fecha_factura = limpiar_fecha(row[col_fecha_factura])
            
            if fecha_ingreso is None or fecha_factura is None:
                continue
            
            # Filtrar por rango de fechas de factura
            if fecha_factura < fecha_inicio or fecha_factura > fecha_fin:
                continue
            
            fecha_key = fecha_factura.date()
            
            # Determinar si es modelo o fuera modelo
            if fecha_ingreso >= fecha_inicio and fecha_factura >= fecha_inicio:
                # Incluido en el modelo
                facturado_modelo[fecha_key] = facturado_modelo.get(fecha_key, 0) + 1
            elif fecha_ingreso < fecha_inicio and fecha_factura < fecha_inicio:
                # Fuera del modelo
                facturado_fuera_modelo[fecha_key] = facturado_fuera_modelo.get(fecha_key, 0) + 1
    
    return facturado_modelo, facturado_fuera_modelo

def construir_tabla_resumen(ciudad, config, dfs_hojas, fecha_hasta):
    """
    Construye la tabla resumen para una ciudad específica
    """
    fecha_inicio = config['fecha_inicio']
    
    # Generar rango de fechas
    fechas = pd.date_range(start=fecha_inicio, end=fecha_hasta, freq='D')
    
    # Procesar ingresos
    ingresos_dict = procesar_datos_ingresos(dfs_hojas, fecha_inicio, fecha_hasta)
    
    # Procesar facturación
    facturado_modelo_dict, facturado_fuera_modelo_dict = procesar_datos_facturacion(
        dfs_hojas, ciudad, fecha_inicio, fecha_hasta
    )
    
    # Construir DataFrame
    datos_resumen = []
    
    for fecha in fechas:
        fecha_key = fecha.date()
        
        # Obtener valores
        ingresos = ingresos_dict.get(fecha_key, 0)
        facturado_modelo = facturado_modelo_dict.get(fecha_key, 0)
        facturado_fuera_modelo = facturado_fuera_modelo_dict.get(fecha_key, 0)
        facturado_total = facturado_modelo + facturado_fuera_modelo
        
        # Calcular novedades (registros que no cumplen condiciones)
        novedades = ingresos - facturado_total
        
        datos_resumen.append({
            'semana': fecha.isocalendar()[1],
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos,
            'facturado modelo': facturado_modelo,
            'facturado fuera modelo': facturado_fuera_modelo,
            'facturado total': facturado_total,
            'Novedades': novedades if novedades > 0 else 0
        })
    
    df_resumen = pd.DataFrame(datos_resumen)
    
    # Agregar estadísticas adicionales
    st.session_state.tablas_resumen[ciudad] = {
        'df': df_resumen,
        'fecha_inicio': fecha_inicio,
        'total_ingresos': df_resumen['ingresos'].sum(),
        'total_facturado_modelo': df_resumen['facturado modelo'].sum(),
        'total_facturado_fuera': df_resumen['facturado fuera modelo'].sum(),
        'total_facturado': df_resumen['facturado total'].sum(),
        'total_novedades': df_resumen['Novedades'].sum()
    }
    
    return df_resumen

# Sidebar con información
with st.sidebar:
    st.header("📋 Configuración")
    st.markdown("**Fechas de inicio por ciudad:**")
    for ciudad, config in CIUDADES_CONFIG.items():
        st.markdown(f"- **{config['nombre_completo']}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas de clasificación:**")
    st.markdown("""
    **Incluido en el modelo:**
    - Fecha ingreso ≥ fecha inicio ciudad
    - Fecha factura ≥ fecha inicio ciudad
    
    **Fuera del modelo:**
    - Fecha ingreso < fecha inicio ciudad
    - Fecha factura < fecha inicio ciudad
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
    help="Carga un archivo Excel con las hojas: EVENTO, PGP, PDTE EVENTO, PDTE PGP",
    key="file_uploader_main"
)

if archivo_subido is not None:
    # Verificar si es un archivo nuevo
    if st.session_state.archivo_cargado != archivo_subido.name:
        st.session_state.archivo_cargado = archivo_subido.name
        st.session_state.datos_hojas = {}
        st.session_state.tablas_resumen = {}
        
        try:
            # Leer el archivo Excel
            with st.spinner("Cargando archivo Excel..."):
                excel_file = pd.ExcelFile(archivo_subido)
                hojas_disponibles = excel_file.sheet_names
            
            # Verificar hojas requeridas
            hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_disponibles]
            
            if hojas_faltantes:
                st.error(f"❌ Faltan las siguientes hojas requeridas: {', '.join(hojas_faltantes)}")
                st.warning("Por favor, asegúrate de que el archivo contenga todas las hojas necesarias.")
            else:
                st.success(f"✅ Archivo cargado correctamente. Hojas encontradas: {', '.join(hojas_disponibles)}")
                
                # Cargar datos de las hojas requeridas
                with st.spinner("Cargando datos de las hojas..."):
                    for hoja in HOJAS_REQUERIDAS:
                        df = pd.read_excel(archivo_subido, sheet_name=hoja)
                        st.session_state.datos_hojas[hoja] = df
                        st.info(f"📄 Hoja '{hoja}' cargada: {len(df)} registros")
                
                st.success("✅ Datos cargados correctamente")
                
        except Exception as e:
            st.error(f"❌ Error al cargar el archivo: {str(e)}")
            st.session_state.archivo_cargado = None
            st.session_state.datos_hojas = {}
    
    # Construir tablas resumen si hay datos
    if st.session_state.datos_hojas:
        st.markdown("---")
        st.header("📊 Tablas Resumen por Ciudad")
        
        # Selector de fecha final
        col1, col2 = st.columns([2, 1])
        with col1:
            # Determinar fecha máxima disponible
            fechas_maximas = []
            for hoja, df in st.session_state.datos_hojas.items():
                for col in df.columns:
                    if 'fecha' in col.lower():
                        fechas_validas = pd.to_datetime(df[col], errors='coerce').dropna()
                        if len(fechas_validas) > 0:
                            fechas_maximas.append(fechas_validas.max())
            
            fecha_max_disponible = max(fechas_maximas) if fechas_maximas else datetime.now()
            fecha_max_select = fecha_max_disponible.date()
            
            fecha_hasta = st.date_input(
                "Fecha final para el resumen:",
                value=fecha_max_select,
                min_value=datetime(2025, 9, 16).date(),
                max_value=fecha_max_select,
                help="Selecciona hasta qué fecha mostrar los datos"
            )
        
        with col2:
            st.markdown("---")
            if st.button("🔄 Actualizar tablas", use_container_width=True):
                st.rerun()
        
        # Convertir a datetime
        fecha_hasta_dt = datetime.combine(fecha_hasta, datetime.min.time())
        
        # Construir tablas para cada ciudad
        tabs = st.tabs([CIUDADES_CONFIG[ciudad]['nombre_completo'] for ciudad in CIUDADES_CONFIG.keys()])
        
        for tab, ciudad in zip(tabs, CIUDADES_CONFIG.keys()):
            with tab:
                with st.spinner(f"Construyendo tabla para {CIUDADES_CONFIG[ciudad]['nombre_completo']}..."):
                    # Construir tabla resumen
                    df_resumen = construir_tabla_resumen(
                        ciudad, 
                        CIUDADES_CONFIG[ciudad], 
                        st.session_state.datos_hojas, 
                        fecha_hasta_dt
                    )
                    
                    # Mostrar métricas
                    st.subheader(f"📈 Métricas - {CIUDADES_CONFIG[ciudad]['nombre_completo']}")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    metrics = st.session_state.tablas_resumen[ciudad]
                    
                    with col1:
                        st.metric("Total Ingresos", f"{metrics['total_ingresos']:,}")
                    with col2:
                        st.metric("Facturado Modelo", f"{metrics['total_facturado_modelo']:,}")
                    with col3:
                        st.metric("Facturado Fuera", f"{metrics['total_facturado_fuera']:,}")
                    with col4:
                        st.metric("Facturado Total", f"{metrics['total_facturado']:,}")
                    with col5:
                        st.metric("Novedades", f"{metrics['total_novedades']:,}")
                    
                    # Mostrar tabla
                    st.subheader("📋 Detalle por Fecha")
                    st.dataframe(
                        df_resumen,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "semana": st.column_config.NumberColumn("Semana", format="%d"),
                            "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                            "año": st.column_config.NumberColumn("Año", format="%d"),
                            "mes": st.column_config.TextColumn("Mes"),
                            "ingresos": st.column_config.NumberColumn("Ingresos", format="%d"),
                            "facturado modelo": st.column_config.NumberColumn("Fact. Modelo", format="%d"),
                            "facturado fuera modelo": st.column_config.NumberColumn("Fact. Fuera", format="%d"),
                            "facturado total": st.column_config.NumberColumn("Fact. Total", format="%d"),
                            "Novedades": st.column_config.NumberColumn("Novedades", format="%d")
                        }
                    )
                    
                    # Gráficos
                    if len(df_resumen) > 1:
                        st.subheader("📈 Evolución Temporal")
                        
                        # Gráfico de ingresos vs facturado
                        chart_data = df_resumen[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
                        chart_data.index = pd.to_datetime(df_resumen['Fecha'])
                        st.line_chart(chart_data)
                        
                        # Gráfico de novedades
                        if df_resumen['Novedades'].sum() > 0:
                            st.subheader("⚠️ Novedades por Fecha")
                            novedades_data = df_resumen[df_resumen['Novedades'] > 0][['Fecha', 'Novedades']].copy()
                            novedades_data.index = pd.to_datetime(novedades_data['Fecha'])
                            st.bar_chart(novedades_data['Novedades'])
                    
                    # Botones de descarga
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df_resumen.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"📥 Descargar CSV - {CIUDADES_CONFIG[ciudad]['nombre_completo']}",
                            data=csv,
                            file_name=f"resumen_{ciudad.lower()}_{fecha_hasta.strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            key=f"csv_{ciudad}"
                        )
                    
                    with col2:
                        # Exportar a Excel
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_resumen.to_excel(writer, sheet_name=ciudad, index=False)
                            
                            # Agregar métricas en otra hoja
                            metrics_df = pd.DataFrame([
                                ['Total Ingresos', metrics['total_ingresos']],
                                ['Facturado Modelo', metrics['total_facturado_modelo']],
                                ['Facturado Fuera Modelo', metrics['total_facturado_fuera']],
                                ['Facturado Total', metrics['total_facturado']],
                                ['Novedades', metrics['total_novedades']]
                            ], columns=['Métrica', 'Valor'])
                            metrics_df.to_excel(writer, sheet_name='Métricas', index=False)
                        
                        st.download_button(
                            label=f"📥 Descargar Excel - {CIUDADES_CONFIG[ciudad]['nombre_completo']}",
                            data=output.getvalue(),
                            file_name=f"resumen_{ciudad.lower()}_{fecha_hasta.strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"excel_{ciudad}"
                        )
        
        # Opción para descargar todas las tablas juntas
        st.markdown("---")
        st.subheader("💾 Exportar Todas las Tablas")
        
        if st.button("📥 Exportar todas las ciudades a Excel", use_container_width=True):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for ciudad, data in st.session_state.tablas_resumen.items():
                    nombre_ciudad = CIUDADES_CONFIG[ciudad]['nombre_completo']
                    data['df'].to_excel(writer, sheet_name=nombre_ciudad[:31], index=False)
                    
                    # Agregar métricas
                    metrics_df = pd.DataFrame([
                        ['Ciudad', nombre_ciudad],
                        ['Fecha Inicio', CIUDADES_CONFIG[ciudad]['fecha_inicio'].strftime('%d/%m/%Y')],
                        ['Fecha Fin', fecha_hasta.strftime('%d/%m/%Y')],
                        ['Total Ingresos', data['total_ingresos']],
                        ['Facturado Modelo', data['total_facturado_modelo']],
                        ['Facturado Fuera Modelo', data['total_facturado_fuera']],
                        ['Facturado Total', data['total_facturado']],
                        ['Novedades', data['total_novedades']]
                    ], columns=['Información', 'Valor'])
                    metrics_df.to_excel(writer, sheet_name=f'Métricas_{nombre_ciudad[:20]}', index=False)
            
            st.download_button(
                label="📥 Descargar Excel completo",
                data=output.getvalue(),
                file_name=f"resumen_todas_ciudades_{fecha_hasta.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    # Mensaje cuando no hay archivo cargado
    st.info("👆 Por favor, carga un archivo Excel para comenzar")
    
    # Mostrar estructura esperada
    with st.expander("📋 Ver estructura esperada del archivo"):
        st.markdown("""
        **El archivo debe contener las siguientes hojas:**
        - `EVENTO`
        - `PGP`
        - `PDTE EVENTO`
        - `PDTE PGP`
        
        **Columnas necesarias:**
        
        *Para todas las hojas:*
        - Una columna que identifique la ciudad (puede llamarse 'Ciudad', 'Unidad Operativa', etc.)
        - Una columna de fecha de ingreso (puede llamarse 'Fecha Ingreso', 'fechaing', etc.)
        
        *Para hojas EVENTO y PGP (adicional):*
        - Una columna de fecha de factura (puede llamarse 'Fecha Factura', 'fechafac', etc.)
        
        **Ejemplo de estructura:**
        """)
        
        ejemplo = pd.DataFrame({
            'Ciudad': ['MANIZALES', 'ARMENIA', 'PEREIRA'],
            'Fecha Ingreso': ['2025-09-16', '2025-11-20', '2026-04-15'],
            'Fecha Factura': ['2025-09-17', '2025-11-21', '2026-04-16']
        })
        st.dataframe(ejemplo, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("💡 **Nota:** Las tablas se construyen automáticamente según las fechas de inicio de cada ciudad.")
