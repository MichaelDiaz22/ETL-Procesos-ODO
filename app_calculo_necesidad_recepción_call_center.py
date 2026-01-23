import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
import io
import plotly.graph_objects as go
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para calcular métricas de demanda y recursos")

# Constante para el cálculo de validación
CONSTANTE_VALIDACION = 14.08

# Lista de códigos a filtrar en el campo "To" y "From"
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

# Definición de códigos por empresa
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

# Horas para ingresar recursos (6:00 a 19:00)
HORAS_DISPONIBLES = list(range(6, 20))  # 6:00 a 19:00

# Sidebar para cargar el archivo
with st.sidebar:
    st.header("Cargar Datos")
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    
    st.markdown("---")
    st.markdown("**Instrucciones:**")
    st.markdown("""
    1. Sube un archivo CSV con los campos requeridos
    2. Ingresa los recursos disponibles por hora (6:00-19:00)
    3. La app filtrará por los códigos especificados
    4. Calculará todas las métricas y clasificaciones
    5. Analiza los resultados
    6. Descarga los datos procesados
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

# Función para determinar empresa_inbound (basado en campo "To")
def determinar_empresa_inbound(valor_to):
    """
    Determina la empresa inbound basado en el campo "To" y los códigos específicos
    """
    valor_str = str(valor_to)
    
    # Verificar CCB
    for codigo in CODIGOS_CCB:
        if codigo in valor_str:
            return "CCB"
    
    # Verificar ODO
    for codigo in CODIGOS_ODO:
        if codigo in valor_str:
            return "ODO"
    
    # Verificar UDC
    for codigo in CODIGOS_UDC:
        if codigo in valor_str:
            return "UDC"
    
    # Si no encontró ningún código de las empresas, es Externo
    return "Externo"

# Función para determinar empresa_outbound (basado en campo "From")
def determinar_empresa_outbound(valor_from):
    """
    Determina la empresa outbound basado en el campo "From" y los códigos específicos
    """
    valor_str = str(valor_from)
    
    # Verificar CCB
    for codigo in CODIGOS_CCB:
        if codigo in valor_str:
            return "CCB"
    
    # Verificar ODO
    for codigo in CODIGOS_ODO:
        if codigo in valor_str:
            return "ODO"
    
    # Verificar UDC
    for codigo in CODIGOS_UDC:
        if codigo in valor_str:
            return "UDC"
    
    # Si no encontró ningún código de las empresas, es Externo
    return "Externo"

# Función para ingresar recursos por hora
def ingresar_recursos_por_hora():
    """
    Muestra un formulario para ingresar la cantidad de recursos disponibles por hora
    """
    recursos = {}
    
    # Crear 3 columnas para organizar las horas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        for hora in HORAS_DISPONIBLES[:5]:  # 6:00 - 10:00
            recursos[hora] = st.number_input(
                f"{hora}:00",
                min_value=0,
                max_value=100,
                value=1,
                key=f"recurso_{hora}"
            )
    
    with col2:
        for hora in HORAS_DISPONIBLES[5:10]:  # 11:00 - 15:00
            recursos[hora] = st.number_input(
                f"{hora}:00",
                min_value=0,
                max_value=100,
                value=1,
                key=f"recurso_{hora}"
            )
    
    with col3:
        for hora in HORAS_DISPONIBLES[10:]:  # 16:00 - 19:00
            recursos[hora] = st.number_input(
                f"{hora}:00",
                min_value=0,
                max_value=100,
                value=1,
                key=f"recurso_{hora}"
            )
    
    return recursos

# Función para filtrar datos - MODIFICADA para usar empresa_outbound y empresa_inbound
def filtrar_por_codigos(df):
    """
    Filtra el DataFrame para incluir solo registros donde:
    - empresa_outbound == "Externo" (origen externo)
    - empresa_inbound != "Externo" (destino interno: CCB, ODO o UDC)
    """
    df_filtrado = df.copy()
    
    # Verificar que existan las columnas necesarias
    columnas_requeridas = ['Call Time', 'From', 'To']
    for col in columnas_requeridas:
        if col not in df_filtrado.columns:
            st.error(f"El archivo no contiene la columna '{col}' necesaria para el filtrado.")
            return None
    
    # Primero, calcular empresa_inbound y empresa_outbound para todos los registros
    df_filtrado['empresa_inbound_temp'] = df_filtrado['To'].apply(determinar_empresa_inbound)
    df_filtrado['empresa_outbound_temp'] = df_filtrado['From'].apply(determinar_empresa_outbound)
    
    # Aplicar el filtro: empresa_outbound == "Externo" Y empresa_inbound != "Externo"
    mascara = (df_filtrado['empresa_outbound_temp'] == "Externo") & (df_filtrado['empresa_inbound_temp'] != "Externo")
    
    # Aplicar filtro
    df_filtrado = df_filtrado[mascara].copy()
    
    # Eliminar columnas temporales
    df_filtrado = df_filtrado.drop(columns=['empresa_inbound_temp', 'empresa_outbound_temp'])
    
    # Mostrar estadísticas del filtrado
    total_registros = len(df)
    registros_filtrados = len(df_filtrado)
    porcentaje_filtrado = (registros_filtrados / total_registros * 100) if total_registros > 0 else 0
    
    st.info(f"**Filtro aplicado:** {registros_filtrados:,} de {total_registros:,} registros ({porcentaje_filtrado:.1f}%)")
    
    # Mostrar distribución del filtro
    if registros_filtrados > 0:
        # Calcular nuevamente para mostrar distribución
        df_filtrado['empresa_inbound_temp'] = df_filtrado['To'].apply(determinar_empresa_inbound)
        distribucion_inbound = df_filtrado['empresa_inbound_temp'].value_counts()
        st.info("**Distribución por empresa_inbound (destino):**")
        for empresa, count in distribucion_inbound.items():
            st.write(f"- {empresa}: {count:,} registros")
        df_filtrado = df_filtrado.drop(columns=['empresa_inbound_temp'])
    
    return df_filtrado

# Función para procesar los datos y calcular proporción de equivalencia
def procesar_datos_con_proporcion(df, recursos_por_hora):
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
        
        # 10. PASO 6: Calcular empresa_inbound (basado en campo "To")
        df_procesado['empresa_inbound'] = df_procesado['To'].apply(determinar_empresa_inbound)
        
        # 11. PASO 7: Calcular empresa_outbound (NUEVA - basado en campo "From")
        df_procesado['empresa_outbound'] = df_procesado['From'].apply(determinar_empresa_outbound)
        
        # 12. PASO 8: Calcular validador_recurso_hora
        # Primero necesitamos contar registros por hora, fecha y rol_inbound
        df_procesado['Clave_Hora_Fecha_Rol'] = (
            df_procesado['Hora_Numerica'].astype(str) + '_' +
            df_procesado['Fecha_Creacion'].astype(str) + '_' +
            df_procesado['rol_inbound'].astype(str)
        )
        
        # Calcular conteo por grupo (hora, fecha, rol)
        conteo_hora_fecha_rol = df_procesado.groupby('Clave_Hora_Fecha_Rol').size()
        
        # Asignar el conteo a cada registro
        df_procesado['Conteo_Hora_Fecha_Rol'] = df_procesado['Clave_Hora_Fecha_Rol'].map(conteo_hora_fecha_rol)
        
        # Calcular validador_recurso_hora
        def calcular_validador_recurso_hora(fila, recursos_dict):
            hora = fila['Hora_Numerica']
            conteo = fila['Conteo_Hora_Fecha_Rol']
            
            # Obtener recursos para esta hora (si no existe, usar 0)
            recursos = recursos_dict.get(hora, 0)
            
            if conteo > 0 and recursos > 0:
                return (recursos * CONSTANTE_VALIDACION) / conteo
            else:
                return 0
        
        df_procesado['validador_recurso_hora'] = df_procesado.apply(
            lambda x: calcular_validador_recurso_hora(x, recursos_por_hora), 
            axis=1
        )
        
        # 13. PASO 9: Calcular validador_necesidad_personas_hora
        def calcular_validador_necesidad_personas_hora(fila, recursos_dict):
            hora = fila['Hora_Numerica']
            conteo = fila['Conteo_Hora_Fecha_Rol']
            
            # Obtener recursos para esta hora (si no existe, usar 0)
            recursos = recursos_dict.get(hora, 0)
            
            if conteo > 0:
                return recursos / conteo
            else:
                return 0
        
        df_procesado['validador_necesidad_personas_hora'] = df_procesado.apply(
            lambda x: calcular_validador_necesidad_personas_hora(x, recursos_por_hora), 
            axis=1
        )
        
        # Redondear a 6 decimales para mayor precisión
        df_procesado['Proporcion_Equivalencia'] = df_procesado['Proporcion_Equivalencia'].round(6)
        df_procesado['Paso_1_Division'] = df_procesado['Paso_1_Division'].round(6)
        df_procesado['validador_demanda_personas_hora'] = df_procesado['validador_demanda_personas_hora'].round(6)
        df_procesado['validador_recurso_hora'] = df_procesado['validador_recurso_hora'].round(6)
        df_procesado['validador_necesidad_personas_hora'] = df_procesado['validador_necesidad_personas_hora'].round(6)
        
        # Eliminar columnas temporales
        columnas_a_eliminar = ['Clave_Agrupacion', 'Clave_Hora_Fecha_Rol']
        df_procesado = df_procesado.drop(columns=columnas_a_eliminar)
        
        # Mostrar distribución de empresa_inbound y empresa_outbound
        st.info("**Distribución de categorías:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            distribucion_inbound = df_procesado['empresa_inbound'].value_counts()
            st.write("**Empresa Inbound (destino):**")
            for empresa, count in distribucion_inbound.items():
                porcentaje = (count / len(df_procesado)) * 100
                st.write(f"- {empresa}: {count:,} registros ({porcentaje:.1f}%)")
        
        with col2:
            distribucion_outbound = df_procesado['empresa_outbound'].value_counts()
            st.write("**Empresa Outbound (origen):**")
            for empresa, count in distribucion_outbound.items():
                porcentaje = (count / len(df_procesado)) * 100
                st.write(f"- {empresa}: {count:,} registros ({porcentaje:.1f}%)")
        
        st.success("✅ Datos procesados y cálculos realizados exitosamente")
        
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None
    
    return df_procesado

# Función para crear gráfico de proporciones por hora y día - MODIFICADA con Plotly y etiquetas
def crear_grafico_proporciones_dia_hora(df_procesado):
    """
    Crea un gráfico de líneas que muestra la SUMA de Proporción de Equivalencia
    para registros donde empresa_outbound == "Externo" y la suma de validador_recurso_hora por hora para un día específico
    """
    st.write("### 📈 Suma de Proporción Demanda (Origen Externo) vs Recursos por Hora y Día")
    
    # Obtener lista de días disponibles
    dias_disponibles = df_procesado['Dia_Semana'].unique()
    
    # Selector de día
    dia_seleccionado = st.selectbox(
        "Selecciona el día de la semana:",
        options=sorted(dias_disponibles),
        key="selector_dia_grafico"
    )
    
    # Filtrar datos por día seleccionado y empresa_outbound == "Externo"
    df_dia = df_procesado[(df_procesado['Dia_Semana'] == dia_seleccionado) & 
                          (df_procesado['empresa_outbound'] == "Externo")].copy()
    
    if len(df_dia) > 0:
        # Para la Proporción de Equivalencia: calcular SUMA por hora (no frecuencia/count)
        # Para validador_recurso_hora: calcular suma por hora
        
        # Calcular SUMA de Proporcion_Equivalencia por hora para empresa_outbound == "Externo"
        suma_proporcion = df_dia.groupby('Hora_Numerica')['Proporcion_Equivalencia'].sum().reset_index()
        suma_proporcion = suma_proporcion.rename(columns={
            'Hora_Numerica': 'Hora',
            'Proporcion_Equivalencia': 'Suma Proporción Demanda (Origen Externo)'
        })
        
        # Calcular suma de validador_recurso_hora por hora (sin filtrar por empresa_outbound)
        # Para recursos, necesitamos TODOS los registros del día seleccionado
        df_dia_todos = df_procesado[df_procesado['Dia_Semana'] == dia_seleccionado].copy()
        suma_recursos = df_dia_todos.groupby('Hora_Numerica')['validador_recurso_hora'].sum().reset_index()
        suma_recursos = suma_recursos.rename(columns={
            'Hora_Numerica': 'Hora',
            'validador_recurso_hora': 'Suma Recursos Disponibles'
        })
        
        # Combinar ambos DataFrames
        datos_grafico = pd.merge(suma_proporcion, suma_recursos, on='Hora', how='outer')
        
        # Rellenar valores NaN con 0
        datos_grafico = datos_grafico.fillna(0)
        
        # Ordenar por hora
        datos_grafico = datos_grafico.sort_values('Hora')
        
        # Crear rango completo de horas de 0 a 24
        horas_completas = pd.DataFrame({'Hora': range(0, 25)})
        
        # Combinar con datos existentes
        datos_grafico_completo = pd.merge(horas_completas, datos_grafico, on='Hora', how='left')
        
        # Rellenar valores NaN con 0
        datos_grafico_completo = datos_grafico_completo.fillna(0)
        
        # Formatear horas para mostrar
        datos_grafico_completo['Hora_Formateada'] = datos_grafico_completo['Hora'].apply(lambda x: f"{x}:00")
        
        # Crear gráfico con Plotly para tener etiquetas
        fig = go.Figure()
        
        # Agregar línea para Suma Proporción Demanda
        fig.add_trace(go.Scatter(
            x=datos_grafico_completo['Hora'],
            y=datos_grafico_completo['Suma Proporción Demanda (Origen Externo)'],
            mode='lines+markers+text',
            name='Suma Proporción Demanda (Origen Externo)',
            line=dict(color='blue', width=3),
            marker=dict(size=8, color='blue'),
            text=[f"{val:.4f}" if val > 0 else "" for val in datos_grafico_completo['Suma Proporción Demanda (Origen Externo)']],
            textposition="top center",
            textfont=dict(size=10, color='blue'),
            hovertemplate='Hora: %{x}:00<br>Suma Proporción: %{y:.6f}<extra></extra>'
        ))
        
        # Agregar línea para Suma Recursos Disponibles
        fig.add_trace(go.Scatter(
            x=datos_grafico_completo['Hora'],
            y=datos_grafico_completo['Suma Recursos Disponibles'],
            mode='lines+markers+text',
            name='Suma Recursos Disponibles',
            line=dict(color='red', width=3, dash='dash'),
            marker=dict(size=8, color='red', symbol='square'),
            text=[f"{val:.4f}" if val > 0 else "" for val in datos_grafico_completo['Suma Recursos Disponibles']],
            textposition="bottom center",
            textfont=dict(size=10, color='red'),
            hovertemplate='Hora: %{x}:00<br>Suma Recursos: %{y:.6f}<extra></extra>'
        ))
        
        # Configurar el layout del gráfico
        fig.update_layout(
            title=f"Distribución para {dia_seleccionado} (Llamadas con Origen Externo)",
            xaxis_title="Hora del Día",
            yaxis_title="Valor",
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(0, 25)),
                ticktext=[f"{h}:00" for h in range(0, 25)],
                range=[0, 24]
            ),
            yaxis=dict(
                rangemode='tozero'
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500,
            showlegend=True
        )
        
        # Mostrar gráfico
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar tabla de datos
        with st.expander("📊 Ver datos detallados de la gráfica"):
            st.dataframe(datos_grafico_completo[['Hora', 'Hora_Formateada', 
                                                'Suma Proporción Demanda (Origen Externo)', 
                                                'Suma Recursos Disponibles']].round(6), 
                        use_container_width=True)
        
        # Mostrar métricas de comparación
        st.write("**Métricas de comparación:**")
        
        col_comp1, col_comp2, col_comp3 = st.columns(3)
        
        with col_comp1:
            # Ratio promedio suma_proporcion/suma_recursos
            total_proporcion = datos_grafico_completo['Suma Proporción Demanda (Origen Externo)'].sum()
            total_recursos = datos_grafico_completo['Suma Recursos Disponibles'].sum()
            if total_recursos > 0:
                ratio_promedio = total_proporcion / total_recursos
                st.metric("Ratio Total Proporción/Recursos", f"{ratio_promedio:.6f}")
        
        with col_comp2:
            # Total de proporción demanda
            st.metric("Total Proporción Demanda", f"{total_proporcion:.6f}")
        
        with col_comp3:
            # Total de recursos
            st.metric("Total Recursos Disponibles", f"{total_recursos:.6f}")
        
        # Mostrar distribución por empresa_inbound para las llamadas con origen externo en este día
        st.write(f"**Distribución por empresa_inbound (destino) para {dia_seleccionado} (origen externo):**")
        distribucion_dia = df_dia['empresa_inbound'].value_counts()
        for empresa, count in distribucion_dia.items():
            porcentaje = (count / len(df_dia)) * 100
            st.write(f"- {empresa}: {count:,} registros ({porcentaje:.1f}%)")
    else:
        st.warning(f"No hay datos disponibles para {dia_seleccionado} con empresa_outbound == 'Externo'")

# Función para mostrar tabla de primeros 10 registros con columnas nuevas (SIMPLIFICADA)
def mostrar_primeros_registros(df_procesado):
    """
    Muestra una tabla con los primeros 10 registros del dataset procesado,
    incluyendo las columnas nuevas del procesamiento
    """
    # Seleccionar columnas originales importantes y las nuevas calculadas
    columnas_originales = ['Call Time', 'From', 'To']
    columnas_nuevas = [
        'Hora_Registro', 'Hora_Numerica', 'Fecha_Creacion', 'Dia_Semana',
        'Dias_Mismo_Tipo_Dataset', 'Conteo_Registros_Similares', 'Paso_1_Division',
        'Proporcion_Equivalencia', 'validador_demanda_personas_hora', 'rol_inbound',
        'empresa_inbound', 'empresa_outbound', 'Conteo_Hora_Fecha_Rol', 'validador_recurso_hora',
        'validador_necesidad_personas_hora'
    ]
    
    # Verificar qué columnas existen en el DataFrame
    columnas_existentes = [col for col in columnas_originales + columnas_nuevas if col in df_procesado.columns]
    
    if columnas_existentes:
        # Tomar solo los primeros 10 registros
        df_muestra = df_procesado[columnas_existentes].head(10).copy()
        
        # Formatear columnas para mejor visualización
        if 'Call Time' in df_muestra.columns and pd.api.types.is_datetime64_any_dtype(df_muestra['Call Time']):
            df_muestra['Call Time'] = df_muestra['Call Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Mostrar la tabla
        st.dataframe(df_muestra, use_container_width=True)

# Función principal
def main():
    # Inicializar session state para recursos
    if 'recursos_por_hora' not in st.session_state:
        st.session_state.recursos_por_hora = {}
    
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2 = st.tabs(["📋 Datos y Configuración", "📊 Resultados y Exportación"])
            
            with tab1:
                st.subheader("Datos Originales")
                st.write(f"**Forma del dataset:** {df.shape[0]} filas × {df.shape[1]} columnas")
                
                # Mostrar vista previa de datos
                st.write("**Vista previa de datos (primeras 10 filas):**")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Divider
                st.divider()
                
                # Configuración de recursos por hora en dos columnas
                st.subheader("👥 Configuración de Recursos por Hora")
                st.info("Ingresa la cantidad de personas disponibles para cada hora (6:00 AM - 7:00 PM)")
                
                col_recursos1, col_recursos2 = st.columns([3, 2])
                
                with col_recursos1:
                    # Ingresar recursos por hora
                    recursos = ingresar_recursos_por_hora()
                    
                    # Guardar recursos en session state
                    st.session_state.recursos_por_hora = recursos
                    
                    # Calcular máximo de recursos
                    if recursos:
                        max_recursos = max(recursos.values())
                        st.metric("Máximo de recursos por hora", max_recursos)
                
                with col_recursos2:
                    # Mostrar gráfico de recursos por hora
                    if recursos:
                        st.write("**📈 Distribución de recursos por hora:**")
                        recursos_df = pd.DataFrame(list(recursos.items()), columns=['Hora', 'Recursos'])
                        st.line_chart(recursos_df.set_index('Hora')['Recursos'])
                
                # Botón para procesar datos
                st.divider()
                st.subheader("Procesamiento de Datos")
                
                # Verificar que se hayan ingresado recursos
                if not st.session_state.recursos_por_hora:
                    st.warning("⚠️ Primero ingresa los recursos por hora")
                else:
                    if st.button("🔧 Aplicar Filtro y Calcular Métricas", type="primary", use_container_width=True):
                        with st.spinner("Procesando datos..."):
                            # Aplicar filtro (nuevo criterio: empresa_outbound == "Externo" Y empresa_inbound != "Externo")
                            df_filtrado = filtrar_por_codigos(df)
                            
                            if df_filtrado is not None and len(df_filtrado) > 0:
                                # Procesar datos y calcular proporción
                                df_procesado = procesar_datos_con_proporcion(
                                    df_filtrado, 
                                    st.session_state.recursos_por_hora
                                )
                                
                                if df_procesado is not None:
                                    # Guardar en session state
                                    st.session_state['df_procesado'] = df_procesado
                                    
                                    # Mostrar tabla con primeros 10 registros y columnas nuevas
                                    st.divider()
                                    st.write("### 📋 Primeros 10 Registros del Dataset Procesado")
                                    mostrar_primeros_registros(df_procesado)
                                else:
                                    st.error("Error al procesar los datos filtrados.")
                            else:
                                st.error("No se encontraron registros que coincidan con el criterio: empresa_outbound == 'Externo' Y empresa_inbound != 'Externo'")
            
            with tab2:
                st.subheader("Resultados y Exportación")
                
                if 'df_procesado' in st.session_state:
                    df_procesado = st.session_state['df_procesado']
                    
                    # Mostrar tabla con primeros 10 registros y columnas nuevas
                    mostrar_primeros_registros(df_procesado)
                    
                    st.divider()
                    
                    # Mostrar estadísticas generales
                    st.write("### 📈 Estadísticas Generales")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total registros", len(df_procesado))
                    
                    with col2:
                        # Fecha mínima y máxima
                        if 'Call Time' in df_procesado.columns and pd.api.types.is_datetime64_any_dtype(df_procesado['Call Time']):
                            fecha_min = df_procesado['Call Time'].min().strftime('%d/%m/%Y')
                            fecha_max = df_procesado['Call Time'].max().strftime('%d/%m/%Y')
                            st.metric("Rango de fechas", f"{fecha_min} a {fecha_max}")
                    
                    with col3:
                        # Máximo de recursos
                        if st.session_state.recursos_por_hora:
                            max_recursos = max(st.session_state.recursos_por_hora.values())
                            st.metric("Máximo recursos/hora", max_recursos)
                    
                    # Gráfico de proporciones por hora y día (MODIFICADO para empresa_outbound == "Externo")
                    crear_grafico_proporciones_dia_hora(df_procesado)
                    
                    # Exportación de datos
                    st.write("### 💾 Exportar Datos Procesados")
                    
                    col_exp1, col_exp2 = st.columns(2)
                    
                    with col_exp1:
                        # Exportar a CSV completo
                        csv = df_procesado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar CSV completo",
                            data=csv,
                            file_name="datos_procesados.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    
                    with col_exp2:
                        # Exportar a Excel
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            # Hoja 1: Datos completos
                            df_procesado.to_excel(writer, sheet_name='Datos_Completos', index=False)
                            
                            # Hoja 2: Estadísticas generales
                            stats_df = pd.DataFrame({
                                'Métrica': [
                                    'Total Registros',
                                    'Constante de Validación',
                                    'Máximo Recursos/Hora',
                                    'Suma Proporción Demanda',
                                    'Suma validador_recurso_hora',
                                    'Registros CCB (destino)',
                                    'Registros ODO (destino)',
                                    'Registros UDC (destino)',
                                    'Registros Origen Externo',
                                    'Registros Origen Interno'
                                ],
                                'Valor': [
                                    len(df_procesado),
                                    CONSTANTE_VALIDACION,
                                    max(st.session_state.recursos_por_hora.values()) if st.session_state.recursos_por_hora else 0,
                                    df_procesado['Proporcion_Equivalencia'].sum(),
                                    df_procesado['validador_recurso_hora'].sum(),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'CCB']),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'ODO']),
                                    len(df_procesado[df_procesado['empresa_inbound'] == 'UDC']),
                                    len(df_procesado[df_procesado['empresa_outbound'] == 'Externo']),
                                    len(df_procesado[df_procesado['empresa_outbound'] != 'Externo'])
                                ]
                            })
                            stats_df.to_excel(writer, sheet_name='Estadisticas_Generales', index=False)
                        
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Descargar como Excel",
                            data=buffer,
                            file_name="datos_procesados.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                
                else:
                    st.info("Primero procesa los datos en la pestaña 'Datos y Configuración'")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo sea un CSV válido con los campos requeridos.")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")

if __name__ == "__main__":
    main()
