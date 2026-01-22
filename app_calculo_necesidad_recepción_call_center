import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para procesar y analizar los datos.")

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
    st.markdown("**Instrucciones:**")
    st.markdown("""
    1. Sube un archivo CSV con los campos requeridos
    2. La app procesará automáticamente los datos
    3. Descarga el resultado procesado
    """)

# Función para procesar los datos
def procesar_datos(df):
    """
    Procesa el DataFrame según las especificaciones requeridas
    """
    # Hacer una copia para no modificar el original
    df_procesado = df.copy()
    
    try:
        # Convertir Call Time a datetime si es necesario
        if 'Call Time' in df_procesado.columns:
            # Intentar diferentes formatos de fecha
            try:
                df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'])
            except:
                # Si falla, intentar parsear manualmente
                df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'], errors='coerce')
            
            # 1. Nueva columna con la hora del registro
            df_procesado['Hora_Registro'] = df_procesado['Call Time'].dt.time
            
            # 2. Nueva columna con la fecha en formato DD/MM/YYYY
            df_procesado['Fecha_Creacion'] = df_procesado['Call Time'].dt.strftime('%d/%m/%Y')
            
            # 3. Nueva columna con el día de la semana y cantidad de días de ese tipo en el mes
            def obtener_info_dia(fecha):
                if pd.isna(fecha):
                    return 'Desconocido', 0
                
                # Obtener nombre del día de la semana
                dia_semana = fecha.strftime('%A')
                
                # Traducir al español si es necesario
                dias_ingles_espanol = {
                    'Monday': 'Lunes',
                    'Tuesday': 'Martes',
                    'Wednesday': 'Miércoles',
                    'Thursday': 'Jueves',
                    'Friday': 'Viernes',
                    'Saturday': 'Sábado',
                    'Sunday': 'Domingo'
                }
                dia_semana_es = dias_ingles_espanol.get(dia_semana, dia_semana)
                
                # Calcular cuántos días de ese tipo hay en el mes
                año = fecha.year
                mes = fecha.month
                # Obtener el número del día de la semana (0=Lunes, 6=Domingo)
                dia_num = fecha.weekday()
                
                # Contar cuántos días de ese tipo hay en el mes
                cal = calendar.monthcalendar(año, mes)
                contador_dias = 0
                for semana in cal:
                    if semana[dia_num] != 0:
                        contador_dias += 1
                
                return f"{dia_semana_es} ({contador_dias} días en el mes)"
            
            df_procesado['Info_Dia_Semana'] = df_procesado['Call Time'].apply(obtener_info_dia)
            
            # 4. Calcular proporción de equivalencia
            def calcular_proporcion(grupo):
                """
                Calcula la proporción de equivalencia para cada grupo
                1 dividido entre el número de registros similares
                """
                total_registros = len(grupo)
                return 1 / total_registros if total_registros > 0 else 0
            
            # Agrupar por fecha, destino y hora (redondeada a horas para agrupar mejor)
            if 'To' in df_procesado.columns:
                # Crear una columna para hora redondeada (solo hora, sin minutos)
                df_procesado['Hora_Redondeada'] = df_procesado['Call Time'].dt.floor('H').dt.time
                
                # Crear clave de agrupación
                df_procesado['Clave_Agrupacion'] = df_procesado['Fecha_Creacion'] + '_' + \
                                                  df_procesado['To'].astype(str) + '_' + \
                                                  df_procesado['Hora_Redondeada'].astype(str)
                
                # Calcular proporción de equivalencia
                conteo_grupos = df_procesado.groupby('Clave_Agrupacion').size()
                df_procesado['Proporcion_Equivalencia'] = df_procesado['Clave_Agrupacion'].map(
                    lambda x: 1 / conteo_grupos[x] if x in conteo_grupos.index else 0
                )
                
                # Eliminar columnas temporales
                df_procesado = df_procesado.drop(['Hora_Redondeada', 'Clave_Agrupacion'], axis=1)
            else:
                st.warning("La columna 'To' no existe en el archivo. No se puede calcular la proporción de equivalencia.")
                df_procesado['Proporcion_Equivalencia'] = np.nan
            
            st.success("✅ Datos procesados exitosamente")
            
        else:
            st.error("El archivo no contiene la columna 'Call Time' necesaria para el procesamiento.")
            return None
            
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None
    
    return df_procesado

# Función para mostrar estadísticas
def mostrar_estadisticas(df):
    """
    Muestra estadísticas básicas del DataFrame procesado
    """
    st.subheader("📈 Estadísticas del Dataset")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Registros", len(df))
    
    with col2:
        if 'Call Time' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Call Time']):
            fecha_min = df['Call Time'].min().strftime('%d/%m/%Y')
            st.metric("Fecha Inicial", fecha_min)
    
    with col3:
        if 'Call Time' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Call Time']):
            fecha_max = df['Call Time'].max().strftime('%d/%m/%Y')
            st.metric("Fecha Final", fecha_max)
    
    with col4:
        if 'To' in df.columns:
            destinos_unicos = df['To'].nunique()
            st.metric("Destinos Únicos", destinos_unicos)
    
    # Mostrar distribución por día de la semana si existe la columna
    if 'Info_Dia_Semana' in df.columns:
        st.subheader("📅 Distribución por Día de la Semana")
        
        # Extraer solo el nombre del día para el conteo
        df['Dia_Semana_Simple'] = df['Info_Dia_Semana'].str.split(' ').str[0]
        distribucion_dias = df['Dia_Semana_Simple'].value_counts().sort_index()
        
        # Reordenar según días de la semana
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        distribucion_dias = distribucion_dias.reindex([d for d in orden_dias if d in distribucion_dias.index])
        
        st.bar_chart(distribucion_dias)

# Función principal
def main():
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Datos Originales", "⚙️ Procesar Datos", "📊 Resultados", "💾 Exportar"])
            
            with tab1:
                st.subheader("Datos Originales")
                st.write(f"**Forma del dataset:** {df.shape[0]} filas × {df.shape[1]} columnas")
                st.dataframe(df.head(100), use_container_width=True)
                
                # Mostrar información de las columnas
                with st.expander("Ver información de columnas"):
                    st.write("**Columnas disponibles:**")
                    for col in df.columns:
                        st.write(f"- {col}")
            
            with tab2:
                st.subheader("Procesamiento de Datos")
                st.write("""
                **Operaciones que se realizarán:**
                1. Extraer hora del registro del campo 'Call Time'
                2. Crear fecha en formato DD/MM/YYYY
                3. Identificar día de la semana y cantidad de días de ese tipo en el mes
                4. Calcular proporción de equivalencia basada en fecha, destino y hora
                """)
                
                if st.button("Procesar Datos", type="primary"):
                    with st.spinner("Procesando datos..."):
                        df_procesado = procesar_datos(df)
                        
                        if df_procesado is not None:
                            # Guardar en session state para usar en otras pestañas
                            st.session_state['df_procesado'] = df_procesado
                            st.success("Procesamiento completado!")
            
            with tab3:
                st.subheader("Resultados del Procesamiento")
                
                if 'df_procesado' in st.session_state:
                    df_procesado = st.session_state['df_procesado']
                    
                    # Mostrar estadísticas
                    mostrar_estadisticas(df_procesado)
                    
                    # Mostrar datos procesados
                    st.subheader("Datos Procesados")
                    st.write(f"**Forma del dataset procesado:** {df_procesado.shape[0]} filas × {df_procesado.shape[1]} columnas")
                    
                    # Mostrar solo las nuevas columnas y algunas originales
                    columnas_interes = ['Call Time', 'Hora_Registro', 'Fecha_Creacion', 
                                       'Info_Dia_Semana', 'To', 'Proporcion_Equivalencia',
                                       'Status', 'Sentiment', 'Summary']
                    
                    # Filtrar columnas que existen en el dataframe
                    columnas_a_mostrar = [col for col in columnas_interes if col in df_procesado.columns]
                    
                    st.dataframe(df_procesado[columnas_a_mostrar].head(100), use_container_width=True)
                    
                    # Mostrar resumen de proporciones
                    if 'Proporcion_Equivalencia' in df_procesado.columns:
                        st.subheader("Resumen de Proporciones de Equivalencia")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Estadísticas:**")
                            st.write(f"- Mínima: {df_procesado['Proporcion_Equivalencia'].min():.4f}")
                            st.write(f"- Máxima: {df_procesado['Proporcion_Equivalencia'].max():.4f}")
                            st.write(f"- Promedio: {df_procesado['Proporcion_Equivalencia'].mean():.4f}")
                        
                        with col2:
                            st.write("**Distribución:**")
                            st.bar_chart(df_procesado['Proporcion_Equivalencia'].value_counts().sort_index())
                else:
                    st.info("Primero procesa los datos en la pestaña 'Procesar Datos'")
            
            with tab4:
                st.subheader("Exportar Datos Procesados")
                
                if 'df_procesado' in st.session_state:
                    df_procesado = st.session_state['df_procesado']
                    
                    # Opciones de exportación
                    st.write("**Opciones de exportación:**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Exportar a CSV
                        csv = df_procesado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar como CSV",
                            data=csv,
                            file_name="datos_procesados.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    
                    with col2:
                        # Exportar a Excel
                        @st.cache_data
                        def convert_to_excel(df):
                            output = pd.ExcelWriter('datos_procesados.xlsx', engine='openpyxl')
                            df.to_excel(output, index=False)
                            output.close()
                            with open('datos_procesados.xlsx', 'rb') as f:
                                data = f.read()
                            return data
                        
                        excel_data = convert_to_excel(df_procesado)
                        st.download_button(
                            label="📥 Descargar como Excel",
                            data=excel_data,
                            file_name="datos_procesados.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # Vista previa del archivo a exportar
                    with st.expander("Vista previa de datos a exportar"):
                        st.dataframe(df_procesado.head(20), use_container_width=True)
                else:
                    st.info("No hay datos procesados para exportar. Primero procesa los datos en la pestaña 'Procesar Datos'")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo sea un CSV válido con los campos requeridos.")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")
        
        # Mostrar ejemplo de estructura esperada
        with st.expander("Ver estructura esperada del CSV"):
            st.write("""
            El archivo CSV debe contener al menos las siguientes columnas:
            
            - **Call Time**: Fecha y hora de la llamada
            - **Call ID**: Identificador único de la llamada
            - **From**: Número o identificador de origen
            - **To**: Número o identificador de destino
            - **Direction**: Dirección de la llamada
            - **Status**: Estado de la llamada
            - **Ringing**: Tiempo de timbre
            - **Talking**: Tiempo de conversación
            - **Cost**: Costo de la llamada
            - **Call Activity Details**: Detalles de la actividad
            - **Sentiment**: Sentimiento detectado
            - **Summary**: Resumen de la llamada
            - **Transcription**: Transcripción de la llamada
            
            **Nota:** Los nombres de las columnas pueden variar ligeramente, pero al menos se requiere 'Call Time' y 'To'.
            """)

if __name__ == "__main__":
    main()
