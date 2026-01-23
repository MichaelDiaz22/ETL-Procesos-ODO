import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas - Análisis por Día y Hora")
st.markdown("Carga un archivo CSV con registros de llamadas para analizar patrones por día de la semana y hora")

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
    2. La app calculará promedios por día y hora
    3. Analiza los patrones de llamadas
    4. Descarga los resultados procesados
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
            df_procesado['Hora_Numerica'] = df_procesado['Call Time'].dt.hour
            
            # 2. Nueva columna con la fecha en formato DD/MM/YYYY
            df_procesado['Fecha_Creacion'] = df_procesado['Call Time'].dt.strftime('%d/%m/%Y')
            df_procesado['Fecha_Datetime'] = df_procesado['Call Time'].dt.date
            
            # 3. Nueva columna con el día de la semana
            df_procesado['Dia_Semana'] = df_procesado['Call Time'].dt.day_name()
            df_procesado['Dia_Semana'] = df_procesado['Dia_Semana'].apply(traducir_dia)
            
            # 4. Calcular cantidad de días de ese tipo en el mes
            def obtener_cantidad_dias_mes(fecha):
                if pd.isna(fecha):
                    return 0
                
                # Obtener el número del día de la semana (0=Lunes, 6=Domingo)
                dia_num = fecha.weekday()
                año = fecha.year
                mes = fecha.month
                
                # Contar cuántos días de ese tipo hay en el mes
                cal = calendar.monthcalendar(año, mes)
                contador_dias = 0
                for semana in cal:
                    if semana[dia_num] != 0:
                        contador_dias += 1
                
                return contador_dias
            
            df_procesado['Dias_Tipo_Mes'] = df_procesado['Call Time'].apply(obtener_cantidad_dias_mes)
            df_procesado['Info_Dia_Semana'] = df_procesado['Dia_Semana'] + ' (' + df_procesado['Dias_Tipo_Mes'].astype(str) + ' días en el mes)'
            
            st.success("✅ Datos básicos procesados exitosamente")
            
        else:
            st.error("El archivo no contiene la columna 'Call Time' necesaria para el procesamiento.")
            return None
            
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None
    
    return df_procesado

# Función para calcular promedios por día y hora
def calcular_promedios_llamadas(df):
    """
    Calcula los promedios de llamadas por día de la semana y hora
    """
    # Crear DataFrame para análisis
    df_analisis = df.copy()
    
    # Asegurarse de que tenemos las columnas necesarias
    if not all(col in df_analisis.columns for col in ['Call Time', 'Dia_Semana', 'Hora_Numerica']):
        st.error("No se pueden calcular promedios: faltan columnas necesarias")
        return None, None
    
    # Crear columna de fecha sin hora para contar por día
    df_analisis['Fecha'] = df_analisis['Call Time'].dt.date
    
    # 1. Calcular promedio de llamadas por día de la semana
    # Primero, contar llamadas por fecha y día de semana
    llamadas_por_fecha = df_analisis.groupby(['Fecha', 'Dia_Semana']).size().reset_index(name='Total_Llamadas')
    
    # Luego, calcular promedio por día de semana
    promedio_por_dia = llamadas_por_fecha.groupby('Dia_Semana')['Total_Llamadas'].mean().reset_index()
    promedio_por_dia = promedio_por_dia.rename(columns={'Total_Llamadas': 'Promedio_Llamadas_Dia'})
    promedio_por_dia['Promedio_Llamadas_Dia'] = promedio_por_dia['Promedio_Llamadas_Dia'].round(2)
    
    # Ordenar por días de la semana
    orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    promedio_por_dia['Dia_Semana'] = pd.Categorical(promedio_por_dia['Dia_Semana'], categories=orden_dias, ordered=True)
    promedio_por_dia = promedio_por_dia.sort_values('Dia_Semana')
    
    # 2. Calcular promedio de llamadas por día de semana y hora
    # Contar llamadas por fecha, día y hora
    df_analisis['Hora_Redondeada'] = df_analisis['Hora_Numerica']  # Usar hora completa
    
    llamadas_por_hora = df_analisis.groupby(['Fecha', 'Dia_Semana', 'Hora_Redondeada']).size().reset_index(name='Conteo')
    
    # Calcular promedio por día y hora
    promedio_por_dia_hora = llamadas_por_hora.groupby(['Dia_Semana', 'Hora_Redondeada'])['Conteo'].mean().reset_index()
    promedio_por_dia_hora = promedio_por_dia_hora.rename(columns={'Conteo': 'Promedio_Llamadas'})
    promedio_por_dia_hora['Promedio_Llamadas'] = promedio_por_dia_hora['Promedio_Llamadas'].round(2)
    
    # Ordenar
    promedio_por_dia_hora['Dia_Semana'] = pd.Categorical(promedio_por_dia_hora['Dia_Semana'], categories=orden_dias, ordered=True)
    promedio_por_dia_hora = promedio_por_dia_hora.sort_values(['Dia_Semana', 'Hora_Redondeada'])
    
    return promedio_por_dia, promedio_por_dia_hora

# Función para calcular proporción de equivalencia
def calcular_proporcion_equivalencia(df, promedio_por_dia_hora):
    """
    Calcula la proporción de equivalencia basada en los promedios por día y hora
    """
    df_con_proporcion = df.copy()
    
    # Crear clave de unión
    df_con_proporcion['Clave_Union'] = list(zip(df_con_proporcion['Dia_Semana'], df_con_proporcion['Hora_Numerica']))
    
    # Crear diccionario de promedios
    dict_promedios = {}
    for _, row in promedio_por_dia_hora.iterrows():
        clave = (row['Dia_Semana'], row['Hora_Redondeada'])
        dict_promedios[clave] = row['Promedio_Llamadas']
    
    # Asignar promedio a cada registro
    def obtener_promedio(dia, hora):
        clave = (dia, hora)
        return dict_promedios.get(clave, 0)
    
    df_con_proporcion['Promedio_Dia_Hora'] = df_con_proporcion.apply(
        lambda x: obtener_promedio(x['Dia_Semana'], x['Hora_Numerica']), axis=1
    )
    
    # Calcular proporción de equivalencia: 1 / promedio
    # Si el promedio es 0, asignar 0
    df_con_proporcion['Proporcion_Equivalencia'] = df_con_proporcion['Promedio_Dia_Hora'].apply(
        lambda x: 1 / x if x > 0 else 0
    )
    
    # Redondear a 4 decimales
    df_con_proporcion['Proporcion_Equivalencia'] = df_con_proporcion['Proporcion_Equivalencia'].round(4)
    
    # Eliminar columna temporal
    df_con_proporcion = df_con_proporcion.drop('Clave_Union', axis=1)
    
    return df_con_proporcion

# Función para crear visualizaciones con Streamlit nativo
def crear_visualizaciones(promedio_por_dia, promedio_por_dia_hora, df_procesado):
    """
    Crea visualizaciones usando solo Streamlit nativo
    """
    # Crear pestañas para diferentes visualizaciones
    tab1, tab2, tab3 = st.tabs(["📊 Promedios por Día", "🕐 Promedios por Día y Hora", "📋 Tabla de Calor"])
    
    with tab1:
        st.subheader("Promedio de Llamadas por Día de la Semana")
        
        # Crear gráfico de barras simple con Streamlit
        st.bar_chart(promedio_por_dia.set_index('Dia_Semana')['Promedio_Llamadas_Dia'])
        
        # Mostrar tabla de datos
        st.write("**Datos detallados:**")
        st.dataframe(promedio_por_dia, use_container_width=True)
        
        # Métricas clave
        st.write("**Métricas clave:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dia_max = promedio_por_dia.loc[promedio_por_dia['Promedio_Llamadas_Dia'].idxmax()]
            st.metric("Día más ocupado", dia_max['Dia_Semana'], f"{dia_max['Promedio_Llamadas_Dia']:.1f}")
        
        with col2:
            dia_min = promedio_por_dia.loc[promedio_por_dia['Promedio_Llamadas_Dia'].idxmin()]
            st.metric("Día menos ocupado", dia_min['Dia_Semana'], f"{dia_min['Promedio_Llamadas_Dia']:.1f}")
        
        with col3:
            promedio_total = promedio_por_dia['Promedio_Llamadas_Dia'].mean()
            st.metric("Promedio general", f"{promedio_total:.1f}", "llamadas/día")
    
    with tab2:
        st.subheader("Promedio de Llamadas por Día y Hora")
        
        # Crear tabla pivote para visualización
        tabla_pivote = promedio_por_dia_hora.pivot_table(
            index='Dia_Semana',
            columns='Hora_Redondeada',
            values='Promedio_Llamadas',
            fill_value=0
        ).round(2)
        
        # Ordenar días
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        tabla_pivote = tabla_pivote.reindex(orden_dias)
        
        # Ordenar horas
        tabla_pivote = tabla_pivote.sort_index(axis=1)
        
        # Mostrar tabla
        st.write("**Tabla de promedios:**")
        st.dataframe(tabla_pivote, use_container_width=True)
        
        # Encontrar hora pico por día
        st.write("**Horas pico por día:**")
        for dia in orden_dias:
            if dia in tabla_pivote.index:
                fila = tabla_pivote.loc[dia]
                hora_pico = fila.idxmax()
                valor_pico = fila.max()
                if valor_pico > 0:
                    st.write(f"- **{dia}**: {hora_pico}:00 hrs ({valor_pico:.1f} llamadas)")
    
    with tab3:
        st.subheader("Tabla de Calor - Promedios por Día y Hora")
        
        # Crear matriz para la tabla de calor
        matriz_promedios = promedio_por_dia_hora.pivot_table(
            index='Dia_Semana',
            columns='Hora_Redondeada',
            values='Promedio_Llamadas',
            fill_value=0
        )
        
        # Ordenar días
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        matriz_promedios = matriz_promedios.reindex(orden_dias)
        
        # Ordenar horas
        matriz_promedios = matriz_promedios.sort_index(axis=1)
        
        # Aplicar formato condicional
        def color_cells(val):
            if val == 0:
                color = '#f0f0f0'  # Gris claro para 0
            elif val < 1:
                color = '#ffebee'  # Rojo muy claro
            elif val < 5:
                color = '#ffcdd2'  # Rojo claro
            elif val < 10:
                color = '#ef9a9a'  # Rojo
            elif val < 20:
                color = '#e57373'  # Rojo medio
            elif val < 50:
                color = '#ef5350'  # Rojo oscuro
            else:
                color = '#d32f2f'  # Rojo muy oscuro
            return f'background-color: {color}'
        
        # Mostrar tabla con colores
        st.write("**Mapa de calor (colores indican volumen):**")
        styled_table = matriz_promedios.style.applymap(color_cells).format("{:.1f}")
        st.dataframe(styled_table, use_container_width=True)
        
        # Leyenda
        st.write("**Leyenda de colores:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div style="background-color: #ffebee; padding: 5px; border-radius: 3px;">&lt; 1 llamada</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div style="background-color: #ef9a9a; padding: 5px; border-radius: 3px;">1-5 llamadas</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div style="background-color: #e57373; padding: 5px; border-radius: 3px;">5-10 llamadas</div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div style="background-color: #d32f2f; padding: 5px; border-radius: 3px;">&gt; 20 llamadas</div>', unsafe_allow_html=True)

# Función para mostrar resumen ejecutivo
def mostrar_resumen_ejecutivo(df_procesado, promedio_por_dia, promedio_por_dia_hora):
    """
    Muestra un resumen ejecutivo del análisis
    """
    st.subheader("📋 Resumen Ejecutivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Día con más llamadas en promedio
        dia_max = promedio_por_dia.loc[promedio_por_dia['Promedio_Llamadas_Dia'].idxmax()]
        st.metric(
            label="Día con más llamadas",
            value=dia_max['Dia_Semana'],
            delta=f"{dia_max['Promedio_Llamadas_Dia']:.1f} llamadas/día"
        )
    
    with col2:
        # Hora pico promedio
        hora_max_row = promedio_por_dia_hora.loc[promedio_por_dia_hora['Promedio_Llamadas'].idxmax()]
        st.metric(
            label="Hora pico promedio",
            value=f"{int(hora_max_row['Hora_Redondeada'])}:00",
            delta=f"{hora_max_row['Promedio_Llamadas']:.1f} llamadas"
        )
    
    with col3:
        # Promedio total de llamadas por día
        promedio_total = promedio_por_dia['Promedio_Llamadas_Dia'].mean()
        st.metric(
            label="Promedio total/día",
            value=f"{promedio_total:.1f}",
            delta="llamadas"
        )
    
    with col4:
        # Rango horario con más actividad
        # Agrupar por horas (mañana, tarde, noche)
        def clasificar_hora(hora):
            if 6 <= hora < 12:
                return "Mañana (6-11)"
            elif 12 <= hora < 18:
                return "Tarde (12-17)"
            elif 18 <= hora < 24:
                return "Noche (18-23)"
            else:
                return "Madrugada (0-5)"
        
        df_temp = promedio_por_dia_hora.copy()
        df_temp['Periodo'] = df_temp['Hora_Redondeada'].apply(clasificar_hora)
        periodo_actividad = df_temp.groupby('Periodo')['Promedio_Llamadas'].sum().idxmax()
        
        st.metric(
            label="Periodo más activo",
            value=periodo_actividad,
            delta="Mayor volumen"
        )
    
    # Insights adicionales
    st.write("**📈 Insights clave:**")
    
    # Calcular variabilidad entre días
    variabilidad = promedio_por_dia['Promedio_Llamadas_Dia'].std() / promedio_por_dia['Promedio_Llamadas_Dia'].mean() * 100
    
    col_insight1, col_insight2 = st.columns(2)
    
    with col_insight1:
        st.info(f"**Variabilidad entre días:** {variabilidad:.1f}%")
        st.caption("Mide cuánto varía el volumen de llamadas entre diferentes días de la semana")
    
    with col_insight2:
        # Distribución por período del día
        horas_pico = promedio_por_dia_hora[promedio_por_dia_hora['Promedio_Llamadas'] > promedio_por_dia_hora['Promedio_Llamadas'].mean()]
        st.info(f"**Horas pico:** {len(horas_pico)} horas con arriba del promedio")
        st.caption("Horas donde el volumen de llamadas supera el promedio general")
        
    # Distribución de proporciones
    if 'Proporcion_Equivalencia' in df_procesado.columns:
        st.write("**📊 Distribución de Proporciones de Equivalencia:**")
        col_dist1, col_dist2, col_dist3 = st.columns(3)
        
        with col_dist1:
            st.metric(
                "Proporción mínima",
                f"{df_procesado['Proporcion_Equivalencia'].min():.4f}"
            )
        
        with col_dist2:
            st.metric(
                "Proporción máxima",
                f"{df_procesado['Proporcion_Equivalencia'].max():.4f}"
            )
        
        with col_dist3:
            st.metric(
                "Proporción promedio",
                f"{df_procesado['Proporcion_Equivalencia'].mean():.4f}"
            )

# Función principal
def main():
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Datos Originales", "⚙️ Procesar y Analizar", "📊 Resultados y Visualizaciones", "💾 Exportar"])
            
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
                st.subheader("Procesamiento y Análisis de Datos")
                
                if st.button("Procesar Datos y Calcular Promedios", type="primary"):
                    with st.spinner("Procesando datos y calculando promedios..."):
                        # Procesar datos básicos
                        df_procesado = procesar_datos(df)
                        
                        if df_procesado is not None:
                            # Calcular promedios
                            promedio_por_dia, promedio_por_dia_hora = calcular_promedios_llamadas(df_procesado)
                            
                            if promedio_por_dia is not None and promedio_por_dia_hora is not None:
                                # Calcular proporción de equivalencia
                                df_con_proporcion = calcular_proporcion_equivalencia(df_procesado, promedio_por_dia_hora)
                                
                                # Guardar en session state
                                st.session_state['df_procesado'] = df_procesado
                                st.session_state['df_con_proporcion'] = df_con_proporcion
                                st.session_state['promedio_por_dia'] = promedio_por_dia
                                st.session_state['promedio_por_dia_hora'] = promedio_por_dia_hora
                                
                                st.success("✅ Procesamiento completado!")
                                
                                # Mostrar resumen rápido
                                st.write("**Resumen de promedios calculados:**")
                                col_res1, col_res2 = st.columns(2)
                                
                                with col_res1:
                                    st.write("📅 **Por día de semana:**")
                                    st.dataframe(promedio_por_dia, use_container_width=True)
                                
                                with col_res2:
                                    st.write("🕐 **Por día y hora (ejemplo):**")
                                    st.dataframe(promedio_por_dia_hora.head(10), use_container_width=True)
                            else:
                                st.error("No se pudieron calcular los promedios")
            
            with tab3:
                st.subheader("Resultados y Visualizaciones")
                
                if all(key in st.session_state for key in ['df_con_proporcion', 'promedio_por_dia', 'promedio_por_dia_hora']):
                    df_con_proporcion = st.session_state['df_con_proporcion']
                    promedio_por_dia = st.session_state['promedio_por_dia']
                    promedio_por_dia_hora = st.session_state['promedio_por_dia_hora']
                    
                    # Mostrar resumen ejecutivo
                    mostrar_resumen_ejecutivo(df_con_proporcion, promedio_por_dia, promedio_por_dia_hora)
                    
                    # Mostrar visualizaciones
                    crear_visualizaciones(promedio_por_dia, promedio_por_dia_hora, df_con_proporcion)
                    
                    # Mostrar datos procesados con proporción
                    st.subheader("📋 Datos Procesados con Proporción de Equivalencia")
                    
                    columnas_interes = [
                        'Call Time', 'Fecha_Creacion', 'Dia_Semana', 'Hora_Registro',
                        'Promedio_Dia_Hora', 'Proporcion_Equivalencia', 'To', 'Status', 'Sentiment'
                    ]
                    
                    # Filtrar columnas que existen
                    columnas_a_mostrar = [col for col in columnas_interes if col in df_con_proporcion.columns]
                    
                    st.write(f"**Muestra de datos ({len(df_con_proporcion)} registros totales):**")
                    st.dataframe(df_con_proporcion[columnas_a_mostrar].head(50), use_container_width=True)
                    
                    # Explicación de la proporción
                    with st.expander("📝 ¿Cómo se calcula la proporción de equivalencia?"):
                        st.markdown("""
                        **Fórmula:** Proporción de Equivalencia = 1 / Promedio de Llamadas para ese Día y Hora
                        
                        **Interpretación:**
                        - **Valor alto (ej: 0.5):** Pocas llamadas en ese horario, cada llamada tiene mayor peso relativo
                        - **Valor bajo (ej: 0.01):** Muchas llamadas en ese horario, cada llamada tiene menor peso relativo
                        
                        **Ejemplo práctico:**
                        - Si los lunes a las 9:00 hay en promedio 10 llamadas: Proporción = 1/10 = 0.10
                        - Si los sábados a las 9:00 hay en promedio 2 llamadas: Proporción = 1/2 = 0.50
                        
                        Esto significa que una llamada el sábado a las 9:00 tiene 5 veces más peso relativo que una llamada el lunes a la misma hora.
                        """)
                else:
                    st.info("Primero procesa los datos en la pestaña 'Procesar y Analizar'")
            
            with tab4:
                st.subheader("Exportar Datos Procesados")
                
                if 'df_con_proporcion' in st.session_state:
                    df_con_proporcion = st.session_state['df_con_proporcion']
                    promedio_por_dia = st.session_state.get('promedio_por_dia', pd.DataFrame())
                    promedio_por_dia_hora = st.session_state.get('promedio_por_dia_hora', pd.DataFrame())
                    
                    # Opciones de exportación
                    st.write("**Selecciona qué datos exportar:**")
                    
                    export_option = st.radio(
                        "Tipo de datos a exportar:",
                        ["Datos completos procesados", "Promedios por día", "Promedios por día y hora", "Todos los datasets"]
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Preparar datos según selección
                        if export_option == "Datos completos procesados":
                            data_to_export = df_con_proporcion
                            filename = "datos_procesados_completos.csv"
                        elif export_option == "Promedios por día":
                            data_to_export = promedio_por_dia
                            filename = "promedios_por_dia.csv"
                        elif export_option == "Promedios por día y hora":
                            data_to_export = promedio_por_dia_hora
                            filename = "promedios_por_dia_hora.csv"
                        else:  # Todos los datasets
                            # Crear un Excel con múltiples hojas
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df_con_proporcion.to_excel(writer, sheet_name='Datos_Procesados', index=False)
                                promedio_por_dia.to_excel(writer, sheet_name='Promedios_Dia', index=False)
                                promedio_por_dia_hora.to_excel(writer, sheet_name='Promedios_Dia_Hora', index=False)
                            
                            buffer.seek(0)
                            filename = "todos_los_datos.xlsx"
                            
                            st.download_button(
                                label="📥 Descargar Excel completo",
                                data=buffer,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                            return
                    
                        # Exportar a CSV
                        csv = data_to_export.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar como CSV",
                            data=csv,
                            file_name=filename,
                            mime="text/csv",
                            type="primary"
                        )
                    
                    with col2:
                        # Vista previa
                        st.write("**Vista previa de exportación:**")
                        st.dataframe(data_to_export.head(10), use_container_width=True)
                        
                else:
                    st.info("No hay datos procesados para exportar. Primero procesa los datos en la pestaña 'Procesar y Analizar'")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo sea un CSV válido con los campos requeridos.")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")
        
        # Mostrar ejemplo de estructura esperada
        with st.expander("Ver estructura esperada del CSV"):
            st.write("""
            ## Nuevo Enfoque de Análisis
            
            Esta aplicación ahora calcula:
            
            1. **Promedio de llamadas por día de semana**: Cuántas llamadas en promedio entran cada Lunes, Martes, etc.
            2. **Promedio de llamadas por día y hora**: Patrones detallados por hora para cada día
            3. **Proporción de equivalencia**: 1 dividido entre el promedio correspondiente
            
            **Ejemplo:**
            - Si los Lunes a las 9:00 AM hay en promedio 10 llamadas
            - La proporción de equivalencia para una llamada el Lunes a las 9:00 AM sería: 1/10 = 0.10
            
            Esto permite comparar el "peso relativo" de cada llamada según cuán ocupado es ese horario.
            """)

if __name__ == "__main__":
    main()
