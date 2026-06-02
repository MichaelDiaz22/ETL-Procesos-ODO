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
    """Normaliza texto para comparación (quita acentos, espacios, convierte a mayúsculas)"""
    if pd.isna(texto):
        return ""
    texto_str = str(texto).upper().strip()
    # Reemplazar caracteres comunes
    texto_str = texto_str.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    texto_str = texto_str.replace("Ñ", "N")
    # Eliminar espacios múltiples
    texto_str = " ".join(texto_str.split())
    return texto_str

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
        
        # Normalizar los valores del centro de atención
        centros_normalizados = []
        for valor in df[col_centro]:
            centros_normalizados.append(normalizar_texto(valor))
        
        df_procesado = pd.DataFrame({
            '_fecha_ingreso': fechas_convertidas,
            '_centro': centros_normalizados,
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
                
                # Mostrar valores únicos de ciudad en esta hoja
                ciudades_unicas = df_procesado['_ciudad'].unique()
                st.write(f"📊 {hoja}: {len(df_procesado):,} registros")
                st.write(f"   Ciudades encontradas: {ciudades_unicas[:10].tolist()}")
        
        # Procesar PDTE EVENTO y PDTE PGP
        for hoja in ['PDTE EVENTO', 'PDTE PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_pdte(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                dfs_ingresos.append(df_procesado)
                
                # Mostrar valores únicos de centro en esta hoja
                centros_unicos = df_procesado['_centro'].unique()
                st.write(f"📊 {hoja}: {len(df_procesado):,} registros")
                st.write(f"   Centros encontrados: {centros_unicos[:10].tolist()}")
        
        if dfs_ingresos:
            df_total = pd.concat(dfs_ingresos, ignore_index=True)
            
            st.write("---")
            st.write("**Distribución por hoja:**")
            st.write(df_total['_hoja'].value_counts())
            
            # Mostrar ejemplos de centros para verificar Pereira
            st.write("**Centros de atención encontrados (muestra):**")
            centros_pdte = df_total[df_total['_tipo'] == 'centro_atencion']['_centro'].value_counts().head(20)
            st.write(centros_pdte)
            
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
    """Cuenta los ingresos para una ciudad específica"""
    
    if df_ingresos.empty:
        return {}
    
    ciudad_upper = ciudad.upper()
    centro_upper = normalizar_texto(config['centro_atencion'])
    
    st.write(f"**Debug {ciudad}:**")
    st.write(f"- Centro esperado normalizado: {centro_upper}")
    
    # Para EVENTO y PGP: filtrar por ciudad
    mask_unidad = (df_ingresos['_tipo'] == 'unidad_operativa') & (df_ingresos['_ciudad'] == ciudad_upper)
    registros_unidad = df_ingresos[mask_unidad]
    st.write(f"- Registros en EVENTO/PGP para {ciudad_upper}: {len(registros_unidad)}")
    
    # Para PDTE: filtrar por centro de atención normalizado
    # Usar contains para coincidencia parcial si es necesario
    mask_centro_exacta = (df_ingresos['_tipo'] == 'centro_atencion') & (df_ingresos['_centro'] == centro_upper)
    registros_centro_exacta = df_ingresos[mask_centro_exacta]
    
    # También buscar coincidencia parcial por si hay variaciones en el texto
    mask_centro_parcial = (df_ingresos['_tipo'] == 'centro_atencion') & (df_ingresos['_centro'].str.contains(centro_upper[:20], na=False))
    registros_centro_parcial = df_ingresos[mask_centro_parcial]
    
    st.write(f"- Registros en PDTE para coincidencia exacta '{centro_upper}': {len(registros_centro_exacta)}")
    if len(registros_centro_parcial) > len(registros_centro_exacta):
        st.write(f"- Registros en PDTE para coincidencia parcial: {len(registros_centro_parcial)}")
        mask_centro = mask_centro_parcial
    else:
        mask_centro = mask_centro_exacta
    
    # Combinar
    mask_ciudad = mask_unidad | mask_centro
    df_ciudad = df_ingresos[mask_ciudad]
    st.write(f"- Total registros para {ciudad} antes de fechas: {len(df_ciudad)}")
    
    if df_ciudad.empty:
        return {}
    
    # Mostrar distribución por hoja de los registros encontrados
    st.write(f"- Distribución por hoja:")
    st.write(df_ciudad['_hoja'].value_counts())
    
    # Filtrar por rango de fechas
    mask_fecha = (df_ciudad['_fecha_ingreso'] >= fecha_inicio.date()) & (df_ciudad['_fecha_ingreso'] <= fecha_fin.date())
    df_filtrado = df_ciudad[mask_fecha]
    st.write(f"- Registros después de filtrar fechas: {len(df_filtrado)}")
    
    # Contar por fecha
    conteo = {}
    for fecha in df_filtrado['_fecha_ingreso']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    if conteo:
        total_ingresos = sum(conteo.values())
        st.write(f"- ✅ Total ingresos para {ciudad}: {total_ingresos}")
    
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
    
    # Mostrar resumen de la tabla
    if len(df_filtrado) > 0:
        st.write(f"**Resumen tabla {ciudad}:**")
        st.write(f"- Total ingresos en tabla: {df_filtrado['ingresos'].sum()}")
        st.write(f"- Días con ingresos: {len(df_filtrado)}")
    
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
                    st.warning(f"Fecha anterior a inicio de {ciudad}")
                    continue
                
                with st.expander(f"🔍 Ver depuración de {ciudad}", expanded=False):
                    df_completa, df_filtrado = construir_tabla_con_ingresos(
                        ciudad, config, fecha_inicio, fecha_fin, df_ingresos
                    )
                
                # Ejecutar de nuevo sin el expander para mostrar resultados
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
                    st.caption(f"📅 {len(df_filtrado)} días con ingresos - Total: {total_ingresos:,} ingresos")
                    
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
st.caption("Aplicación para análisis de facturación por ciudad - Versión corregida para Pereira")
