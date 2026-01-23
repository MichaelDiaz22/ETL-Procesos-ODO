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
    3. Calculará promedios por día y hora
    4. Analiza los patrones de llamadas
    5. Descarga los resultados procesados
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

# Función para obtener el número del día de la semana (0=Lunes, 6=Domingo)
def obtener_numero_dia(dia_espanol):
    dias_numeros = {
        'Lunes': 0,
        'Martes': 1,
        'Miércoles': 2,
        'Jueves': 3,
        'Viernes': 4,
        'Sábado': 5,
        'Domingo': 6
    }
    return dias_numeros.get(dia_espanol, 0)

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
    
    # Mostrar distribución por códigos encontrados
    if registros_filtrados > 0:
        st.write("**Distribución por códigos más frecuentes:**")
        
        # Extraer códigos encontrados
        def extraer_codigo(texto):
            texto_str = str(texto)
            for codigo in CODIGOS_FILTRAR:
                if codigo in texto_str:
                    return codigo
            return "Otro"
        
        df_filtrado['Codigo_Filtrado'] = df_filtrado['To'].apply(extraer_codigo)
        distribucion_codigos = df_filtrado['Codigo_Filtrado'].value_counts().head(10)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(distribucion_codigos, use_container_width=True)
        
        with col2:
            st.bar_chart(distribucion_codigos)
        
        # Eliminar columna temporal
        df_filtrado = df_filtrado.drop('Codigo_Filtrado', axis=1)
    
    return df_filtrado

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
            
            # Mostrar información del rango de fechas
            fecha_min = df_procesado['Call Time'].min()
            fecha_max = df_procesado['Call Time'].max()
            st.info(f"**Rango de fechas en el dataset:** {fecha_min.strftime('%d/%m/%Y')} al {fecha_max.strftime('%d/%m/%Y')}")
            
        else:
            st.error("El archivo no contiene la columna 'Call Time' necesaria para el procesamiento.")
            return None
            
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None
    
    return df_procesado

# Función para calcular la cantidad de días de cada tipo en el rango de fechas
def calcular_dias_por_semana(fechas_unicas):
    """
    Calcula cuántos días de cada tipo de día de la semana hay en el rango de fechas
    """
    # Convertir a lista de fechas únicas
    if isinstance(fechas_unicas, pd.Series):
        fechas_lista = fechas_unicas.unique()
    else:
        fechas_lista = fechas_unicas
    
    # Contar días por tipo
    dias_contador = {
        'Lunes': 0,
        'Martes': 0,
        'Miércoles': 0,
        'Jueves': 0,
        'Viernes': 0,
        'Sábado': 0,
        'Domingo': 0
    }
    
    for fecha in fechas_lista:
        if pd.notna(fecha):
            # Obtener nombre del día en español
            dia_num = fecha.weekday()
            dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][dia_num]
            dias_contador[dia_nombre] += 1
    
    return dias_contador

# Función para calcular promedios corregida
def calcular_promedios_llamadas(df):
    """
    Calcula los promedios de llamadas CORREGIDOS:
    1. Suma total de llamadas por día de semana
    2. Divide entre la cantidad de días de ese tipo en el dataset
    3. Igual para promedios por hora y por combinación día-hora
    """
    # Crear DataFrame para análisis
    df_analisis = df.copy()
    
    # Asegurarse de que tenemos las columnas necesarias
    if not all(col in df_analisis.columns for col in ['Call Time', 'Dia_Semana', 'Hora_Numerica', 'Fecha_Datetime']):
        st.error("No se pueden calcular promedios: faltan columnas necesarias")
        return None, None, None
    
    # Obtener rango de fechas únicas
    fechas_unicas = df_analisis['Fecha_Datetime'].unique()
    
    # Calcular cantidad de días de cada tipo en el dataset
    dias_por_semana = calcular_dias_por_semana(fechas_unicas)
    
    # Mostrar información de días disponibles
    st.write("**Días disponibles por tipo en el dataset:**")
    dias_info = pd.DataFrame(list(dias_por_semana.items()), columns=['Día', 'Cantidad'])
    st.dataframe(dias_info, use_container_width=True)
    
    # 1. CALCULAR PROMEDIO GENERAL POR DÍA DE SEMANA (CORREGIDO)
    # Sumar total de llamadas por día de semana
    total_llamadas_por_dia = df_analisis.groupby('Dia_Semana').size().reset_index(name='Total_Llamadas')
    
    # Dividir entre la cantidad de días de ese tipo en el dataset
    promedio_por_dia = total_llamadas_por_dia.copy()
    promedio_por_dia['Dias_Disponibles'] = promedio_por_dia['Dia_Semana'].map(dias_por_semana)
    promedio_por_dia['Promedio_Llamadas_Dia'] = promedio_por_dia.apply(
        lambda x: x['Total_Llamadas'] / x['Dias_Disponibles'] if x['Dias_Disponibles'] > 0 else 0,
        axis=1
    )
    promedio_por_dia['Promedio_Llamadas_Dia'] = promedio_por_dia['Promedio_Llamadas_Dia'].round(2)
    
    # Ordenar por días de la semana
    orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    promedio_por_dia['Dia_Semana'] = pd.Categorical(promedio_por_dia['Dia_Semana'], categories=orden_dias, ordered=True)
    promedio_por_dia = promedio_por_dia.sort_values('Dia_Semana')
    
    # 2. CALCULAR PROMEDIO GENERAL POR HORA (CORREGIDO)
    # Primero, necesitamos saber cuántos días hay para cada hora
    
    # Crear tabla de fechas y horas únicas
    df_analisis['Fecha_Hora'] = df_analisis['Fecha_Datetime'].astype(str) + '_' + df_analisis['Hora_Numerica'].astype(str)
    
    # Contar días únicos por hora (cuántos días diferentes tienen registros a esa hora)
    dias_por_hora = {}
    for hora in range(24):
        # Filtrar registros de esta hora
        registros_hora = df_analisis[df_analisis['Hora_Numerica'] == hora]
        # Contar días únicos con registros a esta hora
        dias_unicos = len(registros_hora['Fecha_Datetime'].unique())
        dias_por_hora[hora] = dias_unicos if dias_unicos > 0 else 1  # Evitar división por 0
    
    # Sumar total de llamadas por hora
    total_llamadas_por_hora = df_analisis.groupby('Hora_Numerica').size().reset_index(name='Total_Llamadas')
    
    # Dividir entre la cantidad de días con registros a esa hora
    promedio_por_hora = total_llamadas_por_hora.copy()
    promedio_por_hora['Dias_Con_Registros'] = promedio_por_hora['Hora_Numerica'].map(dias_por_hora)
    promedio_por_hora['Promedio_Llamadas_Hora'] = promedio_por_hora.apply(
        lambda x: x['Total_Llamadas'] / x['Dias_Con_Registros'] if x['Dias_Con_Registros'] > 0 else 0,
        axis=1
    )
    promedio_por_hora['Promedio_Llamadas_Hora'] = promedio_por_hora['Promedio_Llamadas_Hora'].round(2)
    promedio_por_hora = promedio_por_hora.sort_values('Hora_Numerica')
    
    # 3. CALCULAR PROMEDIO POR DÍA-HORA (COMBINACIÓN) - CORREGIDO
    # Primero, necesitamos saber cuántos días de cada tipo hay para cada combinación día-hora
    
    # Crear clave única para combinación día-hora-fecha
    df_analisis['Clave_Dia_Hora_Fecha'] = (
        df_analisis['Dia_Semana'] + '_' + 
        df_analisis['Hora_Numerica'].astype(str) + '_' + 
        df_analisis['Fecha_Datetime'].astype(str)
    )
    
    # Contar días únicos por combinación día-hora
    combinaciones_info = {}
    for _, row in df_analisis.iterrows():
        clave = (row['Dia_Semana'], row['Hora_Numerica'])
        fecha = row['Fecha_Datetime']
        
        if clave not in combinaciones_info:
            combinaciones_info[clave] = set()
        
        combinaciones_info[clave].add(fecha)
    
    # Convertir a diccionario de conteos
    dias_por_combinacion = {clave: len(fechas) for clave, fechas in combinaciones_info.items()}
    
    # Sumar total de llamadas por combinación día-hora
    total_llamadas_por_combinacion = df_analisis.groupby(['Dia_Semana', 'Hora_Numerica']).size().reset_index(name='Total_Llamadas')
    
    # Dividir entre la cantidad de días de esa combinación
    promedio_por_dia_hora = total_llamadas_por_combinacion.copy()
    promedio_por_dia_hora['Dias_Con_Registros'] = promedio_por_dia_hora.apply(
        lambda x: dias_por_combinacion.get((x['Dia_Semana'], x['Hora_Numerica']), 0),
        axis=1
    )
    promedio_por_dia_hora['Promedio_Llamadas'] = promedio_por_dia_hora.apply(
        lambda x: x['Total_Llamadas'] / x['Dias_Con_Registros'] if x['Dias_Con_Registros'] > 0 else 0,
        axis=1
    )
    promedio_por_dia_hora['Promedio_Llamadas'] = promedio_por_dia_hora['Promedio_Llamadas'].round(2)
    
    # Ordenar
    promedio_por_dia_hora['Dia_Semana'] = pd.Categorical(promedio_por_dia_hora['Dia_Semana'], categories=orden_dias, ordered=True)
    promedio_por_dia_hora = promedio_por_dia_hora.sort_values(['Dia_Semana', 'Hora_Numerica'])
    
    # Eliminar columnas temporales
    promedio_por_dia = promedio_por_dia.drop(['Total_Llamadas', 'Dias_Disponibles'], axis=1)
    promedio_por_hora = promedio_por_hora.drop(['Total_Llamadas', 'Dias_Con_Registros'], axis=1)
    promedio_por_dia_hora = promedio_por_dia_hora.drop(['Total_Llamadas', 'Dias_Con_Registros'], axis=1)
    
    return promedio_por_dia, promedio_por_hora, promedio_por_dia_hora

# Función para calcular proporción de equivalencia corregida
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
        clave = (row['Dia_Semana'], row['Hora_Numerica'])
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

# Función para crear visualizaciones
def crear_visualizaciones(promedio_por_dia, promedio_por_hora, promedio_por_dia_hora, df_procesado):
    """
    Crea visualizaciones usando solo Streamlit nativo
    """
    # Crear pestañas para diferentes visualizaciones
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Promedios por Día", "🕐 Promedios por Hora", "📅 Promedios Día-Hora", "📋 Tabla de Calor"])
    
    with tab1:
        st.subheader("Promedio General por Día de la Semana")
        st.write("**Promedio de llamadas por día (CORREGIDO - dividido entre días disponibles):**")
        
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
        st.subheader("Promedio General por Hora del Día")
        st.write("**Promedio de llamadas por hora (CORREGIDO - dividido entre días con registros):**")
        
        # Crear gráfico de líneas
        st.line_chart(promedio_por_hora.set_index('Hora_Numerica')['Promedio_Llamadas_Hora'])
        
        # Mostrar tabla de datos
        st.write("**Datos detallados:**")
        st.dataframe(promedio_por_hora, use_container_width=True)
        
        # Métricas clave
        st.write("**Métricas clave:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            hora_max = promedio_por_hora.loc[promedio_por_hora['Promedio_Llamadas_Hora'].idxmax()]
            st.metric("Hora más ocupada", f"{int(hora_max['Hora_Numerica'])}:00", f"{hora_max['Promedio_Llamadas_Hora']:.1f}")
        
        with col2:
            hora_min = promedio_por_hora.loc[promedio_por_hora['Promedio_Llamadas_Hora'].idxmin()]
            st.metric("Hora menos ocupada", f"{int(hora_min['Hora_Numerica'])}:00", f"{hora_min['Promedio_Llamadas_Hora']:.1f}")
        
        with col3:
            # Horario de mayor actividad (mañana/tarde/noche)
            def clasificar_periodo(hora):
                if 6 <= hora < 12:
                    return "Mañana"
                elif 12 <= hora < 18:
                    return "Tarde"
                elif 18 <= hora < 24:
                    return "Noche"
                else:
                    return "Madrugada"
            
            promedio_por_hora['Periodo'] = promedio_por_hora['Hora_Numerica'].apply(clasificar_periodo)
            periodo_actividad = promedio_por_hora.groupby('Periodo')['Promedio_Llamadas_Hora'].sum().idxmax()
            st.metric("Periodo más activo", periodo_actividad)
    
    with tab3:
        st.subheader("Promedio por Combinación Día-Hora")
        st.write("**Promedio de llamadas para cada combinación específica de día y hora (CORREGIDO):**")
        
        # Mostrar los primeros resultados
        st.dataframe(promedio_por_dia_hora.head(20), use_container_width=True)
        
        # Resumen estadístico
        st.write("**Resumen estadístico:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total combinaciones", len(promedio_por_dia_hora))
        
        with col2:
            st.metric("Combinación máxima", 
                     f"{promedio_por_dia_hora['Promedio_Llamadas'].max():.1f}")
        
        with col3:
            st.metric("Combinación mínima", 
                     f"{promedio_por_dia_hora['Promedio_Llamadas'].min():.1f}")
        
        with col4:
            st.metric("Promedio combinaciones", 
                     f"{promedio_por_dia_hora['Promedio_Llamadas'].mean():.1f}")
        
        # Ejemplos específicos
        st.write("**Ejemplos de combinaciones:**")
        
        # Encontrar algunas combinaciones específicas
        ejemplos = [
            ("Lunes", 9),
            ("Martes", 14),
            ("Viernes", 17),
            ("Sábado", 11),
            ("Domingo", 16)
        ]
        
        for dia, hora in ejemplos:
            resultado = promedio_por_dia_hora[
                (promedio_por_dia_hora['Dia_Semana'] == dia) & 
                (promedio_por_dia_hora['Hora_Numerica'] == hora)
            ]
            if not resultado.empty:
                valor = resultado.iloc[0]['Promedio_Llamadas']
                st.write(f"- **{dia} a las {hora}:00**: {valor:.1f} llamadas en promedio")
    
    with tab4:
        st.subheader("Tabla de Calor - Promedios por Día y Hora")
        
        # Crear matriz para la tabla de calor
        matriz_promedios = promedio_por_dia_hora.pivot_table(
            index='Dia_Semana',
            columns='Hora_Numerica',
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
                color = '#e8f5e9'  # Verde muy claro
            elif val < 3:
                color = '#c8e6c9'  # Verde claro
            elif val < 5:
                color = '#a5d6a7'  # Verde
            elif val < 10:
                color = '#81c784'  # Verde medio
            elif val < 20:
                color = '#4caf50'  # Verde oscuro
            elif val < 50:
                color = '#388e3c'  # Verde muy oscuro
            else:
                color = '#1b5e20'  # Verde intenso
            return f'background-color: {color}; color: black;'
        
        # Mostrar tabla con colores
        st.write("**Mapa de calor (colores indican volumen):**")
        styled_table = matriz_promedios.style.applymap(color_cells).format("{:.1f}")
        st.dataframe(styled_table, use_container_width=True)
        
        # Leyenda
        st.write("**Leyenda de colores:**")
        cols = st.columns(6)
        leyenda = [
            ("0", '#f0f0f0'),
            ("< 1", '#e8f5e9'),
            ("1-3", '#c8e6c9'),
            ("3-5", '#a5d6a7'),
            ("5-10", '#81c784'),
            ("10-20", '#4caf50'),
            ("> 20", '#388e3c'),
            ("> 50", '#1b5e20')
        ]
        
        for i, (texto, color) in enumerate(leyenda):
            with cols[i % 6]:
                st.markdown(f'<div style="background-color: {color}; padding: 5px; border-radius: 3px; text-align: center;">{texto}</div>', 
                           unsafe_allow_html=True)

# Función para mostrar resumen ejecutivo
def mostrar_resumen_ejecutivo(df_procesado, promedio_por_dia, promedio_por_hora, promedio_por_dia_hora):
    """
    Muestra un resumen ejecutivo del análisis
    """
    st.subheader("📋 Resumen Ejecutivo del Análisis (Filtrado por Códigos Específicos)")
    
    # Estadísticas generales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Día con más llamadas en promedio
        dia_max = promedio_por_dia.loc[promedio_por_dia['Promedio_Llamadas_Dia'].idxmax()]
        st.metric(
            label="Día más ocupado",
            value=dia_max['Dia_Semana'],
            delta=f"{dia_max['Promedio_Llamadas_Dia']:.1f} llamadas/día"
        )
    
    with col2:
        # Hora con más llamadas en promedio
        hora_max = promedio_por_hora.loc[promedio_por_hora['Promedio_Llamadas_Hora'].idxmax()]
        st.metric(
            label="Hora más ocupada",
            value=f"{int(hora_max['Hora_Numerica'])}:00",
            delta=f"{hora_max['Promedio_Llamadas_Hora']:.1f} llamadas/hora"
        )
    
    with col3:
        # Combinación día-hora con más llamadas
        comb_max = promedio_por_dia_hora.loc[promedio_por_dia_hora['Promedio_Llamadas'].idxmax()]
        st.metric(
            label="Combinación más ocupada",
            value=f"{comb_max['Dia_Semana']} {comb_max['Hora_Numerica']}:00",
            delta=f"{comb_max['Promedio_Llamadas']:.1f} llamadas"
        )
    
    with col4:
        # Promedio total de llamadas por día
        promedio_total_dia = promedio_por_dia['Promedio_Llamadas_Dia'].mean()
        st.metric(
            label="Promedio general/día",
            value=f"{promedio_total_dia:.1f}",
            delta="llamadas"
        )
    
    # Insights adicionales
    st.write("**📈 Insights clave:**")
    
    col_insight1, col_insight2, col_insight3 = st.columns(3)
    
    with col_insight1:
        # Variabilidad entre días
        variabilidad_dias = (promedio_por_dia['Promedio_Llamadas_Dia'].std() / 
                           promedio_por_dia['Promedio_Llamadas_Dia'].mean() * 100)
        st.info(f"**Variabilidad entre días:** {variabilidad_dias:.1f}%")
        st.caption("Mide cuánto varía el volumen entre diferentes días")
    
    with col_insight2:
        # Variabilidad entre horas
        variabilidad_horas = (promedio_por_hora['Promedio_Llamadas_Hora'].std() / 
                            promedio_por_hora['Promedio_Llamadas_Hora'].mean() * 100)
        st.info(f"**Variabilidad entre horas:** {variabilidad_horas:.1f}%")
        st.caption("Mide cuánto varía el volumen a lo largo del día")
    
    with col_insight3:
        # Horas pico
        horas_pico = promedio_por_dia_hora[promedio_por_dia_hora['Promedio_Llamadas'] > 
                                         promedio_por_dia_hora['Promedio_Llamadas'].mean()]
        st.info(f"**Combinaciones pico:** {len(horas_pico)} de {len(promedio_por_dia_hora)}")
        st.caption("Combinaciones día-hora con arriba del promedio")
    
    # Distribución de proporciones (si existe)
    if 'Proporcion_Equivalencia' in df_procesado.columns:
        st.write("**📊 Distribución de Proporciones de Equivalencia:**")
        
        # Calcular estadísticas de proporciones
        proporciones = df_procesado['Proporcion_Equivalencia']
        col_prop1, col_prop2, col_prop3, col_prop4 = st.columns(4)
        
        with col_prop1:
            st.metric("Proporción mínima", f"{proporciones.min():.4f}")
        
        with col_prop2:
            st.metric("Proporción máxima", f"{proporciones.max():.4f}")
        
        with col_prop3:
            st.metric("Proporción promedio", f"{proporciones.mean():.4f}")
        
        with col_prop4:
            # Contar proporciones significativas (> 0.1)
            proporciones_significativas = len(proporciones[proporciones > 0.1])
            total_proporciones = len(proporciones)
            porcentaje = (proporciones_significativas / total_proporciones * 100) if total_proporciones > 0 else 0
            st.metric("Proporciones > 0.1", f"{porcentaje:.1f}%")

# Función principal
def main():
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Datos Originales", "⚙️ Filtrar y Procesar", "📊 Resultados y Visualizaciones", "💾 Exportar"])
            
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
                st.subheader("Filtrado y Procesamiento de Datos")
                
                # Primero aplicar el filtro
                st.write("### Paso 1: Aplicar Filtro por Códigos")
                st.info(f"Se filtrarán los registros cuyo campo 'To' contenga alguno de los {len(CODIGOS_FILTRAR)} códigos especificados")
                
                if st.button("Aplicar Filtro", type="primary", key="filtrar"):
                    with st.spinner("Aplicando filtro..."):
                        df_filtrado = filtrar_por_codigos(df)
                        
                        if df_filtrado is not None and len(df_filtrado) > 0:
                            # Guardar en session state
                            st.session_state['df_filtrado'] = df_filtrado
                            st.success(f"✅ Filtro aplicado. {len(df_filtrado)} registros incluidos.")
                            
                            # Mostrar vista previa de datos filtrados
                            st.write("**Vista previa de datos filtrados:**")
                            st.dataframe(df_filtrado.head(50), use_container_width=True)
                        else:
                            st.error("No se encontraron registros que coincidan con los códigos especificados.")
                
                # Procesar datos filtrados
                st.write("### Paso 2: Procesar Datos Filtrados")
                
                if 'df_filtrado' in st.session_state and len(st.session_state['df_filtrado']) > 0:
                    df_filtrado = st.session_state['df_filtrado']
                    
                    if st.button("Procesar Datos y Calcular Promedios", type="primary", key="procesar"):
                        with st.spinner("Procesando datos y calculando promedios..."):
                            # Procesar datos básicos
                            df_procesado = procesar_datos(df_filtrado)
                            
                            if df_procesado is not None:
                                # Calcular promedios CORREGIDOS
                                promedio_por_dia, promedio_por_hora, promedio_por_dia_hora = calcular_promedios_llamadas(df_procesado)
                                
                                if (promedio_por_dia is not None and 
                                    promedio_por_hora is not None and 
                                    promedio_por_dia_hora is not None):
                                    
                                    # Calcular proporción de equivalencia
                                    df_con_proporcion = calcular_proporcion_equivalencia(df_procesado, promedio_por_dia_hora)
                                    
                                    # Guardar en session state
                                    st.session_state['df_procesado'] = df_procesado
                                    st.session_state['df_con_proporcion'] = df_con_proporcion
                                    st.session_state['promedio_por_dia'] = promedio_por_dia
                                    st.session_state['promedio_por_hora'] = promedio_por_hora
                                    st.session_state['promedio_por_dia_hora'] = promedio_por_dia_hora
                                    
                                    st.success("✅ Procesamiento completado!")
                                    
                                    # Explicar la metodología CORREGIDA
                                    with st.expander("📝 Explicación de la metodología CORREGIDA"):
                                        st.markdown("""
                                        **METODOLOGÍA CORREGIDA DE CÁLCULO DE PROMEDIOS:**
                                        
                                        1. **Para promedios por día de semana:**
                                           - Se suman **TODAS** las llamadas de ese día de semana en el dataset
                                           - Se divide entre la **cantidad de días de ese tipo** en el rango de fechas
                                           - **Ejemplo**: Si hay 100 llamadas los Lunes y el dataset tiene 4 Lunes, el promedio es 100/4 = 25 llamadas/Lunes
                                        
                                        2. **Para promedios por hora:**
                                           - Se suman **TODAS** las llamadas de esa hora en el dataset
                                           - Se divide entre la **cantidad de días que tienen registros a esa hora**
                                           - **Ejemplo**: Si hay 50 llamadas a las 9:00 y 10 días tienen registros a las 9:00, el promedio es 50/10 = 5 llamadas/9:00
                                        
                                        3. **Para promedios por combinación día-hora:**
                                           - Se suman **TODAS** las llamadas de esa combinación específica
                                           - Se divide entre la **cantidad de días de ese tipo que tienen registros a esa hora**
                                           - **Ejemplo**: Si hay 20 llamadas los Lunes a las 9:00 y hay 3 Lunes con registros a las 9:00, el promedio es 20/3 ≈ 6.67 llamadas/Lunes-9:00
                                        
                                        4. **Proporción de equivalencia:**
                                           - Se calcula como **1 / Promedio para esa combinación día-hora**
                                           - **Ejemplo**: Si el promedio para Lunes-9:00 es 6.67, la proporción es 1/6.67 ≈ 0.15
                                        """)
                                    
                                    # Mostrar resumen rápido
                                    st.write("**Resumen de promedios calculados (CORREGIDOS):**")
                                    
                                    col_res1, col_res2 = st.columns(2)
                                    
                                    with col_res1:
                                        st.write("📅 **Promedios por día:**")
                                        st.dataframe(promedio_por_dia, use_container_width=True)
                                    
                                    with col_res2:
                                        st.write("🕐 **Promedios por hora (ejemplo):**")
                                        st.dataframe(promedio_por_hora.head(10), use_container_width=True)
                                    
                                    st.write("📊 **Promedios por combinación día-hora (ejemplo):**")
                                    st.dataframe(promedio_por_dia_hora.head(10), use_container_width=True)
                                else:
                                    st.error("No se pudieron calcular los promedios")
                else:
                    st.info("Primero aplica el filtro en el Paso 1")
            
            with tab3:
                st.subheader("Resultados y Visualizaciones")
                
                if all(key in st.session_state for key in ['df_con_proporcion', 'promedio_por_dia', 'promedio_por_hora', 'promedio_por_dia_hora']):
                    df_con_proporcion = st.session_state['df_con_proporcion']
                    promedio_por_dia = st.session_state['promedio_por_dia']
                    promedio_por_hora = st.session_state['promedio_por_hora']
                    promedio_por_dia_hora = st.session_state['promedio_por_dia_hora']
                    
                    # Mostrar resumen ejecutivo
                    mostrar_resumen_ejecutivo(df_con_proporcion, promedio_por_dia, promedio_por_hora, promedio_por_dia_hora)
                    
                    # Mostrar visualizaciones
                    crear_visualizaciones(promedio_por_dia, promedio_por_hora, promedio_por_dia_hora, df_con_proporcion)
                    
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
                    
                else:
                    st.info("Primero procesa los datos en la pestaña 'Filtrar y Procesar'")
            
            with tab4:
                st.subheader("Exportar Datos Procesados")
                
                if 'df_con_proporcion' in st.session_state:
                    df_con_proporcion = st.session_state['df_con_proporcion']
                    promedio_por_dia = st.session_state.get('promedio_por_dia', pd.DataFrame())
                    promedio_por_hora = st.session_state.get('promedio_por_hora', pd.DataFrame())
                    promedio_por_dia_hora = st.session_state.get('promedio_por_dia_hora', pd.DataFrame())
                    
                    # Opciones de exportación
                    st.write("**Selecciona qué datos exportar:**")
                    
                    export_option = st.radio(
                        "Tipo de datos a exportar:",
                        [
                            "Datos completos procesados", 
                            "Promedios por día", 
                            "Promedios por hora",
                            "Promedios por día y hora", 
                            "Todos los datasets"
                        ]
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Preparar datos según selección
                        if export_option == "Datos completos procesados":
                            data_to_export = df_con_proporcion
                            filename = "datos_procesados_filtrados.csv"
                        elif export_option == "Promedios por día":
                            data_to_export = promedio_por_dia
                            filename = "promedios_por_dia_filtrados.csv"
                        elif export_option == "Promedios por hora":
                            data_to_export = promedio_por_hora
                            filename = "promedios_por_hora_filtrados.csv"
                        elif export_option == "Promedios por día y hora":
                            data_to_export = promedio_por_dia_hora
                            filename = "promedios_por_dia_hora_filtrados.csv"
                        else:  # Todos los datasets
                            # Crear un Excel con múltiples hojas
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df_con_proporcion.to_excel(writer, sheet_name='Datos_Procesados', index=False)
                                promedio_por_dia.to_excel(writer, sheet_name='Promedios_Dia', index=False)
                                promedio_por_hora.to_excel(writer, sheet_name='Promedios_Hora', index=False)
                                promedio_por_dia_hora.to_excel(writer, sheet_name='Promedios_Dia_Hora', index=False)
                            
                            buffer.seek(0)
                            filename = "todos_los_datos_filtrados.xlsx"
                            
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
                    st.info("No hay datos procesados para exportar. Primero procesa los datos en la pestaña 'Filtrar y Procesar'")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo sea un CSV válido con los campos requeridos.")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")
        
        # Mostrar ejemplo de estructura esperada
        with st.expander("Ver estructura esperada del CSV"):
            st.write("""
            ## Aplicación con Filtro Específico y Cálculo CORREGIDO
            
            **CORRECCIÓN IMPORTANTE**: 
            Los promedios ahora se calculan CORRECTAMENTE dividiendo entre la cantidad real de días disponibles.
            
            **Ejemplo**: 
            - Si el dataset tiene registros del 1 al 22 de enero de 2026
            - Hay 4 Lunes en ese período (5, 12, 19, 26)
            - Si hay 100 llamadas en total los Lunes
            - El promedio CORRECTO es: 100 llamadas / 4 Lunes = 25 llamadas por Lunes
            
            **Metodología CORREGIDA:**
            1. **Promedios por día**: Total llamadas del día ÷ Cantidad de días de ese tipo en el dataset
            2. **Promedios por hora**: Total llamadas de la hora ÷ Días con registros a esa hora
            3. **Promedios por combinación**: Total llamadas de la combinación ÷ Días de ese tipo con registros a esa hora
            4. **Proporción de equivalencia**: 1 ÷ Promedio de la combinación
            """)

if __name__ == "__main__":
    main()
