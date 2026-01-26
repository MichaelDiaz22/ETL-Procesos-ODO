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

# Constante para el cálculo
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
        
        # Calcular promedio y DIVIDIR ENTRE 3
        demanda_con_dias['Promedio_Demanda'] = (demanda_con_dias['Conteo'] / demanda_con_dias['Num_Dias']) / 3
        
        # Redondear a 2 decimales
        demanda_con_dias['Promedio_Demanda'] = demanda_con_dias['Promedio_Demanda'].round(2)
        
        # Calcular total de llamadas diarias (promedio diario total)
        demanda_total_diaria = demanda_con_dias.groupby('Dia_Semana')['Promedio_Demanda'].sum().reset_index()
        demanda_total_diaria = demanda_total_diaria.rename(columns={'Promedio_Demanda': 'Total_Llamadas_Diarias'})
        
        # Combinar con el DataFrame principal
        demanda_con_dias = pd.merge(demanda_con_dias, demanda_total_diaria, on='Dia_Semana')
        
        # Ordenar por día y hora
        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        demanda_con_dias['Dia_Semana'] = pd.Categorical(demanda_con_dias['Dia_Semana'], categories=orden_dias, ordered=True)
        demanda_con_dias = demanda_con_dias.sort_values(['Dia_Semana', 'Hora'])
        
        return demanda_con_dias[['Dia_Semana', 'Hora', 'Promedio_Demanda', 'Total_Llamadas_Diarias', 'Conteo', 'Num_Dias']]
        
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return None

# Función para crear PDF
def crear_pdf(demanda_df, recursos_por_hora, dia_seleccionado, datos_grafica):
    """Crea un PDF con los resultados del análisis"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Título
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Reporte de Análisis de Llamadas', 0, 1, 'C')
        pdf.ln(10)
        
        # Información general
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'Día analizado: {dia_seleccionado}', 0, 1)
        
        # Recursos configurados
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Recursos configurados por hora:', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        recursos_texto = ""
        for hora, valor in sorted(recursos_por_hora.items()):
            recursos_texto += f"{hora}:00 - Base: {valor}, Total: {valor * CONSTANTE_VALIDACION:.1f}\n"
        
        pdf.multi_cell(0, 8, recursos_texto)
        pdf.ln(5)
        
        # Métricas
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Métricas principales:', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        # Obtener métricas
        max_demanda = datos_grafica['Demanda_Promedio'].max()
        hora_max_demanda = datos_grafica.loc[datos_grafica['Demanda_Promedio'].idxmax(), 'Hora']
        max_recursos = datos_grafica['Recursos_Disponibles'].max()
        hora_max_recursos = datos_grafica.loc[datos_grafica['Recursos_Disponibles'].idxmax(), 'Hora']
        total_llamadas = datos_grafica['Demanda_Promedio'].sum()
        
        # Calcular diferencia
        datos_grafica['Diferencia'] = datos_grafica['Recursos_Disponibles'] - datos_grafica['Demanda_Promedio']
        max_exceso = datos_grafica['Diferencia'].max()
        max_deficit = datos_grafica['Diferencia'].min()
        
        metricas_texto = f"""
        Pico de demanda: {max_demanda:.0f} llamadas (Hora: {hora_max_demanda}:00)
        Máximo recursos: {max_recursos:.0f} (Hora: {hora_max_recursos}:00)
        Total llamadas diarias: {total_llamadas:.0f}
        """
        
        if max_exceso > 0:
            metricas_texto += f"Mayor exceso: {max_exceso:.0f}\n"
        else:
            metricas_texto += f"Mayor déficit: {abs(max_deficit):.0f}\n"
        
        pdf.multi_cell(0, 8, metricas_texto)
        pdf.ln(5)
        
        # Tabla de datos
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Datos por hora:', 0, 1)
        pdf.set_font('Arial', 'B', 10)
        
        # Encabezados de tabla
        pdf.cell(30, 8, 'Hora', 1)
        pdf.cell(40, 8, 'Recursos Base', 1)
        pdf.cell(40, 8, 'Capacidad de Recursos', 1)
        pdf.cell(40, 8, 'Demanda Promedio', 1)
        pdf.ln()
        
        # Datos de tabla
        pdf.set_font('Arial', '', 10)
        for idx, row in datos_grafica.iterrows():
            hora = int(row['Hora'])
            recursos_base = row['Recursos_Base']
            recursos_total = row['Recursos_Disponibles']
            demanda = row['Demanda_Promedio']
            
            pdf.cell(30, 8, f"{hora}:00", 1)
            pdf.cell(40, 8, f"{recursos_base:.1f}", 1)
            pdf.cell(40, 8, f"{recursos_total:.1f}", 1)
            pdf.cell(40, 8, f"{demanda:.1f}", 1)
            pdf.ln()
        
        # Guardar PDF
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Error al crear PDF: {e}")
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
        return None
    
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
    
    # Renombrar columnas para la gráfica
    datos_grafica = datos_grafica.rename(columns={
        'Recursos': 'Recursos_Disponibles',
        'Promedio_Demanda': 'Demanda_Promedio'
    })
    
    # Calcular recursos base
    datos_grafica['Recursos_Base'] = datos_grafica['Recursos_Disponibles'] / CONSTANTE_VALIDACION
    
    # Crear gráfica
    st.write(f"### 📈 Comparación: Recursos vs Demanda - {dia_seleccionado}")
    
    # Configurar gráfica
    chart_data = datos_grafica.set_index('Hora')
    
    # Mostrar gráfica
    st.line_chart(chart_data[['Recursos_Disponibles', 'Demanda_Promedio']], height=500)
    
    # Calcular métricas de comparación
    st.write(f"**Métricas para {dia_seleccionado}:**")
    
    # Obtener total de llamadas diarias
    total_llamadas_dia = demanda_dia['Total_Llamadas_Diarias'].iloc[0] if len(demanda_dia) > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Pico de demanda
        pico_demanda = datos_grafica['Demanda_Promedio'].max()
        hora_pico = datos_grafica.loc[datos_grafica['Demanda_Promedio'].idxmax(), 'Hora']
        st.metric("Pico de demanda", f"{pico_demanda:.0f} llamadas", f"Hora: {hora_pico}:00")
    
    with col2:
        # Pico de recursos
        pico_recursos = datos_grafica['Recursos_Disponibles'].max()
        hora_recursos = datos_grafica.loc[datos_grafica['Recursos_Disponibles'].idxmax(), 'Hora']
        st.metric("Pico capacidad recursos", f"{pico_recursos:.0f}", f"Hora: {hora_recursos}:00")
    
    with col3:
        # Total de llamadas diarias
        st.metric("Promedio llamadas diarias", f"{total_llamadas_dia:.0f}")
    
    with col4:
        # Diferencia máxima
        datos_grafica['Diferencia'] = datos_grafica['Recursos_Disponibles'] - datos_grafica['Demanda_Promedio']
        max_exceso = datos_grafica['Diferencia'].max()
        max_deficit = datos_grafica['Diferencia'].min()
        
        if max_exceso > 0:
            st.metric("Mayor exceso", f"{max_exceso:.0f}")
        else:
            st.metric("Mayor déficit", f"{abs(max_deficit):.0f}")
    
    return datos_grafica

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
                st.subheader("👥 Configuración de Recursos por hora")
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
                        st.metric("Capacidad máxima de recursos", f"{max_recursos_total:.1f}")
                
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
                    datos_grafica = crear_grafica_comparativa(demanda_df, recursos_por_hora, dia_seleccionado)
                    
                    if datos_grafica is not None:
                        # Botón para generar PDF
                        st.divider()
                        st.write("### 📄 Generar Reporte PDF")
                        
                        if st.button("🖨️ Generar Reporte PDF", type="primary"):
                            with st.spinner("Generando reporte PDF..."):
                                pdf_bytes = crear_pdf(demanda_df, recursos_por_hora, dia_seleccionado, datos_grafica)
                                
                                if pdf_bytes:
                                    # Crear botón de descarga
                                    b64 = base64.b64encode(pdf_bytes).decode()
                                    href = f'<a href="data:application/pdf;base64,{b64}" download="reporte_analisis_{dia_seleccionado}.pdf">📥 Descargar Reporte PDF</a>'
                                    st.markdown(href, unsafe_allow_html=True)
                                    st.success("✅ Reporte PDF generado exitosamente")
                
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
