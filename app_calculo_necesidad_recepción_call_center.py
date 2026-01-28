import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from fpdf import FPDF
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
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
    
    # Crear gráficas en paralelo
    st.write(f"### 📈 Comparación: Capacidad vs Demanda - {titulo_dia}")
    
    # Dos columnas para las gráficas
    col_grafica1, col_grafica2 = st.columns(2)
    
    with col_grafica1:
        st.write("#### 📊 Por Llamadas")
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
        
        # Mostrar gráfica sin ylim
        st.line_chart(chart_data, height=400)
        
        # Métricas de llamadas debajo de la gráfica
        st.write("**Métricas de Llamadas:**")
        
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            # Sumatoria de demanda promedio
            suma_demanda = datos_grafica['Promedio_Demanda'].sum()
            st.metric("Sumatoria Demanda", f"{suma_demanda:.0f} llamadas")
        
        with col_met2:
            # Pico de demanda
            pico_demanda = datos_grafica['Promedio_Demanda'].max()
            hora_pico = datos_grafica.loc[datos_grafica['Promedio_Demanda'].idxmax(), 'Hora']
            st.metric("Pico Demanda", f"{pico_demanda:.0f} llamadas", f"Hora: {hora_pico}:00")
        
        with col_met3:
            # Demanda promedio por hora
            demanda_promedio_hora = suma_demanda / 24 if suma_demanda > 0 else 0
            st.metric("Demanda Promedio/Hora", f"{demanda_promedio_hora:.1f} llamadas")
    
    with col_grafica2:
        st.write("#### 👥 Por Recursos")
        # Crear versión de datos para recursos (dividiendo por CONSTANTE_VALIDACION)
        datos_recursos = datos_grafica.copy()
        
        if dia_seleccionado in ['Sábado', 'Domingo']:
            # Solo demanda
            datos_recursos['Demanda_Recursos'] = datos_recursos['Promedio_Demanda'] / CONSTANTE_VALIDACION
            chart_data_recursos = datos_recursos[['Hora', 'Demanda_Recursos']].set_index('Hora')
            chart_data_recursos = chart_data_recursos.rename(columns={'Demanda_Recursos': 'Recursos Necesarios'})
        else:
            # Capacidad y demanda
            datos_recursos['Capacidad_Recursos'] = datos_recursos['Capacidad_Disponible'] / CONSTANTE_VALIDACION
            datos_recursos['Demanda_Recursos'] = datos_recursos['Promedio_Demanda'] / CONSTANTE_VALIDACION
            
            chart_data_recursos = datos_recursos[['Hora', 'Capacidad_Recursos', 'Demanda_Recursos']].set_index('Hora')
            chart_data_recursos = chart_data_recursos.rename(columns={
                'Capacidad_Recursos': 'Recursos Disponibles',
                'Demanda_Recursos': 'Recursos Necesarios'
            })
        
        # Mostrar gráfica de recursos sin ylim
        st.line_chart(chart_data_recursos, height=400)
        
        # Métricas de recursos debajo de la gráfica
        st.write("**Métricas de Recursos:**")
        
        col_met4, col_met5, col_met6 = st.columns(3)
        
        with col_met4:
            # Máximo de recursos disponibles
            if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
                max_recursos_disponibles = datos_recursos['Capacidad_Recursos'].max()
                hora_max_recursos = datos_recursos.loc[datos_recursos['Capacidad_Recursos'].idxmax(), 'Hora']
                st.metric("Máx. Recursos Disponibles", f"{max_recursos_disponibles:.1f}", f"Hora: {hora_max_recursos}:00")
            else:
                suma_recursos_necesarios = datos_recursos['Demanda_Recursos'].sum()
                st.metric("Recursos Necesarios Totales", f"{suma_recursos_necesarios:.1f}")
        
        with col_met5:
            # Máximo de recursos requeridos
            max_recursos_requeridos = datos_recursos['Demanda_Recursos'].max()
            hora_max_requeridos = datos_recursos.loc[datos_recursos['Demanda_Recursos'].idxmax(), 'Hora']
            st.metric("Máx. Recursos Requeridos", f"{max_recursos_requeridos:.1f}", f"Hora: {hora_max_requeridos}:00")
        
        with col_met6:
            # Déficit de recursos
            if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
                datos_recursos['Diferencia_Recursos'] = datos_recursos['Capacidad_Recursos'] - datos_recursos['Demanda_Recursos']
                max_deficit = datos_recursos['Diferencia_Recursos'].min()
                if max_deficit < 0:
                    hora_deficit = datos_recursos.loc[datos_recursos['Diferencia_Recursos'].idxmin(), 'Hora']
                    st.metric("Máx. Déficit Recursos", f"{abs(max_deficit):.1f}", f"Hora: {hora_deficit}:00")
                else:
                    st.metric("Déficit Recursos", "0.0", "Sin déficit")
            else:
                # Para sábado y domingo
                pico_demanda = datos_grafica['Promedio_Demanda'].max()
                recursos_pico = (pico_demanda / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
                st.metric("Recursos Pico Demanda", f"{recursos_pico:.1f}")

# Función para preparar datos para modelos de predicción - MEJORADA
def preparar_datos_para_prediccion(df):
    """
    Prepara los datos para entrenar modelos de predicción con características mejoradas
    """
    try:
        # Hacer una copia para no modificar el original
        df_clean = df.copy()
        
        # Convertir Call Time a datetime, manejar errores
        try:
            df_clean['Call Time'] = pd.to_datetime(df_clean['Call Time'], errors='coerce')
        except Exception as e:
            # Intentar con formato específico
            try:
                df_clean['Call Time'] = pd.to_datetime(df_clean['Call Time'], format='mixed', errors='coerce')
            except:
                df_clean['Call Time'] = pd.to_datetime(df_clean['Call Time'], errors='coerce')
        
        # Eliminar filas con Call Time nulo o inválido
        df_clean = df_clean.dropna(subset=['Call Time'])
        
        if len(df_clean) == 0:
            return None, None, None
        
        # Aplicar filtro: From = NO extensión (externo), To = SÍ extensión (interno)
        df_clean['From_es_extension'] = df_clean['From'].apply(es_extension_interna)
        df_clean['To_es_extension'] = df_clean['To'].apply(es_extension_interna)
        
        # Filtrar: origen externo Y destino interno
        mascara = (~df_clean['From_es_extension']) & (df_clean['To_es_extension'])
        df_filtrado = df_clean[mascara].copy()
        
        if len(df_filtrado) == 0:
            return None, None, None
        
        # Extraer características temporales mejoradas
        df_filtrado['Hora'] = df_filtrado['Call Time'].dt.hour
        df_filtrado['Dia_Semana_Num'] = df_filtrado['Call Time'].dt.dayofweek  # 0=Lunes, 6=Domingo
        df_filtrado['Mes'] = df_filtrado['Call Time'].dt.month
        df_filtrado['Dia_Mes'] = df_filtrado['Call Time'].dt.day
        
        # Crear características cíclicas para hora
        df_filtrado['Hora_sin'] = np.sin(2 * np.pi * df_filtrado['Hora'] / 24)
        df_filtrado['Hora_cos'] = np.cos(2 * np.pi * df_filtrado['Hora'] / 24)
        
        # Crear características cíclicas para día de la semana
        df_filtrado['Dia_sin'] = np.sin(2 * np.pi * df_filtrado['Dia_Semana_Num'] / 7)
        df_filtrado['Dia_cos'] = np.cos(2 * np.pi * df_filtrado['Dia_Semana_Num'] / 7)
        
        # Extraer fecha
        df_filtrado['Fecha'] = df_filtrado['Call Time'].dt.date
        
        # Agrupar por fecha y hora para contar llamadas diarias
        df_diario = df_filtrado.groupby(['Fecha', 'Dia_Semana_Num', 'Hora', 'Mes', 'Dia_Mes',
                                        'Hora_sin', 'Hora_cos', 'Dia_sin', 'Dia_cos']).size().reset_index(name='Llamadas')
        
        # Calcular el promedio por día de semana y hora
        df_promedio = df_diario.groupby(['Dia_Semana_Num', 'Hora', 'Hora_sin', 'Hora_cos', 'Dia_sin', 'Dia_cos']).agg({
            'Llamadas': 'mean',
            'Mes': 'first'
        }).reset_index()
        
        # Preparar características y variable objetivo
        X = df_promedio[['Dia_Semana_Num', 'Hora', 'Hora_sin', 'Hora_cos', 'Dia_sin', 'Dia_cos', 'Mes']]
        y = df_promedio['Llamadas']
        
        # Verificar que tenemos suficientes datos para entrenamiento
        if len(X) < 10:
            return None, None, None
        
        # Escalar características para modelos sensibles a la escala
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        return X_scaled, y, df_promedio
        
    except Exception as e:
        return None, None, None

# Función para optimizar hiperparámetros - NUEVA FUNCIÓN INTERNA
def optimizar_hiperparametros(X_train, y_train, modelo_tipo='gradient_boosting'):
    """
    Optimiza los hiperparámetros de los modelos internamente
    """
    if len(X_train) < 20:
        # Si hay pocos datos, usar configuración simple
        if modelo_tipo == 'gradient_boosting':
            return {
                'n_estimators': min(50, len(X_train) * 2),
                'max_depth': 3,
                'learning_rate': 0.1,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'random_state': 42
            }
        elif modelo_tipo == 'random_forest':
            return {
                'n_estimators': min(50, len(X_train)),
                'max_depth': 5,
                'min_samples_split': 3,
                'min_samples_leaf': 1,
                'random_state': 42
            }
    
    # Para conjuntos de datos más grandes, hacer búsqueda simple
    try:
        if modelo_tipo == 'gradient_boosting':
            # Parámetros optimizados para Gradient Boosting
            return {
                'n_estimators': 100,
                'max_depth': 4,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'max_features': 'sqrt',
                'random_state': 42
            }
        
        elif modelo_tipo == 'random_forest':
            # Parámetros optimizados para Random Forest
            return {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 2,
                'min_samples_leaf': 1,
                'max_features': 'sqrt',
                'bootstrap': True,
                'random_state': 42
            }
        
        elif modelo_tipo == 'mlp':
            # Parámetros optimizados para MLP
            return {
                'hidden_layer_sizes': (50, 25, 10),
                'activation': 'relu',
                'solver': 'adam',
                'alpha': 0.001,
                'batch_size': 'auto',
                'learning_rate': 'adaptive',
                'learning_rate_init': 0.001,
                'max_iter': 1000,
                'early_stopping': True,
                'validation_fraction': 0.1,
                'random_state': 42
            }
        
    except:
        # En caso de error, usar configuración por defecto
        return None

# Función para entrenar y evaluar modelos con hiperparámetros optimizados
def entrenar_modelos_prediccion(X, y):
    """
    Entrena y evalúa diferentes modelos de predicción con hiperparámetros optimizados
    """
    resultados = {}
    
    # Verificar que tenemos suficientes datos
    if len(X) < 10:
        return None, None, None
    
    try:
        # Dividir datos en entrenamiento y prueba (80%/20%)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)
        
        # Modelo 1: Gradient Boosting con hiperparámetros optimizados
        with st.spinner("🧠 Entrenando Gradient Boosting (optimizado)..."):
            try:
                params_gb = optimizar_hiperparametros(X_train, y_train, 'gradient_boosting')
                
                if params_gb:
                    modelo_gb = GradientBoostingRegressor(**params_gb)
                else:
                    # Configuración por defecto robusta
                    modelo_gb = GradientBoostingRegressor(
                        n_estimators=min(100, len(X_train)),
                        max_depth=3,
                        learning_rate=0.05,
                        min_samples_split=5,
                        min_samples_leaf=2,
                        random_state=42
                    )
                
                modelo_gb.fit(X_train, y_train)
                y_pred_gb = modelo_gb.predict(X_test)
                
                # Asegurar que las predicciones sean realistas
                y_pred_gb = np.maximum(y_pred_gb, 0)
                max_realistic = np.percentile(y_train, 95) * 1.5 if len(y_train) > 0 else 50
                y_pred_gb = np.minimum(y_pred_gb, max_realistic)
                
                resultados['Gradient Boosting'] = {
                    'modelo': modelo_gb,
                    'mse': mean_squared_error(y_test, y_pred_gb),
                    'mae': mean_absolute_error(y_test, y_pred_gb),
                    'r2': r2_score(y_test, y_pred_gb),
                    'predicciones': y_pred_gb
                }
            except Exception as e:
                resultados['Gradient Boosting'] = None
        
        # Modelo 2: Random Forest con hiperparámetros optimizados
        with st.spinner("🧠 Entrenando Random Forest (optimizado)..."):
            try:
                if len(X_train) > 30:  # Random Forest necesita más datos
                    params_rf = optimizar_hiperparametros(X_train, y_train, 'random_forest')
                    
                    if params_rf:
                        modelo_rf = RandomForestRegressor(**params_rf)
                    else:
                        modelo_rf = RandomForestRegressor(
                            n_estimators=min(50, len(X_train)),
                            max_depth=5,
                            min_samples_split=3,
                            min_samples_leaf=1,
                            random_state=42
                        )
                    
                    modelo_rf.fit(X_train, y_train)
                    y_pred_rf = modelo_rf.predict(X_test)
                    
                    # Asegurar que las predicciones sean realistas
                    y_pred_rf = np.maximum(y_pred_rf, 0)
                    y_pred_rf = np.minimum(y_pred_rf, max_realistic)
                    
                    resultados['Random Forest'] = {
                        'modelo': modelo_rf,
                        'mse': mean_squared_error(y_test, y_pred_rf),
                        'mae': mean_absolute_error(y_test, y_pred_rf),
                        'r2': r2_score(y_test, y_pred_rf),
                        'predicciones': y_pred_rf
                    }
                else:
                    resultados['Random Forest'] = None
            except Exception as e:
                resultados['Random Forest'] = None
        
        # Modelo 3: Ridge Regression (regularizada)
        with st.spinner("🧠 Entrenando Ridge Regression..."):
            try:
                # Buscar mejor alpha con validación cruzada
                alphas = [0.01, 0.1, 1.0, 10.0, 100.0]
                best_alpha = 1.0
                best_score = -float('inf')
                
                for alpha in alphas:
                    modelo_ridge = Ridge(alpha=alpha, random_state=42)
                    score = np.mean(cross_val_score(modelo_ridge, X_train, y_train, cv=3, scoring='r2'))
                    if score > best_score:
                        best_score = score
                        best_alpha = alpha
                
                modelo_ridge = Ridge(alpha=best_alpha, random_state=42)
                modelo_ridge.fit(X_train, y_train)
                y_pred_ridge = modelo_ridge.predict(X_test)
                
                # Asegurar que las predicciones sean realistas
                y_pred_ridge = np.maximum(y_pred_ridge, 0)
                y_pred_ridge = np.minimum(y_pred_ridge, max_realistic)
                
                resultados['Ridge Regression'] = {
                    'modelo': modelo_ridge,
                    'mse': mean_squared_error(y_test, y_pred_ridge),
                    'mae': mean_absolute_error(y_test, y_pred_ridge),
                    'r2': r2_score(y_test, y_pred_ridge),
                    'predicciones': y_pred_ridge,
                    'alpha': best_alpha
                }
            except Exception as e:
                resultados['Ridge Regression'] = None
        
        # Modelo 4: MLP (Red Neuronal) - Solo si hay suficientes datos
        if len(X_train) > 100:
            with st.spinner("🧠 Entrenando MLP (Red Neuronal optimizada)..."):
                try:
                    params_mlp = optimizar_hiperparametros(X_train, y_train, 'mlp')
                    
                    if params_mlp:
                        modelo_mlp = MLPRegressor(**params_mlp)
                    else:
                        modelo_mlp = MLPRegressor(
                            hidden_layer_sizes=(30, 15),
                            max_iter=500,
                            random_state=42,
                            early_stopping=True,
                            validation_fraction=0.1
                        )
                    
                    modelo_mlp.fit(X_train, y_train)
                    y_pred_mlp = modelo_mlp.predict(X_test)
                    
                    # Asegurar que las predicciones sean realistas
                    y_pred_mlp = np.maximum(y_pred_mlp, 0)
                    y_pred_mlp = np.minimum(y_pred_mlp, max_realistic)
                    
                    resultados['MLP (Red Neuronal)'] = {
                        'modelo': modelo_mlp,
                        'mse': mean_squared_error(y_test, y_pred_mlp),
                        'mae': mean_absolute_error(y_test, y_pred_mlp),
                        'r2': r2_score(y_test, y_pred_mlp),
                        'predicciones': y_pred_mlp
                    }
                except Exception as e:
                    resultados['MLP (Red Neuronal)'] = None
        else:
            resultados['MLP (Red Neuronal)'] = None
        
        # Filtrar modelos que se entrenaron correctamente
        modelos_validos = {k: v for k, v in resultados.items() if v is not None}
        
        if not modelos_validos:
            return None, None, None
        
        return modelos_validos, X_test, y_test
        
    except Exception as e:
        return None, None, None

# Función para crear gráfica de predicción - CORREGIDA (sin ylim)
def crear_grafica_prediccion(dia_seleccionado, predicciones_dia, recursos_por_hora, demanda_promedio_actual, modelo_nombre):
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
        
        # Asegurar que las predicciones sean realistas
        if prediccion > promedio_actual * 3 and promedio_actual > 0:  # Si la predicción es más de 3x el promedio
            prediccion = promedio_actual * 1.2  # Ajustar a un aumento más razonable
        
        predicciones_por_hora.append({
            'Hora': hora,
            'Predicción': max(0, prediccion),
            'Promedio Actual': promedio_actual,
            'Capacidad Disponible': capacidad
        })
    
    df_grafica = pd.DataFrame(predicciones_por_hora)
    
    # Crear gráficas en paralelo
    st.write(f"### 📈 Predicción vs Realidad - {dia_seleccionado}")
    st.caption(f"Modelo: {modelo_nombre}")
    
    # Dos columnas para las gráficas
    col_grafica1, col_grafica2 = st.columns(2)
    
    with col_grafica1:
        st.write("#### 📊 Por Llamadas")
        chart_data = df_grafica[['Hora', 'Predicción', 'Promedio Actual', 'Capacidad Disponible']].set_index('Hora')
        chart_data = chart_data.rename(columns={
            'Predicción': 'Predicción',
            'Promedio Actual': 'Promedio Actual',
            'Capacidad Disponible': 'Capacidad Disponible'
        })
        
        # Mostrar gráfica sin ylim
        st.line_chart(chart_data, height=400)
        
        # Métricas de llamadas debajo de la gráfica
        st.write("**Métricas de Llamadas:**")
        
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            # Sumatoria de predicción
            suma_prediccion = df_grafica['Predicción'].sum()
            st.metric("Sumatoria Predicción", f"{suma_prediccion:.0f} llamadas")
        
        with col_met2:
            # Sumatoria promedio actual
            suma_promedio = df_grafica['Promedio Actual'].sum()
            st.metric("Sumatoria Promedio", f"{suma_promedio:.0f} llamadas")
        
        with col_met3:
            # Pico de predicción
            pico_prediccion = df_grafica['Predicción'].max()
            hora_pico_pred = df_grafica.loc[df_grafica['Predicción'].idxmax(), 'Hora']
            st.metric("Pico Predicción", f"{pico_prediccion:.0f} llamadas", f"Hora: {hora_pico_pred}:00")
    
    with col_grafica2:
        st.write("#### 👥 Por Recursos")
        # Crear versión de datos para recursos (dividiendo por CONSTANTE_VALIDACION)
        df_recursos = df_grafica.copy()
        df_recursos['Prediccion_Recursos'] = df_recursos['Predicción'] / CONSTANTE_VALIDACION
        df_recursos['Promedio_Recursos'] = df_recursos['Promedio Actual'] / CONSTANTE_VALIDACION
        df_recursos['Capacidad_Recursos'] = df_recursos['Capacidad Disponible'] / CONSTANTE_VALIDACION
        
        chart_data_recursos = df_recursos[['Hora', 'Prediccion_Recursos', 'Promedio_Recursos', 'Capacidad_Recursos']].set_index('Hora')
        chart_data_recursos = chart_data_recursos.rename(columns={
            'Prediccion_Recursos': 'Predicción Recursos',
            'Promedio_Recursos': 'Promedio Actual Recursos',
            'Capacidad_Recursos': 'Recursos Disponibles'
        })
        
        # Mostrar gráfica de recursos sin ylim
        st.line_chart(chart_data_recursos, height=400)
        
        # Métricas de recursos debajo de la gráfica
        st.write("**Métricas de Recursos:**")
        
        col_met4, col_met5, col_met6 = st.columns(3)
        
        with col_met4:
            # Máximo de recursos disponibles
            max_recursos_disponibles = df_recursos['Capacidad_Recursos'].max()
            hora_max_disp = df_recursos.loc[df_recursos['Capacidad_Recursos'].idxmax(), 'Hora']
            st.metric("Máx. Recursos Disponibles", f"{max_recursos_disponibles:.1f}", f"Hora: {hora_max_disp}:00")
        
        with col_met5:
            # Máximo de recursos requeridos (predicción)
            max_recursos_requeridos = df_recursos['Prediccion_Recursos'].max()
            hora_max_req = df_recursos.loc[df_recursos['Prediccion_Recursos'].idxmax(), 'Hora']
            st.metric("Máx. Recursos Requeridos", f"{max_recursos_requeridos:.1f}", f"Hora: {hora_max_req}:00")
        
        with col_met6:
            # Déficit de recursos (predicción)
            df_recursos['Diferencia_Recursos'] = df_recursos['Capacidad_Recursos'] - df_recursos['Prediccion_Recursos']
            max_deficit = df_recursos['Diferencia_Recursos'].min()
            if max_deficit < 0:
                hora_deficit = df_recursos.loc[df_recursos['Diferencia_Recursos'].idxmin(), 'Hora']
                st.metric("Máx. Déficit Recursos", f"{abs(max_deficit):.1f}", f"Hora: {hora_deficit}:00")
            else:
                st.metric("Déficit Recursos", "0.0", "Sin déficit")
    
    # Calcular métricas adicionales para retornar
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
        'df_grafica': df_grafica,
        'df_recursos': df_recursos
    }

# Función para predecir demanda usando el modelo
def predecir_demanda_con_modelo(modelo, dia_num, mes=1):
    """
    Predice la demanda por hora para un día específico usando el modelo entrenado
    """
    predicciones = {}
    
    # Características cíclicas para la hora
    for hora in range(24):
        try:
            # Crear características para la predicción
            hora_sin = np.sin(2 * np.pi * hora / 24)
            hora_cos = np.cos(2 * np.pi * hora / 24)
            dia_sin = np.sin(2 * np.pi * dia_num / 7)
            dia_cos = np.cos(2 * np.pi * dia_num / 7)
            
            # Crear array de características
            caracteristicas = np.array([[dia_num, hora, hora_sin, hora_cos, dia_sin, dia_cos, mes]])
            
            # Predecir
            prediccion = modelo.predict(caracteristicas)[0]
            
            # Asegurar que la predicción sea razonable
            prediccion = max(0, prediccion)  # No negativa
            prediccion = min(prediccion, 100)  # Máximo 100 llamadas por hora (límite razonable)
            
            predicciones[hora] = prediccion
        except:
            predicciones[hora] = 0
    
    return predicciones

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
                        st.info("Función PDF disponible próximamente")
                    
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
                            X, y, datos_promedio = preparar_datos_para_prediccion(df)
                            
                            if X is not None and y is not None:
                                # Mostrar información de los datos
                                st.info(f"**Datos para entrenamiento:** {len(X)} muestras")
                                st.info(f"**Rango de valores objetivo:** {y.min():.1f} a {y.max():.1f} llamadas por hora")
                                
                                # Entrenar y evaluar modelos
                                resultados, X_test, y_test = entrenar_modelos_prediccion(X, y)
                                
                                if resultados is not None:
                                    # Guardar resultados en session state
                                    st.session_state.modelos_entrenados = resultados
                                    st.session_state.datos_prediccion = {
                                        'X_test': X_test,
                                        'y_test': y_test,
                                        'datos_promedio': datos_promedio
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
                                            'MSE': f"{resultado['mse']:.2f}",
                                            'MAE': f"{resultado['mae']:.2f}",
                                            'R²': f"{resultado['r2']:.4f}"
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
                                    st.error("❌ No se pudieron entrenar modelos válidos")
                            else:
                                st.error("❌ No hay suficientes datos para entrenar los modelos de predicción")
                    
                    # Si ya tenemos modelos entrenados, mostrar la interfaz de predicción
                    if st.session_state.modelos_entrenados is not None:
                        st.divider()
                        st.write("### 🔍 Visualización de Predicciones")
                        
                        # Obtener datos necesarios
                        demanda_df = st.session_state.demanda_df
                        recursos_por_hora = st.session_state.recursos_por_hora
                        mejor_modelo_nombre = st.session_state.mejor_modelo
                        
                        # Verificar que tenemos un mejor modelo
                        if mejor_modelo_nombre and mejor_modelo_nombre in st.session_state.modelos_entrenados:
                            mejor_modelo = st.session_state.modelos_entrenados[mejor_modelo_nombre]['modelo']
                            datos_promedio = st.session_state.datos_prediccion['datos_promedio']
                            
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
                            
                            # Obtener días disponibles para predicción (solo los que tienen datos)
                            dias_disponibles_pred = []
                            for dia_num, dia_nombre in dias_numericos.items():
                                if dia_nombre in demanda_df['Dia_Semana'].unique():
                                    dias_disponibles_pred.append(dia_nombre)
                            
                            # Añadir opción "Todos" (promedio de Lunes a Viernes)
                            if any(dia in dias_disponibles_pred for dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']):
                                dias_disponibles_pred.append("Todos")
                            
                            if dias_disponibles_pred:
                                # Selector de día para predicción
                                dia_prediccion = st.selectbox(
                                    "Selecciona día para ver predicción:",
                                    options=dias_disponibles_pred,
                                    key="selector_dia_prediccion"
                                )
                                
                                # Preparar datos según la selección
                                if dia_prediccion == "Todos":
                                    # Calcular promedio de predicciones para Lunes a Viernes
                                    dias_semana_nums = [0, 1, 2, 3, 4]  # Lunes a Viernes
                                    mes_comun = 1  # Mes por defecto
                                    
                                    # Calcular demanda promedio actual para "Todos"
                                    demanda_promedio_actual = {}
                                    dias_semana_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                                    for hora in range(24):
                                        demandas_hora = []
                                        for dia_nombre in dias_semana_nombres:
                                            if dia_nombre in demanda_df['Dia_Semana'].unique():
                                                datos_dia = demanda_df[demanda_df['Dia_Semana'] == dia_nombre]
                                                datos_hora = datos_dia[datos_dia['Hora'] == hora]
                                                if not datos_hora.empty:
                                                    demandas_hora.append(datos_hora['Promedio_Demanda'].values[0])
                                        demanda_promedio_actual[hora] = np.mean(demandas_hora) if demandas_hora else 0
                                    
                                    # Generar predicciones para cada día y promediar
                                    predicciones_por_hora_todas = {}
                                    for dia_num in dias_semana_nums:
                                        predicciones_dia = predecir_demanda_con_modelo(mejor_modelo, dia_num, mes_comun)
                                        
                                        # Acumular predicciones por hora
                                        for hora, pred in predicciones_dia.items():
                                            if hora not in predicciones_por_hora_todas:
                                                predicciones_por_hora_todas[hora] = []
                                            predicciones_por_hora_todas[hora].append(pred)
                                    
                                    # Calcular promedio por hora para todos los días
                                    predicciones_por_hora = {}
                                    for hora, preds in predicciones_por_hora_todas.items():
                                        predicciones_por_hora[hora] = np.mean(preds) if preds else 0
                                    
                                else:
                                    # Obtener el número del día seleccionado
                                    dia_num = None
                                    for num, nombre in dias_numericos.items():
                                        if nombre == dia_prediccion:
                                            dia_num = num
                                            break
                                    
                                    if dia_num is not None:
                                        mes_comun = 1  # Mes por defecto
                                        
                                        # Obtener datos actuales del día seleccionado
                                        demanda_promedio_actual = {}
                                        datos_dia_actual = demanda_df[demanda_df['Dia_Semana'] == dia_prediccion]
                                        for _, row in datos_dia_actual.iterrows():
                                            demanda_promedio_actual[row['Hora']] = row['Promedio_Demanda']
                                        
                                        # Generar predicciones usando la nueva función
                                        predicciones_por_hora = predecir_demanda_con_modelo(mejor_modelo, dia_num, mes_comun)
                                        
                                        # Si no hay datos actuales para este día, usar 0
                                        if not demanda_promedio_actual:
                                            for hora in range(24):
                                                demanda_promedio_actual[hora] = 0
                                    
                                # Crear gráfica de predicción
                                metricas_prediccion = crear_grafica_prediccion(
                                    dia_prediccion, 
                                    predicciones_por_hora, 
                                    recursos_por_hora,
                                    demanda_promedio_actual,
                                    mejor_modelo_nombre
                                )
                                
                                # Mostrar métricas de predicción adicionales
                                st.divider()
                                st.write("### 📈 Métricas de Predicción Adicionales")
                                
                                # Obtener métricas del mejor modelo
                                r2_mejor = st.session_state.modelos_entrenados[mejor_modelo_nombre]['r2']
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    # Métrica de desempeño del modelo
                                    st.metric(
                                        "Desempeño Modelo (R²)", 
                                        f"{r2_mejor:.4f}",
                                        f"{mejor_modelo_nombre}"
                                    )
                                
                                with col2:
                                    # Diferencia entre predicción y promedio
                                    suma_prediccion = metricas_prediccion['suma_prediccion']
                                    suma_promedio = metricas_prediccion['suma_promedio']
                                    if suma_promedio > 0:
                                        dif_porcentaje = ((suma_prediccion - suma_promedio) / suma_promedio * 100)
                                        st.metric(
                                            "Diferencia Predicción", 
                                            f"{suma_prediccion - suma_promedio:.0f} llamadas",
                                            f"{dif_porcentaje:+.1f}% vs promedio"
                                        )
                                    else:
                                        st.metric(
                                            "Diferencia Predicción", 
                                            f"{suma_prediccion:.0f} llamadas",
                                            "Sin datos previos"
                                        )
                                
                                with col3:
                                    # Déficit predicho vs promedio
                                    deficit_prediccion = metricas_prediccion['deficit_prediccion']
                                    deficit_promedio = metricas_prediccion['deficit_promedio']
                                    dif_deficit = deficit_prediccion - deficit_promedio
                                    
                                    st.metric(
                                        "Diferencia Déficit", 
                                        f"{deficit_prediccion:.0f} vs {deficit_promedio:.0f}",
                                        f"{dif_deficit:+.0f} de cambio"
                                    )
                                
                                # Mostrar tabla detallada
                                with st.expander("📋 Ver predicciones detalladas por hora"):
                                    df_detalle = metricas_prediccion['df_grafica'].copy()
                                    df_detalle['Hora_Formato'] = df_detalle['Hora'].apply(lambda x: f"{x}:00")
                                    df_detalle['Diferencia'] = df_detalle['Predicción'] - df_detalle['Promedio Actual']
                                    df_detalle['% Cambio'] = (df_detalle['Diferencia'] / df_detalle['Promedio Actual'] * 100).where(df_detalle['Promedio Actual'] > 0, 0)
                                    df_detalle['Prediccion_Recursos'] = (df_detalle['Predicción'] / CONSTANTE_VALIDACION).round(2)
                                    df_detalle['Promedio_Recursos'] = (df_detalle['Promedio Actual'] / CONSTANTE_VALIDACION).round(2)
                                    
                                    st.dataframe(
                                        df_detalle[['Hora_Formato', 'Predicción', 'Promedio Actual', 
                                                   'Prediccion_Recursos', 'Promedio_Recursos',
                                                   'Diferencia', '% Cambio', 'Capacidad Disponible']].round(2),
                                        use_container_width=True
                                    )
                                
                                # Exportar predicciones
                                st.divider()
                                st.write("### 💾 Exportar Predicciones")
                                
                                # Selector de formato de exportación
                                formato_exportacion_pred = st.radio(
                                    "Selecciona formato de exportación:",
                                    ["CSV", "XLSX", "PDF"],
                                    horizontal=True,
                                    key="formato_exportacion_pred"
                                )
                                
                                # Preparar datos para exportación
                                df_export = metricas_prediccion['df_grafica'].copy()
                                df_export['Hora_Formato'] = df_export['Hora'].apply(lambda x: f"{x}:00")
                                df_export['Diferencia'] = df_export['Predicción'] - df_export['Promedio Actual']
                                df_export['% Cambio'] = (df_export['Diferencia'] / df_export['Promedio Actual'] * 100).where(df_export['Promedio Actual'] > 0, 0)
                                df_export['Prediccion_Recursos'] = (df_export['Predicción'] / CONSTANTE_VALIDACION).round(2)
                                df_export['Promedio_Recursos'] = (df_export['Promedio Actual'] / CONSTANTE_VALIDACION).round(2)
                                
                                # Para días con capacidad disponible, agregar columnas adicionales
                                if dia_prediccion in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
                                    df_export['Recursos_Base'] = df_export['Hora'].apply(lambda h: recursos_por_hora.get(h, 0))
                                    df_export['Capacidad_Disponible'] = (df_export['Recursos_Base'] * CONSTANTE_VALIDACION).round(2)
                                    df_export['Recursos_Disponibles'] = (df_export['Capacidad_Disponible'] / CONSTANTE_VALIDACION).round(2)
                                
                                nombre_base = dia_prediccion.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u') if dia_prediccion != "Todos" else "prediccion_promedio"
                                
                                col_exp1, col_exp2, col_exp3 = st.columns(3)
                                
                                with col_exp1:
                                    if formato_exportacion_pred == "CSV":
                                        csv_data = df_export.to_csv(index=False).encode('utf-8')
                                        nombre_archivo = f"prediccion_{nombre_base}.csv"
                                        st.download_button(
                                            label="📥 Descargar CSV",
                                            data=csv_data,
                                            file_name=nombre_archivo,
                                            mime="text/csv",
                                            type="primary",
                                            use_container_width=True
                                        )
                                
                                with col_exp2:
                                    if formato_exportacion_pred == "XLSX":
                                        # Crear Excel en memoria
                                        output = io.BytesIO()
                                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                            df_export.to_excel(writer, index=False, sheet_name='Predicción')
                                        
                                        excel_data = output.getvalue()
                                        nombre_archivo = f"prediccion_{nombre_base}.xlsx"
                                        st.download_button(
                                            label="📥 Descargar Excel",
                                            data=excel_data,
                                            file_name=nombre_archivo,
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            type="primary",
                                            use_container_width=True
                                        )
                                
                                with col_exp3:
                                    if formato_exportacion_pred == "PDF":
                                        st.info("PDF disponible próximamente")
                            
                            else:
                                st.warning("⚠️ No hay datos suficientes para días de semana (Lunes a Viernes) en los datos históricos")
                        else:
                            st.warning("⚠️ No se pudo determinar el mejor modelo. Intenta entrenar nuevamente.")
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
