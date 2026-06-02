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

# Definición de ciudades con sus fechas de inicio y centros de atención
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
if 'unidades_funcionales' not in st.session_state:
    st.session_state.unidades_funcionales = []
if 'unidades_seleccionadas' not in st.session_state:
    st.session_state.unidades_seleccionadas = []

def convertir_fecha_excel(numero):
    """Convierte número serial de Excel a fecha"""
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
    """Lee todas las hojas y obtiene los valores únicos de UNIDAD FUNCIONAL INGRESO"""
    try:
        unidades_set = set()
        
        for hoja in HOJAS_REQUERIDAS:
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            col_unidad_funcional = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'unidad funcional ingreso' in col_lower or 'unidad_funcional_ingreso' in col_lower:
                    col_unidad_funcional = col
                    break
            
            if col_unidad_funcional:
                valores = df[col_unidad_funcional].dropna().unique()
                for valor in valores:
                    unidades_set.add(str(valor).strip())
        
        return sorted(list(unidades_set))
    
    except Exception as e:
        st.error(f"Error al leer unidades funcionales: {str(e)}")
        return []

def procesar_hoja_evento_pgp(df, nombre_hoja, unidades_filtro):
    """Procesa hojas EVENTO y PGP"""
    
    # Identificar columnas
    col_fecha = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'fecha ingreso' in col_lower or 'fecha_ingreso' in col_lower:
            col_fecha = col
            break
    
    col_ciudad = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'ciudad unidad operativa' in col_lower or 'unidad operativa' in col_lower:
            col_ciudad = col
            break
    
    col_unidad_funcional = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'unidad funcional ingreso' in col_lower or 'unidad_funcional_ingreso' in col_lower:
            col_unidad_funcional = col
            break
    
    if col_fecha and col_ciudad:
        # Convertir fechas
        fechas_convertidas = []
        for valor in df[col_fecha]:
            fecha = convertir_fecha_excel(valor)
            fechas_convertidas.append(fecha.date() if fecha else None)
        
        df_procesado = pd.DataFrame({
            '_fecha_ingreso': fechas_convertidas,
            '_ciudad': df[col_ciudad].astype(str).str.upper().str.strip(),
            '_tipo': 'unidad_operativa',
            '_hoja': nombre_hoja
        })
        
        # Aplicar filtro de unidad funcional
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            mask_funcional = df_procesado['_unidad_funcional'].isin(unidades_filtro)
            df_procesado = df_procesado[mask_funcional]
        
        return df_procesado
    
    return pd.DataFrame()

def procesar_hoja_pdte(df, nombre_hoja, unidades_filtro):
    """Procesa hojas PDTE EVENTO y PDTE PGP"""
    
    # Identificar columnas
    col_fecha = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'fecha ingreso' in col_lower or 'fecha_ingreso' in col_lower:
            col_fecha = col
            break
    
    col_centro = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'centro de atencion' in col_lower or 'centro_atencion' in col_lower:
            col_centro = col
            break
    
    col_unidad_funcional = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'unidad funcional ingreso' in col_lower or 'unidad_funcional_ingreso' in col_lower:
            col_unidad_funcional = col
            break
    
    if col_fecha and col_centro:
        # Convertir fechas
        fechas_convertidas = []
        for valor in df[col_fecha]:
            fecha = convertir_fecha_excel(valor)
            fechas_convertidas.append(fecha.date() if fecha else None)
        
        df_procesado = pd.DataFrame({
            '_fecha_ingreso': fechas_convertidas,
            '_centro': df[col_centro].astype(str).str.upper().str.strip(),
            '_tipo': 'centro_atencion',
            '_hoja': nombre_hoja
        })
        
        # Aplicar filtro de unidad funcional
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            mask_funcional = df_procesado['_unidad_funcional'].isin(unidades_filtro)
            df_procesado = df_procesado[mask_funcional]
        
        return df_procesado
    
    return pd.DataFrame()

def cargar_archivo(archivo, unidades_filtro):
    """Carga el archivo Excel y procesa todas las hojas"""
    try:
        excel_file = pd.ExcelFile(archivo)
        hojas_disponibles = excel_file.sheet_names
        
        hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_disponibles]
        if hojas_faltantes:
            st.error(f"❌ Faltan las siguientes hojas: {', '.join(hojas_faltantes)}")
            return False, None, None
        
        dfs_ingresos = []
        
        # Procesar EVENTO y PGP
        for hoja in ['EVENTO', 'PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_evento_pgp(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                dfs_ingresos.append(df_procesado)
                st.write(f"📊 {hoja}: {len(df_procesado):,} registros después de filtros")
        
        # Procesar PDTE EVENTO y PDTE PGP
        for hoja in ['PDTE EVENTO', 'PDTE PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_pdte(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                dfs_ingresos.append(df_procesado)
                st.write(f"📊 {hoja}: {len(df_procesado):,} registros después de filtros")
        
        if dfs_ingresos:
            df_total = pd.concat(dfs_ingresos, ignore_index=True)
            
            # Mostrar distribución por hoja y tipo
            st.write("---")
            st.write("**Distribución de registros por hoja:**")
            st.write(df_total['_hoja'].value_counts())
            st.write("**Distribución por tipo de filtro:**")
            st.write(df_total['_tipo'].value_counts())
            
            # Mostrar ejemplos de ciudades y centros
            st.write("**Ejemplos de valores únicos en EVENTO/PGP (UNIDAD OPERATIVA):**")
            valores_unidad = df_total[df_total['_tipo'] == 'unidad_operativa']['_ciudad'].unique()
            st.write(valores_unidad[:20].tolist())
            
            st.write("**Ejemplos de valores únicos en PDTE (CENTRO DE ATENCIÓN):**")
            valores_centro = df_total[df_total['_tipo'] == 'centro_atencion']['_centro'].unique()
            st.write(valores_centro[:20].tolist())
            
            # Fecha máxima
            fechas_validas = df_total['_fecha_ingreso'].dropna()
            fecha_max = datetime.now()
            if not fechas_validas.empty:
                fecha_max = datetime.combine(fechas_validas.max(), datetime.min.time())
            
            return True, {'INGRESOS_TOTAL': df_total}, fecha_max
        
        return False, None, None
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False, None, None

def contar_ingresos_ciudad(df_ingresos, ciudad, config, fecha_inicio, fecha_fin):
    """Cuenta los ingresos para una ciudad específica - SUMANDO TODAS LAS HOJAS"""
    
    if df_ingresos.empty:
        st.warning("DataFrame de ingresos vacío")
        return {}
    
    ciudad_upper = ciudad.upper()
    centro_upper = config['centro_atencion'].upper()
    
    st.write(f"**Debug {ciudad}:**")
    st.write(f"- Centro esperado: {centro_upper}")
    
    # Para EVENTO y PGP: filtrar por ciudad en columna '_ciudad'
    mask_unidad = (df_ingresos['_tipo'] == 'unidad_operativa') & (df_ingresos['_ciudad'] == ciudad_upper)
    registros_unidad = df_ingresos[mask_unidad]
    st.write(f"- Registros en EVENTO/PGP para {ciudad_upper}: {len(registros_unidad)}")
    
    # Para PDTE: filtrar por centro de atención
    mask_centro = (df_ingresos['_tipo'] == 'centro_atencion') & (df_ingresos['_centro'] == centro_upper)
    registros_centro = df_ingresos[mask_centro]
    st.write(f"- Registros en PDTE para centro {centro_upper}: {len(registros_centro)}")
    
    # Combinar
    mask_ciudad = mask_unidad | mask_centro
    df_ciudad = df_ingresos[mask_ciudad]
    st.write(f"- Total registros para {ciudad} antes de filtro de fechas: {len(df_ciudad)}")
    
    if df_ciudad.empty:
        return {}
    
    # Filtrar por rango de fechas
    mask_fecha = (df_ciudad['_fecha_ingreso'] >= fecha_inicio.date()) & (df_ciudad['_fecha_ingreso'] <= fecha_fin.date())
    df_filtrado = df_ciudad[mask_fecha]
    st.write(f"- Registros después de filtrar fechas ({fecha_inicio.date()} a {fecha_fin.date()}): {len(df_filtrado)}")
    
    # Contar por fecha
    conteo = {}
    for fecha in df_filtrado['_fecha_ingreso']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    if conteo:
        st.write(f"- Días con ingresos: {len(conteo)}")
        st.write(f"- Total ingresos sumados: {sum(conteo.values())}")
    
    return conteo

def construir_tabla_con_ingresos(ciudad, config, fecha_inicio, fecha_fin, df_ingresos):
    """Construye la tabla con las fechas y los ingresos"""
    
    conteo_ingresos = contar_ingresos_ciudad(df_ingresos, ciudad, config, fecha_inicio, fecha_fin)
    
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
            'ingresos': ingresos,
            'facturado modelo': 0,
            'facturado fuera modelo': 0,
            'facturado total': 0,
            'Novedades': 0
        })
    
    df = pd.DataFrame(datos)
    df_filtrado = df[df['ingresos'] > 0]
    
    return df, df_filtrado

# Sidebar
with st.sidebar:
    st.header("📋 Información")
    st.markdown("**Fechas de inicio y centros de atención:**")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"- **{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")
        st.markdown(f"  Centro: {config['centro_atencion']}")

# Carga de archivo
st.header("📁 Cargar Archivo")

# Selector de fecha
st.markdown("### ⚙️ Configuración del Reporte")
fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 9, 16).date(),
    max_value=fecha_actual.date()
)

st.markdown("---")

archivo = st.file_uploader(
    "Selecciona el archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: EVENTO, PGP, PDTE EVENTO, PDTE PGP"
)

if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    if st.button("📋 Cargar unidades funcionales", use_container_width=True):
        with st.spinner("Cargando unidades funcionales..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            if unidades:
                st.success(f"✅ Se encontraron {len(unidades)} unidades funcionales")
            else:
                st.warning("No se encontraron unidades funcionales")
    
    if st.session_state.unidades_funcionales:
        unidades_seleccionadas = st.multiselect(
            "Selecciona las unidades funcionales:",
            options=st.session_state.unidades_funcionales,
            default=st.session_state.unidades_seleccionadas
        )
        st.session_state.unidades_seleccionadas = unidades_seleccionadas
        
        if unidades_seleccionadas:
            st.info(f"📌 Filtro activo: {len(unidades_seleccionadas)} unidades")
        else:
            st.info("📌 Sin filtro: todas las unidades")
    
    st.markdown("---")
    
    if st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
        with st.spinner("Procesando archivo..."):
            exito, dfs, fecha_max = cargar_archivo(archivo, st.session_state.unidades_seleccionadas)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_maxima = fecha_max
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                st.success("✅ Archivo procesado correctamente!")

# Mostrar resultados
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    df_ingresos = st.session_state.dfs.get('INGRESOS_TOTAL', pd.DataFrame())
    
    if df_ingresos.empty:
        st.warning("No hay datos de ingresos")
    else:
        tabs = st.tabs(list(CIUDADES.keys()))
        
        for tab, ciudad in zip(tabs, CIUDADES.keys()):
            with tab:
                config = CIUDADES[ciudad]
                fecha_inicio = config['fecha_inicio']
                fecha_fin = st.session_state.fecha_hasta
                
                if fecha_fin < fecha_inicio:
                    st.warning(f"Fecha {fecha_fin.strftime('%d/%m/%Y')} anterior a inicio de {ciudad}")
                    continue
                
                with st.spinner(f"Calculando {ciudad}..."):
                    df_completa, df_filtrado = construir_tabla_con_ingresos(
                        ciudad, config, fecha_inicio, fecha_fin, df_ingresos
                    )
                    
                    if len(df_filtrado) > 0:
                        total_ingresos = df_completa['ingresos'].sum()
                        
                        cols = st.columns(5)
                        cols[0].metric("📥 Total Ingresos", f"{total_ingresos:,}")
                        cols[1].metric("✅ Facturado Modelo", "Pendiente")
                        cols[2].metric("❌ Facturado Fuera", "Pendiente")
                        cols[3].metric("💰 Facturado Total", "Pendiente")
                        cols[4].metric("⚠️ Novedades", "Pendiente")
                        
                        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
                        st.caption(f"📅 {len(df_filtrado)} días con ingresos")
                        
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
                            f"{ciudad.lower()}_ingresos.xlsx",
                            key=f"excel_{ciudad}"
                        )
                    else:
                        st.info(f"No hay ingresos para {ciudad}")
    
    if st.button("🔄 Reiniciar"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 Sigue los pasos para generar el reporte")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad")
