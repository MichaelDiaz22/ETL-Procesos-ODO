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

# Definición de ciudades
CIUDADES = {
    "Manizales": {
        "fecha_inicio": datetime(2025, 9, 16),
        "centro_atencion": "SAN MARCEL"
    },
    "Armenia": {
        "fecha_inicio": datetime(2025, 11, 20),
        "centro_atencion": "CENTENARIO"
    },
    "Pereira": {
        "fecha_inicio": datetime(2026, 4, 15),
        "centro_atencion": "CLINICA DE ALTA TECNOLOGIA MARAYA"
    }
}

HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']

# Session state
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'dfs' not in st.session_state:
    st.session_state.dfs = {}
if 'fecha_hasta' not in st.session_state:
    st.session_state.fecha_hasta = None
if 'unidades_funcionales' not in st.session_state:
    st.session_state.unidades_funcionales = []
if 'unidades_seleccionadas' not in st.session_state:
    st.session_state.unidades_seleccionadas = []

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
        unidades_set = set()
        for hoja in HOJAS_REQUERIDAS:
            df = pd.read_excel(archivo, sheet_name=hoja)
            col_unidad_funcional = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'unidad funcional ingreso' in col_lower:
                    col_unidad_funcional = col
                    break
            if col_unidad_funcional:
                valores = df[col_unidad_funcional].dropna().unique()
                for valor in valores:
                    unidades_set.add(str(valor).strip())
        return sorted(list(unidades_set))
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto_str = str(texto).upper().strip()
    texto_str = texto_str.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    texto_str = texto_str.replace("Ñ", "N")
    texto_str = " ".join(texto_str.split())
    return texto_str

def procesar_hoja_ingresos(df, nombre_hoja, unidades_filtro):
    col_fecha = None
    for col in df.columns:
        if 'fecha ingreso' in col.lower():
            col_fecha = col
            break
    
    col_ciudad = None
    for col in df.columns:
        if 'ciudad unidad operativa' in col.lower() or 'unidad operativa' in col.lower():
            col_ciudad = col
            break
    
    col_unidad_funcional = None
    for col in df.columns:
        if 'unidad funcional ingreso' in col.lower():
            col_unidad_funcional = col
            break
    
    if col_fecha and col_ciudad:
        fechas_convertidas = []
        for v in df[col_fecha]:
            fecha = convertir_fecha_excel(v)
            fechas_convertidas.append(fecha.date() if fecha else None)
        
        df_procesado = pd.DataFrame({
            '_fecha': fechas_convertidas,
            '_ciudad': df[col_ciudad].astype(str).str.upper().str.strip(),
            '_tipo': 'unidad_operativa',
            '_hoja': nombre_hoja
        })
        
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            df_procesado = df_procesado[df_procesado['_unidad_funcional'].isin(unidades_filtro)]
        
        return df_procesado
    return pd.DataFrame()

def procesar_hoja_pdte_ingresos(df, nombre_hoja, unidades_filtro):
    col_fecha = None
    for col in df.columns:
        if 'fecha ingreso' in col.lower():
            col_fecha = col
            break
    
    col_centro = None
    for col in df.columns:
        if 'centro de atencion' in col.lower():
            col_centro = col
            break
    
    col_unidad_funcional = None
    for col in df.columns:
        if 'unidad funcional ingreso' in col.lower():
            col_unidad_funcional = col
            break
    
    if col_fecha and col_centro:
        fechas_convertidas = []
        for v in df[col_fecha]:
            fecha = convertir_fecha_excel(v)
            fechas_convertidas.append(fecha.date() if fecha else None)
        
        centros_normalizados = [normalizar_texto(v) for v in df[col_centro]]
        
        df_procesado = pd.DataFrame({
            '_fecha': fechas_convertidas,
            '_centro': centros_normalizados,
            '_tipo': 'centro_atencion',
            '_hoja': nombre_hoja
        })
        
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            df_procesado = df_procesado[df_procesado['_unidad_funcional'].isin(unidades_filtro)]
        
        return df_procesado
    return pd.DataFrame()

def procesar_hoja_facturacion(df, nombre_hoja, unidades_filtro):
    col_fecha_ingreso = None
    col_fecha_factura = None
    col_ciudad = None
    col_unidad_funcional = None
    
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'fecha ingreso' in col_lower:
            col_fecha_ingreso = col
        elif 'fecha factura' in col_lower or 'fecha_factura' in col_lower:
            col_fecha_factura = col
        elif 'ciudad unidad operativa' in col_lower or 'unidad operativa' in col_lower:
            col_ciudad = col
        elif 'unidad funcional ingreso' in col_lower:
            col_unidad_funcional = col
    
    if col_fecha_ingreso and col_fecha_factura and col_ciudad:
        fechas_ingreso = []
        for v in df[col_fecha_ingreso]:
            fecha = convertir_fecha_excel(v)
            fechas_ingreso.append(fecha.date() if fecha else None)
        
        fechas_factura = []
        for v in df[col_fecha_factura]:
            fecha = convertir_fecha_excel(v)
            fechas_factura.append(fecha.date() if fecha else None)
        
        df_procesado = pd.DataFrame({
            '_fecha_ingreso': fechas_ingreso,
            '_fecha_factura': fechas_factura,
            '_ciudad': df[col_ciudad].astype(str).str.upper().str.strip(),
            '_hoja': nombre_hoja
        })
        
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            df_procesado = df_procesado[df_procesado['_unidad_funcional'].isin(unidades_filtro)]
        
        return df_procesado
    return pd.DataFrame()

def cargar_archivo(archivo, unidades_filtro):
    try:
        excel_file = pd.ExcelFile(archivo)
        hojas_disponibles = excel_file.sheet_names
        hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_disponibles]
        if hojas_faltantes:
            st.error(f"Faltan hojas: {', '.join(hojas_faltantes)}")
            return False, None, None
        
        dfs_ingresos = []
        dfs_facturacion = []
        
        for hoja in ['EVENTO', 'PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            df_ing = procesar_hoja_ingresos(df, hoja, unidades_filtro)
            if not df_ing.empty:
                dfs_ingresos.append(df_ing)
            
            df_fac = procesar_hoja_facturacion(df, hoja, unidades_filtro)
            if not df_fac.empty:
                dfs_facturacion.append(df_fac)
        
        for hoja in ['PDTE EVENTO', 'PDTE PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_ing = procesar_hoja_pdte_ingresos(df, hoja, unidades_filtro)
            if not df_ing.empty:
                dfs_ingresos.append(df_ing)
        
        df_ingresos_total = pd.concat(dfs_ingresos, ignore_index=True) if dfs_ingresos else pd.DataFrame()
        df_facturacion_total = pd.concat(dfs_facturacion, ignore_index=True) if dfs_facturacion else pd.DataFrame()
        
        return True, {
            'INGRESOS': df_ingresos_total,
            'FACTURACION': df_facturacion_total
        }, datetime.now()
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False, None, None

def contar_ingresos(df_ingresos, ciudad, config, fecha_inicio, fecha_fin):
    ciudad_upper = ciudad.upper()
    centro_upper = normalizar_texto(config['centro_atencion'])
    
    mask_unidad = (df_ingresos['_tipo'] == 'unidad_operativa') & (df_ingresos['_ciudad'] == ciudad_upper)
    mask_centro = (df_ingresos['_tipo'] == 'centro_atencion') & (df_ingresos['_centro'] == centro_upper)
    df_ciudad = df_ingresos[mask_unidad | mask_centro]
    
    if df_ciudad.empty:
        return {}
    
    mask_fecha = (df_ciudad['_fecha'] >= fecha_inicio.date()) & (df_ciudad['_fecha'] <= fecha_fin.date())
    df_filtrado = df_ciudad[mask_fecha]
    
    conteo = {}
    for fecha in df_filtrado['_fecha']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def contar_facturado_modelo(df_facturacion, ciudad, config, fecha_inicio, fecha_fin):
    ciudad_upper = ciudad.upper()
    
    mask_ciudad = df_facturacion['_ciudad'] == ciudad_upper
    df_ciudad = df_facturacion[mask_ciudad]
    
    if df_ciudad.empty:
        return {}
    
    mask_fechas = (df_ciudad['_fecha_ingreso'] >= fecha_inicio.date()) & (df_ciudad['_fecha_factura'] >= fecha_inicio.date())
    df_filtrado = df_ciudad[mask_fechas]
    
    mask_fecha_fin = df_filtrado['_fecha_factura'] <= fecha_fin.date()
    df_filtrado = df_filtrado[mask_fecha_fin]
    
    conteo = {}
    for fecha in df_filtrado['_fecha_factura']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def contar_facturado_fuera_modelo(df_facturacion, ciudad, config, fecha_inicio, fecha_fin):
    ciudad_upper = ciudad.upper()
    
    mask_ciudad = df_facturacion['_ciudad'] == ciudad_upper
    df_ciudad = df_facturacion[mask_ciudad]
    
    if df_ciudad.empty:
        return {}
    
    mask_fechas = (df_ciudad['_fecha_ingreso'] < fecha_inicio.date()) & (df_ciudad['_fecha_factura'] >= fecha_inicio.date())
    df_filtrado = df_ciudad[mask_fechas]
    
    mask_fecha_fin = df_filtrado['_fecha_factura'] <= fecha_fin.date()
    df_filtrado = df_filtrado[mask_fecha_fin]
    
    conteo = {}
    for fecha in df_filtrado['_fecha_factura']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def agrupar_por_periodo(df, periodo):
    """Agrupa los datos por periodo (diario, semanal, mensual)"""
    if df.empty:
        return df
    
    df_agrupado = df.copy()
    df_agrupado['Fecha'] = pd.to_datetime(df_agrupado['Fecha'])
    
    if periodo == 'Mensual':
        df_agrupado['Periodo'] = df_agrupado['Fecha'].dt.strftime('%Y-%m')
        df_agrupado['Fecha'] = df_agrupado['Fecha'].dt.to_period('M').dt.start_time
        df_agrupado['semana'] = 'Mensual'
        df_agrupado['mes'] = df_agrupado['Periodo']
    elif periodo == 'Semanal':
        df_agrupado['Periodo'] = df_agrupado['Fecha'].dt.strftime('%Y-W%W')
        df_agrupado['Fecha'] = df_agrupado['Fecha'] - pd.to_timedelta(df_agrupado['Fecha'].dt.dayofweek, unit='d')
        df_agrupado['semana'] = df_agrupado['Periodo']
        df_agrupado['mes'] = 'Semanal'
    else:  # Diario
        df_agrupado['Periodo'] = df_agrupado['Fecha'].dt.strftime('%Y-%m-%d')
        df_agrupado['mes'] = df_agrupado['Fecha'].dt.strftime('%Y-%m')
    
    # Agrupar
    columnas_agrupar = ['ingresos', 'facturado modelo', 'facturado fuera modelo', 'facturado total']
    df_resultado = df_agrupado.groupby(['Periodo', 'Fecha', 'semana', 'mes', 'año'])[columnas_agrupar].sum().reset_index()
    df_resultado['Novedades'] = 0  # Novedades en 0 por ahora
    
    return df_resultado

def construir_tabla(ciudad, config, fecha_inicio, fecha_fin, df_ingresos, df_facturacion, periodo):
    conteo_ingresos = contar_ingresos(df_ingresos, ciudad, config, fecha_inicio, fecha_fin)
    conteo_facturado_modelo = contar_facturado_modelo(df_facturacion, ciudad, config, fecha_inicio, fecha_fin)
    conteo_facturado_fuera = contar_facturado_fuera_modelo(df_facturacion, ciudad, config, fecha_inicio, fecha_fin)
    
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    datos = []
    for fecha in fechas:
        fecha_key = fecha.date()
        ingresos = conteo_ingresos.get(fecha_key, 0)
        facturado_modelo = conteo_facturado_modelo.get(fecha_key, 0)
        facturado_fuera = conteo_facturado_fuera.get(fecha_key, 0)
        facturado_total = facturado_modelo + facturado_fuera
        
        datos.append({
            'Fecha': fecha,
            'semana': fecha.isocalendar()[1],
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos,
            'facturado modelo': facturado_modelo,
            'facturado fuera modelo': facturado_fuera,
            'facturado total': facturado_total,
            'Novedades': 0
        })
    
    df = pd.DataFrame(datos)
    df_agrupado = agrupar_por_periodo(df, periodo)
    
    return df_agrupado

# Sidebar
with st.sidebar:
    st.header("📋 Información")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"**{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")

# Interfaz principal
st.header("📁 Cargar Archivo")

st.markdown("### ⚙️ Configuración del Reporte")

fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 9, 16).date(),
    max_value=fecha_actual.date()
)

st.markdown("---")

archivo = st.file_uploader("Selecciona el archivo Excel", type=['xlsx', 'xls'])

if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    if st.button("📋 Cargar unidades funcionales"):
        with st.spinner("Cargando..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            if unidades:
                st.success(f"✅ {len(unidades)} unidades encontradas")
    
    if st.session_state.unidades_funcionales:
        st.session_state.unidades_seleccionadas = st.multiselect(
            "Selecciona unidades funcionales:",
            options=st.session_state.unidades_funcionales,
            default=st.session_state.unidades_seleccionadas
        )
    
    st.markdown("---")
    
    if st.button("📊 Procesar Archivo", type="primary"):
        with st.spinner("Procesando..."):
            exito, dfs, _ = cargar_archivo(archivo, st.session_state.unidades_seleccionadas)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                st.success("✅ Archivo procesado correctamente!")

# Mostrar resultados
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    df_ingresos = st.session_state.dfs.get('INGRESOS', pd.DataFrame())
    df_facturacion = st.session_state.dfs.get('FACTURACION', pd.DataFrame())
    fecha_fin = st.session_state.fecha_hasta
    
    tabs = st.tabs(list(CIUDADES.keys()))
    
    for tab, ciudad in zip(tabs, CIUDADES.keys()):
        with tab:
            config = CIUDADES[ciudad]
            fecha_inicio = config['fecha_inicio']
            
            if fecha_fin < fecha_inicio:
                st.warning(f"La fecha {fecha_fin.date()} es anterior a la fecha de inicio de {ciudad}")
                continue
            
            # Selector de período
            periodo = st.selectbox(
                "📊 Agrupar por:",
                options=['Diario', 'Semanal', 'Mensual'],
                key=f"periodo_{ciudad}"
            )
            
            with st.spinner(f"Calculando {ciudad}..."):
                df_tabla = construir_tabla(
                    ciudad, config, fecha_inicio, fecha_fin, df_ingresos, df_facturacion, periodo
                )
                
                if len(df_tabla) > 0:
                    total_ingresos = df_tabla['ingresos'].sum()
                    total_facturado_modelo = df_tabla['facturado modelo'].sum()
                    total_facturado_fuera = df_tabla['facturado fuera modelo'].sum()
                    total_facturado = df_tabla['facturado total'].sum()
                    
                    # Calcular porcentajes
                    pct_modelo = (total_facturado_modelo / total_ingresos * 100) if total_ingresos > 0 else 0
                    pct_fuera = (total_facturado_fuera / total_ingresos * 100) if total_ingresos > 0 else 0
                    pct_total = (total_facturado / total_ingresos * 100) if total_ingresos > 0 else 0
                    
                    cols = st.columns(5)
                    cols[0].metric("📥 Total Ingresos", f"{total_ingresos:,}")
                    cols[1].metric("✅ Facturado Modelo", f"{total_facturado_modelo:,}", f"{pct_modelo:.1f}%")
                    cols[2].metric("❌ Facturado Fuera", f"{total_facturado_fuera:,}", f"{pct_fuera:.1f}%")
                    cols[3].metric("💰 Facturado Total", f"{total_facturado:,}", f"{pct_total:.1f}%")
                    cols[4].metric("⚠️ Novedades", "0")
                    
                    # Mostrar tabla
                    columnas_mostrar = ['Fecha', 'ingresos', 'facturado modelo', 'facturado fuera modelo', 'facturado total', 'Novedades']
                    if periodo == 'Semanal':
                        columnas_mostrar.insert(1, 'semana')
                    elif periodo == 'Mensual':
                        columnas_mostrar.insert(1, 'mes')
                    
                    df_display = df_tabla[columnas_mostrar].copy()
                    if 'Fecha' in df_display.columns:
                        df_display['Fecha'] = df_display['Fecha'].dt.strftime('%Y-%m-%d')
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    # Gráfico
                    if len(df_tabla) > 1:
                        chart_data = df_tabla[['ingresos', 'facturado total', 'Novedades']].copy()
                        chart_data.index = df_tabla['Fecha']
                        st.line_chart(chart_data)
                    
                    # Exportar
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_tabla.to_excel(writer, sheet_name=f'Resumen_{periodo}', index=False)
                    
                    st.download_button(
                        "📥 Descargar Excel",
                        output.getvalue(),
                        f"{ciudad.lower()}_{periodo.lower()}.xlsx",
                        key=f"excel_{ciudad}_{periodo}"
                    )
                else:
                    st.info(f"No hay datos para {ciudad} en el período seleccionado")
    
    if st.button("🔄 Reiniciar"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

else:
    st.info("👆 Carga un archivo Excel para comenzar")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
