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
    
    # Generar rango de fechas (máximo 365 días para evitar sobrecarga)
    max_days = 365
    date_range = pd.date_range(start=start_date, end=min(end_date, start_date + timedelta(days=max_days)), freq='D')
    
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
        
        # Solo mostrar días con actividad
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
                st.error(f"Error al procesar: {str(e)}")

# Mostrar resultados
if st.session_state.data is not None and st.session_state.max_date is not None:
    st.markdown("---")
    st.header("📊 Resultados")
    
    # Información de fechas disponibles
    st.info(f"📅 Datos disponibles hasta: {st.session_state.max_date.strftime('%d/%m/%Y')}")
    
    # Selector de ciudad
    ciudad_seleccionada = st.selectbox(
        "Selecciona ciudad:",
        list(CIUDADES_CONFIG.keys()),
        format_func=lambda x: CIUDADES_CONFIG[x]['nombre']
    )
    
    # Opción para ver todas las fechas o solo hasta cierta fecha
    ver_todas = st.checkbox("Ver todas las fechas disponibles", value=True)
    
    # Procesar ciudad seleccionada
    config = CIUDADES_CONFIG[ciudad_seleccionada]
    
    # Determinar fecha final
    if ver_todas:
        end_date_dt = st.session_state.max_date
    else:
        # Usar fecha de inicio + 30 días como ejemplo
        end_date_dt = min(
            st.session_state.max_date,
            config['fecha_inicio'] + timedelta(days=90)
        )
        st.caption(f"Mostrando hasta {end_date_dt.strftime('%d/%m/%Y')} (primeros 90 días)")
    
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
        
        # Mostrar rango de fechas
        st.caption(f"📅 Período: {df_table['Fecha'].min()} al {df_table['Fecha'].max()}")
        
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
                ['Fecha Fin', end_date_dt.strftime('%d/%m/%Y')],
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
        st.rerun()

else:
    if uploaded_file is None:
        st.info("👆 1. Carga un archivo Excel\n\n👆 2. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Presiona 'Procesar Archivo' para analizar los datos")

# Footer
st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad | v1.0")
