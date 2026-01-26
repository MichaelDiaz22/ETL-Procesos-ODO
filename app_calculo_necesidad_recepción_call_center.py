import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from fpdf import FPDF
import base64

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para analizar demanda vs recursos")

# Constante para el cálculo de recursos
CONSTANTE_VALIDACION = 14.08
# Constante para calcular recursos necesarios de la demanda
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
    '(8062)', '(8063)', '(8064)', '(8071)', '(8072)', '(8079)', '(8080)', '(8068)', 
    '(8004)', '(8070)', '(8006)', '(7999)', '(8069)', '(8055)', '(8050)'
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
    APLICANDO FILTRO: From = externo, To = interno
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
        
        # Extraer hora y día de la semana del dataset filtrado
        df_filtrado['Hora'] = df_filtrado['Call Time'].dt.hour
        df_filtrado['Dia_Semana'] = df_filtrado['Call Time'].dt.day_name()
        df_filtrado['Dia_Semana'] = df_filtrado['Dia_Semana'].apply(traducir_dia)
        
        # Calcular conteo por hora y día
        demanda_por_hora_dia = df_filtrado.groupby(['Dia_Semana', 'Hora']).size().reset_index(name='Conteo')
        
        # Calcular promedio por hora para cada día
        # Primero, obtener todas las fechas únicas
        df_filtrado['Fecha'] = df_filtrado['Call Time'].dt.date
        fechas_por_dia = df_filtrado.groupby('Dia_Semana')['Fecha'].nunique().reset_index(name='Num_Dias')
        
        # Combinar con conteo
        demanda_con_dias = pd.merge(demanda_por_hora_dia, fechas_por_dia, on='Dia_Semana')
        
        # Calcular promedio
        demanda_con_dias['Promedio_Demanda'] = demanda_con_dias['Conteo'] / demanda_con_dias['Num_Dias']
        
        # Redondear a 2 decimales
        demanda_con_dias['Promedio_Demanda'] = demanda_con_dias['Promedio_Demanda'].round(2)
        
        # Calcular recursos necesarios (DEMANDA DIVIDIDA ENTRE 3)
        demanda_con_dias['Recursos_Necesarios'] = (demanda_con_dias['Promedio_Demanda'] / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
        
        # Ordenar por día y hora
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        demanda_con_dias['Dia_Semana'] = pd.Categorical(demanda_con_dias['Dia_Semana'], categories=orden_dias, ordered=True)
        demanda_con_dias = demanda_con_dias.sort_values(['Dia_Semana', 'Hora'])
        
        return demanda_con_dias[['Dia_Semana', 'Hora', 'Promedio_Demanda', 'Recursos_Necesarios', 'Conteo', 'Num_Dias']]
        
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
    
    # CALCULAR RECURSOS NECESARIOS PARA LA DEMANDA (DEMANDA DIVIDIDA ENTRE 3)
    demanda_completo['Recursos_Necesarios'] = (demanda_completo['Promedio_Demanda'] / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
    
    # Combinar ambos DataFrames
    datos_grafica = pd.merge(recursos_completo, demanda_completo, on='Hora')
    
    # Renombrar columnas para la gráfica
    datos_grafica = datos_grafica.rename(columns={
        'Recursos': 'Recursos_Disponibles',
        'Promedio_Demanda': 'Demanda_Promedio'
    })
    
    # Crear gráfica
    st.write(f"### 📈 Comparación: Recursos vs Demanda - {dia_seleccionado}")
    
    # Configurar gráfica
    chart_data = datos_grafica.set_index('Hora')
    
    # Mostrar gráfica
    st.line_chart(chart_data, height=500)
    
    # Calcular métricas de comparación
    st.write(f"**Métricas para {dia_seleccionado}:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Pico de demanda
        pico_demanda = datos_grafica['Demanda_Promedio'].max()
        hora_pico = datos_grafica.loc[datos_grafica['Demanda_Promedio'].idxmax(), 'Hora']
        recursos_necesarios_pico = (pico_demanda / CONSTANTE_DEMANDA_A_RECURSOS).round(2)
        st.metric("Pico de demanda", f"{pico_demanda:.0f} llamadas", 
                 f"Hora: {hora_pico}:00")
    
    with col2:
        # Pico de capacidad de recursos
        pico_recursos = datos_grafica['Recursos_Disponibles'].max()
        hora_recursos = datos_grafica.loc[datos_grafica['Recursos_Disponibles'].idxmax(), 'Hora']
        st.metric("Pico de capacidad de recursos", f"{pico_recursos:.0f}", 
                 f"Hora: {hora_recursos}:00")
    
    with col3:
        # Diferencia máxima
        datos_grafica['Diferencia'] = datos_grafica['Recursos_Disponibles'] - datos_grafica['Demanda_Promedio']
        max_exceso = datos_grafica['Diferencia'].max()
        max_deficit = datos_grafica['Diferencia'].min()
        
        if max_exceso > 0:
            st.metric("Mayor exceso", f"{max_exceso:.0f}")
        else:
            st.metric("Mayor déficit", f"{abs(max_deficit):.0f}")

# Función para generar PDF
def generar_pdf(demanda_df, recursos_por_hora, dia_seleccionado):
    """
    Genera un PDF con el reporte del día seleccionado
    """
    # Filtrar demanda para el día seleccionado
    demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
    
    if len(demanda_dia) == 0:
        return None
    
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Configurar fuente
    pdf.set_font("Arial", 'B', 16)
    
    # Título
    pdf.cell(0, 10, f"Reporte de Análisis de Llamadas - {dia_seleccionado}", ln=True, align='C')
    pdf.ln(5)
    
    # Información general
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"Constante de validación: {CONSTANTE_VALIDACION}", ln=True)
    pdf.cell(0, 10, f"Factor demanda a recursos: {CONSTANTE_DEMANDA_A_RECURSOS}", ln=True)
    pdf.ln(10)
    
    # Crear tabla
    pdf.set_font("Arial", 'B', 12)
    
    # Encabezados de la tabla
    encabezados = ['Hora', 'Demanda Promedio', 'Recursos Necesarios', 'Recursos Base', 'Capacidad Recursos', 'Diferencia']
    anchos = [20, 30, 30, 25, 35, 25]
    
    # Agregar encabezados
    for i, encabezado in enumerate(encabezados):
        pdf.cell(anchos[i], 10, encabezado, border=1, align='C')
    pdf.ln()
    
    # Agregar datos
    pdf.set_font("Arial", '', 10)
    
    for _, row in demanda_dia.iterrows():
        hora = row['Hora']
        demanda = row['Promedio_Demanda']
        recursos_necesarios = row['Recursos_Necesarios']
        
        # Obtener recursos disponibles para esta hora
        recursos_base = recursos_por_hora.get(hora, 0)
        capacidad_recursos = recursos_base * CONSTANTE_VALIDACION
        diferencia = capacidad_recursos - demanda
        
        # Agregar fila
        pdf.cell(anchos[0], 10, f"{hora}:00", border=1, align='C')
        pdf.cell(anchos[1], 10, f"{demanda:.2f}", border=1, align='C')
        pdf.cell(anchos[2], 10, f"{recursos_necesarios:.2f}", border=1, align='C')
        pdf.cell(anchos[3], 10, f"{recursos_base}", border=1, align='C')
        pdf.cell(anchos[4], 10, f"{capacidad_recursos:.2f}", border=1, align='C')
        pdf.cell(anchos[5], 10, f"{diferencia:.2f}", border=1, align='C')
        pdf.ln()
    
    # Agregar resumen
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Resumen:", ln=True)
    
    pdf.set_font("Arial", '', 10)
    
    # Calcular métricas
    demanda_total = demanda_dia['Promedio_Demanda'].sum()
    recursos_necesarios_total = demanda_dia['Recursos_Necesarios'].sum()
    
    # Obtener recursos disponibles totales (solo para horas con datos)
    recursos_disponibles_total = 0
    for hora in demanda_dia['Hora']:
        recursos_base = recursos_por_hora.get(hora, 0)
        recursos_disponibles_total += recursos_base * CONSTANTE_VALIDACION
    
    # Agregar métricas al PDF
    pdf.cell(0, 10, f"Demanda total del día: {demanda_total:.2f} llamadas", ln=True)
    pdf.cell(0, 10, f"Recursos necesarios total: {recursos_necesarios_total:.2f} personas", ln=True)
    pdf.cell(0, 10, f"Capacidad de recursos total: {recursos_disponibles_total:.2f}", ln=True)
    
    # Guardar PDF en bytes
    return pdf.output(dest='S').encode('latin1')

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
                        st.metric("Máximo capacidad recursos", f"{max_recursos_total:.1f}")
                
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
                    
                    # Obtener días disponibles en orden correcto (Lunes a Domingo)
                    orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                    dias_disponibles = [dia for dia in orden_dias if dia in demanda_df['Dia_Semana'].unique()]
                    
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
                    
                    col_exp1, col_exp2 = st.columns(2)
                    
                    with col_exp1:
                        # Exportar datos de demanda como CSV
                        csv_demanda = demanda_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Datos CSV",
                            data=csv_demanda,
                            file_name="demanda_promedio.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    
                    with col_exp2:
                        # Generar y exportar PDF
                        pdf_bytes = generar_pdf(demanda_df, recursos_por_hora, dia_seleccionado)
                        if pdf_bytes:
                            st.download_button(
                                label="📄 Descargar Reporte PDF",
                                data=pdf_bytes,
                                file_name=f"reporte_{dia_seleccionado}.pdf",
                                mime="application/pdf"
                            )
                
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
