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

# Definición de ciudades
CIUDADES_CONFIG = {
    "MANIZALES": {"fecha_inicio": datetime(2025, 9, 16), "nombre": "Manizales"},
    "ARMENIA": {"fecha_inicio": datetime(2025, 11, 20), "nombre": "Armenia"},
    "PEREIRA": {"fecha_inicio": datetime(2026, 4, 15), "nombre": "Pereira"}
}

HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']

# Inicializar session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'max_date' not in st.session_state:
    st.session_state.max_date = None
if 'columnas_identificadas' not in st.session_state:
    st.session_state.columnas_identificadas = {}

def normalize_city(city):
    if pd.isna(city):
        return None
    city_str = str(city).upper().strip()
    if 'MANIZALES' in city_str:
        return 'MANIZALES'
    elif 'ARMENIA' in city_str:
        return 'ARMENIA'
    elif 'PEREIRA' in city_str:
        return 'PEREIRA'
    return None

def identificar_columnas(df, hoja_nombre):
    """Identifica las columnas relevantes en cada hoja"""
    columnas = {
        'ciudad': None,
        'fecha_ingreso': None,
        'fecha_factura': None
    }
    
    # Lista de posibles nombres para cada tipo de columna
    ciudad_keywords = ['ciudad', 'unidad operativa', 'unidad', 'ciiu', 'sede', 'municipio']
    ingreso_keywords = ['fecha ingreso', 'fecha_ingreso', 'fechaing', 'fecha de ingreso', 'ingreso', 'f_ingreso']
    factura_keywords = ['fecha factura', 'fecha_factura', 'fechafac', 'fecha de factura', 'factura', 'f_factura']
    
    # Buscar columnas
    for col in df.columns:
        col_lower = col.lower().strip()
        
        # Buscar ciudad
        if columnas['ciudad'] is None:
            for keyword in ciudad_keywords:
                if keyword in col_lower:
                    columnas['ciudad'] = col
                    break
        
        # Buscar fecha ingreso
        if columnas['fecha_ingreso'] is None:
            for keyword in ingreso_keywords:
                if keyword in col_lower:
                    columnas['fecha_ingreso'] = col
                    break
        
        # Buscar fecha factura (solo para EVENTO y PGP)
        if hoja_nombre in ['EVENTO', 'PGP'] and columnas['fecha_factura'] is None:
            for keyword in factura_keywords:
                if keyword in col_lower:
                    columnas['fecha_factura'] = col
                    break
    
    return columnas

def convertir_fechas(df, columna_fecha):
    """Convierte una columna a fechas de manera robusta"""
    if columna_fecha is None:
        return pd.Series([None] * len(df))
    
    # Intentar diferentes formatos de fecha
    formatos = [
        '%Y-%m-%d',  # 2025-09-16
        '%d/%m/%Y',  # 16/09/2025
        '%d-%m-%Y',  # 16-09-2025
        '%Y/%m/%d',  # 2025/09/16
        '%d.%m.%Y',  # 16.09.2025
    ]
    
    fechas = pd.Series([None] * len(df))
    
    for idx, valor in enumerate(df[columna_fecha]):
        if pd.isna(valor):
            continue
        
        valor_str = str(valor).strip()
        
        # Intentar con formatos específicos
        fecha_convertida = None
        for formato in formatos:
            try:
                fecha_convertida = datetime.strptime(valor_str, formato)
                break
            except:
                continue
        
        # Si no funcionó, intentar con pandas
        if fecha_convertida is None:
            try:
                fecha_convertida = pd.to_datetime(valor_str, errors='coerce')
                if pd.isna(fecha_convertida):
                    fecha_convertida = None
            except:
                pass
        
        fechas[idx] = fecha_convertida
    
    return fechas

def process_ingresos(dfs, start_date, end_date):
    """Procesa ingresos de todas las hojas"""
    ingresos = {}
    
    for sheet in ['PDTE EVENTO', 'PDTE PGP', 'EVENTO', 'PGP']:
        if sheet not in dfs:
            continue
        
        df = dfs[sheet]
        
        # Obtener columna de fecha de ingreso
        if sheet not in st.session_state.columnas_identificadas:
            continue
        
        col_fecha_ingreso = st.session_state.columnas_identificadas[sheet]['fecha_ingreso']
        
        if col_fecha_ingreso is None:
            st.warning(f"Hoja {sheet}: No se encontró columna de fecha de ingreso")
            continue
        
        # Convertir fechas
        fechas = convertir_fechas(df, col_fecha_ingreso)
        
        # Contar ingresos por fecha
        for fecha in fechas:
            if fecha is not None and start_date <= fecha <= end_date:
                fecha_key = fecha.date()
                ingresos[fecha_key] = ingresos.get(fecha_key, 0) + 1
    
    return ingresos

def process_facturacion(dfs, city, start_date, end_date):
    """Procesa facturación de EVENTO y PGP"""
    modelo = {}
    fuera = {}
    
    for sheet in ['EVENTO', 'PGP']:
        if sheet not in dfs:
            continue
        
        df = dfs[sheet]
        
        if sheet not in st.session_state.columnas_identificadas:
            continue
        
        cols = st.session_state.columnas_identificadas[sheet]
        col_ciudad = cols['ciudad']
        col_ingreso = cols['fecha_ingreso']
        col_factura = cols['fecha_factura']
        
        if any(x is None for x in [col_ciudad, col_ingreso, col_factura]):
            st.warning(f"Hoja {sheet}: Faltan columnas necesarias (Ciudad: {col_ciudad}, Ingreso: {col_ingreso}, Factura: {col_factura})")
            continue
        
        # Convertir fechas
        fechas_ingreso = convertir_fechas(df, col_ingreso)
        fechas_factura = convertir_fechas(df, col_factura)
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            # Normalizar ciudad
            ciudad_val = normalize_city(row[col_ciudad])
            if ciudad_val != city:
                continue
            
            fecha_ingreso = fechas_ingreso[idx]
            fecha_factura = fechas_factura[idx]
            
            if fecha_ingreso is None or fecha_factura is None:
                continue
            
            if fecha_factura < start_date or fecha_factura > end_date:
                continue
            
            fecha_key = fecha_factura.date()
            
            # Clasificar
            if fecha_ingreso >= start_date and fecha_factura >= start_date:
                modelo[fecha_key] = modelo.get(fecha_key, 0) + 1
            elif fecha_ingreso < start_date and fecha_factura < start_date:
                fuera[fecha_key] = fuera.get(fecha_key, 0) + 1
    
    return modelo, fuera

def build_table(city, config, dfs, end_date):
    """Construye tabla resumen"""
    start_date = config['fecha_inicio']
    
    # Generar rango de fechas
    days_diff = (end_date - start_date).days
    if days_diff > 365:
        days_diff = 365
        end_date = start_date + timedelta(days=365)
    
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Procesar datos
    ingresos = process_ingresos(dfs, start_date, end_date)
    modelo, fuera = process_facturacion(dfs, city, start_date, end_date)
    
    # Construir DataFrame
    rows = []
    for date in date_range:
        date_key = date.date()
        ing = ingresos.get(date_key, 0)
        mod = modelo.get(date_key, 0)
        out = fuera.get(date_key, 0)
        total = mod + out
        nov = max(0, ing - total)
        
        # Mostrar días con actividad o con valores
        if ing > 0 or total > 0:
            rows.append({
                'semana': date.isocalendar()[1],
                'Fecha': date.strftime('%Y-%m-%d'),
                'año': date.year,
                'mes': calendar.month_name[date.month],
                'ingresos': ing,
                'facturado modelo': mod,
                'facturado fuera modelo': out,
                'facturado total': total,
                'Novedades': nov
            })
    
    return pd.DataFrame(rows)

def obtener_fecha_maxima(dfs):
    """Obtiene la fecha máxima de todas las hojas"""
    fechas_maximas = []
    
    for sheet, df in dfs.items():
        if sheet not in st.session_state.columnas_identificadas:
            continue
        
        cols = st.session_state.columnas_identificadas[sheet]
        
        # Revisar fecha de ingreso
        if cols['fecha_ingreso']:
            fechas = convertir_fechas(df, cols['fecha_ingreso'])
            fechas_validas = fechas.dropna()
            if len(fechas_validas) > 0:
                fechas_maximas.append(fechas_validas.max())
        
        # Revisar fecha de factura (si existe)
        if cols['fecha_factura']:
            fechas = convertir_fechas(df, cols['fecha_factura'])
            fechas_validas = fechas.dropna()
            if len(fechas_validas) > 0:
                fechas_maximas.append(fechas_validas.max())
    
    if fechas_maximas:
        return max(fechas_maximas)
    return datetime.now()

# Título
st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("ℹ️ Información")
    st.markdown("**Fechas de inicio:**")
    for city, config in CIUDADES_CONFIG.items():
        st.markdown(f"- **{config['nombre']}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Reglas:**")
    st.markdown("""
    - **Modelo:** Ingreso ≥ inicio AND Factura ≥ inicio
    - **Fuera modelo:** Ingreso < inicio AND Factura < inicio
    - **Novedades:** Ingresos - Facturado Total
    """)

# Carga de archivo
st.header("📁 Cargar Archivo")

uploaded_file = st.file_uploader(
    "Selecciona archivo Excel",
    type=['xlsx', 'xls']
)

if uploaded_file:
    if st.button("📊 Procesar Archivo", type="primary"):
        with st.spinner("Procesando archivo..."):
            try:
                # Leer todas las hojas
                excel_file = pd.ExcelFile(uploaded_file)
                sheets = excel_file.sheet_names
                
                # Verificar hojas
                missing = [h for h in HOJAS_REQUERIDAS if h not in sheets]
                if missing:
                    st.error(f"Faltan hojas requeridas: {', '.join(missing)}")
                else:
                    # Cargar datos
                    data = {}
                    for sheet in HOJAS_REQUERIDAS:
                        data[sheet] = pd.read_excel(uploaded_file, sheet_name=sheet)
                        st.info(f"📄 {sheet}: {len(data[sheet]):,} registros")
                    
                    # Identificar columnas en cada hoja
                    st.info("🔍 Identificando columnas...")
                    for sheet, df in data.items():
                        columnas = identificar_columnas(df, sheet)
                        st.session_state.columnas_identificadas[sheet] = columnas
                        
                        # Mostrar columnas identificadas
                        with st.expander(f"Columnas identificadas - {sheet}"):
                            st.write(f"**Ciudad:** {columnas['ciudad']}")
                            st.write(f"**Fecha Ingreso:** {columnas['fecha_ingreso']}")
                            if columnas['fecha_factura']:
                                st.write(f"**Fecha Factura:** {columnas['fecha_factura']}")
                    
                    # Encontrar fecha máxima
                    st.session_state.data = data
                    st.session_state.max_date = obtener_fecha_maxima(data)
                    
                    st.success(f"✅ Archivo procesado exitosamente!")
                    st.info(f"📅 Fecha máxima encontrada: {st.session_state.max_date.strftime('%d/%m/%Y')}")
                    
            except Exception as e:
                st.error(f"Error al procesar: {str(e)}")
                st.exception(e)

# Mostrar resultados
if st.session_state.data is not None and st.session_state.max_date is not None:
    st.markdown("---")
    st.header("📊 Resultados")
    
    # Verificar que la fecha máxima sea válida
    if st.session_state.max_date.year == 1970:
        st.error("⚠️ No se pudieron leer las fechas correctamente. Verifica que las columnas de fecha tengan formatos válidos.")
        
        # Mostrar ejemplo de los primeros registros
        st.subheader("📋 Vista previa de los datos - Primeros 5 registros")
        for sheet, df in st.session_state.data.items():
            with st.expander(f"Hoja: {sheet}"):
                st.write(df.head())
        
        st.info("💡 Las columnas de fecha deben contener fechas en formatos como: YYYY-MM-DD, DD/MM/YYYY, o DD-MM-YYYY")
    else:
        # Selector de ciudad
        ciudad_seleccionada = st.selectbox(
            "Selecciona ciudad:",
            list(CIUDADES_CONFIG.keys()),
            format_func=lambda x: CIUDADES_CONFIG[x]['nombre']
        )
        
        config = CIUDADES_CONFIG[ciudad_seleccionada]
        
        # Determinar fecha final (máximo 365 días desde inicio)
        max_end_date = min(st.session_state.max_date, config['fecha_inicio'] + timedelta(days=365))
        
        st.info(f"📅 Período a analizar: {config['fecha_inicio'].strftime('%d/%m/%Y')} al {max_end_date.strftime('%d/%m/%Y')}")
        
        with st.spinner(f"Procesando {config['nombre']}..."):
            df_table = build_table(
                ciudad_seleccionada,
                config,
                st.session_state.data,
                max_end_date
            )
        
        if len(df_table) > 0:
            # Métricas
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Ingresos", f"{df_table['ingresos'].sum():,}")
            col2.metric("Facturado Modelo", f"{df_table['facturado modelo'].sum():,}")
            col3.metric("Facturado Fuera", f"{df_table['facturado fuera modelo'].sum():,}")
            col4.metric("Facturado Total", f"{df_table['facturado total'].sum():,}")
            col5.metric("Novedades", f"{df_table['Novedades'].sum():,}")
            
            # Mostrar rango de fechas
            st.caption(f"📅 Período con datos: {df_table['Fecha'].min()} al {df_table['Fecha'].max()}")
            
            # Tabla
            st.dataframe(df_table, use_container_width=True)
            
            # Gráfico
            if len(df_table) > 1:
                chart_data = df_table[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
                chart_data.index = pd.to_datetime(df_table['Fecha'])
                st.line_chart(chart_data)
            
            # Descargas
            st.markdown("---")
            st.subheader("💾 Exportar datos")
            
            col1, col2 = st.columns(2)
            
            # CSV
            csv_data = df_table.to_csv(index=False).encode('utf-8')
            col1.download_button(
                "📥 Descargar CSV",
                csv_data,
                f"{ciudad_seleccionada.lower()}_resumen.csv",
                "text/csv",
                use_container_width=True
            )
            
            # Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_table.to_excel(writer, sheet_name=config['nombre'], index=False)
                
                # Agregar resumen de métricas
                metrics_df = pd.DataFrame([
                    ['Ciudad', config['nombre']],
                    ['Fecha Inicio', config['fecha_inicio'].strftime('%d/%m/%Y')],
                    ['Fecha Fin', max_end_date.strftime('%d/%m/%Y')],
                    ['Total Ingresos', df_table['ingresos'].sum()],
                    ['Facturado Modelo', df_table['facturado modelo'].sum()],
                    ['Facturado Fuera Modelo', df_table['facturado fuera modelo'].sum()],
                    ['Facturado Total', df_table['facturado total'].sum()],
                    ['Novedades', df_table['Novedades'].sum()]
                ], columns=['Métrica', 'Valor'])
                metrics_df.to_excel(writer, sheet_name='Métricas', index=False)
            
            col2.download_button(
                "📥 Descargar Excel",
                output.getvalue(),
                f"{ciudad_seleccionada.lower()}_resumen.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            # Mostrar resumen por mes
            with st.expander("📊 Ver resumen por mes"):
                monthly = df_table.groupby('mes').agg({
                    'ingresos': 'sum',
                    'facturado modelo': 'sum',
                    'facturado fuera modelo': 'sum',
                    'facturado total': 'sum',
                    'Novedades': 'sum'
                }).reset_index()
                
                # Reordenar meses
                order = ['January', 'February', 'March', 'April', 'May', 'June', 
                        'July', 'August', 'September', 'October', 'November', 'December']
                monthly['mes'] = pd.Categorical(monthly['mes'], categories=order, ordered=True)
                monthly = monthly.sort_values('mes')
                
                st.dataframe(monthly, use_container_width=True)
        
        else:
            st.warning("No hay datos para mostrar en el período disponible")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Cargar otro archivo", use_container_width=True):
        st.session_state.data = None
        st.session_state.max_date = None
        st.session_state.columnas_identificadas = {}
        st.rerun()

else:
    if uploaded_file is None:
        st.info("👆 1. Carga un archivo Excel\n\n👆 2. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para analizar los datos")

# Footer
st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad | v2.0")
