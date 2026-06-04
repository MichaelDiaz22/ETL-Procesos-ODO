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

# Unidades funcionales por defecto
UNIDADES_POR_DEFECTO = [
    "CONSULTA ESPECIALIZADA SAN MARCEL",
    "CONSULTA ESPECIALIZADA CENTENARIO",
    "CONSULTA ESPECIALIZADA MARAYA",
    "LABORATORIO CLINICO MARAYA",
    "PROCEDIMIENTOS MENORES CONSULTA CENTENARIO",
    "PROCEDIMIENTOS MENORES CONSULTA SAN MARCEL",
    "RADIOTERAPIA CENTENARIO"
]

# Definición de ciudades con sus fechas de inicio
CIUDADES = {
    "Manizales": {
        "fecha_inicio": datetime(2025, 9, 16)
    },
    "Armenia": {
        "fecha_inicio": datetime(2025, 11, 20)
    },
    "Pereira": {
        "fecha_inicio": datetime(2026, 4, 15)
    }
}

HOJAS_REQUERIDAS = ['PGP']

# Session state
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'df_pgp' not in st.session_state:
    st.session_state.df_pgp = None
if 'fecha_hasta' not in st.session_state:
    st.session_state.fecha_hasta = None
if 'unidades_funcionales' not in st.session_state:
    st.session_state.unidades_funcionales = []
if 'unidades_seleccionadas' not in st.session_state:
    st.session_state.unidades_seleccionadas = UNIDADES_POR_DEFECTO.copy()
if 'resumen_ejecutivo' not in st.session_state:
    st.session_state.resumen_ejecutivo = None

def convertir_fecha_excel(numero):
    try:
        if pd.isna(numero):
            return None
        if isinstance(numero, (int, float)):
            if numero >= 61:
                numero -= 1
            fecha_base = datetime(1899, 12, 30)
            return fecha_base + timedelta(days=numero)
        elif isinstance(numero, datetime):
            return numero
        else:
            fecha = pd.to_datetime(numero, errors='coerce', dayfirst=True)
            if pd.notna(fecha):
                return fecha
        return None
    except:
        return None

def obtener_unidades_funcionales(archivo):
    try:
        df = pd.read_excel(archivo, sheet_name='PGP', nrows=1000)
        col_unidad_funcional = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'unidad funcional ingreso' in col_lower or 'unidad_funcional_ingreso' in col_lower:
                col_unidad_funcional = col
                break
        if col_unidad_funcional:
            valores = df[col_unidad_funcional].dropna().unique()
            return sorted([str(v).strip() for v in valores])
        return []
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def procesar_ingresos(df, unidades_filtro, fecha_inicio, fecha_fin):
    """Cuenta los ingresos por fecha desde la hoja PGP"""
    
    # Identificar columna de fecha ingreso
    col_fecha = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'fecha ingreso' in col_lower or 'fecha_ingreso' in col_lower or 'fechaing' in col_lower:
            col_fecha = col
            break
    
    # Identificar columna de unidad funcional ingreso
    col_unidad = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'unidad funcional ingreso' in col_lower or 'unidad_funcional_ingreso' in col_lower:
            col_unidad = col
            break
    
    if not col_fecha or not col_unidad:
        st.error("No se encontraron las columnas necesarias en la hoja PGP")
        return {}
    
    # Convertir fechas
    fechas_convertidas = []
    for v in df[col_fecha]:
        fecha = convertir_fecha_excel(v)
        fechas_convertidas.append(fecha.date() if fecha else None)
    
    valores_unidades = df[col_unidad].astype(str).str.upper().str.strip()
    
    # Crear DataFrame con los datos necesarios
    df_temp = pd.DataFrame({
        'fecha': fechas_convertidas,
        'unidad': valores_unidades
    })
    
    # Filtrar por unidades seleccionadas
    if unidades_filtro and len(unidades_filtro) > 0:
        unidades_upper = [u.upper().strip() for u in unidades_filtro]
        df_temp = df_temp[df_temp['unidad'].isin(unidades_upper)]
    
    # Filtrar por rango de fechas
    df_temp = df_temp[(df_temp['fecha'] >= fecha_inicio.date()) & (df_temp['fecha'] <= fecha_fin.date())]
    
    # Contar por fecha
    conteo = {}
    for fecha in df_temp['fecha']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def cargar_archivo(archivo, unidades_filtro):
    try:
        # Verificar que exista la hoja PGP
        excel_file = pd.ExcelFile(archivo)
        if 'PGP' not in excel_file.sheet_names:
            st.error("No se encontró la hoja 'PGP' en el archivo")
            return False, None
        
        # Cargar hoja PGP
        df = pd.read_excel(archivo, sheet_name='PGP')
        st.info(f"📄 Hoja 'PGP': {len(df):,} registros")
        
        return True, df
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False, None

def construir_tabla(ciudad, fecha_inicio, fecha_fin, conteo_ingresos):
    """Construye la tabla resumen para una ciudad"""
    
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
        ingresos = conteo_ingresos.get(fecha_key, 0)
        
        datos.append({
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'semana': fecha.isocalendar()[1],
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos
        })
    
    df = pd.DataFrame(datos)
    df_filtrado = df[df['ingresos'] > 0]
    
    return df, df_filtrado

# Sidebar
with st.sidebar:
    st.header("📋 Información")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"**{ciudad}:** Inicio {config['fecha_inicio'].strftime('%d/%m/%Y')}")

# Interfaz principal
st.header("📁 Cargar Archivo")

st.markdown("### ⚙️ Configuración del Reporte")

fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 1, 1).date(),
    max_value=fecha_actual.date()
)

st.markdown("---")

archivo = st.file_uploader("Selecciona el archivo Excel", type=['xlsx', 'xls'])

if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    if st.button("📋 Cargar unidades funcionales disponibles"):
        with st.spinner("Cargando..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            if unidades:
                st.success(f"✅ {len(unidades)} unidades funcionales encontradas")
            else:
                st.warning("No se encontraron unidades funcionales en la hoja PGP")
    
    if st.session_state.unidades_funcionales:
        unidades_seleccionadas = st.multiselect(
            "Selecciona unidades funcionales a incluir:",
            options=st.session_state.unidades_funcionales,
            default=[u for u in st.session_state.unidades_funcionales if u in UNIDADES_POR_DEFECTO]
        )
        st.session_state.unidades_seleccionadas = unidades_seleccionadas
        
        if unidades_seleccionadas:
            st.info(f"📌 {len(unidades_seleccionadas)} unidades funcionales seleccionadas")
        else:
            st.warning("⚠️ No hay unidades funcionales seleccionadas. No se contarán ingresos.")
    
    st.markdown("---")
    
    if st.button("📊 Procesar Archivo", type="primary"):
        with st.spinner("Procesando archivo..."):
            exito, df = cargar_archivo(archivo, st.session_state.unidades_seleccionadas)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.df_pgp = df
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                st.success("✅ Archivo procesado correctamente!")

# Mostrar resultados
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    df_pgp = st.session_state.df_pgp
    fecha_fin = st.session_state.fecha_hasta
    
    # Procesar ingresos para todas las ciudades
    conteos_por_ciudad = {}
    for ciudad, config in CIUDADES.items():
        fecha_inicio = config['fecha_inicio']
        if fecha_fin >= fecha_inicio:
            conteo = procesar_ingresos(df_pgp, st.session_state.unidades_seleccionadas, fecha_inicio, fecha_fin)
            conteos_por_ciudad[ciudad] = conteo
    
    # Crear pestañas por ciudad
    tabs = st.tabs(list(CIUDADES.keys()))
    
    for tab, ciudad in zip(tabs, CIUDADES.keys()):
        with tab:
            config = CIUDADES[ciudad]
            fecha_inicio = config['fecha_inicio']
            
            if fecha_fin < fecha_inicio:
                st.warning(f"La fecha {fecha_fin.date()} es anterior a la fecha de inicio de {ciudad}")
                continue
            
            conteo_ingresos = conteos_por_ciudad.get(ciudad, {})
            df_completa, df_filtrado = construir_tabla(ciudad, fecha_inicio, fecha_fin, conteo_ingresos)
            
            if len(df_filtrado) > 0:
                total_ingresos = df_completa['ingresos'].sum()
                
                cols = st.columns(1)
                cols[0].metric("📥 Total Ingresos", f"{total_ingresos:,}")
                
                st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
                st.caption(f"📅 {len(df_filtrado)} días con ingresos del {df_filtrado['Fecha'].min()} al {df_filtrado['Fecha'].max()}")
                
                # Gráfico
                if len(df_filtrado) > 1:
                    chart_data = df_filtrado[['ingresos']].copy()
                    chart_data.index = pd.to_datetime(df_filtrado['Fecha'])
                    st.line_chart(chart_data)
                
                # Exportar
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_completa.to_excel(writer, sheet_name='Todos los días', index=False)
                    df_filtrado.to_excel(writer, sheet_name='Días con ingresos', index=False)
                
                st.download_button(
                    "📥 Descargar Excel",
                    output.getvalue(),
                    f"{ciudad.lower()}_ingresos_pgp.xlsx",
                    key=f"excel_{ciudad}"
                )
            else:
                st.info(f"No hay ingresos para {ciudad} en el período seleccionado")
    
    if st.button("🔄 Reiniciar"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

else:
    st.info("👆 Carga un archivo Excel para comenzar")

st.markdown("---")
st.caption("Aplicación para análisis de ingresos desde hoja PGP")
