import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas - Proporción de Equivalencia")
st.markdown("Carga un archivo CSV con registros de llamadas para calcular la proporción de equivalencia")

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
    st.markdown("**Filtros aplicados:**")
    st.markdown("""
    Solo se analizarán registros cuyo campo 'To' contenga alguno de estos códigos:
    - (0220), (0221), (0222), ...
    - Total: 74 códigos específicos
    """)
    
    st.markdown("---")
    st.markdown("**Instrucciones:**")
    st.markdown("""
    1. Sube un archivo CSV con los campos requeridos
    2. La app filtrará por los códigos especificados
    3. Calculará la proporción de equivalencia
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
    Procesa el DataFrame y calcula la proporción de equivalencia según la nueva especificación
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
        def calcular_dias_tipo_en_dataset(fecha, dia_semana, df_completo):
            """
            Calcula cuántos días del mismo tipo (mismo día de semana) hay en el dataset
            para el mes y año de la fecha dada
            """
            if pd.isna(fecha):
                return 0
            
            # Obtener año y mes de la fecha
            año = fecha.year
            mes = fecha.month
            
            # Obtener el número del día de la semana (0=Lunes, 6=Domingo)
            dias_numeros = {
                'Lunes': 0, 'Martes': 1, 'Miércoles': 2, 'Jueves': 3,
                'Viernes': 4, 'Sábado': 5, 'Domingo': 6
            }
            dia_num = dias_numeros.get(dia_semana, 0)
            
            # Contar cuántos días de ese tipo hay en el mes
            cal = calendar.monthcalendar(año, mes)
            contador_dias = 0
            for semana in cal:
                if semana[dia_num] != 0:
                    contador_dias += 1
            
            return contador_dias
        
        # Aplicar la función para calcular días del mismo tipo en el mes
        df_procesado['Dias_Mismo_Tipo_Mes'] = df_procesado.apply(
            lambda x: calcular_dias_tipo_en_dataset(x['Call Time'], x['Dia_Semana'], df_procesado), 
            axis=1
        )
        
        # 5. Calcular cantidad de días de ese tipo en el DATASET (no solo en el mes teórico)
        # Esto es importante porque el dataset puede no cubrir todo el mes
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
        
        # 6. PASO 1: Calcular conteo de registros que coinciden en:
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
        
        # 7. PASO 2: Calcular primera división (1 / conteo de registros similares)
        df_procesado['Paso_1_Division'] = 1 / df_procesado['Conteo_Registros_Similares']
        
        # 8. PASO 3: Dividir entre la cantidad de días del mismo tipo en el dataset
        df_procesado['Proporcion_Equivalencia'] = (
            df_procesado['Paso_1_Division'] / df_procesado['Dias_Mismo_Tipo_Dataset']
        )
        
        # Redondear a 6 decimales para mayor precisión
        df_procesado['Proporcion_Equivalencia'] = df_procesado['Proporcion_Equivalencia'].round(6)
        df_procesado['Paso_1_Division'] = df_procesado['Paso_1_Division'].round(6)
        
        # Eliminar columnas temporales
        columnas_a_eliminar = ['Clave_Agrupacion']
        df_procesado = df_procesado.drop(columns=columnas_a_eliminar)
        
        st.success("✅ Datos procesados y proporción de equivalencia calculada exitosamente")
        
        # Mostrar ejemplo de cálculo
        with st.expander("📝 Ver ejemplo de cálculo de proporción de equivalencia"):
            st.markdown("""
            **Fórmula de cálculo:**
            
            ```
            Proporción de Equivalencia = (1 / Conteo_Registros_Similares) / Dias_Mismo_Tipo_Dataset
            ```
            
            **Donde:**
            - `Conteo_Registros_Similares`: Número de registros con el mismo "To", fecha, día de semana, hora y "From"
            - `Dias_Mismo_Tipo_Dataset`: Cantidad de días del mismo tipo (ej: Lunes) en el dataset
            
            **Ejemplo práctico:**
            1. Si hay 5 registros con las mismas características (mismo To, fecha, día, hora, From)
               - Paso 1: 1 / 5 = 0.2
            2. Si hay 4 días del mismo tipo (ej: Lunes) en el dataset
               - Paso 2: 0.2 / 4 = 0.05
            3. **Proporción final: 0.05**
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
        
        # Mostrar resumen de la proporción
        st.write("**📊 Resumen de la proporción de equivalencia:**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Proporción mínima", f"{df_procesado['Proporcion_Equivalencia'].min():.6f}")
        
        with col2:
            st.metric("Proporción máxima", f"{df_procesado['Proporcion_Equivalencia'].max():.6f}")
        
        with col3:
            st.metric("Proporción promedio", f"{df_procesado['Proporcion_Equivalencia'].mean():.6f}")
        
        with col4:
            total_registros = len(df_procesado)
            suma_proporciones = df_procesado['Proporcion_Equivalencia'].sum()
            st.metric("Suma total", f"{suma_proporciones:.6f}")
        
        # Mostrar distribución de conteos de registros similares
        st.write("**Distribución de registros por grupo:**")
        distribucion = df_procesado['Conteo_Registros_Similares'].value_counts().sort_index()
        
        col_dist1, col_dist2 = st.columns(2)
        
        with col_dist1:
            st.write("**Conteo de grupos:**")
            st.dataframe(distribucion.head(10), use_container_width=True)
        
        with col_dist2:
            st.write("**Gráfico de distribución:**")
            st.bar_chart(distribucion.head(10))
        
        # Mostrar estadísticas de días por tipo
        st.write("**Estadísticas de días por tipo:**")
        dias_stats = df_procesado.groupby('Dia_Semana').agg({
            'Dias_Mismo_Tipo_Dataset': 'first',
            'Proporcion_Equivalencia': ['mean', 'sum', 'count']
        }).round(4)
        
        st.dataframe(dias_stats, use_container_width=True)
        
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
                st.subheader("Filtrado y Cálculo de Proporción de Equivalencia")
                
                # Primero aplicar el filtro
                st.write("### Paso 1: Aplicar Filtro por Códigos")
                st.info(f"Se filtrarán los registros cuyo campo 'To' contenga alguno de los {len(CODIGOS_FILTRAR)} códigos especificados")
                
                if st.button("Aplicar Filtro y Calcular Proporción", type="primary"):
                    with st.spinner("Aplicando filtro y calculando proporción de equivalencia..."):
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
                                    'Dias_Mismo_Tipo_Dataset', 'Proporcion_Equivalencia'
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
                        # Suma total de proporciones
                        suma_total = df_procesado['Proporcion_Equivalencia'].sum()
                        st.metric("Suma total proporciones", f"{suma_total:.6f}")
                    
                    # Análisis por día de la semana
                    st.write("### 📅 Análisis por Día de la Semana")
                    
                    if 'Dia_Semana' in df_procesado.columns:
                        analisis_dias = df_procesado.groupby('Dia_Semana').agg({
                            'Proporcion_Equivalencia': ['count', 'sum', 'mean', 'min', 'max'],
                            'Conteo_Registros_Similares': 'mean',
                            'Dias_Mismo_Tipo_Dataset': 'first'
                        }).round(6)
                        
                        # Renombrar columnas para mejor visualización
                        analisis_dias.columns = [
                            'Cantidad Registros', 'Suma Proporciones', 'Promedio Proporción',
                            'Mínima Proporción', 'Máxima Proporción', 
                            'Promedio Registros Similares', 'Días Mismo Tipo Dataset'
                        ]
                        
                        # Ordenar por días de la semana
                        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                        analisis_dias = analisis_dias.reindex(orden_dias)
                        
                        st.dataframe(analisis_dias, use_container_width=True)
                        
                        # Gráfico de suma de proporciones por día
                        st.write("**Suma de proporciones por día de la semana:**")
                        st.bar_chart(analisis_dias['Suma Proporciones'])
                    
                    # Análisis por hora del día
                    st.write("### 🕐 Análisis por Hora del Día")
                    
                    if 'Hora_Numerica' in df_procesado.columns:
                        analisis_horas = df_procesado.groupby('Hora_Numerica').agg({
                            'Proporcion_Equivalencia': ['count', 'sum', 'mean'],
                        }).round(6)
                        
                        analisis_horas.columns = ['Cantidad Registros', 'Suma Proporciones', 'Promedio Proporción']
                        analisis_horas = analisis_horas.sort_index()
                        
                        col_hora1, col_hora2 = st.columns(2)
                        
                        with col_hora1:
                            st.dataframe(analisis_horas, use_container_width=True)
                        
                        with col_hora2:
                            st.write("**Suma de proporciones por hora:**")
                            st.line_chart(analisis_horas['Suma Proporciones'])
                    
                    # Exportación de datos
                    st.write("### 💾 Exportar Datos Procesados")
                    
                    col_exp1, col_exp2 = st.columns(2)
                    
                    with col_exp1:
                        # Exportar a CSV
                        csv = df_procesado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar como CSV",
                            data=csv,
                            file_name="datos_con_proporcion_equivalencia.csv",
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
                                'Dia_Semana', 'Hora_Registro', 'Proporcion_Equivalencia'
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
                            
                            # Hoja 2: Resumen por día
                            if 'Dia_Semana' in df_procesado.columns:
                                resumen_dias = df_procesado.groupby('Dia_Semana').agg({
                                    'Proporcion_Equivalencia': ['count', 'sum', 'mean', 'min', 'max']
                                }).round(6)
                                resumen_dias.to_excel(writer, sheet_name='Resumen_Por_Dia')
                            
                            # Hoja 3: Resumen por hora
                            if 'Hora_Numerica' in df_procesado.columns:
                                resumen_horas = df_procesado.groupby('Hora_Numerica').agg({
                                    'Proporcion_Equivalencia': ['count', 'sum', 'mean']
                                }).round(6)
                                resumen_horas.to_excel(writer, sheet_name='Resumen_Por_Hora')
                        
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
        with st.expander("Ver estructura esperada del CSV"):
            st.write("""
            ## Cálculo de Proporción de Equivalencia
            
            **Nueva especificación del cálculo:**
            
            Para cada registro, la proporción de equivalencia se calcula como:
            
            ```
            Proporción = (1 / Conteo_Registros_Similares) / Dias_Mismo_Tipo_Dataset
            ```
            
            **Donde:**
            
            1. **Conteo_Registros_Similares**: 
               - Número de registros que tienen el MISMO:
                 - Valor en "To"
                 - Fecha de creación (DD/MM/YYYY)
                 - Día de la semana (Lunes, Martes, etc.)
                 - Hora del día
                 - Valor en "From"
            
            2. **Dias_Mismo_Tipo_Dataset**:
               - Cantidad de días del MISMO tipo (mismo día de la semana) que existen en el dataset
            
            **Ejemplo paso a paso:**
            
            1. **Registro A** tiene:
               - To: "(0220)"
               - Fecha: "15/01/2026"
               - Día: "Miércoles"
               - Hora: "14:00"
               - From: "ClienteX"
            
            2. Si hay 3 registros en total con estas mismas características
               - Paso 1: 1 / 3 = 0.333333
            
            3. Si en el dataset hay 4 días que son Miércoles
               - Paso 2: 0.333333 / 4 = 0.083333
            
            4. **Proporción final para Registro A: 0.083333**
            
            **Interpretación:**
            - Valor más alto = Menos registros similares / Más peso relativo
            - Valor más bajo = Más registros similares / Menos peso relativo
            - La suma de todas las proporciones indica el "peso total" del dataset
            """)

if __name__ == "__main__":
    main()
