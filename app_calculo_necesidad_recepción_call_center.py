import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para analizar demanda vs recursos")

# Constante para el cálculo
CONSTANTE_VALIDACION = 14.08

# Horas para ingresar recursos (6:00 a 19:00)
HORAS_DISPONIBLES = list(range(6, 20))  # 6:00 a 19:00

# Sidebar para cargar el archivo
with st.sidebar:
    st.header("Cargar Datos")
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    
    st.markdown("---")
    st.markdown("**Instrucciones:**")
    st.markdown("""
    1. Sube un archivo CSV con registros de llamadas
    2. Ingresa los recursos disponibles por hora (6:00-19:00)
    3. La app calculará la demanda promedio por hora y día
    4. Compara demanda vs recursos en la gráfica
    5. Analiza los resultados
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

# Función para procesar los datos y calcular demanda
def procesar_datos_demanda(df):
    """
    Procesa el DataFrame para calcular la demanda promedio por hora y día
    """
    df_procesado = df.copy()
    
    try:
        # Verificar columnas necesarias
        if 'Call Time' not in df_procesado.columns:
            st.error("El archivo no contiene la columna 'Call Time' necesaria.")
            return None
        
        # Convertir Call Time a datetime si es necesario
        try:
            df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'])
        except:
            df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'], errors='coerce')
        
        # Extraer hora y día de la semana
        df_procesado['Hora'] = df_procesado['Call Time'].dt.hour
        df_procesado['Dia_Semana'] = df_procesado['Call Time'].dt.day_name()
        df_procesado['Dia_Semana'] = df_procesado['Dia_Semana'].apply(traducir_dia)
        
        # Calcular conteo por hora y día
        demanda_por_hora_dia = df_procesado.groupby(['Dia_Semana', 'Hora']).size().reset_index(name='Conteo')
        
        # Calcular promedio por hora para cada día
        # Primero, obtener todas las fechas únicas
        df_procesado['Fecha'] = df_procesado['Call Time'].dt.date
        fechas_por_dia = df_procesado.groupby('Dia_Semana')['Fecha'].nunique().reset_index(name='Num_Dias')
        
        # Combinar con conteo
        demanda_con_dias = pd.merge(demanda_por_hora_dia, fechas_por_dia, on='Dia_Semana')
        
        # Calcular promedio
        demanda_con_dias['Promedio_Demanda'] = demanda_con_dias['Conteo'] / demanda_con_dias['Num_Dias']
        
        # Redondear a 2 decimales
        demanda_con_dias['Promedio_Demanda'] = demanda_con_dias['Promedio_Demanda'].round(2)
        
        # Ordenar por día y hora
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        demanda_con_dias['Dia_Semana'] = pd.Categorical(demanda_con_dias['Dia_Semana'], categories=orden_dias, ordered=True)
        demanda_con_dias = demanda_con_dias.sort_values(['Dia_Semana', 'Hora'])
        
        st.success("✅ Datos procesados y demanda calculada exitosamente")
        
        return demanda_con_dias[['Dia_Semana', 'Hora', 'Promedio_Demanda', 'Conteo', 'Num_Dias']]
        
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None

# Función para crear gráfica comparativa
def crear_grafica_comparativa(demanda_df, recursos_por_hora, dia_seleccionado):
    """
    Crea una gráfica comparando recursos disponibles vs demanda promedio
    """
    # Filtrar demanda para el día seleccionado
    demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
    
    if len(demanda_dia) == 0:
        st.warning(f"No hay datos de demanda para {dia_seleccionado}")
        return
    
    # Crear DataFrame para la gráfica
    # Primero, crear rango completo de horas de 0 a 23
    horas_completas = pd.DataFrame({'Hora': range(0, 24)})
    
    # Preparar datos de recursos
    recursos_lista = []
    for hora, valor in recursos_por_hora.items():
        recursos_lista.append({'Hora': hora, 'Recursos': valor * CONSTANTE_VALIDACION})
    
    recursos_df = pd.DataFrame(recursos_lista)
    
    # Combinar con horas completas
    recursos_completo = pd.merge(horas_completas, recursos_df, on='Hora', how='left')
    recursos_completo['Recursos'] = recursos_completo['Recursos'].fillna(0)
    
    # Preparar datos de demanda
    demanda_completo = pd.merge(horas_completas, demanda_dia[['Hora', 'Promedio_Demanda']], on='Hora', how='left')
    demanda_completo['Promedio_Demanda'] = demanda_completo['Promedio_Demanda'].fillna(0)
    
    # Combinar ambos DataFrames
    datos_grafica = pd.merge(recursos_completo, demanda_completo, on='Hora')
    
    # Crear gráfica
    st.write(f"### 📈 Comparación: Recursos vs Demanda - {dia_seleccionado}")
    
    # Configurar gráfica
    chart_data = datos_grafica.set_index('Hora')
    chart_data = chart_data.rename(columns={
        'Recursos': 'Recursos Disponibles',
        'Promedio_Demanda': 'Demanda Promedio'
    })
    
    # Mostrar gráfica
    st.line_chart(chart_data, height=500)
    
    # Mostrar tabla de datos
    with st.expander("📊 Ver datos detallados"):
        datos_tabla = datos_grafica.copy()
        datos_tabla['Hora_Formateada'] = datos_tabla['Hora'].apply(lambda x: f"{x}:00")
        datos_tabla['Recursos_Base'] = datos_tabla['Recursos'] / CONSTANTE_VALIDACION
        st.dataframe(datos_tabla[['Hora', 'Hora_Formateada', 'Recursos_Base', 
                                'Recursos Disponibles', 'Demanda Promedio']].round(2), 
                    use_container_width=True)
    
    # Calcular métricas de comparación
    st.write(f"**Métricas para {dia_seleccionado}:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Pico de demanda
        pico_demanda = datos_grafica['Promedio_Demanda'].max()
        hora_pico = datos_grafica.loc[datos_grafica['Promedio_Demanda'].idxmax(), 'Hora']
        st.metric("Pico de demanda", f"{pico_demanda:.0f} pacientes", f"Hora: {hora_pico}:00")
    
    with col2:
        # Pico de recursos
        pico_recursos = datos_grafica['Recursos'].max()
        hora_recursos = datos_grafica.loc[datos_grafica['Recursos'].idxmax(), 'Hora']
        st.metric("Máximo recursos", f"{pico_recursos:.0f}", f"Hora: {hora_recursos}:00")
    
    with col3:
        # Diferencia máxima
        datos_grafica['Diferencia'] = datos_grafica['Recursos'] - datos_grafica['Promedio_Demanda']
        max_exceso = datos_grafica['Diferencia'].max()
        max_deficit = datos_grafica['Diferencia'].min()
        
        if max_exceso > 0:
            st.metric("Mayor exceso", f"{max_exceso:.0f}")
        else:
            st.metric("Mayor déficit", f"{abs(max_deficit):.0f}")

# Función principal
def main():
    # Inicializar session state
    if 'recursos_por_hora' not in st.session_state:
        st.session_state.recursos_por_hora = {}
    if 'demanda_df' not in st.session_state:
        st.session_state.demanda_df = None
    
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2 = st.tabs(["📋 Datos y Configuración", "📊 Resultados y Análisis"])
            
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
                st.write(f"**Nota:** Cada valor se multiplicará por {CONSTANTE_VALIDACION} para calcular recursos disponibles")
                
                col_recursos1, col_recursos2 = st.columns([3, 2])
                
                with col_recursos1:
                    # Ingresar recursos por hora
                    recursos = ingresar_recursos_por_hora()
                    
                    # Guardar recursos en session state
                    st.session_state.recursos_por_hora = recursos
                    
                    # Calcular máximo de recursos base
                    if recursos:
                        max_recursos_base = max(recursos.values())
                        max_recursos_total = max_recursos_base * CONSTANTE_VALIDACION
                        st.metric("Máximo recursos base", f"{max_recursos_base}")
                        st.metric("Máximo recursos total", f"{max_recursos_total:.1f}")
                
                with col_recursos2:
                    # Mostrar gráfico de recursos por hora
                    if recursos:
                        st.write("**📈 Distribución de recursos por hora (base):**")
                        recursos_df = pd.DataFrame(list(recursos.items()), columns=['Hora', 'Recursos_Base'])
                        st.bar_chart(recursos_df.set_index('Hora')['Recursos_Base'])
                
                # Botón para procesar datos de demanda
                st.divider()
                st.subheader("Procesamiento de Datos de Demanda")
                
                if st.button("📊 Calcular Demanda Promedio", type="primary", use_container_width=True):
                    with st.spinner("Calculando demanda promedio por hora y día..."):
                        # Procesar datos para calcular demanda
                        demanda_df = procesar_datos_demanda(df)
                        
                        if demanda_df is not None:
                            # Guardar en session state
                            st.session_state.demanda_df = demanda_df
                            
                            # Mostrar resumen de demanda
                            st.write("**Resumen de demanda calculada:**")
                            
                            # Calcular días únicos
                            dias_unicos = demanda_df['Dia_Semana'].unique()
                            num_dias_por_dia = demanda_df[['Dia_Semana', 'Num_Dias']].drop_duplicates()
                            
                            col_dias1, col_dias2 = st.columns(2)
                            
                            with col_dias1:
                                st.write("**Días disponibles:**")
                                for _, row in num_dias_por_dia.iterrows():
                                    st.write(f"- {row['Dia_Semana']}: {row['Num_Dias']} días")
                            
                            with col_dias2:
                                # Calcular demanda promedio total por día
                                demanda_total_dia = demanda_df.groupby('Dia_Semana')['Promedio_Demanda'].sum().reset_index()
                                st.write("**Demanda promedio total por día:**")
                                for _, row in demanda_total_dia.iterrows():
                                    st.write(f"- {row['Dia_Semana']}: {row['Promedio_Demanda']:.0f} pacientes")
            
            with tab2:
                st.subheader("Resultados y Análisis")
                
                # Verificar que tenemos datos procesados
                if st.session_state.demanda_df is not None and st.session_state.recursos_por_hora:
                    demanda_df = st.session_state.demanda_df
                    recursos_por_hora = st.session_state.recursos_por_hora
                    
                    # Selector de día de la semana
                    dias_disponibles = sorted(demanda_df['Dia_Semana'].unique())
                    
                    st.write("### 🔍 Selecciona un día para analizar:")
                    dia_seleccionado = st.selectbox(
                        "Día de la semana:",
                        options=dias_disponibles,
                        key="selector_dia_analisis"
                    )
                    
                    # Mostrar información del día seleccionado
                    info_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado]
                    num_dias = info_dia['Num_Dias'].iloc[0] if len(info_dia) > 0 else 0
                    
                    st.info(f"**Información para {dia_seleccionado}:**")
                    st.write(f"- Basado en {num_dias} días de datos")
                    st.write(f"- Horas con datos: {len(info_dia)} horas del día")
                    
                    # Crear gráfica comparativa
                    crear_grafica_comparativa(demanda_df, recursos_por_hora, dia_seleccionado)
                    
                    # Exportación de datos
                    st.divider()
                    st.write("### 💾 Exportar Datos")
                    
                    col_exp1, col_exp2 = st.columns(2)
                    
                    with col_exp1:
                        # Exportar datos de demanda
                        csv_demanda = demanda_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Datos de Demanda",
                            data=csv_demanda,
                            file_name="demanda_promedio.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    
                    with col_exp2:
                        # Exportar configuración de recursos
                        recursos_df = pd.DataFrame({
                            'Hora': list(recursos_por_hora.keys()),
                            'Recursos_Base': list(recursos_por_hora.values()),
                            'Recursos_Total': [r * CONSTANTE_VALIDACION for r in recursos_por_hora.values()]
                        })
                        csv_recursos = recursos_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Configuración Recursos",
                            data=csv_recursos,
                            file_name="recursos_configuracion.csv",
                            mime="text/csv"
                        )
                
                else:
                    st.info("👈 Primero procesa los datos en la pestaña 'Datos y Configuración'")
                    if st.session_state.demanda_df is None:
                        st.warning("- Falta calcular la demanda promedio")
                    if not st.session_state.recursos_por_hora:
                        st.warning("- Falta configurar los recursos por hora")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo sea un CSV válido y tenga una columna 'Call Time'")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")

if __name__ == "__main__":
    main()
