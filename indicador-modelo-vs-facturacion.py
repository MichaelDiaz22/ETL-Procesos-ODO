import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

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

def clasificar_unidad(row, ciudad, fecha_ingreso, fecha_factura):
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

def procesar_hoja(df, nombre_hoja):
    """
    Procesa cada hoja del Excel agregando la columna de clasificación
    """
    df_procesado = df.copy()
    
    # Identificar columnas relevantes
    columnas = identificar_columnas(df, nombre_hoja)
    
    # Verificar que se encontraron las columnas necesarias
    columnas_faltantes = []
    if columnas['ciudad'] is None:
        columnas_faltantes.append('ciudad')
    if columnas['fecha_ingreso'] is None:
        columnas_faltantes.append('fecha ingreso')
    if columnas['fecha_factura'] is None:
        columnas_faltantes.append('fecha factura')
    
    if columnas_faltantes:
        st.warning(f"⚠️ En la hoja {nombre_hoja} no se encontraron las columnas: {', '.join(columnas_faltantes)}")
        df_procesado['Clasificación'] = "columnas no encontradas"
        df_procesado['Fecha Ingreso Válida'] = False
        df_procesado['Fecha Factura Válida'] = False
        return df_procesado
    
    # Aplicar clasificación
    clasificaciones = []
    fechas_ingreso_validas = []
    fechas_factura_validas = []
    
    # Barra de progreso para el procesamiento de la hoja
    progress_text = f"Procesando registros de {nombre_hoja}..."
    my_bar = st.progress(0, text=progress_text)
    
    total_rows = len(df_procesado)
    for idx, row in df_procesado.iterrows():
        # Obtener valores
        ciudad = row[columnas['ciudad']] if pd.notna(row[columnas['ciudad']]) else ""
        fecha_ingreso = row[columnas['fecha_ingreso']] if columnas['fecha_ingreso'] in df_procesado.columns else None
        fecha_factura = row[columnas['fecha_factura']] if columnas['fecha_factura'] in df_procesado.columns else None
        
        # Verificar si las fechas son válidas
        ingreso_valida = es_fecha_valida(fecha_ingreso)
        factura_valida = es_fecha_valida(fecha_factura)
        
        fechas_ingreso_validas.append(ingreso_valida)
        fechas_factura_validas.append(factura_valida)
        
        # Clasificar
        clasificacion = clasificar_unidad(row, ciudad, fecha_ingreso, fecha_factura)
        clasificaciones.append(clasificacion)
        
        # Actualizar barra de progreso
        if idx % 100 == 0:  # Actualizar cada 100 registros para mejorar rendimiento
            my_bar.progress((idx + 1) / total_rows, text=progress_text)
    
    my_bar.progress(1.0, text="¡Procesamiento completado!")
    
    # Agregar columnas de información
    df_procesado['Clasificación'] = clasificaciones
    df_procesado['Fecha Ingreso Válida'] = fechas_ingreso_validas
    df_procesado['Fecha Factura Válida'] = fechas_factura_validas
    
    return df_procesado

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
    
    **Posibles clasificaciones:**
    - ✅ incluido en el modelo
    - ❌ no incluido en el modelo
    - ⚠️ fecha no válida
    - ❓ ciudad no identificada
    - ⏳ clasificación pendiente
    """)
    
    st.markdown("---")
    st.markdown("**Hojas esperadas en el archivo:**")
    st.markdown("- PGP")
    st.markdown("- EVENTO")
    st.markdown("- PDTE PGP")
    st.markdown("- PDTE EVENTO")

# Carga del archivo
archivo_subido = st.file_uploader(
    "Cargar archivo Excel", 
    type=['xlsx', 'xls'],
    help="Selecciona el archivo Excel con las 4 hojas requeridas"
)

if archivo_subido is not None:
    try:
        # Leer todas las hojas del Excel
        excel_file = pd.ExcelFile(archivo_subido)
        hojas_disponibles = excel_file.sheet_names
        
        # Verificar que estén todas las hojas requeridas
        hojas_requeridas = ['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']
        hojas_faltantes = [h for h in hojas_requeridas if h not in hojas_disponibles]
        
        if hojas_faltantes:
            st.error(f"❌ Faltan las siguientes hojas: {', '.join(hojas_faltantes)}")
        else:
            st.success("✅ Archivo cargado correctamente con todas las hojas requeridas")
            
            # Procesar cada hoja
            dfs_procesados = {}
            
            # Barra de progreso general
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, hoja in enumerate(hojas_requeridas):
                status_text.text(f"Procesando hoja: {hoja}")
                
                # Leer la hoja
                df = pd.read_excel(archivo_subido, sheet_name=hoja)
                
                # Mostrar información de la hoja
                with st.expander(f"📊 Ver columnas encontradas en {hoja}"):
                    st.write("Columnas disponibles:", list(df.columns))
                
                # Procesar la hoja
                df_procesado = procesar_hoja(df, hoja)
                dfs_procesados[hoja] = df_procesado
                
                # Actualizar barra de progreso
                progress_bar.progress((i + 1) / len(hojas_requeridas))
            
            status_text.text("¡Procesamiento completado!")
            progress_bar.empty()
            
            # Mostrar resultados
            st.markdown("---")
            st.header("📊 Resultados")
            
            # Tabs para cada hoja
            tabs = st.tabs(hojas_requeridas)
            
            for tab, hoja in zip(tabs, hojas_requeridas):
                with tab:
                    df_actual = dfs_procesados[hoja]
                    
                    # Métricas
                    col1, col2, col3, col4, col5 = st.columns(5)
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
                    with col5:
                        otros = len(df_actual[~df_actual['Clasificación'].isin(['incluido en el modelo', 'no incluido en el modelo', 'fecha no válida'])])
                        st.metric("❓ Otros", otros)
                    
                    # Mostrar DataFrame
                    st.dataframe(df_actual, use_container_width=True)
                    
                    # Estadísticas adicionales
                    with st.expander("📈 Ver estadísticas detalladas"):
                        st.write("Distribución de clasificaciones:")
                        st.write(df_actual['Clasificación'].value_counts())
                        
                        st.write("Fechas válidas vs inválidas:")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Fechas ingreso válidas", df_actual['Fecha Ingreso Válida'].sum())
                        with col2:
                            st.metric("Fechas factura válidas", df_actual['Fecha Factura Válida'].sum())
                    
                    # Botón de descarga para cada hoja
                    csv = df_actual.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"📥 Descargar {hoja} como CSV",
                        data=csv,
                        file_name=f"{hoja}_clasificado.csv",
                        mime="text/csv",
                        key=f"download_{hoja}"
                    )
            
            # Botón para descargar todo como Excel
            st.markdown("---")
            with st.expander("📥 Descargar todas las hojas en un archivo Excel"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for hoja, df in dfs_procesados.items():
                        df.to_excel(writer, sheet_name=hoja, index=False)
                
                st.download_button(
                    label="📥 Descargar Excel completo",
                    data=output.getvalue(),
                    file_name="unidades_clasificadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
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
            'Fecha Ingreso': ['2025-09-15', '2025-11-21', 'ARM112318', '2025-11-19'],
            'Fecha Factura': ['2025-09-14', '2025-11-22', '2025-09-17', 'TEXTO_INVALIDO']
        }
        ejemplo_df = pd.DataFrame(ejemplo_data)
        st.dataframe(ejemplo_df)
        st.caption("""
        El archivo debe contener columnas con nombres similares para:
        - Ciudad (puede llamarse 'ciudad', 'unidad', 'unidad operativa')
        - Fecha ingreso (puede llamarse 'fecha ingreso', 'fechaing', 'f_ingreso')
        - Fecha factura (puede llamarse 'fecha factura', 'fechafac', 'f_factura')
        
        Los valores no válidos en fechas serán marcados como "fecha no válida"
        """)
