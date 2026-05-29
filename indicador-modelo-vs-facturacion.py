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
if 'columnas_identificadas' not in st.session_state:
    st.session_state.columnas_identificadas = {}

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
            
            # Mostrar primeras columnas para depuración
            with st.expander(f"Ver columnas de {hoja}"):
                st.write(list(dfs[hoja].columns))
        
        # Identificar columnas en cada hoja
        columnas_info = {}
        for hoja, df in dfs.items():
            columnas = {
                'fecha_ingreso': None,
                'unidad_operativa': None,
                'centro_atencion': None
            }
            
            for col in df.columns:
                col_lower = col.lower().strip()
                
                # Buscar fecha ingreso
                if any(palabra in col_lower for palabra in ['fecha ingreso', 'fecha_ingreso', 'fechaing', 'ingreso', 'fecha de ingreso']):
                    if columnas['fecha_ingreso'] is None:
                        columnas['fecha_ingreso'] = col
                
                # Buscar unidad operativa
                if any(palabra in col_lower for palabra in ['unidad operativa', 'unidad', 'operativa', 'ciudad', 'ciiu']):
                    if columnas['unidad_operativa'] is None:
                        columnas['unidad_operativa'] = col
                
                # Buscar centro de atención
                if any(palabra in col_lower for palabra in ['centro de atencion', 'centro atencion', 'centro', 'atencion']):
                    if columnas['centro_atencion'] is None:
                        columnas['centro_atencion'] = col
            
            columnas_info[hoja] = columnas
            
            # Mostrar columnas identificadas
            with st.expander(f"Columnas identificadas en {hoja}"):
                st.write(f"**Fecha Ingreso:** {columnas['fecha_ingreso']}")
                st.write(f"**Unidad Operativa:** {columnas['unidad_operativa']}")
                st.write(f"**Centro Atención:** {columnas['centro_atencion']}")
                
                # Mostrar ejemplos de valores
                if columnas['fecha_ingreso']:
                    st.write(f"**Ejemplos fechas:** {df[columnas['fecha_ingreso']].head(3).tolist()}")
                if columnas['unidad_operativa']:
                    st.write(f"**Ejemplos unidades:** {df[columnas['unidad_operativa']].head(3).tolist()}")
                if columnas['centro_atencion']:
                    st.write(f"**Ejemplos centros:** {df[columnas['centro_atencion']].head(3).tolist()}")
        
        st.session_state.columnas_identificadas = columnas_info
        
        # Encontrar fecha máxima
        fecha_max = datetime.now()
        for hoja, df in dfs.items():
            col_fecha = columnas_info[hoja]['fecha_ingreso']
            if col_fecha:
                try:
                    # Intentar diferentes formatos de fecha
                    fechas = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True)
                    if not fechas.dropna().empty:
                        max_fecha = fechas.max()
                        if fecha_max is None or max_fecha > fecha_max:
                            fecha_max = max_fecha
                except:
                    pass
        
        return True, dfs, fecha_max
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return False, None, None

def convertir_fecha_valor(valor):
    """Convierte un valor a fecha de manera robusta"""
    if pd.isna(valor):
        return None
    try:
        # Si es string, intentar diferentes formatos
        if isinstance(valor, str):
            # Intentar formato DD/MM/YYYY
            try:
                return datetime.strptime(valor.strip(), '%d/%m/%Y')
            except:
                pass
            # Intentar formato DD-MM-YYYY
            try:
                return datetime.strptime(valor.strip(), '%d-%m-%Y')
            except:
                pass
            # Intentar formato YYYY-MM-DD
            try:
                return datetime.strptime(valor.strip(), '%Y-%m-%d')
            except:
                pass
        
        # Usar pandas como respaldo
        resultado = pd.to_datetime(valor, errors='coerce', dayfirst=True)
        if pd.notna(resultado):
            return resultado
        return None
    except:
        return None

def procesar_ingresos_ciudad(dfs, columnas_info, ciudad, fecha):
    """Procesa ingresos para una ciudad específica"""
    total_ingresos = 0
    fecha_key = fecha.date() if hasattr(fecha, 'date') else fecha
    
    st.write(f"Debug - Procesando {ciudad} para fecha {fecha_key}")
    
    # Para hojas EVENTO y PGP: filtrar por "unidad operativa" = ciudad
    for hoja in ['EVENTO', 'PGP']:
        if hoja in dfs and hoja in columnas_info:
            df = dfs[hoja]
            cols = columnas_info[hoja]
            
            col_fecha = cols['fecha_ingreso']
            col_unidad = cols['unidad_operativa']
            
            if col_fecha and col_unidad:
                # Convertir fechas
                conteo = 0
                for idx, row in df.iterrows():
                    # Convertir fecha
                    fecha_valor = convertir_fecha_valor(row[col_fecha])
                    
                    if fecha_valor and fecha_valor.date() == fecha_key:
                        # Verificar unidad operativa
                        unidad_valor = str(row[col_unidad]).upper().strip() if pd.notna(row[col_unidad]) else ""
                        if ciudad.upper() in unidad_valor:
                            conteo += 1
                
                if conteo > 0:
                    st.write(f"  {hoja}: {conteo} registros")
                total_ingresos += conteo
    
    # Para hojas PDTE EVENTO y PDTE PGP: filtrar por "CENTRO DE ATENCIÓN" = "SAN MARCEL"
    for hoja in ['PDTE EVENTO', 'PDTE PGP']:
        if hoja in dfs and hoja in columnas_info:
            df = dfs[hoja]
            cols = columnas_info[hoja]
            
            col_fecha = cols['fecha_ingreso']
            col_centro = cols['centro_atencion']
            
            if col_fecha and col_centro:
                # Convertir fechas
                conteo = 0
                for idx, row in df.iterrows():
                    # Convertir fecha
                    fecha_valor = convertir_fecha_valor(row[col_fecha])
                    
                    if fecha_valor and fecha_valor.date() == fecha_key:
                        # Verificar centro de atención
                        centro_valor = str(row[col_centro]).upper().strip() if pd.notna(row[col_centro]) else ""
                        if 'SAN MARCEL' in centro_valor:
                            conteo += 1
                
                if conteo > 0:
                    st.write(f"  {hoja}: {conteo} registros")
                total_ingresos += conteo
    
    return total_ingresos

def construir_tabla_fechas_con_ingresos(ciudad, fecha_inicio, fecha_fin, dfs, columnas_info):
    """Construye la tabla con las fechas y calcula los ingresos"""
    
    # Generar todas las fechas del período
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Construir DataFrame
    datos = []
    total_con_ingresos = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, fecha in enumerate(fechas):
        status_text.text(f"Procesando fechas: {idx+1}/{len(fechas)}")
        
        # Calcular ingresos para esta fecha
        ingresos = procesar_ingresos_ciudad(dfs, columnas_info, ciudad, fecha)
        
        if ingresos > 0:
            total_con_ingresos += 1
        
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
        
        progress_bar.progress((idx + 1) / len(fechas))
    
    progress_bar.empty()
    status_text.empty()
    
    df = pd.DataFrame(datos)
    
    # Filtrar solo días con ingresos > 0 para mostrar
    df_filtrado = df[df['ingresos'] > 0]
    
    st.write(f"**Resumen {ciudad}:** {total_con_ingresos} días con ingresos de {len(fechas)} días totales")
    
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
    **Manizales, Armenia, Pereira:**
    - Hojas EVENTO/PGP: Filtrar por 'unidad operativa' = ciudad
    - Hojas PDTE EVENTO/PDTE PGP: Filtrar por 'CENTRO DE ATENCIÓN' = 'SAN MARCEL'
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
                st.info(f"📅 Última fecha disponible en los datos: {fecha_max.strftime('%d/%m/%Y')}")

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
    
    # Debug: Mostrar columnas identificadas
    with st.expander("🔍 Ver columnas identificadas (Debug)"):
        for hoja, cols in st.session_state.columnas_identificadas.items():
            st.write(f"**{hoja}:**")
            st.write(f"  - Fecha Ingreso: {cols['fecha_ingreso']}")
            st.write(f"  - Unidad Operativa: {cols['unidad_operativa']}")
            st.write(f"  - Centro Atención: {cols['centro_atencion']}")
    
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
            
            with st.spinner(f"Procesando {ciudad} - Calculando ingresos..."):
                # Construir tabla con ingresos
                df_completa, df_filtrado = construir_tabla_fechas_con_ingresos(
                    ciudad,
                    fecha_inicio,
                    fecha_fin,
                    st.session_state.dfs,
                    st.session_state.columnas_identificadas
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
                        
                        # Información del procesamiento
                        info = pd.DataFrame([
                            ['Ciudad', ciudad],
                            ['Fecha Inicio', fecha_inicio.strftime('%d/%m/%Y')],
                            ['Fecha Fin', fecha_fin.strftime('%d/%m/%Y')],
                            ['Total Días', len(df_completa)],
                            ['Días con Ingresos', len(df_filtrado)],
                            ['Total Ingresos', total_ingresos]
                        ], columns=['Información', 'Valor'])
                        info.to_excel(writer, sheet_name='Información', index=False)
                    
                    col2.download_button(
                        "📥 Descargar Excel",
                        output.getvalue(),
                        f"{ciudad.lower()}_ingresos.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{ciudad}"
                    )
                    
                else:
                    st.warning(f"No hay ingresos para {ciudad} en el período seleccionado")
                    st.caption(f"Período analizado: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Reiniciar - Cargar otro archivo", use_container_width=True):
        for key in ['datos_cargados', 'dfs', 'fecha_maxima', 'fecha_hasta', 'columnas_identificadas']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 1. Carga un archivo Excel\n\n👆 2. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para cargar los datos")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad - Versión con Debug")
