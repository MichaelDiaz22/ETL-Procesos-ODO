import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# Configuración de la página
st.set_page_config(
    page_title="Analizador de Unidades Operativas",
    page_icon="📊",
    layout="wide"
)

# Título de la aplicación
st.title("📊 Analizador de Unidades Operativas")
st.markdown("---")

# Inicializar session state
if 'archivo_cargado' not in st.session_state:
    st.session_state.archivo_cargado = None
if 'datos_hojas' not in st.session_state:
    st.session_state.datos_hojas = {}
if 'filtros_aplicados' not in st.session_state:
    st.session_state.filtros_aplicados = {}

def limpiar_valor(valor):
    """Limpia y convierte valores para comparación"""
    if pd.isna(valor):
        return ""
    return str(valor).strip().upper()

def mostrar_resumen_hoja(df, nombre_hoja):
    """Muestra un resumen de la hoja con los primeros 10 registros"""
    st.markdown(f"### 📄 Hoja: {nombre_hoja}")
    
    # Métricas básicas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de registros", len(df))
    with col2:
        columnas_relevantes = [col for col in df.columns if any(palabra in col.lower() for palabra in ['unidad', 'ciudad', 'fecha'])]
        st.metric("Columnas relevantes", len(columnas_relevantes))
    with col3:
        st.metric("Columnas totales", len(df.columns))
    
    # Mostrar información de columnas
    with st.expander("📋 Ver estructura de columnas"):
        col_info = pd.DataFrame({
            'Columna': df.columns,
            'Tipo de dato': df.dtypes.astype(str),
            'Valores nulos': df.isnull().sum(),
            '% Nulos': (df.isnull().sum() / len(df) * 100).round(2)
        })
        st.dataframe(col_info, use_container_width=True)
    
    # Mostrar primeros 10 registros
    st.markdown("#### 🔍 Primeros 10 registros")
    st.dataframe(df.head(10), use_container_width=True)
    
    # Estadísticas adicionales
    with st.expander("📊 Estadísticas adicionales"):
        st.markdown("**Resumen de tipos de datos:**")
        tipo_datos = df.dtypes.value_counts()
        st.dataframe(tipo_datos, use_container_width=True)

def aplicar_filtro_unidad_operativa(df, columna_unidad, valor_filtro):
    """Aplica filtro por unidad operativa"""
    if not valor_filtro or valor_filtro == "Todos":
        return df
    
    # Limpiar y comparar valores
    mascara = df[columna_unidad].apply(lambda x: limpiar_valor(x) == limpiar_valor(valor_filtro))
    return df[mascara]

def aplicar_filtro_unidad_funcional(df, columna_funcional, valor_filtro):
    """Aplica filtro por unidad funcional de ingreso"""
    if not valor_filtro or valor_filtro == "Todos":
        return df
    
    # Limpiar y comparar valores
    mascara = df[columna_funcional].apply(lambda x: limpiar_valor(x) == limpiar_valor(valor_filtro))
    return df[mascara]

def identificar_columnas_filtro(df, tipo_filtro):
    """Identifica las columnas disponibles para filtrar"""
    columnas_posibles = []
    
    if tipo_filtro == "unidad_operativa":
        # Palabras clave para unidad operativa
        keywords = ['unidad', 'operativa', 'ciudad', 'ciiu', 'sede']
    else:  # unidad_funcional
        # Palabras clave para unidad funcional de ingreso
        keywords = ['funcional', 'ingreso', 'area', 'departamento', 'seccion']
    
    for col in df.columns:
        col_lower = col.lower()
        for keyword in keywords:
            if keyword in col_lower:
                columnas_posibles.append(col)
                break
    
    return columnas_posibles

def procesar_hoja_con_filtros(df, nombre_hoja):
    """Procesa una hoja y aplica los filtros correspondientes según el tipo de hoja"""
    
    # Determinar qué filtros aplicar según el nombre de la hoja
    aplicar_filtro_uo = nombre_hoja in ['EVENTO', 'PGP']
    aplicar_filtro_uf = nombre_hoja in ['PDTE EVENTO', 'PDTE PGP']
    
    # Crear pestañas para los diferentes filtros si aplica
    if aplicar_filtro_uo or aplicar_filtro_uf:
        tabs = []
        tab_titles = ["📊 Datos completos"]
        
        if aplicar_filtro_uo:
            tab_titles.append("🔍 Filtrar por Unidad Operativa")
        if aplicar_filtro_uf:
            tab_titles.append("🎯 Filtrar por Unidad Funcional de Ingreso")
        
        tabs = st.tabs(tab_titles)
        
        # Pestaña de datos completos
        with tabs[0]:
            mostrar_resumen_hoja(df, nombre_hoja)
        
        # Pestaña de filtro por unidad operativa
        if aplicar_filtro_uo:
            with tabs[1] if len(tabs) > 1 else tabs[0]:
                st.markdown(f"#### Filtro por Unidad Operativa - {nombre_hoja}")
                
                # Identificar columnas de unidad operativa
                columnas_uo = identificar_columnas_filtro(df, "unidad_operativa")
                
                if columnas_uo:
                    columna_seleccionada = st.selectbox(
                        "Selecciona la columna de Unidad Operativa:",
                        columnas_uo,
                        key=f"uo_col_{nombre_hoja}"
                    )
                    
                    # Obtener valores únicos para el filtro
                    valores_unicos = ['Todos'] + sorted(df[columna_seleccionada].dropna().unique().tolist())
                    valor_filtro = st.selectbox(
                        "Selecciona la Unidad Operativa:",
                        valores_unicos,
                        key=f"uo_filtro_{nombre_hoja}"
                    )
                    
                    # Aplicar filtro
                    df_filtrado = aplicar_filtro_unidad_operativa(df, columna_seleccionada, valor_filtro)
                    
                    st.markdown(f"**Registros después del filtro:** {len(df_filtrado)} de {len(df)}")
                    
                    if len(df_filtrado) > 0:
                        st.markdown("**Datos filtrados (primeros 10 registros):**")
                        st.dataframe(df_filtrado.head(10), use_container_width=True)
                    else:
                        st.warning("No se encontraron registros con el filtro seleccionado")
                else:
                    st.warning("No se encontraron columnas que puedan corresponder a Unidad Operativa")
        
        # Pestaña de filtro por unidad funcional de ingreso
        if aplicar_filtro_uf:
            tab_index = 2 if (aplicar_filtro_uo and len(tabs) > 2) else (1 if not aplicar_filtro_uo else 1)
            with tabs[tab_index]:
                st.markdown(f"#### Filtro por Unidad Funcional de Ingreso - {nombre_hoja}")
                
                # Identificar columnas de unidad funcional
                columnas_uf = identificar_columnas_filtro(df, "unidad_funcional")
                
                if columnas_uf:
                    columna_seleccionada = st.selectbox(
                        "Selecciona la columna de Unidad Funcional de Ingreso:",
                        columnas_uf,
                        key=f"uf_col_{nombre_hoja}"
                    )
                    
                    # Obtener valores únicos para el filtro
                    valores_unicos = ['Todos'] + sorted(df[columna_seleccionada].dropna().unique().tolist())
                    valor_filtro = st.selectbox(
                        "Selecciona la Unidad Funcional:",
                        valores_unicos,
                        key=f"uf_filtro_{nombre_hoja}"
                    )
                    
                    # Aplicar filtro
                    df_filtrado = aplicar_filtro_unidad_funcional(df, columna_seleccionada, valor_filtro)
                    
                    st.markdown(f"**Registros después del filtro:** {len(df_filtrado)} de {len(df)}")
                    
                    if len(df_filtrado) > 0:
                        st.markdown("**Datos filtrados (primeros 10 registros):**")
                        st.dataframe(df_filtrado.head(10), use_container_width=True)
                    else:
                        st.warning("No se encontraron registros con el filtro seleccionado")
                else:
                    st.warning("No se encontraron columnas que puedan corresponder a Unidad Funcional de Ingreso")
    
    else:
        # Para hojas que no requieren filtros especiales
        mostrar_resumen_hoja(df, nombre_hoja)

# Sidebar con información
with st.sidebar:
    st.header("📋 Instrucciones")
    st.markdown("""
    **Funcionalidades:**
    1. Carga un archivo Excel con múltiples hojas
    2. Visualiza un resumen de cada hoja con los primeros 10 registros
    3. Aplica filtros específicos según el tipo de hoja:
       - **EVENTO y PGP**: Filtro por Unidad Operativa
       - **PDTE EVENTO y PDTE PGP**: Filtro por Unidad Funcional de Ingreso
    
    **Requisitos del archivo:**
    - Formato: Excel (.xlsx, .xls)
    - Puede contener cualquier nombre de hoja
    - Cada hoja será procesada individualmente
    """)
    
    st.markdown("---")
    st.markdown("**💡 Consejos:**")
    st.markdown("""
    - Los filtros son dinámicos y se aplican en tiempo real
    - Puedes identificar las columnas correctas para filtrar
    - Los valores de filtro se obtienen automáticamente de los datos
    """)

# Área principal para cargar archivo
st.header("📁 Carga de Archivo")

archivo_subido = st.file_uploader(
    "Selecciona un archivo Excel",
    type=['xlsx', 'xls'],
    help="Carga un archivo Excel para analizar sus hojas",
    key="file_uploader_main"
)

if archivo_subido is not None:
    # Verificar si es un archivo nuevo
    if st.session_state.archivo_cargado != archivo_subido.name:
        st.session_state.archivo_cargado = archivo_subido.name
        st.session_state.datos_hojas = {}
        
        try:
            # Leer el archivo Excel
            with st.spinner("Cargando archivo Excel..."):
                excel_file = pd.ExcelFile(archivo_subido)
                hojas = excel_file.sheet_names
            
            st.success(f"✅ Archivo cargado correctamente. Se encontraron {len(hojas)} hojas: {', '.join(hojas)}")
            
            # Procesar cada hoja
            with st.spinner("Procesando hojas..."):
                for hoja in hojas:
                    df = pd.read_excel(archivo_subido, sheet_name=hoja)
                    st.session_state.datos_hojas[hoja] = df
            
            st.success("✅ Todas las hojas han sido procesadas correctamente")
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Error al cargar el archivo: {str(e)}")
            st.session_state.archivo_cargado = None
            st.session_state.datos_hojas = {}
    
    # Mostrar resultados si hay datos cargados
    if st.session_state.datos_hojas:
        st.markdown("---")
        st.header("📊 Análisis de Hojas")
        
        # Crear pestañas para cada hoja
        hojas_nombres = list(st.session_state.datos_hojas.keys())
        tabs = st.tabs(hojas_nombres)
        
        # Procesar cada hoja en su pestaña correspondiente
        for tab, nombre_hoja in zip(tabs, hojas_nombres):
            with tab:
                df = st.session_state.datos_hojas[nombre_hoja]
                procesar_hoja_con_filtros(df, nombre_hoja)
                
                # Separador visual
                st.markdown("---")
        
        # Opción para descargar resultados
        st.markdown("---")
        st.header("💾 Exportar Resultados")
        
        # Botón para exportar todas las hojas originales
        if st.button("📥 Exportar todas las hojas a Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for nombre_hoja, df in st.session_state.datos_hojas.items():
                    # Limitar nombre de la hoja a 31 caracteres (límite de Excel)
                    nombre_sheet = nombre_hoja[:31]
                    df.to_excel(writer, sheet_name=nombre_sheet, index=False)
            
            st.download_button(
                label="📥 Descargar archivo Excel",
                data=output.getvalue(),
                file_name=f"datos_exportados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    # Mensaje cuando no hay archivo cargado
    st.info("👆 Por favor, carga un archivo Excel para comenzar el análisis")
    
    # Mostrar ejemplo
    with st.expander("📋 Ver ejemplo de estructura esperada"):
        st.markdown("""
        **El archivo Excel puede contener múltiples hojas con cualquier nombre.**
        
        **Para aprovechar los filtros, las hojas deberían llamarse:**
        - `EVENTO` o `PGP` → Filtro por Unidad Operativa
        - `PDTE EVENTO` o `PDTE PGP` → Filtro por Unidad Funcional de Ingreso
        
        **Ejemplo de columnas que se pueden filtrar:**
        
        *Para Unidad Operativa:*
        - Unidad
        - Ciudad
        - Unidad Operativa
        - Sede
        
        *Para Unidad Funcional de Ingreso:*
        - Unidad Funcional
        - Área de Ingreso
        - Departamento
        - Sección
        """)
        
        # Datos de ejemplo
        ejemplo_uo = pd.DataFrame({
            'Fecha': ['2025-01-01', '2025-01-02', '2025-01-03'],
            'Unidad Operativa': ['Manizales', 'Armenia', 'Pereira'],
            'Valor': [100, 200, 150]
        })
        
        st.markdown("**Ejemplo con Unidad Operativa:**")
        st.dataframe(ejemplo_uo, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("💡 **Nota:** Los filtros son específicos para cada tipo de hoja y te permiten explorar los datos según tus necesidades.")
