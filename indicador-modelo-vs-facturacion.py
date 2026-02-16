import streamlit as st
import pandas as pd
from datetime import datetime
import io

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

def clasificar_unidad(row, ciudad, fecha_ingreso, fecha_factura):
    """
    Clasifica una unidad según la ciudad y las fechas de ingreso y factura
    """
    # Convertir a datetime si es necesario
    if pd.notna(fecha_ingreso):
        fecha_ingreso = pd.to_datetime(fecha_ingreso)
    if pd.notna(fecha_factura):
        fecha_factura = pd.to_datetime(fecha_factura)
    
    # Determinar fecha de corte según ciudad
    fecha_corte = FECHA_CORTE_MANIZALES if ciudad.upper() == 'MANIZALES' else FECHA_CORTE_ARMENIA
    
    # Caso 1: Manizales con fechas inferiores al corte
    if ciudad.upper() == 'MANIZALES':
        if pd.notna(fecha_ingreso) and pd.notna(fecha_factura):
            if fecha_ingreso < fecha_corte and fecha_factura < fecha_corte:
                return "no incluido en el modelo"
            elif fecha_ingreso >= fecha_corte and fecha_factura >= fecha_corte:
                return "incluido en el modelo"
            elif fecha_ingreso > fecha_corte and fecha_factura < fecha_corte:
                return "no incluido en el modelo"
    
    # Caso 2: Armenia con fechas inferiores al corte
    elif ciudad.upper() == 'ARMENIA':
        if pd.notna(fecha_ingreso) and pd.notna(fecha_factura):
            if fecha_ingreso < fecha_corte and fecha_factura < fecha_corte:
                return "no incluido en el modelo"
            elif fecha_ingreso >= fecha_corte and fecha_factura >= fecha_corte:
                return "incluido en el modelo"
            elif fecha_ingreso > fecha_corte and fecha_factura < fecha_corte:
                return "no incluido en el modelo"
    
    # Si no se cumplen las condiciones o faltan datos
    return "pendiente de clasificar"

def procesar_hoja(df, nombre_hoja):
    """
    Procesa cada hoja del Excel agregando la columna de clasificación
    """
    df_procesado = df.copy()
    
    # Buscar columnas que puedan contener la información de ciudad
    columnas_ciudad = [col for col in df.columns if 'ciudad' in col.lower() or 'unidad' in col.lower()]
    
    if not columnas_ciudad:
        st.warning(f"⚠️ No se encontró columna de ciudad en la hoja {nombre_hoja}")
        return df_procesado
    
    # Buscar columnas de fechas
    columnas_fecha_ingreso = [col for col in df.columns if 'ingreso' in col.lower()]
    columnas_fecha_factura = [col for col in df.columns if 'factura' in col.lower()]
    
    if not columnas_fecha_ingreso or not columnas_fecha_factura:
        st.warning(f"⚠️ No se encontraron columnas de fecha en la hoja {nombre_hoja}")
        return df_procesado
    
    # Aplicar clasificación
    clasificaciones = []
    for idx, row in df_procesado.iterrows():
        ciudad = str(row[columnas_ciudad[0]]).strip() if pd.notna(row[columnas_ciudad[0]]) else ""
        clasificacion = clasificar_unidad(
            row, 
            ciudad,
            row[columnas_fecha_ingreso[0]] if pd.notna(row[columnas_fecha_ingreso[0]]) else None,
            row[columnas_fecha_factura[0]] if pd.notna(row[columnas_fecha_factura[0]]) else None
        )
        clasificaciones.append(clasificacion)
    
    df_procesado['Clasificación'] = clasificaciones
    return df_procesado

# Sidebar con información
with st.sidebar:
    st.header("📋 Información")
    st.markdown("""
    **Fechas de corte:**
    - 🏙️ **Manizales:** 16/09/2025
    - 🏙️ **Armenia:** 20/11/2025
    
    **Reglas de clasificación:**
    - Si fecha ingreso < corte Y fecha factura < corte → "no incluido"
    - Si fecha ingreso ≥ corte Y fecha factura ≥ corte → "incluido"
    - Si fecha ingreso > corte Y fecha factura < corte → "no incluido"
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
            
            # Barra de progreso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, hoja in enumerate(hojas_requeridas):
                status_text.text(f"Procesando hoja: {hoja}")
                
                # Leer la hoja
                df = pd.read_excel(archivo_subido, sheet_name=hoja)
                
                # Procesar la hoja
                df_procesado = procesar_hoja(df, hoja)
                dfs_procesados[hoja] = df_procesado
                
                # Actualizar barra de progreso
                progress_bar.progress((i + 1) / len(hojas_requeridas))
            
            status_text.text("¡Procesamiento completado!")
            
            # Mostrar resultados
            st.markdown("---")
            st.header("📊 Resultados")
            
            # Tabs para cada hoja
            tabs = st.tabs(hojas_requeridas)
            
            for tab, hoja in zip(tabs, hojas_requeridas):
                with tab:
                    df_actual = dfs_procesados[hoja]
                    
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total registros", len(df_actual))
                    with col2:
                        incluidos = len(df_actual[df_actual['Clasificación'] == 'incluido en el modelo'])
                        st.metric("Incluidos", incluidos)
                    with col3:
                        no_incluidos = len(df_actual[df_actual['Clasificación'] == 'no incluido en el modelo'])
                        st.metric("No incluidos", no_incluidos)
                    
                    # Mostrar DataFrame
                    st.dataframe(df_actual, use_container_width=True)
                    
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
            'Unidad': ['U001', 'U002', 'U003'],
            'Ciudad': ['MANIZALES', 'ARMENIA', 'MANIZALES'],
            'Fecha Ingreso': ['2025-09-15', '2025-11-21', '2025-09-17'],
            'Fecha Factura': ['2025-09-14', '2025-11-22', '2025-09-15']
        }
        ejemplo_df = pd.DataFrame(ejemplo_data)
        st.dataframe(ejemplo_df)
        st.caption("El archivo debe contener columnas con nombres similares para 'ciudad', 'fecha ingreso' y 'fecha factura'")
