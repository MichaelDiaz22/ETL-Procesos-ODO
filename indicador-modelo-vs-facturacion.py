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

# Inicializar session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'max_date' not in st.session_state:
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

def find_column(df, keywords):
    """Busca una columna por palabras clave"""
    for col in df.columns:
        col_lower = col.lower()
        for keyword in keywords:
            if keyword in col_lower:
                return col
    return None

def process_ingresos(dfs, start_date, end_date):
    """Procesa ingresos de todas las hojas"""
    ingresos = {}
    
    for sheet in ['PDTE EVENTO', 'PDTE PGP', 'EVENTO', 'PGP']:
        if sheet not in dfs:
            continue
        
        df = dfs[sheet]
        date_col = find_column(df, ['ingreso', 'fechaing'])
        
        if date_col:
            dates = pd.to_datetime(df[date_col], errors='coerce')
            mask = (dates >= start_date) & (dates <= end_date)
            
            for d in dates[mask].dt.date:
                ingresos[d] = ingresos.get(d, 0) + 1
    
    return ingresos

def process_facturacion(dfs, city, start_date, end_date):
    """Procesa facturación de EVENTO y PGP"""
    modelo = {}
    fuera = {}
    
    for sheet in ['EVENTO', 'PGP']:
        if sheet not in dfs:
            continue
        
        df = dfs[sheet]
        
        city_col = find_column(df, ['ciudad', 'unidad'])
        ingreso_col = find_column(df, ['ingreso', 'fechaing'])
        factura_col = find_column(df, ['factura', 'fechafac'])
        
        if not all([city_col, ingreso_col, factura_col]):
            continue
        
        for _, row in df.iterrows():
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
                fuera[date_key] = fuera.get(date_key, 0) + 1
    
    return modelo, fuera

def build_table(city, config, dfs, end_date):
    """Construye tabla resumen"""
    start_date = config['fecha_inicio']
    
    # Generar rango de fechas
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

# Título
st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("ℹ️ Información")
    st.markdown("**Fechas de inicio:**")
    for city, config in CIUDADES_CONFIG.items():
        st.markdown(f"- **{config['nombre']}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")

# Carga de archivo
st.header("📁 Cargar Archivo")

uploaded_file = st.file_uploader(
    "Selecciona archivo Excel",
    type=['xlsx', 'xls']
)

if uploaded_file:
    if st.button("📊 Procesar", type="primary"):
        with st.spinner("Procesando archivo..."):
            try:
                # Leer todas las hojas
                excel_file = pd.ExcelFile(uploaded_file)
                sheets = excel_file.sheet_names
                
                # Verificar hojas
                missing = [h for h in HOJAS_REQUERIDAS if h not in sheets]
                if missing:
                    st.error(f"Faltan hojas: {', '.join(missing)}")
                else:
                    # Cargar datos
                    data = {}
                    for sheet in HOJAS_REQUERIDAS:
                        data[sheet] = pd.read_excel(uploaded_file, sheet_name=sheet)
                        st.info(f"📄 {sheet}: {len(data[sheet]):,} registros")
                    
                    # Encontrar fecha máxima
                    max_date = None
                    for sheet, df in data.items():
                        for col in df.columns:
                            if 'fecha' in col.lower():
                                dates = pd.to_datetime(df[col], errors='coerce')
                                if not dates.dropna().empty:
                                    current_max = dates.max()
                                    if max_date is None or current_max > max_date:
                                        max_date = current_max
                    
                    st.session_state.data = data
                    st.session_state.max_date = max_date
                    st.success("✅ Archivo procesado exitosamente!")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Mostrar resultados
if st.session_state.data is not None and st.session_state.max_date is not None:
    st.markdown("---")
    st.header("📊 Resultados")
    
    # Selector de fecha
    end_date = st.date_input(
        "Fecha final:",
        value=st.session_state.max_date.date(),
        min_value=datetime(2025, 9, 16).date(),
        max_value=st.session_state.max_date.date()
    )
    
    end_date_dt = datetime.combine(end_date, datetime.min.time())
    
    # Selector de ciudad
    ciudad_seleccionada = st.selectbox(
        "Selecciona ciudad:",
        list(CIUDADES_CONFIG.keys()),
        format_func=lambda x: CIUDADES_CONFIG[x]['nombre']
    )
    
    # Procesar ciudad seleccionada
    config = CIUDADES_CONFIG[ciudad_seleccionada]
    
    with st.spinner(f"Procesando {config['nombre']}..."):
        df_table = build_table(
            ciudad_seleccionada,
            config,
            st.session_state.data,
            end_date_dt
        )
    
    if len(df_table) > 0:
        # Métricas
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Ingresos", f"{df_table['ingresos'].sum():,}")
        col2.metric("Facturado Modelo", f"{df_table['facturado modelo'].sum():,}")
        col3.metric("Facturado Fuera", f"{df_table['facturado fuera modelo'].sum():,}")
        col4.metric("Facturado Total", f"{df_table['facturado total'].sum():,}")
        col5.metric("Novedades", f"{df_table['Novedades'].sum():,}")
        
        # Tabla
        st.dataframe(df_table, use_container_width=True)
        
        # Gráfico
        if len(df_table) > 1:
            chart_data = df_table[['ingresos', 'facturado modelo', 'facturado fuera modelo']].copy()
            chart_data.index = pd.to_datetime(df_table['Fecha'])
            st.line_chart(chart_data)
        
        # Descargas
        col1, col2 = st.columns(2)
        
        csv_data = df_table.to_csv(index=False).encode('utf-8')
        col1.download_button(
            "📥 Descargar CSV",
            csv_data,
            f"{ciudad_seleccionada.lower()}_resumen.csv",
            "text/csv"
        )
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_table.to_excel(writer, sheet_name=config['nombre'], index=False)
        
        col2.download_button(
            "📥 Descargar Excel",
            output.getvalue(),
            f"{ciudad_seleccionada.lower()}_resumen.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Estadísticas adicionales
        with st.expander("📊 Estadísticas adicionales"):
            st.write("**Resumen por mes:**")
            monthly = df_table.groupby('mes').agg({
                'ingresos': 'sum',
                'facturado modelo': 'sum',
                'facturado fuera modelo': 'sum',
                'facturado total': 'sum',
                'Novedades': 'sum'
            }).reset_index()
            st.dataframe(monthly, use_container_width=True)
    
    else:
        st.warning("No hay datos para mostrar en el período seleccionado")
    
    # Botón para limpiar
    if st.button("🔄 Cargar otro archivo"):
        st.session_state.data = None
        st.session_state.max_date = None
        st.rerun()

else:
    if uploaded_file is None:
        st.info("👆 Carga un archivo Excel y presiona 'Procesar'")
    else:
        st.info("Presiona 'Procesar' para analizar el archivo")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
