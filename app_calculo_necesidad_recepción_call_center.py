import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="Analizador de Llamadas", page_icon="📞", layout="wide")

# Título de la aplicación
st.title("📊 Analizador de Registros de Llamadas")
st.markdown("Carga un archivo CSV con registros de llamadas para analizar demanda vs recursos")

# Constante para el cálculo de recursos
CONSTANTE_VALIDACION = 14.08

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
        
        # Ordenar por día y hora
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        demanda_con_dias['Dia_Semana'] = pd.Categorical(demanda_con_dias['Dia_Semana'], categories=orden_dias, ordered=True)
        demanda_con_dias = demanda_con_dias.sort_values(['Dia_Semana', 'Hora'])
        
        return demanda_con_dias[['Dia_Semana', 'Hora', 'Promedio_Demanda', 'Conteo', 'Num_Dias']]
        
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
        demanda_promedio = demanda_dia.groupby('Hora')['Promedio_Demanda'].mean().reset_index()
        demanda_promedio['Promedio_Demanda'] = demanda_promedio['Promedio_Demanda'].round(2)
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
    # Primero, crear rango completo de horas de 0 a 23
    horas_completas = pd.DataFrame({'Hora': range(0, 24)})
    
    # Preparar datos de recursos (solo para días de semana)
    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
        recursos_lista = []
        for hora, valor in recursos_por_hora.items():
            recursos_lista.append({'Hora': hora, 'Recursos': valor * CONSTANTE_VALIDACION})
        
        recursos_df = pd.DataFrame(recursos_lista)
        
        # Combinar con horas completas
        recursos_completo = pd.merge(horas_completas, recursos_df, on='Hora', how='left')
        recursos_completo['Recursos'] = recursos_completo['Recursos'].fillna(0)
    else:
        # Para sábado y domingo, no mostrar recursos
        recursos_completo = horas_completas.copy()
        recursos_completo['Recursos'] = 0
    
    # Preparar datos de demanda
    if dia_seleccionado == "Todos":
        demanda_completo = pd.merge(horas_completas, demanda_dia[['Hora', 'Promedio_Demanda']], on='Hora', how='left')
    else:
        demanda_completo = pd.merge(horas_completas, demanda_dia[['Hora', 'Promedio_Demanda']], on='Hora', how='left')
    
    demanda_completo['Promedio_Demanda'] = demanda_completo['Promedio_Demanda'].fillna(0)
    
    # Combinar ambos DataFrames
    datos_grafica = pd.merge(recursos_completo, demanda_completo, on='Hora')
    
    # Renombrar columnas para la gráfica
    datos_grafica = datos_grafica.rename(columns={
        'Recursos': 'Capacidad Disponible',
        'Promedio_Demanda': 'Demanda Promedio'
    })
    
    # Crear gráfica - seleccionar solo las columnas que se deben mostrar
    st.write(f"### 📈 Comparación: Capacidad vs Demanda - {titulo_dia}")
    
    # Para sábado y domingo, solo mostrar demanda
    if dia_seleccionado in ['Sábado', 'Domingo']:
        chart_data = datos_grafica[['Hora', 'Demanda Promedio']].set_index('Hora')
    else:
        chart_data = datos_grafica[['Hora', 'Capacidad Disponible', 'Demanda Promedio']].set_index('Hora')
    
    # Mostrar gráfica
    st.line_chart(chart_data, height=500)
    
    # Calcular métricas
    suma_demanda = datos_grafica['Demanda Promedio'].sum()
    
    # Calcular diferencia y encontrar picos
    datos_grafica['Diferencia'] = datos_grafica['Capacidad Disponible'] - datos_grafica['Demanda Promedio']
    
    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
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
            pico_capacidad = datos_grafica['Capacidad Disponible'].max()
            hora_capacidad = datos_grafica.loc[datos_grafica['Capacidad Disponible'].idxmax(), 'Hora']
            st.metric("Pico Capacidad Disponible", f"{pico_capacidad:.0f}", f"Hora: {hora_capacidad}:00")
        else:
            # Para sábado y domingo, mostrar hora pico de demanda
            pico_demanda = datos_grafica['Demanda Promedio'].max()
            hora_pico = datos_grafica.loc[datos_grafica['Demanda Promedio'].idxmax(), 'Hora']
            st.metric("Pico Demanda", f"{pico_demanda:.0f} llamadas", f"Hora: {hora_pico}:00")
    
    with col3:
        if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
            if max_exceso > 0:
                st.metric("Mayor Exceso", f"{max_exceso:.0f}", f"Hora: {hora_max_exceso}:00")
            elif max_deficit < 0:
                st.metric("Mayor Déficit", f"{abs(max_deficit):.0f}", f"Hora: {hora_max_deficit}:00")
            else:
                st.metric("Equilibrio", "Perfecto", "Sin exceso ni déficit")
        else:
            # Para sábado y domingo, mostrar demanda dividida entre 3
            recursos_necesarios = (suma_demanda / 3).round(2)
            st.metric("Recursos Necesarios", f"{recursos_necesarios:.1f}", "Demanda ÷ 3")

# Función para generar PDF
def generar_pdf(demanda_df, recursos_por_hora, dia_seleccionado):
    """
    Genera un PDF con el reporte del día seleccionado
    """
    # Filtrar demanda para el día seleccionado
    if dia_seleccionado == "Todos":
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
        demanda_dia = demanda_df[demanda_df['Dia_Semana'].isin(dias_semana)].copy()
        # Calcular promedio por hora para todos los días de semana
        demanda_promedio = demanda_dia.groupby('Hora')['Promedio_Demanda'].mean().reset_index()
        demanda_promedio['Promedio_Demanda'] = demanda_promedio['Promedio_Demanda'].round(2)
        demanda_promedio['Dia_Semana'] = 'Promedio L-V'
        demanda_dia = demanda_promedio
    else:
        demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
    
    if len(demanda_dia) == 0:
        return None
    
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Configurar fuente
    pdf.set_font("Arial", 'B', 16)
    
    # Título
    titulo = f"Reporte de Análisis - {dia_seleccionado}" if dia_seleccionado != "Todos" else "Reporte de Análisis - Promedio Lunes a Viernes"
    pdf.cell(0, 10, titulo, ln=True, align='C')
    pdf.ln(5)
    
    # Información general
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"Constante de validación: {CONSTANTE_VALIDACION}", ln=True)
    pdf.ln(5)
    
    # Crear tabla
    pdf.set_font("Arial", 'B', 10)
    
    # Encabezados de la tabla
    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
        encabezados = ['Hora', 'Demanda Promedio', 'Recursos Necesarios', 'Recursos Base', 'Capacidad Disponible', 'Diferencia']
        anchos = [15, 25, 25, 20, 30, 20]
    else:
        encabezados = ['Hora', 'Demanda Promedio', 'Recursos Necesarios']
        anchos = [30, 40, 40]
    
    # Agregar encabezados
    for i, encabezado in enumerate(encabezados):
        pdf.cell(anchos[i], 8, encabezado, border=1, align='C')
    pdf.ln()
    
    # Agregar datos
    pdf.set_font("Arial", '', 9)
    
    for _, row in demanda_dia.iterrows():
        hora = row['Hora']
        demanda = row['Promedio_Demanda']
        recursos_necesarios = demanda / 3  # Dividir demanda entre 3
        
        if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
            # Obtener recursos disponibles para esta hora
            recursos_base = recursos_por_hora.get(hora, 0)
            capacidad_disponible = recursos_base * CONSTANTE_VALIDACION
            diferencia = capacidad_disponible - demanda
            
            # Agregar fila
            pdf.cell(anchos[0], 8, f"{hora}:00", border=1, align='C')
            pdf.cell(anchos[1], 8, f"{demanda:.2f}", border=1, align='C')
            pdf.cell(anchos[2], 8, f"{recursos_necesarios:.2f}", border=1, align='C')
            pdf.cell(anchos[3], 8, f"{recursos_base}", border=1, align='C')
            pdf.cell(anchos[4], 8, f"{capacidad_disponible:.2f}", border=1, align='C')
            pdf.cell(anchos[5], 8, f"{diferencia:.2f}", border=1, align='C')
        else:
            # Para sábado y domingo
            pdf.cell(anchos[0], 8, f"{hora}:00", border=1, align='C')
            pdf.cell(anchos[1], 8, f"{demanda:.2f}", border=1, align='C')
            pdf.cell(anchos[2], 8, f"{recursos_necesarios:.2f}", border=1, align='C')
        
        pdf.ln()
    
    # Agregar resumen
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "Resumen:", ln=True)
    
    pdf.set_font("Arial", '', 9)
    
    # Calcular métricas
    suma_demanda = demanda_dia['Promedio_Demanda'].sum()
    suma_recursos_necesarios = suma_demanda / 3
    
    pdf.cell(0, 8, f"Sumatoria demanda: {suma_demanda:.2f} llamadas", ln=True)
    pdf.cell(0, 8, f"Recursos necesarios totales: {suma_recursos_necesarios:.2f} (demanda ÷ 3)", ln=True)
    
    if dia_seleccionado in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Todos']:
        # Calcular recursos disponibles totales
        recursos_disponibles_total = 0
        for hora in demanda_dia['Hora']:
            recursos_base = recursos_por_hora.get(hora, 0)
            recursos_disponibles_total += recursos_base * CONSTANTE_VALIDACION
        
        pdf.cell(0, 8, f"Capacidad disponible total: {recursos_disponibles_total:.2f}", ln=True)
    
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
                    
                    # Obtener días disponibles en orden correcto (Lunes a Domingo)
                    orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo', 'Todos']
                    dias_disponibles = []
                    
                    for dia in orden_dias:
                        if dia == "Todos":
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
                    
                    if st.button(f"📥 Descargar Reporte ({formato_exportacion})", type="primary", use_container_width=True):
                        if formato_exportacion == "PDF":
                            # Generar y exportar PDF
                            pdf_bytes = generar_pdf(demanda_df, recursos_por_hora, dia_seleccionado)
                            if pdf_bytes:
                                nombre_archivo = f"reporte_{dia_seleccionado}.pdf" if dia_seleccionado != "Todos" else "reporte_promedio_lv.pdf"
                                st.download_button(
                                    label="Descargar PDF",
                                    data=pdf_bytes,
                                    file_name=nombre_archivo,
                                    mime="application/pdf"
                                )
                        
                        elif formato_exportacion == "CSV":
                            # Preparar datos para CSV
                            if dia_seleccionado == "Todos":
                                dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                                demanda_dia = demanda_df[demanda_df['Dia_Semana'].isin(dias_semana)].copy()
                                # Calcular promedio por hora
                                reporte_data = demanda_dia.groupby('Hora')['Promedio_Demanda'].mean().reset_index()
                                reporte_data['Recursos_Necesarios'] = reporte_data['Promedio_Demanda'] / 3
                                reporte_data['Recursos_Necesarios'] = reporte_data['Recursos_Necesarios'].round(2)
                            else:
                                demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
                                reporte_data = demanda_dia[['Hora', 'Promedio_Demanda']].copy()
                                reporte_data['Recursos_Necesarios'] = reporte_data['Promedio_Demanda'] / 3
                                reporte_data['Recursos_Necesarios'] = reporte_data['Recursos_Necesarios'].round(2)
                            
                            csv_data = reporte_data.to_csv(index=False).encode('utf-8')
                            nombre_archivo = f"reporte_{dia_seleccionado}.csv" if dia_seleccionado != "Todos" else "reporte_promedio_lv.csv"
                            st.download_button(
                                label="Descargar CSV",
                                data=csv_data,
                                file_name=nombre_archivo,
                                mime="text/csv"
                            )
                        
                        elif formato_exportacion == "XLSX":
                            # Preparar datos para Excel
                            if dia_seleccionado == "Todos":
                                dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                                demanda_dia = demanda_df[demanda_df['Dia_Semana'].isin(dias_semana)].copy()
                                # Calcular promedio por hora
                                reporte_data = demanda_dia.groupby('Hora')['Promedio_Demanda'].mean().reset_index()
                                reporte_data['Recursos_Necesarios'] = reporte_data['Promedio_Demanda'] / 3
                                reporte_data['Recursos_Necesarios'] = reporte_data['Recursos_Necesarios'].round(2)
                            else:
                                demanda_dia = demanda_df[demanda_df['Dia_Semana'] == dia_seleccionado].copy()
                                reporte_data = demanda_dia[['Hora', 'Promedio_Demanda']].copy()
                                reporte_data['Recursos_Necesarios'] = reporte_data['Promedio_Demanda'] / 3
                                reporte_data['Recursos_Necesarios'] = reporte_data['Recursos_Necesarios'].round(2)
                            
                            # Crear Excel en memoria
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                reporte_data.to_excel(writer, index=False, sheet_name='Reporte')
                            
                            excel_data = output.getvalue()
                            nombre_archivo = f"reporte_{dia_seleccionado}.xlsx" if dia_seleccionado != "Todos" else "reporte_promedio_lv.xlsx"
                            st.download_button(
                                label="Descargar Excel",
                                data=excel_data,
                                file_name=nombre_archivo,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
