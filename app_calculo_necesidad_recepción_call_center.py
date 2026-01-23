import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para calcular métricas de demanda y recursos")

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
HORAS_DISPONIBLES = list(range(6, 20))

def traducir_dia(dia_ingles):
    dias_traduccion = {
        'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    return dias_traduccion.get(dia_ingles, dia_ingles)

def determinar_rol_inbound(valor_to, codigos_filtro):
    valor_str = str(valor_to)
    for codigo in codigos_filtro:
        if codigo in valor_str:
            return "Call center"
    return "Externo"

def determinar_empresa_inbound(valor_to, codigos_ccb, codigos_odo, codigos_udc):
    valor_str = str(valor_to)
    if any(c in valor_str for c in codigos_ccb): return "CCB"
    if any(c in valor_str for c in codigos_odo): return "ODO"
    if any(c in valor_str for c in codigos_udc): return "UDC"
    return "Externo"

def ingresar_recursos_por_hora():
    recursos = {}
    col1, col2, col3 = st.columns(3)
    with col1:
        for hora in HORAS_DISPONIBLES[:5]:
            recursos[hora] = st.number_input(f"{hora}:00", min_value=0, max_value=100, value=1, key=f"recurso_{hora}")
    with col2:
        for hora in HORAS_DISPONIBLES[5:10]:
            recursos[hora] = st.number_input(f"{hora}:00", min_value=0, max_value=100, value=1, key=f"recurso_{hora}")
    with col3:
        for hora in HORAS_DISPONIBLES[10:]:
            recursos[hora] = st.number_input(f"{hora}:00", min_value=0, max_value=100, value=1, key=f"recurso_{hora}")
    return recursos

def filtrar_por_codigos(df):
    if 'To' not in df.columns:
        st.error("El archivo no contiene la columna 'To'.")
        return None
    mascara = df['To'].astype(str).apply(lambda x: any(codigo in str(x) for codigo in CODIGOS_FILTRAR))
    df_filtrado = df[mascara].copy()
    st.info(f"**Filtro aplicado:** {len(df_filtrado):,} de {len(df):,} registros.")
    return df_filtrado

def procesar_datos_con_proporcion(df, recursos_por_hora):
    df_procesado = df.copy()
    try:
        df_procesado['Call Time'] = pd.to_datetime(df_procesado['Call Time'], errors='coerce')
        df_procesado['Hora_Registro'] = df_procesado['Call Time'].dt.time
        df_procesado['Hora_Numerica'] = df_procesado['Call Time'].dt.hour
        df_procesado['Fecha_Creacion'] = df_procesado['Call Time'].dt.strftime('%d/%m/%Y')
        df_procesado['Fecha_Datetime'] = df_procesado['Call Time'].dt.date
        df_procesado['Dia_Semana'] = df_procesado['Call Time'].dt.day_name().apply(traducir_dia)
        
        def calcular_dias_tipo(dia_semana, df_c):
            fechas_unicas = df_c['Fecha_Datetime'].unique()
            contador = sum(1 for f in fechas_unicas if pd.notna(f) and ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][f.weekday()] == dia_semana)
            return contador if contador > 0 else 1

        dias_por_tipo = {dia: calcular_dias_tipo(dia, df_procesado) for dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']}
        df_procesado['Dias_Mismo_Tipo_Dataset'] = df_procesado['Dia_Semana'].map(dias_por_tipo)
        
        df_procesado['Clave_Agrupacion'] = (df_procesado['To'].astype(str) + '_' + df_procesado['Fecha_Creacion'] + '_' + df_procesado['Dia_Semana'] + '_' + df_procesado['Hora_Numerica'].astype(str) + '_' + df_procesado['From'].astype(str))
        conteo_grupos = df_procesado.groupby('Clave_Agrupacion').size()
        df_procesado['Conteo_Registros_Similares'] = df_procesado['Clave_Agrupacion'].map(conteo_grupos)
        
        df_procesado['Paso_1_Division'] = 1 / df_procesado['Conteo_Registros_Similares']
        df_procesado['Proporcion_Equivalencia'] = (df_procesado['Paso_1_Division'] / df_procesado['Dias_Mismo_Tipo_Dataset']).round(6)
        df_procesado['validador_demanda_personas_hora'] = (df_procesado['Proporcion_Equivalencia'] / CONSTANTE_VALIDACION).round(6)
        df_procesado['rol_inbound'] = df_procesado['To'].apply(lambda x: determinar_rol_inbound(x, CODIGOS_FILTRAR))
        df_procesado['empresa_inbound'] = df_procesado['To'].apply(lambda x: determinar_empresa_inbound(x, CODIGOS_CCB, CODIGOS_ODO, CODIGOS_UDC))
        
        df_procesado['Clave_Hora_Fecha_Rol'] = (df_procesado['Hora_Numerica'].astype(str) + '_' + df_procesado['Fecha_Creacion'] + '_' + df_procesado['rol_inbound'])
        conteo_hfr = df_procesado.groupby('Clave_Hora_Fecha_Rol').size()
        df_procesado['Conteo_Hora_Fecha_Rol'] = df_procesado['Clave_Hora_Fecha_Rol'].map(conteo_hfr)
        
        df_procesado['validador_recurso_hora'] = df_procesado.apply(lambda x: (recursos_por_hora.get(x['Hora_Numerica'], 0) * CONSTANTE_VALIDACION) / x['Conteo_Hora_Fecha_Rol'] if x['Conteo_Hora_Fecha_Rol'] > 0 else 0, axis=1).round(6)
        df_procesado['validador_necesidad_personas_hora'] = df_procesado.apply(lambda x: recursos_por_hora.get(x['Hora_Numerica'], 0) / x['Conteo_Hora_Fecha_Rol'] if x['Conteo_Hora_Fecha_Rol'] > 0 else 0, axis=1).round(6)
        
        return df_procesado.drop(columns=['Clave_Agrupacion', 'Clave_Hora_Fecha_Rol'])
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def main():
    if 'recursos_por_hora' not in st.session_state:
        st.session_state.recursos_por_hora = {}
    
    with st.sidebar:
        st.header("Cargar Datos")
        uploaded_file = st.file_uploader("Sube tu archivo CSV", type=['csv'])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        tab1, tab2 = st.tabs(["📋 Configuración", "📊 Resultados"])
        
        with tab1:
            recursos = ingresar_recursos_por_hora()
            st.session_state.recursos_por_hora = recursos
            
            if st.button("🔧 Procesar Datos", type="primary", use_container_width=True):
                df_f = filtrar_por_codigos(df)
                if df_f is not None:
                    df_p = procesar_datos_con_proporcion(df_f, recursos)
                    if df_p is not None:
                        st.session_state['df_procesado'] = df_p
                        st.success("✅ Procesamiento completado")
                        
                        # NUEVA TABLA: Primeros 10 registros con columnas procesadas
                        st.write("### 🔍 Vista Previa: Primeros 10 Registros Procesados")
                        st.dataframe(df_p.head(10), use_container_width=True)

        with tab2:
            if 'df_procesado' in st.session_state:
                df_p = st.session_state['df_procesado']
                
                # También mostramos la tabla al inicio de los resultados para referencia rápida
                st.write("### 📋 Muestra de Columnas Calculadas (Top 10)")
                st.dataframe(df_p.head(10), use_container_width=True)
                
                # Análisis y gráficos...
                st.divider()
                st.write("### 🕐 Análisis por Hora")
                res_h = df_p.groupby('Hora_Numerica').agg({'Proporcion_Equivalencia': 'sum', 'validador_recurso_hora': 'sum'}).round(4)
                st.dataframe(res_h, use_container_width=True)
                
                csv = df_p.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Resultados", data=csv, file_name="analisis_llamadas.csv", mime="text/csv")
            else:
                st.info("Procesa los datos en la pestaña anterior")

if __name__ == "__main__":
    main()
