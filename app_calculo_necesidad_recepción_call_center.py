import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Análisis de demanda externa hacia líneas internas (CCB, ODO, UDC)")

# Constante para el cálculo de validación
CONSTANTE_VALIDACION = 14.08

# Códigos por empresa
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

TODOS_LOS_CODIGOS = CODIGOS_CCB + CODIGOS_ODO + CODIGOS_UDC
HORAS_DISPONIBLES = list(range(6, 20))

# Sidebar para cargar el archivo
with st.sidebar:
    st.header("Cargar Datos")
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    st.info("Filtro: Outbound == 'Externo' & Inbound != 'Externo'")

# Función para determinar empresa (Genérica para To y From)
def determinar_empresa(valor):
    valor_str = str(valor)
    if any(c in valor_str for c in CODIGOS_CCB): return "CCB"
    if any(c in valor_str for c in CODIGOS_ODO): return "ODO"
    if any(c in valor_str for c in CODIGOS_UDC): return "UDC"
    return "Externo"

def traducir_dia(dia_ingles):
    dias = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
    return dias.get(dia_ingles, dia_ingles)

def ingresar_recursos_por_hora():
    recursos = {}
    col1, col2, col3 = st.columns(3)
    with col1:
        for h in HORAS_DISPONIBLES[:5]: recursos[h] = st.number_input(f"{h}:00", 0, 100, 1, key=f"r_{h}")
    with col2:
        for h in HORAS_DISPONIBLES[5:10]: recursos[h] = st.number_input(f"{h}:00", 0, 100, 1, key=f"r_{h}")
    with col3:
        for h in HORAS_DISPONIBLES[10:]: recursos[h] = st.number_input(f"{h}:00", 0, 100, 1, key=f"r_{h}")
    return recursos

def procesar_datos(df, recursos_dict):
    df_p = df.copy()
    try:
        # 1. Asignación de Empresas (Inbound y Outbound)
        df_p['empresa_inbound'] = df_p['To'].apply(determinar_empresa)
        df_p['empresa_outbound'] = df_p['From'].apply(determinar_empresa)

        # 2. Aplicación del Filtro Solicitado
        # Outbound == "Externo" Y Inbound != "Externo"
        condicion = (df_p['empresa_outbound'] == "Externo") & (df_p['empresa_inbound'] != "Externo")
        df_p = df_p[condicion].copy()

        if df_p.empty:
            st.warning("No hay registros que cumplan la condición (Outbound Externo e Inbound de Empresa).")
            return None

        # 3. Preparación de Tiempos y Fechas
        df_p['Call Time'] = pd.to_datetime(df_p['Call Time'], errors='coerce')
        df_p['Hora_Registro'] = df_p['Call Time'].dt.time
        df_p['Hora_Numerica'] = df_p['Call Time'].dt.hour
        df_p['Fecha_Creacion'] = df_p['Call Time'].dt.strftime('%d/%m/%Y')
        df_p['Fecha_Datetime'] = df_p['Call Time'].dt.date
        df_p['Dia_Semana'] = df_p['Call Time'].dt.day_name().apply(traducir_dia)

        # 4. Cálculo de Días del Mismo Tipo
        fechas_unicas = df_p[['Fecha_Datetime', 'Dia_Semana']].drop_duplicates()
        dias_por_tipo = fechas_unicas['Dia_Semana'].value_counts().to_dict()
        df_p['Dias_Mismo_Tipo_Dataset'] = df_p['Dia_Semana'].map(dias_por_tipo)

        # 5. Proporción Equivalencia
        df_p['Clave_Agrupacion'] = (df_p['To'].astype(str) + '_' + df_p['Fecha_Creacion'] + '_' + df_p['Dia_Semana'] + '_' + df_p['Hora_Numerica'].astype(str) + '_' + df_p['From'].astype(str))
        conteo_grupos = df_p.groupby('Clave_Agrupacion').size()
        df_p['Conteo_Registros_Similares'] = df_p['Clave_Agrupacion'].map(conteo_grupos)
        
        df_p['Paso_1_Division'] = 1 / df_p['Conteo_Registros_Similares']
        df_p['Proporcion_Equivalencia'] = (df_p['Paso_1_Division'] / df_p['Dias_Mismo_Tipo_Dataset']).round(6)
        
        # 6. Validadores
        df_p['validador_demanda_personas_hora'] = (df_p['Proporcion_Equivalencia'] / CONSTANTE_VALIDACION).round(6)
        df_p['rol_inbound'] = df_p['To'].apply(lambda x: "Call center" if any(c in str(x) for c in TODOS_LOS_CODIGOS) else "Externo")
        
        df_p['Clave_HFR'] = df_p['Hora_Numerica'].astype(str) + '_' + df_p['Fecha_Creacion'] + '_' + df_p['rol_inbound']
        conteo_hfr = df_p.groupby('Clave_HFR').size()
        df_p['Conteo_Hora_Fecha_Rol'] = df_p['Clave_HFR'].map(conteo_hfr)

        df_p['validador_recurso_hora'] = df_p.apply(lambda x: (recursos_dict.get(x['Hora_Numerica'], 0) * CONSTANTE_VALIDACION) / x['Conteo_Hora_Fecha_Rol'] if x['Conteo_Hora_Fecha_Rol'] > 0 else 0, axis=1).round(6)
        df_p['validador_necesidad_personas_hora'] = df_p.apply(lambda x: recursos_dict.get(x['Hora_Numerica'], 0) / x['Conteo_Hora_Fecha_Rol'] if x['Conteo_Hora_Fecha_Rol'] > 0 else 0, axis=1).round(6)

        return df_p.drop(columns=['Clave_Agrupacion', 'Clave_HFR'])
    except Exception as e:
        st.error(f"Error en procesamiento: {e}")
        return None

def main():
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        tab1, tab2 = st.tabs(["📋 Configuración", "📊 Análisis"])
        
        with tab1:
            recursos = ingresar_recursos_por_hora()
            if st.button("🔧 Procesar con Filtros", type="primary", use_container_width=True):
                df_p = procesar_datos(df, recursos)
                if df_p is not None:
                    st.session_state['df_p'] = df_p
                    st.success(f"Procesados {len(df_p)} registros (Filtrados: Outbound Externo & Inbound Empresa)")
                    st.write("### 🔍 Vista Previa (Top 10)")
                    st.dataframe(df_p.head(10), use_container_width=True)

        with tab2:
            if 'df_p' in st.session_state:
                df_res = st.session_state['df_p']
                
                # Gráfica
                st.subheader("📈 Demanda vs Recursos por Día")
                dias = sorted(df_res['Dia_Semana'].unique())
                dia_sel = st.selectbox("Selecciona día:", dias)
                
                # Filtrado para la gráfica (Inbound != 'Externo' ya garantizado por el filtro global)
                df_dia = df_res[df_res['Dia_Semana'] == dia_sel]
                
                g_demanda = df_dia.groupby('Hora_Numerica')['Proporcion_Equivalencia'].sum()
                g_recurso = df_dia.groupby('Hora_Numerica')['validador_recurso_hora'].sum()
                
                chart_df = pd.DataFrame({
                    'Demanda (Empresas)': g_demanda,
                    'Recursos Disponibles': g_recurso
                }).fillna(0)
                
                st.line_chart(chart_df)
                
                # Métricas Rápidas
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Registros", len(df_res))
                c2.metric("Suma Demanda", round(df_res['Proporcion_Equivalencia'].sum(), 2))
                c3.metric("Empresas Impactadas", ", ".join(df_res['empresa_inbound'].unique()))
                
                # Exportación
                buffer = io.BytesIO()
                df_res.to_excel(buffer, index=False)
                st.download_button("📥 Descargar Excel", buffer.getvalue(), "analisis_filtrado.xlsx", "application/vnd.ms-excel")
            else:
                st.info("Primero procesa los datos en la pestaña de Configuración.")

if __name__ == "__main__":
    main()
