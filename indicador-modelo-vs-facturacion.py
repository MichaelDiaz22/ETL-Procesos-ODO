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

def normalizar_texto(texto):
    """Normaliza texto para comparación"""
    if pd.isna(texto):
        return ""
    texto_str = str(texto).upper().strip()
    texto_str = texto_str.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    texto_str = texto_str.replace("Ñ", "N")
    texto_str = " ".join(texto_str.split())
    return texto_str

def procesar_hoja_evento_pgp(df, nombre_hoja, unidades_filtro):
    """Procesa hojas EVENTO y PGP"""
    
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
        
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            mask_funcional = df_procesado['_unidad_funcional'].isin(unidades_filtro)
            df_procesado = df_procesado[mask_funcional]
        
        return df_procesado
    
    return pd.DataFrame()

def procesar_hoja_pdte(df, nombre_hoja, unidades_filtro):
    """Procesa hojas PDTE EVENTO y PDTE PGP"""
    
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
        fechas_convertidas = []
        for valor in df[col_fecha]:
            fecha = convertir_fecha_excel(valor)
            fechas_convertidas.append(fecha.date() if fecha else None)
        
        centros_normalizados = []
        for valor in df[col_centro]:
            centros_normalizados.append(normalizar_texto(valor))
        
        df_procesado = pd.DataFrame({
            '_fecha_ingreso': fechas_convertidas,
            '_centro': centros_normalizados,
            '_tipo': 'centro_atencion',
            '_hoja': nombre_hoja
        })
        
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
        
        for hoja in ['EVENTO', 'PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_evento_pgp(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                dfs_ingresos.append(df_procesado)
        
        for hoja in ['PDTE EVENTO', 'PDTE PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_pdte(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                dfs_ingresos.append(df_procesado)
        
        if dfs_ingresos:
            df_total = pd.concat(dfs_ingresos, ignore_index=True)
            
            # Mostrar estadísticas globales
            st.write("---")
            st.write("**📊 ESTADÍSTICAS GLOBALES DEL ARCHIVO**")
            
            for ciudad, config in CIUDADES.items():
                ciudad_upper = ciudad.upper()
                centro_upper = normalizar_texto(config['centro_atencion'])
                
                # Contar EVENTO/PGP
                mask_unidad = (df_total['_tipo'] == 'unidad_operativa') & (df_total['_ciudad'] == ciudad_upper)
                total_unidad = df_total[mask_unidad].shape[0]
                
                # Contar PDTE
                mask_centro = (df_total['_tipo'] == 'centro_atencion') & (df_total['_centro'] == centro_upper)
                total_centro = df_total[mask_centro].shape[0]
                
                st.write(f"**{ciudad}:**")
                st.write(f"  - EVENTO/PGP: {total_unidad:,} registros")
                st.write(f"  - PDTE EVENTO/PDTE PGP: {total_centro:,} registros")
                st.write(f"  - TOTAL: {total_unidad + total_centro:,} registros")
            
            # Mostrar rangos de fechas por ciudad
            st.write("**📅 RANGOS DE FECHAS POR CIUDAD (antes del filtro de fecha_hasta):**")
            for ciudad, config in CIUDADES.items():
                ciudad_upper = ciudad.upper()
                centro_upper = normalizar_texto(config['centro_atencion'])
                
                mask_unidad = (df_total['_tipo'] == 'unidad_operativa') & (df_total['_ciudad'] == ciudad_upper)
                mask_centro = (df_total['_tipo'] == 'centro_atencion') & (df_total['_centro'] == centro_upper)
                mask_ciudad = mask_unidad | mask_centro
                df_ciudad = df_total[mask_ciudad]
                
                if not df_ciudad.empty:
                    fechas_validas = df_ciudad['_fecha_ingreso'].dropna()
                    if not fechas_validas.empty:
                        st.write(f"  **{ciudad}:** {fechas_validas.min()} a {fechas_validas.max()}")
                    else:
                        st.write(f"  **{ciudad}:** Sin fechas válidas")
                else:
                    st.write(f"  **{ciudad}:** Sin registros")
            
            fecha_max = datetime.now()
            fechas_validas = df_total['_fecha_ingreso'].dropna()
            if not fechas_validas.empty:
                fecha_max = datetime.combine(fechas_validas.max(), datetime.min.time())
            
            return True, {'INGRESOS_TOTAL': df_total}, fecha_max
        
        return False, None, None
    
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return False, None, None

def contar_ingresos_ciudad(df_ingresos, ciudad, config, fecha_inicio, fecha_fin):
    """Cuenta los ingresos para una ciudad específica con debug detallado"""
    
    if df_ingresos.empty:
        return {}
    
    ciudad_upper = ciudad.upper()
    centro_upper = normalizar_texto(config['centro_atencion'])
    
    st.write(f"**🔍 DEBUG DETALLADO PARA {ciudad}**")
    st.write(f"Fecha inicio ciudad: {fecha_inicio.date()}")
    st.write(f"Fecha fin seleccionada: {fecha_fin.date()}")
    st.write(f"Centro esperado: {centro_upper}")
    
    # Filtrar por ciudad/centro
    mask_unidad = (df_ingresos['_tipo'] == 'unidad_operativa') & (df_ingresos['_ciudad'] == ciudad_upper)
    mask_centro = (df_ingresos['_tipo'] == 'centro_atencion') & (df_ingresos['_centro'] == centro_upper)
    mask_ciudad = mask_unidad | mask_centro
    df_ciudad = df_ingresos[mask_ciudad].copy()
    
    st.write(f"\n**1. FILTRO POR CIUDAD/CENTRO:**")
    st.write(f"   - Registros EVENTO/PGP: {df_ingresos[mask_unidad].shape[0]:,}")
    st.write(f"   - Registros PDTE: {df_ingresos[mask_centro].shape[0]:,}")
    st.write(f"   - Total después de filtro: {df_ciudad.shape[0]:,}")
    
    if df_ciudad.empty:
        return {}
    
    # Análisis de fechas antes del filtro
    st.write(f"\n**2. ANÁLISIS DE FECHAS (antes de aplicar filtro de fecha_fin):**")
    fechas_ciudad = df_ciudad['_fecha_ingreso'].dropna()
    if not fechas_ciudad.empty:
        st.write(f"   - Fecha mínima: {fechas_ciudad.min()}")
        st.write(f"   - Fecha máxima: {fechas_ciudad.max()}")
        st.write(f"   - Registros con fecha válida: {len(fechas_ciudad):,}")
        
        # Contar registros por año para identificar dónde están
        df_ciudad['_año'] = pd.to_datetime(fechas_ciudad).dt.year
        st.write(f"   - Distribución por año:")
        for año in sorted(df_ciudad['_año'].dropna().unique()):
            count = (df_ciudad['_año'] == año).sum()
            st.write(f"     * {año}: {count:,} registros")
    
    # Aplicar filtro de fechas
    st.write(f"\n**3. APLICANDO FILTRO DE FECHAS:**")
    st.write(f"   - Fechas permitidas: desde {fecha_inicio.date()} hasta {fecha_fin.date()}")
    
    mask_fecha = (df_ciudad['_fecha_ingreso'] >= fecha_inicio.date()) & (df_ciudad['_fecha_ingreso'] <= fecha_fin.date())
    df_filtrado = df_ciudad[mask_fecha]
    
    st.write(f"   - Registros después de filtro de fechas: {df_filtrado.shape[0]:,}")
    
    # Mostrar qué porcentaje se perdió
    if df_ciudad.shape[0] > 0:
        perdidos = df_ciudad.shape[0] - df_filtrado.shape[0]
        porcentaje = (perdidos / df_ciudad.shape[0]) * 100
        st.write(f"   - Registros fuera del rango: {perdidos:,} ({porcentaje:.1f}%)")
    
    # Mostrar distribución por hoja después del filtro
    if not df_filtrado.empty:
        st.write(f"\n**4. DISTRIBUCIÓN DESPUÉS DEL FILTRO:**")
        st.write(df_filtrado['_hoja'].value_counts())
    
    # Contar por fecha
    conteo = {}
    for fecha in df_filtrado['_fecha_ingreso']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    if conteo:
        total_ingresos = sum(conteo.values())
        st.write(f"\n**5. RESULTADO FINAL:**")
        st.write(f"   - Total ingresos a mostrar en tabla: {total_ingresos:,}")
        st.write(f"   - Días con ingresos: {len(conteo)}")
    
    st.write("---")
    
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
    st.markdown("**Fechas de inicio:**")
    for ciudad, config in CIUDADES.items():
        st.markdown(f"- **{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')}")

# Carga de archivo
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

archivo = st.file_uploader(
    "Selecciona el archivo Excel",
    type=['xlsx', 'xls']
)

if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    if st.button("📋 Cargar unidades funcionales", use_container_width=True):
        with st.spinner("Cargando..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            if unidades:
                st.success(f"✅ {len(unidades)} unidades encontradas")
    
    if st.session_state.unidades_funcionales:
        unidades_seleccionadas = st.multiselect(
            "Selecciona unidades funcionales:",
            options=st.session_state.unidades_funcionales,
            default=st.session_state.unidades_seleccionadas
        )
        st.session_state.unidades_seleccionadas = unidades_seleccionadas
    
    st.markdown("---")
    
    if st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
        with st.spinner("Procesando..."):
            exito, dfs, fecha_max = cargar_archivo(archivo, st.session_state.unidades_seleccionadas)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_maxima = fecha_max
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                st.success("✅ Procesado correctamente!")

# Mostrar resultados
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    df_ingresos = st.session_state.dfs.get('INGRESOS_TOTAL', pd.DataFrame())
    
    if df_ingresos.empty:
        st.warning("No hay datos")
    else:
        tabs = st.tabs(list(CIUDADES.keys()))
        
        for tab, ciudad in zip(tabs, CIUDADES.keys()):
            with tab:
                config = CIUDADES[ciudad]
                fecha_inicio = config['fecha_inicio']
                fecha_fin = st.session_state.fecha_hasta
                
                if fecha_fin < fecha_inicio:
                    st.warning(f"Fecha anterior a inicio de {ciudad}")
                    continue
                
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
                else:
                    st.info(f"No hay ingresos para {ciudad}")
    
    if st.button("🔄 Reiniciar"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 Sigue los pasos")

st.markdown("---")
st.caption("Aplicación de análisis")
