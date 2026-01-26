import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from fpdf import FPDF
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para analizar demanda vs recursos")

# Constante para el cálculo de recursos
CONSTANTE_VALIDACION = 14.08
CONSTANTE_DEMANDA_A_RECURSOS = 3.0

# Lista de códigos que representan extensiones internas
CODIGOS_EXTENSION = [
    '(0220)', '(0221)', '(0222)', '(0303)', '(0305)', '(0308)', '(0316)', '(0320)', 
    '(0323)', '(0324)', '(0327)', '(0331)', '(0404)', '(0407)', '(0410)', '(0412)', 
    '(0413)', '(0414)', '(0415)', '(0417)', '(2001)', '(2002)', '(2003)', '(2004)', 
    '(2005)', '(2006)', '(2007)', '(2008)', '(2009)', '(2010)', '(2011)', '(2012)', 
    '(2013)', '(2014)', '(2015)', '(2016)', '(2017)', '(2018)', '(2019)', '(2021)', 
    '(2022)', '(2023)', '(2024)', '(2025)', '(2026)', '(2028)', '(2029)', '(2030)', 
    '(2032)', '(2034)', '(2035)', '(8000)', '(8002)', '(8003)', '(8051)', '(8052)', 
    '(8062)', '(8063)', '(8064)', '(8071)', '(8072)', '(8079)', '(8080)'
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
    1. Sube un archivo CSV con registros de llamadas
    2. Ingresa los recursos disponibles por hora (6:00-19:00)
    3. La app calculará la demanda promedio por hora y día
    4. **Filtro aplicado**: Llamadas externas → internas
    5. Compara demanda vs recursos en la gráfica
    6. Analiza los resultados
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

# Función para determinar si un número es extensión interna
def es_extension_interna(numero):
    """
    Determina si un número contiene algún código de extensión interna
    """
    if pd.isna(numero):
        return False
    
    numero_str = str(numero)
    for extension in CODIGOS_EXTENSION:
        if extension in numero_str:
            return True
    return False

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

# Función para procesar los datos y calcular demanda CON FILTRO
def procesar_datos_demanda_filtrada(df):
    """
    Procesa el DataFrame para calcular la demanda promedio por hora y día
    APLICANDO FILTRO: From = NO extensión (externo), To = SÍ extensión (interno)
    """
    df_procesado = df.copy()
    
    try:
        # Verificar columnas necesarias
        columnas_requeridas = ['Call Time', 'From', 'To']
        for col in columnas_requeridas:
            if col not in df_procesado.columns:
                st.error(f"El archivo no contiene la columna '{col}' necesaria.")
                return None
        
        # Convertir Call Time a datetime si es necesario
        try:
            df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'])
        except:
            df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'], errors='coerce')
        
        # Eliminar filas con Call Time nulo
        df_procesado = df_procesado.dropna(subset=['Call Time'])
        
        if len(df_procesado) == 0:
            st.error("No hay fechas válidas en los datos.")
            return None
        
        # Aplicar filtro: From = NO extensión (externo), To = SÍ extensión (interno)
        df_procesado['From_es_extension'] = df_procesado['From'].apply(es_extension_interna)
        df_procesado['To_es_extension'] = df_procesado['To'].apply(es_extension_interna)
        
        # Filtrar: origen externo Y destino interno
        mascara = (~df_procesado['From_es_extension']) & (df_procesado['To_es_extension'])
        df_filtrado = df_procesado[mascara].copy()
        
        # Mostrar estadísticas del filtro
        total_registros = len(df_procesado)
        registros_filtrados = len(df_filtrado)
        porcentaje_filtrado = (registros_filtrados / total_registros * 100) if total_registros > 0 else 0
        
        st.info(f"**Filtro aplicado:** {registros_filtrados:,} de {total_registros:,} registros ({porcentaje_filtrado:.1f}%)")
        
        if registros_filtrados == 0:
            st.warning("No se encontraron registros que cumplan el criterio de filtro.")
            return None
        
        # Extraer hora, día de la semana y fecha
        df_filtrado['Hora'] = df_filtrado['Call Time'].dt.hour
        df_filtrado['Dia_Semana'] = df_filtrado['Call Time'].dt.day_name()
        df_filtrado['Dia_Semana'] = df_filtrado['Dia_Semana'].apply(traducir_dia)
        df_filtrado['Fecha'] = df_filtrado['Call Time'].dt.date
        
        # Verificar que tenemos datos
        if len(df_filtrado) == 0:
            st.warning("No hay datos después del filtro.")
            return None
        
        # Mostrar información de las fechas encontradas
        fecha_min = df_filtrado['Fecha'].min()
        fecha_max = df_filtrado['Fecha'].max()
        dias_totales = (fecha_max - fecha_min).days + 1
        st.info(f"**Rango de fechas:** {fecha_min} a {fecha_max} ({dias_totales} días)")
        
        # Contar el número de días únicos por día de la semana
        dias_por_semana = df_filtrado.groupby('Dia_Semana')['Fecha'].nunique().reset_index()
        dias_por_semana.columns = ['Dia_Semana', 'Num_Dias']
        
        # Agrupar por día de la semana, hora y fecha para contar llamadas
        # Primero agrupar por fecha, día y hora
        llamadas_por_hora_fecha = df_filtrado.groupby(['Fecha', 'Dia_Semana', 'Hora']).size().reset_index(name='Llamadas')
        
        # Ahora calcular el promedio por día de la semana y hora
        demanda_promedio = llamadas_por_hora_fecha.groupby(['Dia_Semana', 'Hora'])['Llamadas'].mean().reset_index()
        demanda_promedio.rename(columns={'Llamadas': 'Promedio_Demanda'}, inplace=True)
        demanda_promedio['Promedio_Demanda'] = demanda_promedio['Promedio_Demanda'].round(2)
        
        # Combinar con el número de días
        demanda_final = pd.merge(demanda_promedio, dias_por_semana, on='Dia_Semana')
        
        # Calcular Recursos Necesarios (demanda promedio ÷ 3)
        demanda_final['Recursos_Necesarios'] = (demanda_final['Promedio_Demanda'] / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
        
        # Ordenar por día y hora
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        demanda_final['Dia_Semana'] = pd.Categorical(demanda_final['Dia_Semana'], categories=orden_dias, ordered=True)
        demanda_final = demanda_final.sort_values(['Dia_Semana', 'Hora'])
        
        # Mostrar resumen estadístico
        st.success("✅ Demanda promedio calculada correctamente")
        st.write(f"**Resumen por día de la semana:**")
        for dia in orden_dias:
            if dia in demanda_final['Dia_Semana'].unique():
                dias_count = dias_por_semana[dias_por_semana['Dia_Semana'] == dia]['Num_Dias'].values[0]
                demanda_dia = demanda_final[demanda_final['Dia_Semana'] == dia]['Promedio_Demanda'].sum()
                st.write(f"- {dia}: {dias_count} días, demanda total: {demanda_dia:.1f} llamadas")
        
        return demanda_final[['Dia_Semana', 'Hora', 'Promedio_Demanda', 'Recursos_Necesarios', 'Num_Dias']]
        
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None

# Función para crear gráfica comparativa
def crear_grafica_comparativa(demanda_df, recursos_por_hora, dia_seleccionado):
    """
    Crea una gráfica comparando recursos disponibles vs demanda promedio
    """
    if dia_seleccionado == "Todos":
        # Filtrar solo días de semana (Lunes a Viernes)
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
        demanda_dia = demanda_df[demanda_df['Dia_Semana'].isin(dias_semana)].copy()
        
        if len(demanda_dia) == 0:
            st.warning("No hay datos de demanda para días de semana")
            return
        
        # Calcular promedio por hora para todos los días de semana
        demanda_promedio = demanda_dia.groupby('Hora').agg({
            'Promedio_Demanda': 'mean',
            'Recursos_Necesarios': 'mean'
        }).reset_index()
        
        demanda_promedio['Promedio_Demanda'] = demanda_promedio['Promedio_Demanda'].round(2)
        demanda_promedio['Recursos_Necesarios'] = demanda_promedio['Recursos_Necesarios'].round(2)
        
        demanda_dia = demanda_promedio
        titulo_dia = "Todos (Lunes a Viernes)"
    else:
        # Filtrar demanda para el día seleccionado
        demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
        titulo_dia = dia_seleccionado
    
    if len(demanda_dia) == 0:
        st.warning(f"No hay datos de demanda para {titulo_dia}")
        return
    
    # Crear DataFrame para la gráfica
    horas_completas = pd.DataFrame({'Hora': range(0, 24)})
    
    # Preparar datos de recursos (solo para días de semana)
    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
        recursos_lista = []
        for hora, valor in recursos_por_hora.items():
            recursos_lista.append({'Hora': hora, 'Capacidad_Disponible': valor * CONSTANTE_VALIDACION})
        
        recursos_df = pd.DataFrame(recursos_lista)
        
        # Combinar con horas completas
        recursos_completo = pd.merge(horas_completas, recursos_df, on='Hora', how='left')
        recursos_completo['Capacidad_Disponible'] = recursos_completo['Capacidad_Disponible'].fillna(0)
    else:
        # Para sábado y domingo, no mostrar recursos
        recursos_completo = horas_completas.copy()
        recursos_completo['Capacidad_Disponible'] = 0
    
    # Preparar datos de demanda
    if dia_seleccionado == "Todos":
        demanda_completo = pd.merge(horas_completas, demanda_dia[['Hora', 'Promedio_Demanda']], on='Hora', how='left')
    else:
        demanda_completo = pd.merge(horas_completas, demanda_dia[['Hora', 'Promedio_Demanda']], on='Hora', how='left')
    
    demanda_completo['Promedio_Demanda'] = demanda_completo['Promedio_Demanda'].fillna(0)
    
    # Combinar ambos DataFrames
    datos_grafica = pd.merge(recursos_completo, demanda_completo, on='Hora')
    
    # Crear gráfica
    st.write(f"### 📈 Comparación: Capacidad vs Demanda - {titulo_dia}")
    
    # Para sábado y domingo, solo mostrar demanda
    if dia_seleccionado in ['Sábado', 'Domingo']:
        chart_data = datos_grafica[['Hora', 'Promedio_Demanda']].set_index('Hora')
        chart_data = chart_data.rename(columns={'Promedio_Demanda': 'Demanda Promedio'})
    else:
        chart_data = datos_grafica[['Hora', 'Capacidad_Disponible', 'Promedio_Demanda']].set_index('Hora')
        chart_data = chart_data.rename(columns={
            'Capacidad_Disponible': 'Capacidad Disponible',
            'Promedio_Demanda': 'Demanda Promedio'
        })
    
    # Mostrar gráfica
    st.line_chart(chart_data, height=500)
    
    # Calcular métricas
    suma_demanda = datos_grafica['Promedio_Demanda'].sum()
    suma_recursos_necesarios = (suma_demanda / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
    
    # Calcular diferencia y encontrar picos (solo para días con capacidad disponible)
    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
        datos_grafica['Diferencia'] = datos_grafica['Capacidad_Disponible'] - datos_grafica['Promedio_Demanda']
        max_exceso = datos_grafica['Diferencia'].max()
        max_deficit = datos_grafica['Diferencia'].min()
        hora_max_exceso = datos_grafica.loc[datos_grafica['Diferencia'].idxmax(), 'Hora'] if max_exceso > 0 else None
        hora_max_deficit = datos_grafica.loc[datos_grafica['Diferencia'].idxmin(), 'Hora'] if max_deficit < 0 else None
    
    # Mostrar métricas
    st.write(f"**Métricas para {titulo_dia}:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Sumatoria de demanda promedio
        st.metric("Sumatoria Demanda", f"{suma_demanda:.0f} llamadas")
    
    with col2:
        if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
            # Pico de capacidad disponible
            pico_capacidad = datos_grafica['Capacidad_Disponible'].max()
            hora_capacidad = datos_grafica.loc[datos_grafica['Capacidad_Disponible'].idxmax(), 'Hora']
            st.metric("Pico Capacidad Disponible", f"{pico_capacidad:.0f}", f"Hora: {hora_capacidad}:00")
        else:
            # Para sábado y domingo, mostrar recursos necesarios
            st.metric("Recursos Necesarios", f"{suma_recursos_necesarios:.1f}", "Demanda total ÷ 3")
    
    with col3:
        if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
            if max_exceso > 0:
                st.metric("Mayor Exceso", f"{max_exceso:.0f}", f"Hora: {hora_max_exceso}:00")
            elif max_deficit < 0:
                st.metric("Mayor Déficit", f"{abs(max_deficit):.0f}", f"Hora: {hora_max_deficit}:00")
            else:
                st.metric("Equilibrio", "Perfecto", "Sin exceso ni déficit")
        else:
            # Para sábado y domingo, mostrar pico de demanda
            pico_demanda = datos_grafica['Promedio_Demanda'].max()
            hora_pico = datos_grafica.loc[datos_grafica['Promedio_Demanda'].idxmax(), 'Hora']
            recursos_pico = (pico_demanda / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
            st.metric("Pico Demanda", f"{pico_demanda:.0f} llamadas", f"Recursos: {recursos_pico}")

# Función para preparar datos para modelos de predicción
def preparar_datos_para_prediccion(df):
    """
    Prepara los datos para entrenar modelos de predicción
    """
    try:
        # Convertir Call Time a datetime
        df['Call Time'] = pd.to_datetime(df['Call Time'])
        
        # Aplicar filtro: From = NO extensión (externo), To = SÍ extensión (interno)
        df['From_es_extension'] = df['From'].apply(es_extension_interna)
        df['To_es_extension'] = df['To'].apply(es_extension_interna)
        
        # Filtrar: origen externo Y destino interno
        mascara = (~df['From_es_extension']) & (df['To_es_extension'])
        df_filtrado = df[mascara].copy()
        
        if len(df_filtrado) == 0:
            return None, None, None
        
        # Extraer características
        df_filtrado['Hora'] = df_filtrado['Call Time'].dt.hour
        df_filtrado['Dia_Semana_Num'] = df_filtrado['Call Time'].dt.dayofweek  # 0=Lunes, 6=Domingo
        df_filtrado['Mes'] = df_filtrado['Call Time'].dt.month
        df_filtrado['Dia_Mes'] = df_filtrado['Call Time'].dt.day
        
        # Agrupar por día y hora para obtener datos diarios
        df_agrupado = df_filtrado.groupby(['Dia_Semana_Num', 'Hora', 'Mes', 'Dia_Mes']).size().reset_index(name='Llamadas')
        
        # Preparar características y variable objetivo
        X = df_agrupado[['Dia_Semana_Num', 'Hora', 'Mes', 'Dia_Mes']]
        y = df_agrupado['Llamadas']
        
        return X, y, df_agrupado
        
    except Exception as e:
        st.error(f"Error preparando datos para predicción: {e}")
        return None, None, None

# Función para entrenar y evaluar modelos
def entrenar_modelos_prediccion(X, y):
    """
    Entrena y evalúa diferentes modelos de predicción
    """
    resultados = {}
    
    # Dividir datos en entrenamiento y prueba (70%/30%)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    # Modelo 1: Regresión Lineal
    with st.spinner("Entrenando Regresión Lineal..."):
        modelo_lr = LinearRegression()
        modelo_lr.fit(X_train, y_train)
        y_pred_lr = modelo_lr.predict(X_test)
        
        resultados['Regresión Lineal'] = {
            'modelo': modelo_lr,
            'mse': mean_squared_error(y_test, y_pred_lr),
            'mae': mean_absolute_error(y_test, y_pred_lr),
            'r2': r2_score(y_test, y_pred_lr),
            'predicciones': y_pred_lr
        }
    
    # Modelo 2: MLP (Red Neuronal)
    with st.spinner("Entrenando MLP (Red Neuronal)..."):
        modelo_mlp = MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
        modelo_mlp.fit(X_train, y_train)
        y_pred_mlp = modelo_mlp.predict(X_test)
        
        resultados['MLP (Red Neuronal)'] = {
            'modelo': modelo_mlp,
            'mse': mean_squared_error(y_test, y_pred_mlp),
            'mae': mean_absolute_error(y_test, y_pred_mlp),
            'r2': r2_score(y_test, y_pred_mlp),
            'predicciones': y_pred_mlp
        }
    
    # Modelo 3: Gradient Boosting
    with st.spinner("Entrenando Gradient Boosting..."):
        modelo_gb = GradientBoostingRegressor(n_estimators=100, random_state=42)
        modelo_gb.fit(X_train, y_train)
        y_pred_gb = modelo_gb.predict(X_test)
        
        resultados['Gradient Boosting'] = {
            'modelo': modelo_gb,
            'mse': mean_squared_error(y_test, y_pred_gb),
            'mae': mean_absolute_error(y_test, y_pred_gb),
            'r2': r2_score(y_test, y_pred_gb),
            'predicciones': y_pred_gb
        }
    
    return resultados, X_test, y_test

# Función para crear gráfica de predicción
def crear_grafica_prediccion(dia_seleccionado, predicciones_dia, recursos_por_hora, demanda_promedio_actual):
    """
    Crea una gráfica con las predicciones para un día específico
    """
    # Crear DataFrame con las predicciones por hora
    horas = list(range(24))
    predicciones_por_hora = []
    
    for hora in horas:
        prediccion = predicciones_dia.get(hora, 0)
        promedio_actual = demanda_promedio_actual.get(hora, 0)
        capacidad = recursos_por_hora.get(hora, 0) * CONSTANTE_VALIDACION if hora in recursos_por_hora else 0
        
        predicciones_por_hora.append({
            'Hora': hora,
            'Predicción': prediccion,
            'Promedio Actual': promedio_actual,
            'Capacidad Disponible': capacidad
        })
    
    df_grafica = pd.DataFrame(predicciones_por_hora)
    
    # Crear gráfica
    st.write(f"### 📈 Predicción vs Realidad - {dia_seleccionado}")
    
    chart_data = df_grafica[['Hora', 'Predicción', 'Promedio Actual', 'Capacidad Disponible']].set_index('Hora')
    
    # Mostrar gráfica
    st.line_chart(chart_data, height=500)
    
    # Calcular métricas
    suma_prediccion = df_grafica['Predicción'].sum()
    suma_promedio = df_grafica['Promedio Actual'].sum()
    suma_capacidad = df_grafica['Capacidad Disponible'].sum()
    
    diferencia_prediccion = suma_prediccion - suma_promedio
    porcentaje_diferencia = (diferencia_prediccion / suma_promedio * 100) if suma_promedio > 0 else 0
    
    # Calcular déficit predicho
    deficit_prediccion = max(0, suma_prediccion - suma_capacidad)
    deficit_promedio = max(0, suma_promedio - suma_capacidad)
    diferencia_deficit = deficit_prediccion - deficit_promedio
    
    return {
        'suma_prediccion': suma_prediccion,
        'suma_promedio': suma_promedio,
        'diferencia_prediccion': diferencia_prediccion,
        'porcentaje_diferencia': porcentaje_diferencia,
        'deficit_prediccion': deficit_prediccion,
        'deficit_promedio': deficit_promedio,
        'diferencia_deficit': diferencia_deficit,
        'df_grafica': df_grafica
    }

# Función principal
def main():
    # Inicializar session state
    if 'recursos_por_hora' not in st.session_state:
        st.session_state.recursos_por_hora = {}
    if 'demanda_df' not in st.session_state:
        st.session_state.demanda_df = None
    if 'modelos_entrenados' not in st.session_state:
        st.session_state.modelos_entrenados = None
    if 'mejor_modelo' not in st.session_state:
        st.session_state.mejor_modelo = None
    if 'metricas_modelos' not in st.session_state:
        st.session_state.metricas_modelos = None
    if 'datos_prediccion' not in st.session_state:
        st.session_state.datos_prediccion = None
    
    if uploaded_file is not None:
        try:
            # Leer el archivo CSV
            df = pd.read_csv(uploaded_file)
            
            # Mostrar pestañas para diferentes vistas
            tab1, tab2, tab3 = st.tabs(["📋 Datos y Configuración", "📊 Resultados y Análisis", "🤖 Predicción de Demanda"])
            
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
                st.write(f"**Nota:** Cada valor se multiplicará por {CONSTANTE_VALIDACION} para calcular capacidad disponible")
                
                col_recursos1, col_recursos2 = st.columns([3, 2])
                
                with col_recursos1:
                    # Ingresar recursos por hora
                    recursos = ingresar_recursos_por_hora()
                    
                    # Guardar recursos en session state
                    st.session_state.recursos_por_hora = recursos
                    
                    # Calcular máximo de recursos base
                    if recursos:
                        max_recursos_base = max(recursos.values())
                        max_capacidad = max_recursos_base * CONSTANTE_VALIDACION
                        st.metric("Máximo recursos base", f"{max_recursos_base}")
                        st.metric("Máxima capacidad", f"{max_capacidad:.1f}")
                
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
                    with st.spinner("Calculando demanda promedio..."):
                        # Procesar datos para calcular demanda CON FILTRO
                        demanda_df = procesar_datos_demanda_filtrada(df)
                        
                        if demanda_df is not None:
                            # Guardar en session state
                            st.session_state.demanda_df = demanda_df
            
            with tab2:
                st.subheader("Resultados y Análisis")
                
                # Verificar que tenemos datos procesados
                if st.session_state.demanda_df is not None and st.session_state.recursos_por_hora:
                    demanda_df = st.session_state.demanda_df
                    recursos_por_hora = st.session_state.recursos_por_hora
                    
                    # Obtener días disponibles en orden correcto
                    orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo', 'Todos']
                    dias_disponibles = []
                    
                    for dia in orden_dias:
                        if dia == "Todos":
                            # Verificar si hay datos de lunes a viernes
                            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                            if any(dia_sem in demanda_df['Dia_Semana'].unique() for dia_sem in dias_semana):
                                dias_disponibles.append(dia)
                        elif dia in demanda_df['Dia_Semana'].unique():
                            dias_disponibles.append(dia)
                    
                    if not dias_disponibles:
                        st.warning("No hay días disponibles para mostrar")
                        return
                    
                    st.write("### 🔍 Selecciona un día para analizar:")
                    dia_seleccionado = st.selectbox(
                        "Día de la semana:",
                        options=dias_disponibles,
                        key="selector_dia_analisis"
                    )
                    
                    # Crear gráfica comparativa
                    crear_grafica_comparativa(demanda_df, recursos_por_hora, dia_seleccionado)
                    
                    # Exportación de datos
                    st.divider()
                    st.write("### 💾 Exportar Datos")
                    
                    # Selector de formato de exportación
                    formato_exportacion = st.radio(
                        "Selecciona formato de exportación:",
                        ["PDF", "CSV", "XLSX"],
                        horizontal=True,
                        key="formato_exportacion"
                    )
                    
                    # Preparar datos para exportación
                    if dia_seleccionado == "Todos":
                        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                        demanda_dia = demanda_df[demanda_df['Dia_Semana'].isin(dias_semana)].copy()
                        # Calcular promedio por hora
                        export_data = demanda_dia.groupby('Hora').agg({
                            'Promedio_Demanda': 'mean',
                            'Recursos_Necesarios': 'mean'
                        }).reset_index()
                        
                        export_data['Promedio_Demanda'] = export_data['Promedio_Demanda'].round(2)
                        export_data['Recursos_Necesarios'] = export_data['Recursos_Necesarios'].round(2)
                        nombre_base = "promedio_lv"
                    else:
                        demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
                        export_data = demanda_dia[['Hora', 'Promedio_Demanda', 'Recursos_Necesarios']].copy()
                        nombre_base = dia_seleccionado.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                    
                    # Para días con capacidad disponible, agregar columnas adicionales
                    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
                        export_data['Recursos_Base'] = export_data['Hora'].apply(lambda h: recursos_por_hora.get(h, 0))
                        export_data['Capacidad_Disponible'] = (export_data['Recursos_Base'] * CONSTANTE_VALIDACION).round(2)
                        export_data['Diferencia'] = (export_data['Capacidad_Disponible'] - export_data['Promedio_Demanda']).round(2)
                    
                    # Botones de descarga
                    if formato_exportacion == "PDF":
                        # Función para generar PDF estaría aquí
                        pass
                    
                    elif formato_exportacion == "CSV":
                        csv_data = export_data.to_csv(index=False).encode('utf-8')
                        nombre_archivo = f"reporte_{nombre_base}.csv"
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv_data,
                            file_name=nombre_archivo,
                            mime="text/csv",
                            type="primary",
                            use_container_width=True
                        )
                    
                    elif formato_exportacion == "XLSX":
                        # Crear Excel en memoria
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            export_data.to_excel(writer, index=False, sheet_name='Reporte')
                        
                        excel_data = output.getvalue()
                        nombre_archivo = f"reporte_{nombre_base}.xlsx"
                        st.download_button(
                            label="📥 Descargar Excel",
                            data=excel_data,
                            file_name=nombre_archivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True
                        )
                
                else:
                    st.info("👈 Primero procesa los datos en la pestaña 'Datos y Configuración'")
                    if st.session_state.demanda_df is None:
                        st.warning("- Falta calcular la demanda promedio")
                    if not st.session_state.recursos_por_hora:
                        st.warning("- Falta configurar los recursos por hora")
            
            with tab3:
                st.subheader("🤖 Predicción de Demanda con Machine Learning")
                st.info("Esta sección utiliza modelos de machine learning para predecir la demanda futura de llamadas")
                
                # Verificar que tenemos datos procesados
                if st.session_state.demanda_df is not None and st.session_state.recursos_por_hora:
                    
                    # Botón para iniciar el procesamiento de predicción
                    st.divider()
                    st.write("### 🚀 Configuración de Predicción")
                    
                    if st.button("🤖 Ejecutar Modelos de Predicción", type="primary", use_container_width=True):
                        with st.spinner("Preparando datos y entrenando modelos..."):
                            # Preparar datos para predicción
                            X, y, datos_agrupados = preparar_datos_para_prediccion(df)
                            
                            if X is not None and y is not None:
                                # Entrenar y evaluar modelos
                                resultados, X_test, y_test = entrenar_modelos_prediccion(X, y)
                                
                                # Guardar resultados en session state
                                st.session_state.modelos_entrenados = resultados
                                st.session_state.datos_prediccion = {
                                    'X_test': X_test,
                                    'y_test': y_test,
                                    'datos_agrupados': datos_agrupados
                                }
                                
                                # Determinar el mejor modelo (basado en R²)
                                mejor_modelo_nombre = None
                                mejor_r2 = -float('inf')
                                metricas_comparativas = []
                                
                                for nombre, resultado in resultados.items():
                                    if resultado['r2'] > mejor_r2:
                                        mejor_r2 = resultado['r2']
                                        mejor_modelo_nombre = nombre
                                    
                                    metricas_comparativas.append({
                                        'Modelo': nombre,
                                        'MSE': resultado['mse'],
                                        'MAE': resultado['mae'],
                                        'R²': resultado['r2']
                                    })
                                
                                st.session_state.mejor_modelo = mejor_modelo_nombre
                                st.session_state.metricas_modelos = pd.DataFrame(metricas_comparativas)
                                
                                st.success("✅ Modelos entrenados exitosamente!")
                                
                                # Mostrar comparativa de modelos
                                st.write("### 📊 Comparativa de Modelos")
                                st.dataframe(st.session_state.metricas_modelos, use_container_width=True)
                                
                                # Mostrar el mejor modelo
                                st.info(f"**Mejor modelo:** {mejor_modelo_nombre} (R² = {mejor_r2:.4f})")
                            else:
                                st.error("No hay suficientes datos para entrenar los modelos de predicción")
                    
                    # Si ya tenemos modelos entrenados, mostrar la interfaz de predicción
                    if st.session_state.modelos_entrenados is not None:
                        st.divider()
                        st.write("### 🔍 Visualización de Predicciones")
                        
                        # Obtener datos necesarios
                        demanda_df = st.session_state.demanda_df
                        recursos_por_hora = st.session_state.recursos_por_hora
                        mejor_modelo_nombre = st.session_state.mejor_modelo
                        mejor_modelo = st.session_state.modelos_entrenados[mejor_modelo_nombre]['modelo']
                        datos_agrupados = st.session_state.datos_prediccion['datos_agrupados']
                        
                        # Crear un mapeo de día de semana numérico a nombre
                        dias_numericos = {
                            0: 'Lunes',
                            1: 'Martes',
                            2: 'Miércoles',
                            3: 'Jueves',
                            4: 'Viernes',
                            5: 'Sábado',
                            6: 'Domingo'
                        }
                        
                        # Obtener días disponibles para predicción (solo L-V que tengan datos)
                        dias_disponibles_pred = []
                        for dia_num, dia_nombre in dias_numericos.items():
                            if dia_nombre in demanda_df['Dia_Semana'].unique() and dia_num <= 4:  # Solo L-V
                                dias_disponibles_pred.append(dia_nombre)
                        
                        if dias_disponibles_pred:
                            # Selector de día para predicción
                            dia_prediccion = st.selectbox(
                                "Selecciona día para ver predicción:",
                                options=dias_disponibles_pred,
                                key="selector_dia_prediccion"
                            )
                            
                            # Obtener el número del día seleccionado
                            dia_num = None
                            for num, nombre in dias_numericos.items():
                                if nombre == dia_prediccion:
                                    dia_num = num
                                    break
                            
                            if dia_num is not None:
                                # Preparar datos para predicción del día seleccionado
                                # Usar el mes y día más común en los datos para predecir
                                mes_comun = datos_agrupados['Mes'].mode()[0] if not datos_agrupados['Mes'].mode().empty else 1
                                dia_mes_comun = 15  # Día medio del mes
                                
                                # Crear predicciones por hora para el día seleccionado
                                predicciones_por_hora = {}
                                demanda_promedio_actual = {}
                                
                                # Obtener datos actuales del día seleccionado
                                datos_dia_actual = demanda_df[demanda_df['Dia_Semana'] == dia_prediccion]
                                for _, row in datos_dia_actual.iterrows():
                                    demanda_promedio_actual[row['Hora']] = row['Promedio_Demanda']
                                
                                # Generar predicciones para cada hora
                                for hora in range(24):
                                    # Crear características para la predicción
                                    caracteristicas = np.array([[dia_num, hora, mes_comun, dia_mes_comun]])
                                    
                                    # Predecir
                                    prediccion = mejor_modelo.predict(caracteristicas)[0]
                                    prediccion = max(0, prediccion)  # No permitir valores negativos
                                    
                                    predicciones_por_hora[hora] = prediccion
                                
                                # Crear gráfica de predicción
                                metricas_prediccion = crear_grafica_prediccion(
                                    dia_prediccion, 
                                    predicciones_por_hora, 
                                    recursos_por_hora,
                                    demanda_promedio_actual
                                )
                                
                                # Mostrar métricas de predicción
                                st.divider()
                                st.write("### 📈 Métricas de Predicción")
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    # Métrica de desempeño del modelo
                                    r2_mejor = st.session_state.modelos_entrenados[mejor_modelo_nombre]['r2']
                                    st.metric(
                                        "Desempeño Modelo (R²)", 
                                        f"{r2_mejor:.4f}",
                                        f"{mejor_modelo_nombre}"
                                    )
                                
                                with col2:
                                    # Predicción de sumatoria de demanda diaria
                                    dif_porcentaje = metricas_prediccion['porcentaje_diferencia']
                                    st.metric(
                                        "Predicción Demanda Diaria", 
                                        f"{metricas_prediccion['suma_prediccion']:.0f} llamadas",
                                        f"{dif_porcentaje:+.1f}% vs promedio"
                                    )
                                
                                with col3:
                                    # Predicción de déficit
                                    dif_deficit = metricas_prediccion['diferencia_deficit']
                                    st.metric(
                                        "Predicción Déficit", 
                                        f"{metricas_prediccion['deficit_prediccion']:.0f}",
                                        f"{dif_deficit:+.0f} vs promedio"
                                    )
                                
                                # Mostrar tabla detallada
                                with st.expander("📋 Ver predicciones detalladas por hora"):
                                    df_detalle = metricas_prediccion['df_grafica'].copy()
                                    df_detalle['Hora_Formato'] = df_detalle['Hora'].apply(lambda x: f"{x}:00")
                                    df_detalle['Diferencia'] = df_detalle['Predicción'] - df_detalle['Promedio Actual']
                                    df_detalle['% Cambio'] = (df_detalle['Diferencia'] / df_detalle['Promedio Actual'] * 100).where(df_detalle['Promedio Actual'] > 0, 0)
                                    
                                    st.dataframe(
                                        df_detalle[['Hora_Formato', 'Predicción', 'Promedio Actual', 
                                                   'Diferencia', '% Cambio', 'Capacidad Disponible']].round(2),
                                        use_container_width=True
                                    )
                                
                                # Exportar predicciones
                                st.divider()
                                st.write("### 💾 Exportar Predicciones")
                                
                                if st.button("📥 Descargar Predicciones (CSV)", use_container_width=True):
                                    df_export = metricas_prediccion['df_grafica'].copy()
                                    df_export['Hora_Formato'] = df_export['Hora'].apply(lambda x: f"{x}:00")
                                    df_export['Diferencia'] = df_export['Predicción'] - df_export['Promedio Actual']
                                    df_export['% Cambio'] = (df_export['Diferencia'] / df_export['Promedio Actual'] * 100).where(df_export['Promedio Actual'] > 0, 0)
                                    
                                    csv_data = df_export.to_csv(index=False).encode('utf-8')
                                    nombre_archivo = f"prediccion_{dia_prediccion.lower()}.csv"
                                    st.download_button(
                                        label="Click para descargar",
                                        data=csv_data,
                                        file_name=nombre_archivo,
                                        mime="text/csv"
                                    )
                        else:
                            st.warning("No hay datos suficientes para días de semana (Lunes a Viernes)")
                    
                    else:
                        st.info("👈 Presiona 'Ejecutar Modelos de Predicción' para entrenar los modelos y generar predicciones")
                
                else:
                    st.info("👈 Primero procesa los datos en la pestaña 'Datos y Configuración'")
                    if st.session_state.demanda_df is None:
                        st.warning("- Falta calcular la demanda promedio")
                    if not st.session_state.recursos_por_hora:
                        st.warning("- Falta configurar los recursos por hora")
        
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.info("Asegúrate de que el archivo sea un CSV válido y tenga las columnas 'Call Time', 'From', 'To'")
    
    else:
        # Mostrar mensaje inicial si no hay archivo cargado
        st.info("👈 Por favor, carga un archivo CSV usando el panel lateral")

if __name__ == "__main__":
    main()
