import streamlit as st

# Configuración de la página - DEBE SER LO PRIMERO
st.set_page_config(
    page_title="Clasificador de Modelo PGP/EVENTO",
    page_layout="wide"
)

import pandas as pd
import numpy as np
from datetime import datetime, date

# El resto del código continúa aquí...
st.title("📊 Clasificador de Modelo PGP y EVENTO")
st.markdown("---")

# Función para clasificar según las reglas de negocio
def clasificar_registro(row, unidad_operativa, fecha_ingreso, fecha_factura):
    """
    Clasifica un registro según las reglas de negocio
    """
    if pd.isna(fecha_ingreso) or pd.isna(fecha_factura) or pd.isna(unidad_operativa):
        return "No clasificado"
    
    fecha_ingreso = pd.to_datetime(fecha_ingreso)
    fecha_factura = pd.to_datetime(fecha_factura)
    unidad = str(unidad_operativa).strip().upper()
    
    # Fechas límite según unidad operativa
    if "MANIZALES" in unidad:
        fecha_limite = pd.to_datetime("2025-09-16")
    elif "ARMENIA" in unidad:
        fecha_limite = pd.to_datetime("2025-11-20")
    else:
        return "No clasificado"
    
    # Reglas de clasificación
    if fecha_ingreso < fecha_limite and fecha_factura < fecha_limite:
        return "No incluido en el modelo"
    elif fecha_ingreso >= fecha_limite and fecha_factura >= fecha_limite:
        return "Incluido en el modelo"
    elif fecha_ingreso >= fecha_limite and fecha_factura < fecha_limite:
        return "No incluido en el modelo"
    elif fecha_ingreso < fecha_limite and fecha_factura >= fecha_limite:
        return "No incluido en el modelo"
    else:
        return "No clasificado"

# Función para procesar todas las hojas
def procesar_archivo_excel(dfs, fecha_fin_seleccionada):
    """
    Procesa todas las hojas del Excel y genera la tabla resumen
    """
    resultados = []
    
    # Procesar cada hoja
    for nombre_hoja, df in dfs.items():
        if nombre_hoja in ['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']:
            # Verificar que las columnas necesarias existan
            columnas_requeridas = ['Fecha ingreso', 'Fecha factura', 'Unidad operativa', 'Ingreso']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                st.warning(f"Hoja '{nombre_hoja}' no tiene las columnas: {columnas_faltantes}")
                continue
            
            # Clasificar cada registro
            clasificaciones = []
            for idx, row in df.iterrows():
                clasificacion = clasificar_registro(
                    row, 
                    row.get('Unidad operativa'), 
                    row.get('Fecha ingreso'), 
                    row.get('Fecha factura')
                )
                clasificaciones.append(clasificacion)
            
            df['Clasificacion'] = clasificaciones
            
            # Agregar nombre de hoja para referencia
            df['Hoja'] = nombre_hoja
            resultados.append(df)
    
    if not resultados:
        return pd.DataFrame()
    
    # Combinar todos los dataframes
    df_combinado = pd.concat(resultados, ignore_index=True)
    
    # Convertir fechas
    df_combinado['Fecha ingreso'] = pd.to_datetime(df_combinado['Fecha ingreso'], errors='coerce')
    df_combinado['Fecha factura'] = pd.to_datetime(df_combinado['Fecha factura'], errors='coerce')
    
    # Crear rango de fechas para la tabla resumen
    fecha_inicio = pd.to_datetime("2025-09-16")
    fecha_fin = pd.to_datetime(fecha_fin_seleccionada)
    
    # Generar todas las fechas en el rango
    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
    
    # Crear dataframe resumen
    resumen = []
    
    for fecha_actual in fechas:
        fecha_str = fecha_actual.strftime('%Y-%m-%d')
        
        # Ingresos (todas las hojas)
        ingresos_fecha = df_combinado[
            (df_combinado['Fecha ingreso'].dt.date == fecha_actual.date()) &
            (df_combinado['Hoja'].isin(['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']))
        ]['Ingreso'].sum()
        
        # Facturado modelo (solo PGP y EVENTO, clasificados como incluido)
        fact_modelo = df_combinado[
            (df_combinado['Fecha factura'].dt.date == fecha_actual.date()) &
            (df_combinado['Hoja'].isin(['PGP', 'EVENTO'])) &
            (df_combinado['Clasificacion'] == 'Incluido en el modelo')
        ]['Ingreso'].sum()
        
        # Facturado fuera modelo (solo PGP y EVENTO, clasificados como no incluido)
        fact_fuera_modelo = df_combinado[
            (df_combinado['Fecha factura'].dt.date == fecha_actual.date()) &
            (df_combinado['Hoja'].isin(['PGP', 'EVENTO'])) &
            (df_combinado['Clasificacion'] == 'No incluido en el modelo')
        ]['Ingreso'].sum()
        
        resumen.append({
            'fecha': fecha_str,
            'semana del año': fecha_actual.isocalendar()[1],
            'año': fecha_actual.year,
            'ingresos': ingresos_fecha,
            'facturado modelo': fact_modelo,
            'facturado fuera modelo': fact_fuera_modelo,
            'Facturado total': fact_modelo + fact_fuera_modelo
        })
    
    df_resumen = pd.DataFrame(resumen)
    
    return df_resumen, df_combinado

# Interfaz de usuario
col1, col2 = st.columns([2, 1])

with col1:
    # Cargar archivo
    archivo_subido = st.file_uploader(
        "Cargar archivo Excel", 
        type=['xlsx', 'xls'],
        help="Selecciona el archivo Excel con las hojas: PGP, EVENTO, PDTE PGP, PDTE EVENTO"
    )

with col2:
    # Selector de fecha fin
    fecha_max = date.today()
    fecha_fin = st.date_input(
        "Fecha fin para el análisis",
        value=date(2025, 12, 31),
        min_value=date(2025, 9, 16),
        max_value=fecha_max,
        help="Selecciona la fecha hasta la cual quieres generar el análisis"
    )

if archivo_subido is not None:
    try:
        # Leer todas las hojas del Excel
        with st.spinner('Cargando y procesando el archivo...'):
            excel_file = pd.ExcelFile(archivo_subido)
            hojas = {}
            
            for hoja in ['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']:
                if hoja in excel_file.sheet_names:
                    hojas[hoja] = pd.read_excel(archivo_subido, sheet_name=hoja)
                    st.success(f"✅ Hoja '{hoja}' cargada correctamente")
                else:
                    st.warning(f"⚠️ Hoja '{hoja}' no encontrada en el archivo")
            
            if hojas:
                # Procesar el archivo
                df_resumen, df_detalle = procesar_archivo_excel(hojas, fecha_fin)
                
                if not df_resumen.empty:
                    st.markdown("---")
                    st.subheader("📈 Tabla Resumen")
                    
                    # Mostrar estadísticas rápidas
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Ingresos", f"${df_resumen['ingresos'].sum():,.0f}")
                    with col2:
                        st.metric("Total Facturado Modelo", f"${df_resumen['facturado modelo'].sum():,.0f}")
                    with col3:
                        st.metric("Total Facturado Fuera Modelo", f"${df_resumen['facturado fuera modelo'].sum():,.0f}")
                    with col4:
                        st.metric("Total Facturado General", f"${df_resumen['Facturado total'].sum():,.0f}")
                    
                    # Mostrar tabla
                    st.dataframe(
                        df_resumen,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "fecha": "Fecha",
                            "semana del año": "Semana",
                            "año": "Año",
                            "ingresos": st.column_config.NumberColumn("Ingresos", format="$%.0f"),
                            "facturado modelo": st.column_config.NumberColumn("Facturado Modelo", format="$%.0f"),
                            "facturado fuera modelo": st.column_config.NumberColumn("Facturado Fuera Modelo", format="$%.0f"),
                            "Facturado total": st.column_config.NumberColumn("Facturado Total", format="$%.0f")
                        }
                    )
                    
                    # Gráficos con Streamlit (sin plotly)
                    st.markdown("---")
                    st.subheader("📊 Visualizaciones")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Gráfico de líneas con datos agregados por semana
                        st.subheader("Evolución por Semana")
                        if not df_resumen.empty:
                            df_semanal = df_resumen.groupby('semana del año').agg({
                                'ingresos': 'sum',
                                'facturado modelo': 'sum',
                                'facturado fuera modelo': 'sum'
                            }).reset_index()
                            
                            st.line_chart(
                                df_semanal.set_index('semana del año')[['ingresos', 'facturado modelo', 'facturado fuera modelo']]
                            )
                    
                    with col2:
                        # Gráfico de barras para facturado
                        st.subheader("Facturado Modelo vs Fuera Modelo")
                        if not df_resumen.empty and len(df_resumen) > 0:
                            # Mostrar solo últimos 30 días para mejor visualización
                            df_ultimos = df_resumen.tail(30)
                            df_barras = df_ultimos[['fecha', 'facturado modelo', 'facturado fuera modelo']].set_index('fecha')
                            st.bar_chart(df_barras)
                    
                    # Botón para descargar
                    st.markdown("---")
                    csv = df_resumen.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar tabla resumen (CSV)",
                        data=csv,
                        file_name=f"resumen_modelo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # Mostrar detalle de clasificaciones
                    with st.expander("Ver detalle de clasificaciones por hoja"):
                        for nombre_hoja, df_hoja in hojas.items():
                            st.subheader(f"Hoja: {nombre_hoja}")
                            
                            # Aplicar clasificación para vista previa
                            df_vista = df_hoja.copy()
                            clasif_temp = []
                            for idx, row in df_vista.iterrows():
                                clasif_temp.append(clasificar_registro(
                                    row,
                                    row.get('Unidad operativa'),
                                    row.get('Fecha ingreso'),
                                    row.get('Fecha factura')
                                ))
                            df_vista['Clasificacion'] = clasif_temp
                            
                            # Mostrar conteo
                            conteo = df_vista['Clasificacion'].value_counts()
                            st.write("Conteo de clasificaciones:")
                            st.write(conteo)
                            
                            # Mostrar muestra de datos
                            st.dataframe(df_vista.head(10))
                            
                else:
                    st.warning("No se pudieron procesar los datos. Verifica la estructura del archivo.")
            else:
                st.error("No se encontraron hojas válidas en el archivo. Debe contener al menos una de las hojas: PGP, EVENTO, PDTE PGP, PDTE EVENTO")
                
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        st.exception(e)

else:
    st.info("👆 Por favor, carga un archivo Excel para comenzar el análisis")

# Instrucciones de uso
with st.expander("📋 Instrucciones de uso"):
    st.markdown("""
    ### Reglas de clasificación:
    1. **Manizales**: 
       - Fecha ingreso < 16/09/2025 Y fecha factura < 16/09/2025 → "No incluido en el modelo"
       - Fecha ingreso >= 16/09/2025 Y fecha factura >= 16/09/2025 → "Incluido en el modelo"
       - Otros casos → "No incluido en el modelo"
    
    2. **Armenia**:
       - Mismas reglas pero con fecha límite 20/11/2025
    
    ### Columnas requeridas en cada hoja:
    - Fecha ingreso
    - Fecha factura
    - Unidad operativa
    - Ingreso
    
    ### Hojas requeridas:
    - PGP
    - EVENTO
    - PDTE PGP
    - PDTE EVENTO
    """)
