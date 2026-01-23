import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas - Proporción de Equivalencia y Validación")
st.markdown("Carga un archivo CSV con registros de llamadas para calcular la proporción de equivalencia y validación de demanda")

# Constante para el cálculo de validación
CONSTANTE_VALIDACION = 14.08

# Lista de códigos a filtrar en el campo "To"
CODIGOS_FILTRAR = [
    '(0220)', '(0221)', '(0222)', '(0303)', '(0305)', '(0308)', '(0316)', '(0320)', 
    '(0323)', '(0324)', '(0327)', '(0331)', '(0404)', '(0407)', '(0410)', '(0412)', 
    '(0413)', '(0414)', '(0415)', '(0417)', '(2001)', '(2002)', '(2003)', '(2004)', 
    '(2005)', '(2006)', '(2007)', '(2008)', '(2009)', '(2010)', '(2011)', '(2012)', 
    '(2013)', '(2014)', '(2015)', '(2016)', '(2017)', '(2018)', '(2019)', '(2021)', 
    '(2022)', '(2023)', '(2024)', '(2025)', '(2026)', '(2028)', '(2029)', '(2030)', 
    '(2032)', '(2034)', '(2035)', '(8000)', '(8002)', '(8003)', '(8051)', '(8052)', 
    '(8062)', '(8063)', '(8064)', '(8071)', '(8072)', '(8079)', '(8080)', '(8068)', 
    '(8004)', '(8070)', '(8006)', '(7999)', '(8069)', '(8055)', '(8050)'
]

# Definición de códigos por empresa para la columna empresa_inbound
CODIGOS_CCB = [
    '(2028)', '(2029)', '(2030)', '(2035)', '(8051)', '(8052)', '(8006)', '(8055)', '(8050)'
]

CODIGOS_ODO = [
    '(2001)', '(2002)', '(2003)', '(2004)', '(2005)', '(2006)', '(2007)', '(2008)', 
    '(2009)', '(2010)', '(2011)', '(2012)', '(2013)', '(2014)', '(2015)', '(2016)', 
    '(2017)', '(2018)', '(2019)', '(2021)', '(2022)', '(2023)', '(2024)', '(2025)', 
    '(2026)', '(2032)', '(2034)', '(8000)', '(8002)', '(8003)', '(8071)', '(8079)', 
    '(8068)', '(8004)', '(7999)'
]

CODIGOS_UDC = [
    '(0220)', '(0221)', '(0222)', '(0303)', '(0305)', '(0308)', '(0316)', '(0320)', 
    '(0323)', '(0324)', '(0327)', '(0331)', '(0404)', '(0407)', '(0410)', '(0412)', 
    '(0413)', '(0414)', '(0415)', '(0417)', '(8062)', '(8063)', '(8064)', '(8072)', 
    '(8080)', '(8070)', '(8069)'
]

# Sidebar para cargar el archivo
with st.sidebar:
    st.header("Cargar Datos")
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    
    if uploaded_file is not None:
        st.success("Archivo cargado exitosamente")
        
        # Mostrar información del archivo
        file_details = {
            "Nombre": uploaded_file.name,
            "Tamaño": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.write("**Detalles del archivo:**")
        st.json(file_details)
    
    st.markdown("---")
    st.markdown("**Filtros y Clasificaciones:**")
    st.markdown(f"""
    **Filtro aplicado:**
    - Total códigos filtrados: {len(CODIGOS_FILTRAR)}
    
    **Clasificación por empresa:**
    - CCB: {len(CODIGOS_CCB)} códigos
    - ODO: {len(CODIGOS_ODO)} códigos  
    - UDC: {len(CODIGOS_UDC)} códigos
    """)
    
    st.markdown("---")
    st.markdown("**Cálculos realizados:**")
    st.markdown(f"""
    1. **Proporción de Equivalencia**: (1 / Conteo_Similares) / Días_Mismo_Tipo
    2. **Validador Demanda/Personas/Hora**: Proporción / {CONSTANTE_VALIDACION}
    3. **Rol Inbound**: Call Center / Externo
    4. **Empresa Inbound**: CCB / ODO / UDC / Externo
    """)
    
    st.markdown("---")
    st.markdown("**Instrucciones:**")
    st.markdown("""
    1. Sube un archivo CSV con los campos requeridos
    2. La app filtrará por los códigos especificados
    3. Calculará todas las métricas y clasificaciones
    4. Analiza los resultados
    5. Descarga los datos procesados
    """)

# Función para traducir días de la semana
def traducir_dia(dia_ingles):
    dias_traduccion = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    return dias_traduccion.get(dia_ingles, dia_ingles)

# Función para determinar rol_inbound
def determinar_rol_inbound(valor_to, codigos_filtro):
    """
    Determina el rol inbound basado en si el código está en la lista filtrada
    """
    valor_str = str(valor_to)
    # Verificar si contiene algún código del filtro
    for codigo in codigos_filtro:
        if codigo in valor_str:
            return "Call center"
    return "Externo"

# Función para determinar empresa_inbound
def determinar_empresa_inbound(valor_to, codigos_ccb, codigos_odo, codigos_udc):
    """
    Determina la empresa inbound basado en los códigos específicos
    """
    valor_str = str(valor_to)
    
    # Verificar CCB
    for codigo in codigos_ccb:
        if codigo in valor_str:
            return "CCB"
    
    # Verificar ODO
    for codigo in codigos_odo:
        if codigo in valor_str:
            return "ODO"
    
    # Verificar UDC
    for codigo in codigos_udc:
        if codigo in valor_str:
            return "UDC"
    
    return "Externo"

# Función para filtrar datos por códigos en el campo "To"
def filtrar_por_codigos(df):
    """
    Filtra el DataFrame para incluir solo registros cuyo campo 'To' contenga
    alguno de los códigos especificados
    """
    df_filtrado = df.copy()
    
    # Verificar que exista la columna 'To'
    if 'To' not in df_filtrado.columns:
        st.error("El archivo no contiene la columna 'To' necesaria para el filtrado.")
        return None
    
    # Crear máscara para filtrar
    mascara = df_filtrado['To'].astype(str).apply(
        lambda x: any(codigo in str(x) for codigo in CODIGOS_FILTRAR)
    )
    
    # Aplicar filtro
    df_filtrado = df_filtrado[mascara].copy()
    
    # Mostrar estadísticas del filtrado
    total_registros = len(df)
    registros_filtrados = len(df_filtrado)
    porcentaje_filtrado = (registros_filtrados / total_registros * 100) if total_registros > 0 else 0
    
    st.info(f"""
    **Estadísticas de filtrado:**
    - Total de registros originales: {total_registros:,}
    - Registros después de filtrar: {registros_filtrados:,}
    - Porcentaje incluido: {porcentaje_filtrado:.1f}%
    - Códigos buscados: {len(CODIGOS_FILTRAR)}
    """)
    
    return df_filtrado

# Función para procesar los datos y calcular proporción de equivalencia
def procesar_datos_con_proporcion(df):
    """
    Procesa el DataFrame y calcula la proporción de equivalencia según la especificación
    """
    # Hacer una copia para no modificar el original
    df_procesado = df.copy()
    
    try:
        # Verificar columnas necesarias
        columnas_requeridas = ['Call Time', 'From', 'To']
        for col in columnas_requeridas:
            if col not in df_procesado.columns:
                st.error(f"El archivo no contiene la columna '{col}' necesaria para el procesamiento.")
                return None
        
        # Convertir Call Time a datetime si es necesario
        try:
            df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'])
        except:
            df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'], errors='coerce')
        
        # 1. Nueva columna con la hora del registro
        df_procesado['Hora_Registro'] = df_procesado['Call Time'].dt.time
        df_procesado['Hora_Numerica'] = df_procesado['Call Time'].dt.hour
        
        # 2. Nueva columna con la fecha en formato DD/MM/YYYY
        df_procesado['Fecha_Creacion'] = df_procesado['Call Time'].dt.strftime('%d/%m/%Y')
        df_procesado['Fecha_Datetime'] = df_procesado['Call Time'].dt.date
        
        # 3. Nueva columna con el día de la semana
        df_procesado['Dia_Semana'] = df_procesado['Call Time'].dt.day_name()
        df_procesado['Dia_Semana'] = df_procesado['Dia_Semana'].apply(traducir_dia)
        
        # 4. Calcular cantidad de días de ese tipo en el dataset
        def calcular_dias_tipo_en_dataset_real(dia_semana, df_completo):
            """
            Calcula cuántos días únicos de este tipo hay realmente en el dataset
            """
            # Obtener fechas únicas del dataset
            fechas_unicas = df_completo['Fecha_Datetime'].unique()
            
            # Contar cuántas de esas fechas son del día de la semana especificado
            contador = 0
            for fecha in fechas_unicas:
                if pd.notna(fecha):
                    # Obtener nombre del día en español
                    dia_num = fecha.weekday()
                    dia_nombre_dataset = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 
                                         'Viernes', 'Sábado', 'Domingo'][dia_num]
                    if dia_nombre_dataset == dia_semana:
                        contador += 1
            
            return contador if contador > 0 else 1  # Evitar división por 0
        
        # Crear diccionario con días por tipo en el dataset real
        dias_por_tipo = {}
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        for dia in dias_semana:
            dias_por_tipo[dia] = calcular_dias_tipo_en_dataset_real(dia, df_procesado)
        
        # Añadir columna con días del mismo tipo en el dataset real
        df_procesado['Dias_Mismo_Tipo_Dataset'] = df_procesado['Dia_Semana'].map(dias_por_tipo)
        
        # Mostrar información de días por tipo
        st.write("**Días por tipo en el dataset:**")
        dias_info = pd.DataFrame(list(dias_por_tipo.items()), columns=['Día de la semana', 'Cantidad en dataset'])
        st.dataframe(dias_info, use_container_width=True)
        
        # 5. PASO 1: Calcular conteo de registros que coinciden en:
        # - Mismo "To"
        # - Misma fecha de creación
        # - Mismo día de la semana
        # - Misma hora del día
        # - Mismo "From"
        
        # Crear una clave de agrupación que combine todos estos campos
        df_procesado['Clave_Agrupacion'] = (
            df_procesado['To'].astype(str) + '_' +
            df_procesado['Fecha_Creacion'].astype(str) + '_' +
            df_procesado['Dia_Semana'].astype(str) + '_' +
            df_procesado['Hora_Numerica'].astype(str) + '_' +
            df_procesado['From'].astype(str)
        )
        
        # Calcular el tamaño de cada grupo
        conteo_grupos = df_procesado.groupby('Clave_Agrupacion').size()
        
        # Asignar el conteo a cada registro
        df_procesado['Conteo_Registros_Similares'] = df_procesado['Clave_Agrupacion'].map(conteo_grupos)
        
        # 6. PASO 2: Calcular primera división (1 / conteo de registros similares)
        df_procesado['Paso_1_Division'] = 1 / df_procesado['Conteo_Registros_Similares']
        
        # 7. PASO 3: Dividir entre la cantidad de días del mismo tipo en el dataset
        df_procesado['Proporcion_Equivalencia'] = (
            df_procesado['Paso_1_Division'] / df_procesado['Dias_Mismo_Tipo_Dataset']
        )
        
        # 8. PASO 4: Calcular validador_demanda_personas_hora
        df_procesado['validador_demanda_personas_hora'] = (
            df_procesado['Proporcion_Equivalencia'] / CONSTANTE_VALIDACION
        )
        
        # 9. PASO 5: Calcular rol_inbound
        df_procesado['rol_inbound'] = df_procesado['To'].apply(
            lambda x: determinar_rol_inbound(x, CODIGOS_FILTRAR)
        )
        
        # 10. PASO 6: Calcular empresa_inbound
        df_procesado['empresa_inbound'] = df_procesado['To'].apply(
            lambda x: determinar_empresa_inbound(x, CODIGOS_CCB, CODIGOS_ODO, CODIGOS_UDC)
        )
        
        # Redondear a 6 decimales para mayor precisión
        df_procesado['Proporcion_Equivalencia'] = df_procesado['Proporcion_Equivalencia'].round(6)
        df_procesado['Paso_1_Division'] = df_procesado['Paso_1_Division'].round(6)
        df_procesado['validador_demanda_personas_hora'] = df_procesado['validador_demanda_personas_hora'].round(6)
        
        # Eliminar columnas temporales
        columnas_a_eliminar = ['Clave_Agrupacion']
        df_procesado = df_procesado.drop(columns=columnas_a_eliminar)
        
        st.success("✅ Datos procesados y cálculos realizados exitosamente")
        
        # Mostrar distribución de las nuevas columnas
        st.write("**📊 Distribución de las nuevas columnas:**")
        
        col_dist1, col_dist2 = st.columns(2)
        
        with col_dist1:
            st.write("**Distribución de rol_inbound:**")
            distribucion_rol = df_procesado['rol_inbound'].value_counts()
            st.dataframe(distribucion_rol, use_container_width=True)
            st.bar_chart(distribucion_rol)
        
        with col_dist2:
            st.write("**Distribución de empresa_inbound:**")
            distribucion_empresa = df_procesado['empresa_inbound'].value_counts()
            st.dataframe(distribucion_empresa, use_container_width=True)
            st.bar_chart(distribucion_empresa)
        
        # Mostrar ejemplo de cálculo
        with st.expander("📝 Ver ejemplo de cálculo completo con clasificaciones"):
            st.markdown(f"""
            **Fórmulas de cálculo y clasificaciones:**
            
            1. **Proporción de Equivalencia:**
            ```
            Proporción = (1 / Conteo_Registros_Similares) / Dias_Mismo_Tipo_Dataset
            ```
            
            2. **Validador Demanda/Personas/Hora:**
            ```
            Validador = Proporción_Equivalencia / {CONSTANTE_VALIDACION}
            ```
            
            3. **Rol Inbound:**
            ```
            Si "To" contiene algún código de la lista filtrada → "Call center"
            Si no → "Externo"
            ```
            
            4. **Empresa Inbound:**
            ```
            Si "To" contiene códigos CCB → "CCB"
            Si "To" contiene códigos ODO → "ODO"  
            Si "To" contiene códigos UDC → "UDC"
            Si no → "Externo"
            ```
            """)
            
            # Mostrar un ejemplo real del dataset
            if len(df_procesado) > 0:
                ejemplo = df_procesado.iloc[0]
                st.write("**Ejemplo real del primer registro:**")
                st.write(f"- To: {ejemplo['To']}")
                st.write(f"- Fecha: {ejemplo['Fecha_Creacion']}")
                st.write(f"- Día de semana: {ejemplo['Dia_Semana']}")
                st.write(f"- Hora: {ejemplo['Hora_Numerica']}:00")
                st.write(f"- From: {ejemplo['From']}")
                st.write(f"- Registros similares: {ejemplo['Conteo_Registros_Similares']}")
                st.write(f"- Días del mismo tipo en dataset: {ejemplo['Dias_Mismo_Tipo_Dataset']}")
                st.write(f"- Paso 1 (1/{ejemplo['Conteo_Registros_Similares']}): {ejemplo['Paso_1_Division']:.6f}")
                st.write(f"- **Proporción final: {ejemplo['Proporcion_Equivalencia']:.6f}**")
                st.write(f"- **Validador demanda/personas/hora: {ejemplo['validador_demanda_personas_hora']:.6f}**")
                st.write(f"- **Rol Inbound: {ejemplo['rol_inbound']}**")
                st.write(f"- **Empresa Inbound: {ejemplo['empresa_inbound']}**")
        
        # Mostrar resumen de los cálculos
        st.write("**📊 Resumen de los cálculos:**")
        
        # Métricas para Proporción de Equivalencia
        st.write("##### Proporción de Equivalencia:")
        col_prop1, col_prop2, col_prop3, col_prop4 = st.columns(4)
        
        with col_prop1:
            st.metric("Mínima", f"{df_procesado['Proporcion_Equivalencia'].min():.6f}")
        
        with col_prop2:
            st.metric("Máxima", f"{df_procesado['Proporcion_Equivalencia'].max():.6f}")
        
        with col_prop3:
            st.metric("Promedio", f"{df_procesado['Proporcion_Equivalencia'].mean():.6f}")
        
        with col_prop4:
            suma_proporciones = df_procesado['Proporcion_Equivalencia'].sum()
            st.metric("Suma total", f"{suma_proporciones:.6f}")
        
        # Métricas para Validador Demanda
        st.write("##### Validador Demanda/Personas/Hora:")
        col_val1, col_val2, col_val3, col_val4 = st.columns(4)
        
        with col_val1:
            st.metric("Mínima", f"{df_procesado['validador_demanda_personas_hora'].min():.6f}")
        
        with col_val2:
            st.metric("Máxima", f"{df_procesado['validador_demanda_personas_hora'].max():.6f}")
        
        with col_val3:
            st.metric("Promedio", f"{df_procesado['validador_demanda_personas_hora'].mean():.6f}")
        
        with col_val4:
            suma_validador = df_procesado['validador_demanda_personas_hora'].sum()
            st.metric("Suma total", f"{suma_validador:.6f}")
        
        # Análisis por rol_inbound
        st.write("**👥 Análisis por Rol Inbound:**")
        analisis_rol = df_procesado.groupby('rol_inbound').agg({
            'Proporcion_Equivalencia': ['count', 'sum', 'mean'],
            'validador_demanda_personas_hora': ['sum', 'mean']
        }).round(6)
        
        analisis_rol.columns = ['Cantidad', 'Suma Proporción', 'Promedio Proporción', 
                               'Suma Validador', 'Promedio Validador']
        
        st.dataframe(analisis_rol, use_container_width=True)
        
        # Análisis por empresa_inbound
        st.write("**🏢 Análisis por Empresa Inbound:**")
        analisis_empresa = df_procesado.groupby('empresa_inbound').agg({
            'Proporcion_Equivalencia': ['count', 'sum', 'mean'],
            'validador_demanda_personas_hora': ['sum', 'mean'],
            'rol_inbound': lambda x: x.value_counts().to_dict()
        }).round(6)
        
        analisis_empresa.columns = ['Cantidad', 'Suma Proporción', 'Promedio Proporción', 
                                   'Suma Validador', 'Promedio Validador', 'Distribución Rol']
        
        st.dataframe(analisis_empresa, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None
    
    return df_procesado

# Función principal
def main():
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2, tab3 = st.tabs(["📋 Datos Originales", "⚙️ Filtrar y Procesar", "📊 Resultados y Exportar"])
            
            with tab1:
                st.subheader("Datos Originales (Sin Filtrar)")
                st.write(f"**Forma del dataset:** {df.shape[0]} filas × {df.shape[1]} columnas")
                
                # Mostrar información de las columnas
                with st.expander("Ver información de columnas"):
                    st.write("**Columnas disponibles:**")
                    for col in df.columns:
                        st.write(f"- {col}")
                
                # Mostrar vista previa de datos
                st.write("**Vista previa de datos (primeras 100 filas):**")
                st.dataframe(df.head(100), use_container_width=True)
                
                # Mostrar distribución del campo 'To' si existe
                if 'To' in df.columns:
                    with st.expander("Ver distribución del campo 'To'"):
                        st.write("**Valores únicos en 'To' (primeros 20):**")
                        valores_to = df['To'].unique()[:20]
                        for valor in valores_to:
                            st.write(f"- {valor}")
            
            with tab2:
                st.subheader("Filtrado y Cálculos")
                
                # Primero aplicar el filtro
                st.write("### Paso 1: Aplicar Filtro por Códigos")
                st.info(f"Se filtrarán los registros cuyo campo 'To' contenga alguno de los {len(CODIGOS_FILTRAR)} códigos especificados")
                
                if st.button("Aplicar Filtro y Calcular", type="primary"):
                    with st.spinner("Aplicando filtro y realizando cálculos..."):
                        # Aplicar filtro
                        df_filtrado = filtrar_por_codigos(df)
                        
                        if df_filtrado is not None and len(df_filtrado) > 0:
                            # Procesar datos y calcular proporción
                            df_procesado = procesar_datos_con_proporcion(df_filtrado)
                            
                            if df_procesado is not None:
                                # Guardar en session state
                                st.session_state['df_procesado'] = df_procesado
                                st.success(f"✅ Proceso completado. {len(df_procesado)} registros procesados.")
                                
                                # Mostrar vista previa de datos procesados
                                st.write("### Vista previa de datos procesados:")
                                
                                # Seleccionar columnas importantes para mostrar
                                columnas_a_mostrar = [
                                    'Call Time', 'From', 'To', 'Fecha_Creacion', 
                                    'Dia_Semana', 'Hora_Registro', 'Conteo_Registros_Similares',
                                    'Dias_Mismo_Tipo_Dataset', 'Proporcion_Equivalencia',
                                    'validador_demanda_personas_hora', 'rol_inbound', 'empresa_inbound'
                                ]
                                
                                # Filtrar solo las columnas que existen
                                columnas_existentes = [col for col in columnas_a_mostrar if col in df_procesado.columns]
                                
                                st.dataframe(df_procesado[columnas_existentes].head(20), use_container_width=True)
                            else:
                                st.error("Error al procesar los datos filtrados.")
                        else:
                            st.error("No se encontraron registros que coincidan con los códigos especificados o error en el filtrado.")
            
            with tab3:
                st.subheader("Resultados y Exportación")
                
                if 'df_procesado' in st.session_state:
                    df_procesado = st.session_state['df_procesado']
                    
                    # Mostrar estadísticas generales
                    st.write("### 📈 Estadísticas Generales")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total registros", len(df_procesado))
                    
                    with col2:
                        # Fecha mínima y máxima
                        if 'Call Time' in df_procesado.columns and pd.api.types.is_datetime64_any_dtype(df_procesado['Call Time']):
                            fecha_min = df_procesado['Call Time'].min().strftime('%d/%m/%Y')
                            fecha_max = df_procesado['Call Time'].max().strftime('%d/%m/%Y')
                            st.metric("Rango de fechas", f"{fecha_min} a {fecha_max}")
                    
                    with col3:
                        # Días únicos en el dataset
                        if 'Fecha_Datetime' in df_procesado.columns:
                            dias_unicos = len(df_procesado['Fecha_Datetime'].unique())
                            st.metric("Días únicos", dias_unicos)
                    
                    with col4:
                        # Suma total de validadores
                        suma_validador = df_procesado['validador_demanda_personas_hora'].sum()
                        st.metric("Suma total validador", f"{suma_validador:.6f}")
                    
                    # Análisis de clasificaciones
                    st.write("### 🏷️ Análisis de Clasificaciones")
                    
                    col_clas1, col_clas2 = st.columns(2)
                    
                    with col_clas1:
                        st.write("**Distribución por Rol Inbound:**")
                        distrib_rol = df_procesado['rol_inbound'].value_counts()
                        st.dataframe(distrib_rol, use_container_width=True)
                        st.bar_chart(distrib_rol)
                    
                    with col_clas2:
                        st.write("**Distribución por Empresa Inbound:**")
                        distrib_empresa = df_procesado['empresa_inbound'].value_counts()
                        st.dataframe(distrib_empresa, use_container_width=True)
                        st.bar_chart(distrib_empresa)
                    
                    # Análisis cruzado rol vs empresa
                    st.write("### 🔄 Análisis Cruzado: Rol vs Empresa")
                    
                    cruzado = pd.crosstab(df_procesado['rol_inbound'], 
                                         df_procesado['empresa_inbound'],
                                         margins=True)
                    st.dataframe(cruzado, use_container_width=True)
                    
                    # Análisis por día de la semana con clasificaciones
                    st.write("### 📅 Análisis por Día de la Semana (con clasificaciones)")
                    
                    if 'Dia_Semana' in df_procesado.columns:
                        # Análisis por día y empresa
                        analisis_dia_empresa = df_procesado.groupby(['Dia_Semana', 'empresa_inbound']).agg({
                            'validador_demanda_personas_hora': ['count', 'sum']
                        }).round(6)
                        
                        analisis_dia_empresa.columns = ['Cantidad', 'Suma Validador']
                        st.dataframe(analisis_dia_empresa, use_container_width=True)
                        
                        # Gráfico de suma de validador por día y empresa
                        pivot_table = df_procesado.pivot_table(
                            index='Dia_Semana',
                            columns='empresa_inbound',
                            values='validador_demanda_personas_hora',
                            aggfunc='sum',
                            fill_value=0
                        ).round(6)
                        
                        # Ordenar días
                        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                        pivot_table = pivot_table.reindex(orden_dias)
                        
                        st.write("**Suma de Validador por Día y Empresa:**")
                        st.bar_chart(pivot_table)
                    
                    # Análisis por hora del día con clasificaciones
                    st.write("### 🕐 Análisis por Hora del Día (con clasificaciones)")
                    
                    if 'Hora_Numerica' in df_procesado.columns:
                        # Análisis por hora y rol
                        analisis_hora_rol = df_procesado.groupby(['Hora_Numerica', 'rol_inbound']).agg({
                            'validador_demanda_personas_hora': ['count', 'sum']
                        }).round(6)
                        
                        analisis_hora_rol.columns = ['Cantidad', 'Suma Validador']
                        analisis_hora_rol = analisis_hora_rol.sort_index()
                        
                        st.dataframe(analisis_hora_rol, use_container_width=True)
                    
                    # Exportación de datos
                    st.write("### 💾 Exportar Datos Procesados")
                    
                    col_exp1, col_exp2 = st.columns(2)
                    
                    with col_exp1:
                        # Exportar a CSV completo
                        csv = df_procesado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar CSV completo",
                            data=csv,
                            file_name="datos_con_calculos_clasificaciones.csv",
                            mime="text/csv",
                            type="primary"
                        )
                        
                        # Exportar solo columnas seleccionadas
                        st.write("**Exportar columnas seleccionadas:**")
                        
                        # Seleccionar columnas para exportación simplificada
                        columnas_exportacion = st.multiselect(
                            "Selecciona las columnas a exportar:",
                            options=df_procesado.columns.tolist(),
                            default=[
                                'Call Time', 'From', 'To', 'Fecha_Creacion', 
                                'Dia_Semana', 'Hora_Registro', 
                                'Proporcion_Equivalencia', 'validador_demanda_personas_hora',
                                'rol_inbound', 'empresa_inbound'
                            ]
                        )
                        
                        if columnas_exportacion:
                            df_exportar = df_procesado[columnas_exportacion]
                            csv_selectivo = df_exportar.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Descargar columnas seleccionadas",
                                data=csv_selectivo,
                                file_name="datos_seleccionados.csv",
                                mime="text/csv"
                            )
                    
                    with col_exp2:
                        # Exportar a Excel
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            # Hoja 1: Datos completos
                            df_procesado.to_excel(writer, sheet_name='Datos_Completos', index=False)
                            
                            # Hoja 2: Resumen por empresa
                            resumen_empresa = df_procesado.groupby('empresa_inbound').agg({
                                'Proporcion_Equivalencia': ['count', 'sum', 'mean', 'min', 'max'],
                                'validador_demanda_personas_hora': ['sum', 'mean']
                            }).round(6)
                            resumen_empresa.to_excel(writer, sheet_name='Resumen_Por_Empresa')
                            
                            # Hoja 3: Resumen por rol
                            resumen_rol = df_procesado.groupby('rol_inbound').agg({
                                'Proporcion_Equivalencia': ['count', 'sum', 'mean', 'min', 'max'],
                                'validador_demanda_personas_hora': ['sum', 'mean']
                            }).round(6)
                            resumen_rol.to_excel(writer, sheet_name='Resumen_Por_Rol')
                            
                            # Hoja 4: Tabla cruzada rol vs empresa
                            cruzado_df = pd.crosstab(df_procesado['rol_inbound'], 
                                                    df_procesado['empresa_inbound'],
                                                    margins=True)
                            cruzado_df.to_excel(writer, sheet_name='Cruzado_Rol_Empresa')
                            
                            # Hoja 5: Estadísticas generales
                            stats_df = pd.DataFrame({
                                'Métrica': [
                                    'Total Registros', 
                                    'Suma Proporción Equivalencia',
                                    'Suma Validador Demanda',
                                    'Proporción Mínima',
                                    'Proporción Máxima',
                                    'Validador Mínimo',
                                    'Validador Máximo',
                                    'Constante de Validación',
                                    'Registros Call Center',
                                    'Registros Externos',
                                    'Empresa CCB',
                                    'Empresa ODO',
                                    'Empresa UDC',
                                    'Empresa Externa'
                                ],
                                'Valor': [
                                    len(df_procesado),
                                    df_procesado['Proporcion_Equivalencia'].sum(),
                                    df_procesado['validador_demanda_personas_hora'].sum(),
                                    df_procesado['Proporcion_Equivalencia'].min(),
                                    df_procesado['Proporcion_Equivalencia'].max(),
                                    df_procesado['validador_demanda_personas_hora'].min(),
                                    df_procesado['validador_demanda_personas_hora'].max(),
                                    CONSTANTE_VALIDACION,
                                    len(df_procesado[df_procesado['rol_inbound'] == 'Call center']),
                                    len(df_procesado[df_procesado['rol_inbound'] == 'Externo']),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'CCB']),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'ODO']),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'UDC']),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'Externo'])
                                ]
                            })
                            stats_df.to_excel(writer, sheet_name='Estadisticas_Generales', index=False)
                        
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Descargar como Excel",
                            data=buffer,
                            file_name="datos_procesados_completos.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # Mostrar vista previa de exportación
                        st.write("**Vista previa de datos a exportar:**")
                        st.dataframe(df_procesado.head(10), use_container_width=True)
                
                else:
                    st.info("Primero procesa los datos en la pestaña 'Filtrar y Procesar'")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo sea un CSV válido con los campos requeridos.")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")
        
        # Mostrar ejemplo de estructura esperada
        with st.expander("Ver estructura esperada del CSV y clasificaciones"):
            st.write(f"""
            ## Cálculos y Clasificaciones Realizadas
            
            **1. Proporción de Equivalencia:**
            ```
            Proporción = (1 / Conteo_Registros_Similares) / Dias_Mismo_Tipo_Dataset
            ```
            
            **2. Validador Demanda/Personas/Hora:**
            ```
            Validador = Proporción_Equivalencia / {CONSTANTE_VALIDACION}
            ```
            
            **3. Rol Inbound:**
            - **Call center**: Registros cuyo campo "To" contiene alguno de los {len(CODIGOS_FILTRAR)} códigos filtrados
            - **Externo**: Registros cuyo campo "To" NO contiene ninguno de los códigos filtrados
            
            **4. Empresa Inbound:**
            - **CCB**: {len(CODIGOS_CCB)} códigos específicos (2028, 2029, 2030, 2035, 8051, 8052, 8006, 8055, 8050)
            - **ODO**: {len(CODIGOS_ODO)} códigos específicos (serie 2000 y otros específicos)
            - **UDC**: {len(CODIGOS_UDC)} códigos específicos (series 0200, 0300, 0400 y otros específicos)
            - **Externo**: No coincide con ningún código de las categorías anteriores
            
            **Ejemplo de clasificación:**
            
            Registro con To = "(2028) Oficina Principal":
            1. Contiene "(2028)" → está en lista filtrada → **rol_inbound = "Call center"**
            2. "(2028)" está en lista CCB → **empresa_inbound = "CCB"**
            
            Registro con To = "Cliente Externo 555":
            1. No contiene códigos filtrados → **rol_inbound = "Externo"**
            2. No contiene códigos de empresa → **empresa_inbound = "Externo"**
            """)

if __name__ == "__main__":
    main()
