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

# Definición de ciudades
CIUDADES_CONFIG = {
    "MANIZALES": {"fecha_inicio": datetime(2025, 9, 16), "nombre": "Manizales"},
    "ARMENIA": {"fecha_inicio": datetime(2025, 11, 20), "nombre": "Armenia"},
    "PEREIRA": {"fecha_inicio": datetime(2026, 4, 15), "nombre": "Pereira"}
}

HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']

# Inicializar session state de forma simple
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.dataframes = {}
    st.session_state.max_date = None

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

def get_date_column(df, keywords):
    for col in df.columns:
        col_lower = col.lower()
        for keyword in keywords:
            if keyword in col_lower:
                return col
    return None

def load_excel(file):
    """Carga el archivo Excel y retorna los dataframes"""
    try:
        excel_file = pd.ExcelFile(file)
        sheets = excel_file.sheet_names
        
        # Verificar hojas requeridas
        missing = [h for h in HOJAS_REQUERIDAS if h not in sheets]
        if missing:
            st.error(f"Hojas faltantes: {', '.join(missing)}")
            return None, None
        
        # Cargar dataframes
        dataframes = {}
        for sheet in HOJAS_REQUERIDAS:
            dataframes[sheet] = pd.read_excel(file, sheet_name=sheet)
        
        # Encontrar fecha máxima
        max_date = None
        for sheet, df in dataframes.items():
            for col in df.columns:
                if 'fecha' in col.lower():
                    try:
                        dates = pd.to_datetime(df[col], errors='coerce')
                        if not dates.dropna().empty:
                            current_max = dates.max()
                            if max_date is None or current_max > max_date:
                                max_date = current_max
                    except:
                        pass
        
        return dataframes, max_date
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None, None

def calculate_ingresos(dfs, start_date, end_date):
    """Calcula ingresos por fecha"""
    ingresos = {}
    
    for sheet_name in ['PDTE EVENTO', 'PDTE PGP', 'EVENTO', 'PGP']:
        if sheet_name not in dfs:
            continue
        
        df = dfs[sheet_name]
        date_col = get_date_column(df, ['ingreso', 'fechaing'])
        
        if date_col:
            dates = pd.to_datetime(df[date_col], errors='coerce')
            mask = (dates >= start_date) & (dates <= end_date)
            
            for date in dates[mask].dt.date:
                ingresos[date] = ingresos.get(date, 0) + 1
    
    return ingresos

def calculate_facturacion(dfs, city, start_date, end_date):
    """Calcula facturación modelo y fuera modelo"""
    modelo = {}
    fuera_modelo = {}
    
    for sheet_name in ['EVENTO', 'PGP']:
        if sheet_name not in dfs:
            continue
        
        df = dfs[sheet_name]
        
        city_col = get_date_column(df, ['ciudad', 'unidad'])
        ingreso_col = get_date_column(df, ['ingreso', 'fechaing'])
        factura_col = get_date_column(df, ['factura', 'fechafac'])
        
        if not all([city_col, ingreso_col, factura_col]):
            continue
        
        # Procesar datos
        for idx, row in df.iterrows():
            city_val = normalize_city(row[city_col])
            if city_val != city:
                continue
            
            ingreso = pd.to_datetime(row[ingreso_col], errors='coerce')
            factura = pd.to_datetime(row[factura_col], errors='coerce')
            
            if pd.isna(ingreso) or pd.isna(factura):
                continue
            
            if factura < start_date or factura > end_date:
                continue
            
            date_key = factura.date()
            
            if ingreso >= start_date and factura >= start_date:
                modelo[date_key] = modelo.get(date_key, 0) + 1
            elif ingreso < start_date and factura < start_date:
                fuera_modelo[date_key] = fuera_modelo.get(date_key, 0) + 1
    
    return modelo, fuera_modelo

def build_summary_table(city, config, dfs, end_date):
    """Construye tabla resumen"""
    start_date = config['fecha_inicio']
    
    # Generar rango de fechas
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Calcular datos
    ingresos_dict = calculate_ingresos(dfs, start_date, end_date)
    modelo_dict, fuera_dict = calculate_facturacion(dfs, city, start_date, end_date)
    
    # Construir tabla
    rows = []
    for date in date_range:
        date_key = date.date()
        ingresos = ingresos_dict.get(date_key, 0)
        modelo = modelo_dict.get(date_key, 0)
        fuera = fuera_dict.get(date_key, 0)
        total = modelo + fuera
        novedades = max(0, ingresos - total)
        
        if ingresos > 0 or total > 0:
            rows.append({
                'semana': date.isocalendar()[1],
                'Fecha': date.strftime('%Y-%m-%d'),
                'año': date.year,
                'mes': calendar.month_name[date.month],
                'ingresos': ingresos,
                'facturado modelo': modelo,
                'facturado fuera modelo': fuera,
                'facturado total': total,
                'Novedades': novedades
            })
    
    return pd.DataFrame(rows)

# Interfaz de usuario
st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# Sidebar con información
with st.sidebar:
    st.header("ℹ️ Información")
    st.markdown("**Fechas de inicio:**")
    for city, config in CIUDADES_CONFIG.items():
        st.markdown(f"- **{config['nombre']}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.markdown("**Hojas requeridas:**")
    for sheet in HOJAS_REQUERIDAS:
        st.markdown(f"- {sheet}")

# Carga de archivo
st.header("📁 Cargar Archivo")

uploaded_file = st.file_uploader(
    "Selecciona archivo Excel",
    type=['xlsx', 'xls'],
    key="file_uploader"
)

# Botón para procesar
if uploaded_file and st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
    with st.spinner("Procesando archivo..."):
        dataframes, max_date = load_excel(uploaded_file)
        
        if dataframes and max_date:
            st.session_state.dataframes = dataframes
            st.session_state.max_date = max_date
            st.session_state.data_loaded = True
            st.success("✅ Archivo procesado correctamente!")
            
            # Mostrar información de carga
            for sheet in HOJAS_REQUERIDAS:
                st.info(f"📄 {sheet}: {len(dataframes[sheet]):,} registros")

# Mostrar resultados si hay datos cargados
if st.session_state.data_loaded and st.session_state.dataframes:
    st.markdown("---")
    st.header("📊 Resultados")
    
    # Selector de fecha
    col1, col2 = st.columns([2, 1])
    with col1:
        end_date = st.date_input(
            "Fecha final:",
            value=st.session_state.max_date.date(),
            min_value=datetime(2025, 9, 16).date(),
            max_value=st.session_state.max_date.date(),
            key="end_date"
        )
    
    # Convertir a datetime
    end_date_dt = datetime.combine(end_date, datetime.min.time())
    
    # Procesar cada ciudad
    for city, config in CIUDADES_CONFIG.items():
        st.markdown(f"### 📍 {config['nombre']}")
        
        with st.spinner(f"Procesando {config['nombre']}..."):
            try:
                # Construir tabla
                df_summary = build_summary_table(
                    city, 
                    config, 
                    st.session_state.dataframes, 
                    end_date_dt
                )
                
                if len(df_summary) > 0:
                    # Métricas
                    cols = st.columns(5)
                    cols[0].metric("Ingresos", f"{df_summary['ingresos'].sum():,}")
                    cols[1].metric("Fact. Modelo", f"{df_summary['facturado modelo'].sum():,}")
                    cols[2].metric("Fact. Fuera", f"{df_summary['facturado fuera modelo'].sum():,}")
                    cols[3].metric("Fact. Total", f"{df_summary['facturado total'].sum():,}")
                    cols[4].metric("Novedades", f"{df_summary['Novedades'].sum():,}")
                    
                    # Tabla
                    st.dataframe(
                        df_summary,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Gráfico
                    if len(df_summary) > 1:
                        chart_data = df_summary[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
                        chart_data.index = pd.to_datetime(df_summary['Fecha'])
                        st.line_chart(chart_data)
                    
                    # Descargas
                    col1, col2 = st.columns(2)
                    
                    # CSV
                    csv_data = df_summary.to_csv(index=False).encode('utf-8')
                    col1.download_button(
                        label=f"📥 Descargar CSV",
                        data=csv_data,
                        file_name=f"{city.lower()}_resumen.csv",
                        mime="text/csv",
                        key=f"csv_{city}"
                    )
                    
                    # Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_summary.to_excel(writer, sheet_name=config['nombre'], index=False)
                    
                    col2.download_button(
                        label=f"📥 Descargar Excel",
                        data=output.getvalue(),
                        file_name=f"{city.lower()}_resumen.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{city}"
                    )
                    
                    st.markdown("---")
                    
                else:
                    st.info(f"No hay datos para {config['nombre']} en el período seleccionado")
                    st.markdown("---")
            
            except Exception as e:
                st.error(f"Error procesando {config['nombre']}: {str(e)}")
                st.markdown("---")
    
    # Botón para reiniciar
    if st.button("🔄 Cargar otro archivo", use_container_width=True):
        for key in ['data_loaded', 'dataframes', 'max_date']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    if not st.session_state.data_loaded:
        st.info("👆 Carga un archivo Excel y presiona 'Procesar Archivo' para comenzar")
        
        with st.expander("📋 Ver estructura requerida"):
            st.markdown("""
            **El archivo debe contener estas hojas:**
            - EVENTO
            - PGP  
            - PDTE EVENTO
            - PDTE PGP
            
            **Columnas necesarias:**
            - Ciudad / Unidad Operativa
            - Fecha Ingreso (en cualquier hoja)
            - Fecha Factura (en hojas EVENTO y PGP)
            """)

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
