import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import re
import calendar

# Configuración de la página
st.set_page_config(
    page_title="Clasificador de Unidades Operativas",
    page_icon="📊",
    layout="wide"
)

# Título de la aplicación
st.title("📊 Clasificador de Unidades por Fechas")
st.markdown("---")

# Fechas de corte
FECHA_CORTE_MANIZALES = datetime(2025, 9, 16)
FECHA_CORTE_ARMENIA = datetime(2025, 11, 20)
FECHA_INICIO = datetime(2025, 9, 16)

# Inicializar session state
if 'dfs_procesados' not in st.session_state:
    st.session_state.dfs_procesados = None
if 'archivo_procesado' not in st.session_state:
    st.session_state.archivo_procesado = None
if 'hojas_requeridas' not in st.session_state:
    st.session_state.hojas_requeridas = ['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']
if 'procesamiento_completado' not in st.session_state:
    st.session_state.procesamiento_completado = False

@st.cache_data
def es_fecha_valida(valor):
    """
    Verifica si un valor puede ser una fecha válida
    """
    if pd.isna(valor):
        return False
    
    # Convertir a string y limpiar
    valor_str = str(valor).strip()
    
    # Patrones comunes de fecha
    patrones_fecha = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
        r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
    ]
    
    # Verificar si coincide con algún patrón de fecha
    for patron in patrones_fecha:
        if re.match(patron, valor_str):
            return True
    
    # Intentar convertir con pandas
    try:
        pd.to_datetime(valor_str)
        return True
    except:
        return False

@st.cache_data
def convertir_a_fecha_seguro(valor):
    """
    Convierte un valor a fecha de manera segura, manejando errores
    """
    if pd.isna(valor) or not es_fecha_valida(valor):
        return None
    
    try:
        return pd.to_datetime(valor)
    except:
        return None

@st.cache_data
def clasificar_unidad(ciudad, fecha_ingreso, fecha_factura):
    """
    Clasifica una unidad según la ciudad y las fechas de ingreso y factura
    """
    # Convertir fechas de manera segura
    fecha_ingreso_valida = convertir_a_fecha_seguro(fecha_ingreso)
    fecha_factura_valida = convertir_a_fecha_seguro(fecha_factura)
    
    # Si alguna fecha no es válida, no podemos clasificar
    if fecha_ingreso_valida is None or fecha_factura_valida is None:
        return "fecha no válida"
    
    # Determinar fecha de corte según ciudad
    ciudad_str = str(ciudad).upper().strip() if pd.notna(ciudad) else ""
    
    if 'MANIZALES' in ciudad_str:
        fecha_corte = FECHA_CORTE_MANIZALES
        
        # Aplicar reglas para Manizales
        if fecha_ingreso_valida < fecha_corte and fecha_factura_valida < fecha_corte:
            return "no incluido en el modelo"
        elif fecha_ingreso_valida >= fecha_corte and fecha_factura_valida >= fecha_corte:
            return "incluido en el modelo"
        elif fecha_ingreso_valida > fecha_corte and fecha_factura_valida < fecha_corte:
            return "no incluido en el modelo"
        elif fecha_ingreso_valida < fecha_corte and fecha_factura_valida > fecha_corte:
            return "no incluido en el modelo"
        else:
            return "clasificación pendiente"
    
    elif 'ARMENIA' in ciudad_str:
        fecha_corte = FECHA_CORTE_ARMENIA
        
        # Aplicar reglas para Armenia
        if fecha_ingreso_valida < fecha_corte and fecha_factura_valida < fecha_corte:
            return "no incluido en el modelo"
        elif fecha_ingreso_valida >= fecha_corte and fecha_factura_valida >= fecha_corte:
            return "incluido en el modelo"
        elif fecha_ingreso_valida > fecha_corte and fecha_factura_valida < fecha_corte:
            return "no incluido en el modelo"
        elif fecha_ingreso_valida < fecha_corte and fecha_factura_valida > fecha_corte:
            return "no incluido en el modelo"
        else:
            return "clasificación pendiente"
    
    else:
        return "ciudad no identificada"

def identificar_columnas(df, nombre_hoja):
    """
    Identifica las columnas relevantes en el DataFrame
    """
    columnas_info = {
        'ciudad': None,
        'fecha_ingreso': None,
        'fecha_factura': None
    }
    
    # Buscar columna de ciudad
    for col in df.columns:
        col_lower = col.lower()
        if 'ciudad' in col_lower or 'unidad' in col_lower or 'operativa' in col_lower:
            columnas_info['ciudad'] = col
            break
    
    # Buscar columna de fecha de ingreso
    for col in df.columns:
        col_lower = col.lower()
        if 'ingreso' in col_lower or 'fechaing' in col_lower or 'f_ingreso' in col_lower:
            columnas_info['fecha_ingreso'] = col
            break
    
    # Buscar columna de fecha de factura
    for col in df.columns:
        col_lower = col.lower()
        if 'factura' in col_lower or 'fechafac' in col_lower or 'f_factura' in col_lower:
            columnas_info['fecha_factura'] = col
            break
    
    return columnas_info

# IMPORTANTE: Agregamos guion bajo al parámetro df para evitar el hashing
def procesar_hoja(_df, nombre_hoja):
    """
    Procesa cada hoja del Excel agregando la columna de clasificación
    """
    df_procesado = _df.copy()
    
    # Identificar columnas relevantes
    columnas = identificar_columnas(_df, nombre_hoja)
    
    # Verificar que se encontraron las columnas necesarias
    columnas_faltantes = []
    if columnas['ciudad'] is None:
        columnas_faltantes.append('ciudad')
    if columnas['fecha_ingreso'] is None:
        columnas_faltantes.append('fecha ingreso')
    if columnas['fecha_factura'] is None:
        columnas_faltantes.append('fecha factura')
    
    if columnas_faltantes:
        df_procesado['Clasificación'] = "columnas no encontradas"
        df_procesado['Fecha Ingreso'] = None
        df_procesado['Fecha Factura'] = None
        return df_procesado
    
    # Aplicar clasificación de manera vectorizada
    clasificaciones = []
    fechas_ingreso_proc = []
    fechas_factura_proc = []
    
    total_rows = len(df_procesado)
    for idx, row in df_procesado.iterrows():
        # Obtener valores
        ciudad = row[columnas['ciudad']] if pd.notna(row[columnas['ciudad']]) else ""
        fecha_ingreso = row[columnas['fecha_ingreso']] if columnas['fecha_ingreso'] in df_procesado.columns else None
        fecha_factura = row[columnas['fecha_factura']] if columnas['fecha_factura'] in df_procesado.columns else None
        
        # Convertir fechas de manera segura
        fecha_ingreso_dt = convertir_a_fecha_seguro(fecha_ingreso)
        fecha_factura_dt = convertir_a_fecha_seguro(fecha_factura)
        
        fechas_ingreso_proc.append(fecha_ingreso_dt)
        fechas_factura_proc.append(fecha_factura_dt)
        
        # Clasificar
        clasificacion = clasificar_unidad(ciudad, fecha_ingreso, fecha_factura)
        clasificaciones.append(clasificacion)
    
    # Agregar columnas de información
    df_procesado['Clasificación'] = clasificaciones
    df_procesado['Fecha Ingreso'] = fechas_ingreso_proc
    df_procesado['Fecha Factura'] = fechas_factura_proc
    
    return df_procesado

def construir_tabla_resumen(dfs_procesados, fecha_fin):
    """
    Construye la tabla de resumen con las métricas por fecha
    """
    # Crear rango de fechas desde FECHA_INICIO hasta fecha_fin
    fechas = pd.date_range(start=FECHA_INICIO, end=fecha_fin, freq='D')
    
    # Inicializar lista para almacenar los datos
    datos_resumen = []
    
    # Procesar cada fecha
    for fecha in fechas:
        fecha_str = fecha.strftime('%Y-%m-%d')
        semana = fecha.isocalendar()[1]
        año = fecha.year
        
        # Inicializar contadores
        ingresos = 0
        facturado_modelo = 0
        facturado_fuera_modelo = 0
        
        # Procesar cada hoja
        for nombre_hoja, df in dfs_procesados.items():
            if df is None or 'Fecha Ingreso' not in df.columns or 'Fecha Factura' not in df.columns:
                continue
            
            # Filtrar registros con fechas válidas
            df_validos = df.dropna(subset=['Fecha Ingreso', 'Fecha Factura', 'Clasificación'])
            
            if len(df_validos) == 0:
                continue
            
            # Contar ingresos para esta fecha (basado en Fecha Ingreso)
            ingresos_fecha = len(df_validos[
                df_validos['Fecha Ingreso'].dt.date == fecha.date()
            ])
            ingresos += ingresos_fecha
            
            # Filtrar solo hojas PGP y EVENTO para facturación
            if nombre_hoja in ['PGP', 'EVENTO']:
                # Facturado modelo (incluidos)
                modelo_fecha = len(df_validos[
                    (df_validos['Fecha Factura'].dt.date == fecha.date()) &
                    (df_validos['Clasificación'] == 'incluido en el modelo')
                ])
                facturado_modelo += modelo_fecha
                
                # Facturado fuera modelo (no incluidos)
                fuera_modelo_fecha = len(df_validos[
                    (df_validos['Fecha Factura'].dt.date == fecha.date()) &
                    (df_validos['Clasificación'] == 'no incluido en el modelo')
                ])
                facturado_fuera_modelo += fuera_modelo_fecha
        
        # Solo agregar fila si hay algún valor
        if ingresos > 0 or facturado_modelo > 0 or facturado_fuera_modelo > 0:
            datos_resumen.append({
                'Fecha': fecha_str,
                'Semana del Año': semana,
                'Año': año,
                'Ingresos': ingresos,
                'Facturado Modelo': facturado_modelo,
                'Facturado Fuera Modelo': facturado_fuera_modelo,
                'Facturado Total': facturado_modelo + facturado_fuera_modelo
            })
    
    return pd.DataFrame(datos_resumen)

# Sidebar con información
with st.sidebar:
    st.header("📋 Información")
    st.markdown("""
    **Fechas de corte:**
    - 🏙️ **Manizales:** 16/09/2025
    - 🏙️ **Armenia:** 20/11/2025
    
    **Reglas de clasificación:**
    - Si fecha ingreso < corte Y fecha factura < corte → "no incluido en el modelo"
    - Si fecha ingreso ≥ corte Y fecha factura ≥ corte → "incluido en el modelo"
    - Si fecha ingreso > corte Y fecha factura < corte → "no incluido en el modelo"
    - Si fecha ingreso < corte Y fecha factura > corte → "no incluido en el modelo"
    """)
    
    st.markdown("---")
    st.markdown("**Hojas esperadas en el archivo:**")
    for hoja in st.session_state.hojas_requeridas:
        st.markdown(f"- {hoja}")

# Carga del archivo
archivo_subido = st.file_uploader(
    "Cargar archivo Excel", 
    type=['xlsx', 'xls'],
    help="Selecciona el archivo Excel con las 4 hojas requeridas",
    key="file_uploader"
)

if archivo_subido is not None:
    # Verificar si es un archivo nuevo
    if st.session_state.archivo_procesado != archivo_subido.name:
        st.session_state.dfs_procesados = None
        st.session_state.archivo_procesado = archivo_subido.name
        st.session_state.procesamiento_completado = False
    
    try:
        # Leer todas las hojas del Excel
        with st.spinner("Leyendo archivo Excel..."):
            excel_file = pd.ExcelFile(archivo_subido)
            hojas_disponibles = excel_file.sheet_names
        
        # Verificar que estén todas las hojas requeridas
        hojas_faltantes = [h for h in st.session_state.hojas_requeridas if h not in hojas_disponibles]
        
        if hojas_faltantes:
            st.error(f"❌ Faltan las siguientes hojas: {', '.join(hojas_faltantes)}")
        else:
            st.success("✅ Archivo cargado correctamente con todas las hojas requeridas")
            
            # Procesar cada hoja solo si no están ya procesadas
            if not st.session_state.procesamiento_completado:
                st.session_state.dfs_procesados = {}
                
                # Barra de progreso general
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, hoja in enumerate(st.session_state.hojas_requeridas):
                    status_text.text(f"Procesando hoja: {hoja}")
                    
                    # Leer la hoja
                    df = pd.read_excel(archivo_subido, sheet_name=hoja)
                    
                    # Procesar la hoja (nota: pasamos el DataFrame con guion bajo implícito)
                    df_procesado = procesar_hoja(df, hoja)
                    st.session_state.dfs_procesados[hoja] = df_procesado
                    
                    # Actualizar barra de progreso
                    progress_bar.progress((i + 1) / len(st.session_state.hojas_requeridas))
                
                status_text.text("¡Procesamiento completado!")
                progress_bar.empty()
                st.session_state.procesamiento_completado = True
                st.rerun()  # Forzar rerun para mostrar los resultados
            
            # Mostrar resultados por hoja
            if st.session_state.dfs_procesados:
                with st.expander("📊 Ver resultados detallados por hoja", expanded=False):
                    # Tabs para cada hoja
                    tabs = st.tabs(st.session_state.hojas_requeridas)
                    
                    for tab, hoja in zip(tabs, st.session_state.hojas_requeridas):
                        with tab:
                            df_actual = st.session_state.dfs_procesados[hoja]
                            
                            # Métricas
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total registros", len(df_actual))
                            with col2:
                                incluidos = len(df_actual[df_actual['Clasificación'] == 'incluido en el modelo'])
                                st.metric("✅ Incluidos", incluidos)
                            with col3:
                                no_incluidos = len(df_actual[df_actual['Clasificación'] == 'no incluido en el modelo'])
                                st.metric("❌ No incluidos", no_incluidos)
                            with col4:
                                fechas_invalidas = len(df_actual[df_actual['Clasificación'] == 'fecha no válida'])
                                st.metric("⚠️ Fechas inválidas", fechas_invalidas)
                            
                            # Mostrar DataFrame
                            st.dataframe(df_actual.head(100), use_container_width=True)
                            if len(df_actual) > 100:
                                st.caption(f"Mostrando 100 de {len(df_actual)} registros")
                
                # Sección de tabla resumen
                st.markdown("---")
                st.header("📈 Tabla Resumen por Fecha")
                
                # Selector de fecha
                fecha_maxima = datetime.now().date()
                fecha_seleccionada = st.date_input(
                    "Seleccionar fecha final para el resumen",
                    value=fecha_maxima,
                    min_value=FECHA_INICIO.date(),
                    max_value=fecha_maxima,
                    key="fecha_selector"
                )
                
                # Convertir a datetime
                fecha_fin_dt = datetime.combine(fecha_seleccionada, datetime.min.time())
                
                # Construir tabla resumen
                with st.spinner("Construyendo tabla resumen..."):
                    df_resumen = construir_tabla_resumen(st.session_state.dfs_procesados, fecha_fin_dt)
                    
                    if len(df_resumen) > 0:
                        # Mostrar métricas globales
                        st.subheader("Métricas Globales")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Ingresos", f"{df_resumen['Ingresos'].sum():,}")
                        with col2:
                            st.metric("Total Facturado Modelo", f"{df_resumen['Facturado Modelo'].sum():,}")
                        with col3:
                            st.metric("Total Facturado Fuera Modelo", f"{df_resumen['Facturado Fuera Modelo'].sum():,}")
                        with col4:
                            st.metric("Total Facturado", f"{df_resumen['Facturado Total'].sum():,}")
                        
                        # Mostrar tabla resumen
                        st.subheader("Detalle por Fecha")
                        st.dataframe(
                            df_resumen,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                                "Semana del Año": st.column_config.NumberColumn("Semana", format="%d"),
                                "Año": st.column_config.NumberColumn("Año", format="%d"),
                                "Ingresos": st.column_config.NumberColumn("Ingresos", format="%d"),
                                "Facturado Modelo": st.column_config.NumberColumn("Fact. Modelo", format="%d"),
                                "Facturado Fuera Modelo": st.column_config.NumberColumn("Fact. Fuera Modelo", format="%d"),
                                "Facturado Total": st.column_config.NumberColumn("Fact. Total", format="%d")
                            }
                        )
                        
                        # Gráfico de evolución
                        st.subheader("Evolución Temporal")
                        if len(df_resumen) > 1:
                            chart_data = df_resumen.set_index('Fecha')[['Ingresos', 'Facturado Modelo', 'Facturado Fuera Modelo']]
                            st.line_chart(chart_data)
                        else:
                            st.info("Se necesita más de un día de datos para mostrar el gráfico de evolución")
                        
                        # Botones de descarga
                        col1, col2 = st.columns(2)
                        with col1:
                            csv_resumen = df_resumen.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Descargar tabla resumen como CSV",
                                data=csv_resumen,
                                file_name=f"resumen_fechas_{fecha_seleccionada.strftime('%Y%m%d')}.csv",
                                mime="text/csv"
                            )
                        
                        with col2:
                            # Excel con todas las hojas más el resumen
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                for hoja, df in st.session_state.dfs_procesados.items():
                                    df.to_excel(writer, sheet_name=hoja[:31], index=False)  # Excel limita nombres a 31 caracteres
                                df_resumen.to_excel(writer, sheet_name='RESUMEN', index=False)
                            
                            st.download_button(
                                label="📥 Descargar Excel completo con resumen",
                                data=output.getvalue(),
                                file_name=f"unidades_clasificadas_{fecha_seleccionada.strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning("No hay datos en el rango de fechas seleccionado")
            
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {str(e)}")
        st.exception(e)

else:
    # Mensaje cuando no hay archivo cargado
    st.info("👆 Por favor, carga un archivo Excel para comenzar")
    
    # Ejemplo de estructura esperada
    with st.expander("📋 Ver ejemplo de estructura esperada"):
        ejemplo_data = {
            'Unidad': ['U001', 'U002', 'U003', 'U004'],
            'Ciudad': ['MANIZALES', 'ARMENIA', 'MANIZALES', 'ARMENIA'],
            'Fecha Ingreso': ['2025-09-15', '2025-11-21', '2025-09-17', '2025-11-19'],
            'Fecha Factura': ['2025-09-14', '2025-11-22', '2025-09-18', '2025-11-20']
        }
        ejemplo_df = pd.DataFrame(ejemplo_data)
        st.dataframe(ejemplo_df)
        st.caption("""
        El archivo debe contener columnas con nombres similares para:
        - Ciudad (puede llamarse 'ciudad', 'unidad', 'unidad operativa')
        - Fecha ingreso (puede llamarse 'fecha ingreso', 'fechaing', 'f_ingreso')
        - Fecha factura (puede llamarse 'fecha factura', 'fechafac', 'f_factura')
        """)
