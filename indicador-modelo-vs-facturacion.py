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
            # Leer solo la columna necesaria para optimizar
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            # Buscar columna de UNIDAD FUNCIONAL INGRESO
            col_unidad_funcional = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower == 'unidad funcional ingreso' or col_lower == 'unidad_funcional_ingreso' or col_lower == 'unidadfuncionalingreso':
                    col_unidad_funcional = col
                    break
            
            if col_unidad_funcional is None:
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if 'unidad funcional' in col_lower and 'ingreso' in col_lower:
                        col_unidad_funcional = col
                        break
            
            if col_unidad_funcional:
                # Obtener valores únicos no nulos
                valores = df[col_unidad_funcional].dropna().unique()
                for valor in valores:
                    unidades_set.add(str(valor).strip())
        
        return sorted(list(unidades_set))
    
    except Exception as e:
        st.error(f"Error al leer unidades funcionales: {str(e)}")
        return []

def procesar_hoja_evento_pgp(df, nombre_hoja, unidades_filtro):
    """Procesa hojas EVENTO y PGP usando CIUDAD UNIDAD OPERATIVA y filtro de unidad funcional"""
    
    # Identificar columna de FECHA INGRESO
    col_fecha = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'fecha ingreso' or col_lower == 'fecha_ingreso' or col_lower == 'fechaingreso':
            col_fecha = col
            break
    
    if col_fecha is None:
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'fecha' in col_lower and 'ingreso' in col_lower:
                col_fecha = col
                break
    
    # Identificar columna de CIUDAD UNIDAD OPERATIVA
    col_ciudad = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'ciudad unidad operativa' or col_lower == 'ciudad_unidad_operativa':
            col_ciudad = col
            break
    
    if col_ciudad is None:
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower == 'unidad operativa' or col_lower == 'unidad_operativa':
                col_ciudad = col
                break
    
    # Identificar columna de UNIDAD FUNCIONAL INGRESO
    col_unidad_funcional = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'unidad funcional ingreso' or col_lower == 'unidad_funcional_ingreso' or col_lower == 'unidadfuncionalingreso':
            col_unidad_funcional = col
            break
    
    if col_unidad_funcional is None:
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'unidad funcional' in col_lower and 'ingreso' in col_lower:
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
            '_valor_filtro': df[col_ciudad].astype(str).str.upper().str.strip(),
            '_tipo': 'unidad_operativa'
        })
        
        # Agregar filtro de unidad funcional si existe la columna
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            # Aplicar filtro
            mask_funcional = df_procesado['_unidad_funcional'].isin(unidades_filtro)
            df_procesado = df_procesado[mask_funcional]
        
        return df_procesado
    
    return pd.DataFrame(columns=['_fecha_ingreso', '_valor_filtro', '_tipo'])

def procesar_hoja_pdte(df, nombre_hoja, unidades_filtro):
    """Procesa hojas PDTE EVENTO y PDTE PGP usando CENTRO DE ATENCIÓN y filtro de unidad funcional"""
    
    # Identificar columna de FECHA INGRESO
    col_fecha = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'fecha ingreso' or col_lower == 'fecha_ingreso' or col_lower == 'fechaingreso':
            col_fecha = col
            break
    
    if col_fecha is None:
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'fecha' in col_lower and 'ingreso' in col_lower:
                col_fecha = col
                break
    
    # Identificar columna de CENTRO DE ATENCIÓN
    col_centro = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'centro de atencion' or col_lower == 'centro_atencion' or col_lower == 'centroatencion':
            col_centro = col
            break
    
    if col_centro is None:
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'centro' in col_lower and 'atencion' in col_lower:
                col_centro = col
                break
    
    # Identificar columna de UNIDAD FUNCIONAL INGRESO
    col_unidad_funcional = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower == 'unidad funcional ingreso' or col_lower == 'unidad_funcional_ingreso' or col_lower == 'unidadfuncionalingreso':
            col_unidad_funcional = col
            break
    
    if col_unidad_funcional is None:
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'unidad funcional' in col_lower and 'ingreso' in col_lower:
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
            '_valor_filtro': df[col_centro].astype(str).str.upper().str.strip(),
            '_tipo': 'centro_atencion'
        })
        
        # Agregar filtro de unidad funcional si existe la columna
        if col_unidad_funcional and unidades_filtro:
            df_procesado['_unidad_funcional'] = df[col_unidad_funcional].astype(str).str.strip()
            # Aplicar filtro
            mask_funcional = df_procesado['_unidad_funcional'].isin(unidades_filtro)
            df_procesado = df_procesado[mask_funcional]
        
        return df_procesado
    
    return pd.DataFrame(columns=['_fecha_ingreso', '_valor_filtro', '_tipo'])

def cargar_archivo(archivo, unidades_filtro):
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
        
        # Procesar hojas EVENTO y PGP
        df_ingresos_unidad = []
        for hoja in ['EVENTO', 'PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_evento_pgp(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                df_ingresos_unidad.append(df_procesado)
            st.info(f"📄 Hoja '{hoja}': {len(df):,} registros - Después de filtro: {len(df_procesado):,}")
        
        # Procesar hojas PDTE EVENTO y PDTE PGP
        df_ingresos_centro = []
        for hoja in ['PDTE EVENTO', 'PDTE PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            df_procesado = procesar_hoja_pdte(df, hoja, unidades_filtro)
            if not df_procesado.empty:
                df_ingresos_centro.append(df_procesado)
            st.info(f"📄 Hoja '{hoja}': {len(df):,} registros - Después de filtro: {len(df_procesado):,}")
        
        # Combinar todos los ingresos
        dfs_ingresos = []
        if df_ingresos_unidad:
            dfs_ingresos.append(pd.concat(df_ingresos_unidad, ignore_index=True))
        if df_ingresos_centro:
            dfs_ingresos.append(pd.concat(df_ingresos_centro, ignore_index=True))
        
        if dfs_ingresos:
            df_ingresos_total = pd.concat(dfs_ingresos, ignore_index=True)
            dfs['INGRESOS_TOTAL'] = df_ingresos_total
            
            st.success(f"✅ Total combinado de ingresos después de filtros: {len(df_ingresos_total):,} registros")
            st.write(f"**Distribución por tipo:**")
            st.write(df_ingresos_total['_tipo'].value_counts())
            
            # Mostrar estadísticas de fechas
            fechas_validas = df_ingresos_total['_fecha_ingreso'].dropna()
            if not fechas_validas.empty:
                st.info(f"📅 Rango de fechas en todos los datos: {fechas_validas.min()} a {fechas_validas.max()}")
        else:
            dfs['INGRESOS_TOTAL'] = pd.DataFrame()
            st.warning("No se encontraron datos de ingresos después de aplicar los filtros")
        
        # Encontrar fecha máxima
        fecha_max = datetime.now()
        if 'INGRESOS_TOTAL' in dfs and not dfs['INGRESOS_TOTAL'].empty:
            fechas_validas = dfs['INGRESOS_TOTAL']['_fecha_ingreso'].dropna()
            if not fechas_validas.empty:
                fecha_max = datetime.combine(fechas_validas.max(), datetime.min.time())
                st.info(f"📅 Fecha máxima en los datos: {fecha_max.strftime('%d/%m/%Y')}")
        
        return True, dfs, fecha_max
    
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
    centro_upper = config['centro_atencion'].upper()
    
    mask_unidad = (df_ingresos['_tipo'] == 'unidad_operativa') & (df_ingresos['_valor_filtro'] == ciudad_upper)
    mask_centro = (df_ingresos['_tipo'] == 'centro_atencion') & (df_ingresos['_valor_filtro'] == centro_upper)
    mask_ciudad = mask_unidad | mask_centro
    df_ciudad = df_ingresos[mask_ciudad]
    
    if df_ciudad.empty:
        return {}
    
    mask_fecha = (df_ciudad['_fecha_ingreso'] >= fecha_inicio.date()) & (df_ciudad['_fecha_ingreso'] <= fecha_fin.date())
    df_filtrado = df_ciudad[mask_fecha]
    
    conteo = {}
    for fecha in df_filtrado['_fecha_ingreso']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def construir_tabla_con_ingresos(ciudad, config, fecha_inicio, fecha_fin, df_ingresos):
    """Construye la tabla con las fechas y los ingresos"""
    
    conteo_ingresos = contar_ingresos_ciudad(df_ingresos, ciudad, config, fecha_inicio, fecha_fin)
    
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
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
        st.markdown(f"- **{ciudad}:** {config['fecha_inicio'].strftime('%d/%m/%Y')} - Centro: {config['centro_atencion']}")

# Carga de archivo
st.header("📁 Cargar Archivo")

# Selector de fecha (aparece ANTES del botón procesar)
st.markdown("### ⚙️ Configuración del Reporte")

fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 9, 16).date(),
    max_value=fecha_actual.date(),
    help="La tabla mostrará datos desde la fecha de inicio de cada ciudad hasta esta fecha"
)

st.markdown("---")

archivo = st.file_uploader(
    "Selecciona el archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: EVENTO, PGP, PDTE EVENTO, PDTE PGP"
)

# Filtro de unidad funcional (aparece después de cargar el archivo pero antes de procesar)
if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    # Botón para cargar las unidades funcionales disponibles
    if st.button("📋 Cargar unidades funcionales disponibles", use_container_width=True):
        with st.spinner("Cargando unidades funcionales..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            if unidades:
                st.success(f"✅ Se encontraron {len(unidades)} unidades funcionales")
            else:
                st.warning("No se encontraron unidades funcionales en el archivo")
    
    # Mostrar multiselect si hay unidades disponibles
    if st.session_state.unidades_funcionales:
        unidades_seleccionadas = st.multiselect(
            "Selecciona las unidades funcionales a incluir:",
            options=st.session_state.unidades_funcionales,
            default=st.session_state.unidades_seleccionadas,
            help="Solo se contarán los registros que pertenezcan a las unidades funcionales seleccionadas. Si no selecciona ninguna, se incluirán todas."
        )
        st.session_state.unidades_seleccionadas = unidades_seleccionadas
        
        if unidades_seleccionadas:
            st.info(f"📌 Filtro activo: {len(unidades_seleccionadas)} unidades funcionales seleccionadas")
        else:
            st.info("📌 Sin filtro: Se incluirán todas las unidades funcionales")
    
    st.markdown("---")
    
    # Botón para procesar
    if st.button("📊 Procesar Archivo", type="primary", use_container_width=True):
        with st.spinner("Cargando archivo y aplicando filtros..."):
            exito, dfs, fecha_max = cargar_archivo(archivo, st.session_state.unidades_seleccionadas)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_maxima = fecha_max
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                
                st.success("✅ Archivo procesado correctamente!")

# Mostrar resultados después de procesar
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Ciudad")
    
    df_ingresos = st.session_state.dfs.get('INGRESOS_TOTAL', pd.DataFrame())
    
    if df_ingresos.empty:
        st.warning("No se encontraron datos de ingresos después de aplicar los filtros")
    else:
        tabs = st.tabs(list(CIUDADES.keys()))
        
        for tab, ciudad in zip(tabs, CIUDADES.keys()):
            with tab:
                config = CIUDADES[ciudad]
                fecha_inicio = config['fecha_inicio']
                fecha_fin = st.session_state.fecha_hasta
                
                if fecha_fin < fecha_inicio:
                    st.warning(f"⚠️ La fecha seleccionada ({fecha_fin.strftime('%d/%m/%Y')}) es anterior a la fecha de inicio de {ciudad} ({fecha_inicio.strftime('%d/%m/%Y')})")
                    continue
                
                with st.spinner(f"Calculando ingresos para {ciudad}..."):
                    df_completa, df_filtrado = construir_tabla_con_ingresos(
                        ciudad,
                        config,
                        fecha_inicio,
                        fecha_fin,
                        df_ingresos
                    )
                    
                    if len(df_filtrado) > 0:
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
                        
                        st.caption(f"📅 Mostrando {len(df_filtrado)} días con ingresos del {df_filtrado['Fecha'].min()} al {df_filtrado['Fecha'].max()}")
                        
                        if len(df_filtrado) > 1:
                            st.subheader("📈 Evolución de Ingresos")
                            chart_data = df_filtrado[['ingresos']].copy()
                            chart_data.index = pd.to_datetime(df_filtrado['Fecha'])
                            st.line_chart(chart_data)
                        
                        # Exportar datos
                        st.subheader("💾 Exportar Datos")
                        col1, col2 = st.columns(2)
                        
                        csv = df_completa.to_csv(index=False).encode('utf-8')
                        col1.download_button(
                            "📥 Descargar CSV",
                            csv,
                            f"{ciudad.lower()}_ingresos.csv",
                            "text/csv",
                            key=f"csv_{ciudad}"
                        )
                        
                        from io import BytesIO
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_completa.to_excel(writer, sheet_name='Todos los días', index=False)
                            df_filtrado.to_excel(writer, sheet_name='Días con ingresos', index=False)
                            
                            info = pd.DataFrame([
                                ['Ciudad', ciudad],
                                ['Centro de Atención', config['centro_atencion']],
                                ['Fecha Inicio', fecha_inicio.strftime('%d/%m/%Y')],
                                ['Fecha Fin', fecha_fin.strftime('%d/%m/%Y')],
                                ['Total Días', len(df_completa)],
                                ['Días con Ingresos', len(df_filtrado)],
                                ['Total Ingresos', total_ingresos],
                                ['Unidades Funcionales Filtro', ', '.join(st.session_state.unidades_seleccionadas) if st.session_state.unidades_seleccionadas else 'Todas']
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
                        st.info(f"No hay ingresos para {ciudad} en el período seleccionado")
    
    # Botón para reiniciar
    st.markdown("---")
    if st.button("🔄 Reiniciar - Cargar otro archivo", use_container_width=True):
        for key in ['datos_cargados', 'dfs', 'fecha_maxima', 'fecha_hasta', 'unidades_funcionales', 'unidades_seleccionadas']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    if archivo is None:
        st.info("👆 1. Selecciona la fecha final del reporte\n\n👆 2. Carga un archivo Excel\n\n👆 3. Carga las unidades funcionales\n\n👆 4. Selecciona las unidades a filtrar\n\n👆 5. Presiona 'Procesar Archivo'")
    else:
        st.info("⏳ Carga las unidades funcionales y selecciona las que deseas filtrar")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por ciudad - Con filtro por Unidad Funcional")
