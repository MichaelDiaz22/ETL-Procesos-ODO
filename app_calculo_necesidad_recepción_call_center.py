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

# Horas para ingresar recursos (6:00 a 19:00)
HORAS_DISPONIBLES = list(range(6, 20))  # 6:00 a 19:00

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
    5. **Validador Recurso/Hora**: (Recursos × {CONSTANTE_VALIDACION}) / Conteo por hora, fecha y rol
    6. **Validador Necesidad Personas/Hora**: Recursos / Conteo por hora, fecha y rol
    """)
    
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

# Función para ingresar recursos por hora
def ingresar_recursos_por_hora():
    """
    Muestra un formulario para ingresar la cantidad de recursos disponibles por hora
    """
    st.subheader("👥 Ingreso de Recursos Disponibles por Hora")
    st.info("Ingresa la cantidad de personas disponibles para cada hora (6:00 AM - 7:00 PM)")
    
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
    
    # Mostrar resumen de recursos
    st.write("**📋 Resumen de recursos ingresados:**")
    resumen_df = pd.DataFrame(list(recursos.items()), columns=['Hora', 'Recursos'])
    st.dataframe(resumen_df, use_container_width=True)
    
    # Gráfico de recursos por hora
    st.write("**📈 Distribución de recursos por hora:**")
    st.bar_chart(resumen_df.set_index('Hora')['Recursos'])
    
    return recursos

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
        
        # 11. PASO 7: Calcular validador_recurso_hora
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
        
        # 12. PASO 8: Calcular validador_necesidad_personas_hora
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
        
        st.success("✅ Datos procesados y cálculos realizados exitosamente")
        
        # Mostrar distribución de las nuevas columnas
        st.write("**📊 Distribución de las nuevas columnas de recursos:**")
        
        col_dist1, col_dist2 = st.columns(2)
        
        with col_dist1:
            st.write("**Distribución de validador_recurso_hora:**")
            st.dataframe(df_procesado['validador_recurso_hora'].describe().round(6), use_container_width=True)
            st.bar_chart(df_procesado['validador_recurso_hora'].value_counts().sort_index().head(20))
        
        with col_dist2:
            st.write("**Distribución de validador_necesidad_personas_hora:**")
            st.dataframe(df_procesado['validador_necesidad_personas_hora'].describe().round(6), use_container_width=True)
            st.bar_chart(df_procesado['validador_necesidad_personas_hora'].value_counts().sort_index().head(20))
        
        # Mostrar ejemplo de cálculo
        with st.expander("📝 Ver ejemplo de cálculo completo con recursos"):
            st.markdown(f"""
            **Fórmulas de cálculo con recursos:**
            
            1. **Validador Recurso/Hora:**
            ```
            validador_recurso_hora = (Recursos_Hora × {CONSTANTE_VALIDACION}) / Conteo_Hora_Fecha_Rol
            ```
            
            2. **Validador Necesidad Personas/Hora:**
            ```
            validador_necesidad_personas_hora = Recursos_Hora / Conteo_Hora_Fecha_Rol
            ```
            
            **Donde:**
            - `Recursos_Hora`: Cantidad de personas disponibles en esa hora
            - `Conteo_Hora_Fecha_Rol`: Número de registros con misma hora, fecha y rol_inbound
            - `{CONSTANTE_VALIDACION}`: Constante de validación
            
            **Ejemplo práctico:**
            
            Registro con:
            - Hora: 9:00 (Hora_Numerica = 9)
            - Fecha: "15/01/2026"
            - Rol: "Call center"
            
            **Suposiciones:**
            - Recursos disponibles a las 9:00: 5 personas
            - Total registros a las 9:00, fecha "15/01/2026", rol "Call center": 20
            
            **Cálculos:**
            1. **validador_recurso_hora:** (5 × {CONSTANTE_VALIDACION}) / 20 = {5 * CONSTANTE_VALIDACION} / 20 = {5 * CONSTANTE_VALIDACION / 20:.6f}
            2. **validador_necesidad_personas_hora:** 5 / 20 = 0.25
            """)
            
            # Mostrar un ejemplo real del dataset
            if len(df_procesado) > 0:
                ejemplo = df_procesado.iloc[0]
                st.write("**Ejemplo real del primer registro:**")
                st.write(f"- Hora: {ejemplo['Hora_Numerica']}:00")
                st.write(f"- Fecha: {ejemplo['Fecha_Creacion']}")
                st.write(f"- Rol Inbound: {ejemplo['rol_inbound']}")
                st.write(f"- Recursos disponibles a las {ejemplo['Hora_Numerica']}:00: {recursos_por_hora.get(ejemplo['Hora_Numerica'], 0)}")
                st.write(f"- Conteo registros misma hora/fecha/rol: {ejemplo['Conteo_Hora_Fecha_Rol']}")
                st.write(f"- **validador_recurso_hora: {ejemplo['validador_recurso_hora']:.6f}**")
                st.write(f"- **validador_necesidad_personas_hora: {ejemplo['validador_necesidad_personas_hora']:.6f}**")
        
        # Mostrar resumen de los cálculos
        st.write("**📊 Resumen de todos los cálculos:**")
        
        # Métricas para las nuevas columnas
        st.write("##### Métricas de Recursos por Hora:")
        col_rec1, col_rec2, col_rec3, col_rec4 = st.columns(4)
        
        with col_rec1:
            st.metric("Recursos/Hora Mín", f"{df_procesado['validador_recurso_hora'].min():.6f}")
        
        with col_rec2:
            st.metric("Recursos/Hora Máx", f"{df_procesado['validador_recurso_hora'].max():.6f}")
        
        with col_rec3:
            st.metric("Necesidad/Hora Mín", f"{df_procesado['validador_necesidad_personas_hora'].min():.6f}")
        
        with col_rec4:
            st.metric("Necesidad/Hora Máx", f"{df_procesado['validador_necesidad_personas_hora'].max():.6f}")
        
        # Análisis por hora con recursos
        st.write("**🕐 Análisis por Hora con Recursos:**")
        
        if 'Hora_Numerica' in df_procesado.columns:
            # Agrupar por hora
            analisis_hora = df_procesado.groupby('Hora_Numerica').agg({
                'validador_recurso_hora': ['count', 'mean', 'sum'],
                'validador_necesidad_personas_hora': ['mean', 'sum'],
                'Conteo_Hora_Fecha_Rol': 'mean'
            }).round(6)
            
            analisis_hora.columns = [
                'Cantidad Registros', 'Promedio Recursos/Hora', 'Suma Recursos/Hora',
                'Promedio Necesidad/Hora', 'Suma Necesidad/Hora',
                'Promedio Conteo Grupo'
            ]
            
            # Filtrar solo horas con registros
            analisis_hora = analisis_hora[analisis_hora['Cantidad Registros'] > 0]
            
            # Ordenar por hora
            analisis_hora = analisis_hora.sort_index()
            
            st.dataframe(analisis_hora, use_container_width=True)
            
            # Comparar recursos asignados vs necesidades
            st.write("**📈 Comparación Recursos Asignados vs Necesidades:**")
            
            comparacion_df = pd.DataFrame({
                'Hora': list(recursos_por_hora.keys()),
                'Recursos_Asignados': list(recursos_por_hora.values())
            })
            
            # Unir con análisis por hora
            comparacion_df = comparacion_df.merge(
                analisis_hora[['Promedio Necesidad/Hora', 'Promedio Conteo Grupo']],
                left_on='Hora',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # Calcular diferencia
            comparacion_df['Diferencia'] = comparacion_df['Recursos_Asignados'] - comparacion_df['Promedio Necesidad/Hora']
            
            st.dataframe(comparacion_df, use_container_width=True)
            
            # Gráfico comparativo
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.write("**Recursos Asignados vs Necesidades:**")
                st.line_chart(comparacion_df.set_index('Hora')[['Recursos_Asignados', 'Promedio Necesidad/Hora']])
            
            with col_graf2:
                st.write("**Diferencia (Asignados - Necesidad):**")
                st.bar_chart(comparacion_df.set_index('Hora')['Diferencia'])
        
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None
    
    return df_procesado

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
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Datos Originales", "👥 Recursos por Hora", "⚙️ Filtrar y Procesar", "📊 Resultados y Exportar"])
            
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
                st.subheader("Configuración de Recursos por Hora")
                
                # Ingresar recursos por hora
                recursos = ingresar_recursos_por_hora()
                
                # Guardar recursos en session state
                st.session_state.recursos_por_hora = recursos
                
                # Mostrar resumen
                st.success(f"✅ Recursos configurados para {len(recursos)} horas")
                
                # Análisis de rangos horarios
                st.write("**📊 Análisis de Rangos Horarios:**")
                
                # Calcular total de recursos por rangos
                recursos_df = pd.DataFrame(list(recursos.items()), columns=['Hora', 'Recursos'])
                
                # Definir rangos horarios
                rangos = {
                    'Mañana (6:00-11:00)': range(6, 12),
                    'Mediodía (12:00-14:00)': range(12, 15),
                    'Tarde (15:00-19:00)': range(15, 20)
                }
                
                for rango_nombre, horas in rangos.items():
                    total = sum(recursos.get(hora, 0) for hora in horas)
                    st.write(f"- **{rango_nombre}**: {total} recursos totales")
            
            with tab3:
                st.subheader("Filtrado y Cálculos")
                
                # Verificar que se hayan ingresado recursos
                if not st.session_state.recursos_por_hora:
                    st.warning("⚠️ Primero ingresa los recursos por hora en la pestaña 'Recursos por Hora'")
                    return
                
                # Primero aplicar el filtro
                st.write("### Paso 1: Aplicar Filtro por Códigos")
                st.info(f"Se filtrarán los registros cuyo campo 'To' contenga alguno de los {len(CODIGOS_FILTRAR)} códigos especificados")
                
                if st.button("Aplicar Filtro y Calcular", type="primary"):
                    with st.spinner("Aplicando filtro y realizando cálculos..."):
                        # Aplicar filtro
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
                                st.success(f"✅ Proceso completado. {len(df_procesado)} registros procesados.")
                                
                                # Mostrar vista previa de datos procesados
                                st.write("### Vista previa de datos procesados:")
                                
                                # Seleccionar columnas importantes para mostrar
                                columnas_a_mostrar = [
                                    'Call Time', 'From', 'To', 'Fecha_Creacion', 
                                    'Dia_Semana', 'Hora_Registro', 'rol_inbound',
                                    'Conteo_Hora_Fecha_Rol', 'validador_recurso_hora',
                                    'validador_necesidad_personas_hora'
                                ]
                                
                                # Filtrar solo las columnas que existen
                                columnas_existentes = [col for col in columnas_a_mostrar if col in df_procesado.columns]
                                
                                st.dataframe(df_procesado[columnas_existentes].head(20), use_container_width=True)
                            else:
                                st.error("Error al procesar los datos filtrados.")
                        else:
                            st.error("No se encontraron registros que coincidan con los códigos especificados o error en el filtrado.")
            
            with tab4:
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
                        # Suma total de validadores de recursos
                        suma_validador_recurso = df_procesado['validador_recurso_hora'].sum()
                        st.metric("Suma validador recursos", f"{suma_validador_recurso:.6f}")
                    
                    with col4:
                        # Suma total de necesidades
                        suma_necesidad = df_procesado['validador_necesidad_personas_hora'].sum()
                        st.metric("Suma necesidades", f"{suma_necesidad:.6f}")
                    
                    # Análisis por hora con todos los validadores
                    st.write("### 🕐 Análisis Comparativo por Hora")
                    
                    if 'Hora_Numerica' in df_procesado.columns:
                        analisis_comparativo = df_procesado.groupby('Hora_Numerica').agg({
                            'validador_demanda_personas_hora': ['count', 'mean', 'sum'],
                            'validador_recurso_hora': ['mean', 'sum'],
                            'validador_necesidad_personas_hora': ['mean', 'sum']
                        }).round(6)
                        
                        analisis_comparativo.columns = [
                            'Cantidad', 'Promedio Demanda', 'Suma Demanda',
                            'Promedio Recursos', 'Suma Recursos',
                            'Promedio Necesidad', 'Suma Necesidad'
                        ]
                        
                        # Filtrar solo horas con registros
                        analisis_comparativo = analisis_comparativo[analisis_comparativo['Cantidad'] > 0]
                        
                        # Ordenar por hora
                        analisis_comparativo = analisis_comparativo.sort_index()
                        
                        st.dataframe(analisis_comparativo, use_container_width=True)
                        
                        # Gráfico comparativo
                        st.write("**📈 Comparación de los tres validadores:**")
                        
                        # Seleccionar solo las columnas de promedios para el gráfico
                        datos_grafico = analisis_comparativo[['Promedio Demanda', 'Promedio Recursos', 'Promedio Necesidad']]
                        st.line_chart(datos_grafico)
                    
                    # Análisis por rol con recursos
                    st.write("### 👥 Análisis por Rol Inbound con Recursos")
                    
                    if 'rol_inbound' in df_procesado.columns:
                        analisis_rol_recursos = df_procesado.groupby('rol_inbound').agg({
                            'validador_recurso_hora': ['count', 'mean', 'sum'],
                            'validador_necesidad_personas_hora': ['mean', 'sum'],
                            'Conteo_Hora_Fecha_Rol': 'mean'
                        }).round(6)
                        
                        analisis_rol_recursos.columns = [
                            'Cantidad', 'Promedio Recursos/Hora', 'Suma Recursos/Hora',
                            'Promedio Necesidad/Hora', 'Suma Necesidad/Hora',
                            'Promedio Conteo Grupo'
                        ]
                        
                        st.dataframe(analisis_rol_recursos, use_container_width=True)
                    
                    # Exportación de datos
                    st.write("### 💾 Exportar Datos Procesados")
                    
                    col_exp1, col_exp2 = st.columns(2)
                    
                    with col_exp1:
                        # Exportar a CSV completo
                        csv = df_procesado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar CSV completo",
                            data=csv,
                            file_name="datos_con_calculos_completos.csv",
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
                                'Dia_Semana', 'Hora_Registro', 'rol_inbound',
                                'validador_demanda_personas_hora',
                                'validador_recurso_hora', 'validador_necesidad_personas_hora'
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
                            
                            # Hoja 2: Análisis por hora
                            if 'Hora_Numerica' in df_procesado.columns:
                                analisis_hora = df_procesado.groupby('Hora_Numerica').agg({
                                    'validador_demanda_personas_hora': ['count', 'mean', 'sum'],
                                    'validador_recurso_hora': ['mean', 'sum'],
                                    'validador_necesidad_personas_hora': ['mean', 'sum']
                                }).round(6)
                                analisis_hora.to_excel(writer, sheet_name='Analisis_Por_Hora')
                            
                            # Hoja 3: Recursos ingresados
                            recursos_df = pd.DataFrame({
                                'Hora': list(st.session_state.recursos_por_hora.keys()),
                                'Recursos_Asignados': list(st.session_state.recursos_por_hora.values())
                            })
                            recursos_df.to_excel(writer, sheet_name='Recursos_Asignados', index=False)
                            
                            # Hoja 4: Estadísticas generales
                            stats_df = pd.DataFrame({
                                'Métrica': [
                                    'Total Registros',
                                    'Constante de Validación',
                                    'Total Recursos Asignados',
                                    'Suma validador_demanda_personas_hora',
                                    'Suma validador_recurso_hora',
                                    'Suma validador_necesidad_personas_hora',
                                    'Horas configuradas (6:00-19:00)',
                                    'Recursos promedio por hora',
                                    'Necesidad promedio por hora'
                                ],
                                'Valor': [
                                    len(df_procesado),
                                    CONSTANTE_VALIDACION,
                                    sum(st.session_state.recursos_por_hora.values()),
                                    df_procesado['validador_demanda_personas_hora'].sum(),
                                    df_procesado['validador_recurso_hora'].sum(),
                                    df_procesado['validador_necesidad_personas_hora'].sum(),
                                    len(HORAS_DISPONIBLES),
                                    df_procesado['validador_recurso_hora'].mean() if len(df_procesado) > 0 else 0,
                                    df_procesado['validador_necesidad_personas_hora'].mean() if len(df_procesado) > 0 else 0
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
        with st.expander("Ver estructura esperada del CSV y cálculos"):
            st.write(f"""
            ## Cálculos y Recursos por Hora
            
            **1. Configuración de Recursos:**
            - Ingresa la cantidad de personas disponibles por hora (6:00 AM - 7:00 PM)
            - Estos valores se usarán para calcular los nuevos validadores
            
            **2. Nuevos Cálculos con Recursos:**
            
            **validador_recurso_hora:**
            ```
            validador_recurso_hora = (Recursos_Hora × {CONSTANTE_VALIDACION}) / Conteo_Hora_Fecha_Rol
            ```
            
            **validador_necesidad_personas_hora:**
            ```
            validador_necesidad_personas_hora = Recursos_Hora / Conteo_Hora_Fecha_Rol
            ```
            
            **Donde:**
            - `Recursos_Hora`: Personas disponibles en esa hora (ingresado por usuario)
            - `Conteo_Hora_Fecha_Rol`: Registros con misma hora, fecha y rol_inbound
            - `{CONSTANTE_VALIDACION}`: Constante de validación
            
            **3. Ejemplo Práctico:**
            
            **Configuración:**
            - Recursos a las 10:00: 8 personas
            - Registros 10:00, fecha "20/01/2026", rol "Call center": 25
            
            **Cálculos:**
            1. **validador_recurso_hora:** (8 × {CONSTANTE_VALIDACION}) / 25 = {8 * CONSTANTE_VALIDACION / 25:.6f}
            2. **validador_necesidad_personas_hora:** 8 / 25 = 0.32
            
            **Interpretación:**
            - **validador_recurso_hora**: Eficiencia de recursos ajustada por constante
            - **validador_necesidad_personas_hora**: Personas por registro (necesidad real)
            """)

if __name__ == "__main__":
    main()
