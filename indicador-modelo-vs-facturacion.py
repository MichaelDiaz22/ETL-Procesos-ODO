import streamlit as st

# Única línea antes de set_page_config - IMPORTante: sin comentarios ni líneas en blanco
st.set_page_config(page_title="Clasificador de Modelo PGP/EVENTO", page_layout="wide")

# Ahora sí, todos los demás imports
import pandas as pd
import numpy as np
from datetime import datetime, date

# Título de la aplicación
st.title("📊 Clasificador de Modelo PGP y EVENTO")
st.markdown("---")

# Función para clasificar según las reglas de negocio
def clasificar_registro(row, unidad_operativa, fecha_ingreso, fecha_factura):
    """
    Clasifica un registro según las reglas de negocio
    """
    if pd.isna(fecha_ingreso) or pd.isna(fecha_factura) or pd.isna(unidad_operativa):
        return "No clasificado"
    
    try:
        fecha_ingreso = pd.to_datetime(fecha_ingreso)
        fecha_factura = pd.to_datetime(fecha_factura)
        unidad = str(unidad_operativa).strip().upper()
    except:
        return "No clasificado"
    
    # Fechas límite según unidad operativa
    if "MANIZALES" in unidad:
        fecha_limite = pd.to_datetime("2025-09-16")
    elif "ARMENIA" in unidad:
        fecha_limite = pd.to_datetime("2025-11-20")
    else:
        return "No clasificado"
    
    # Reglas de clasificación
    try:
        if fecha_ingreso < fecha_limite and fecha_factura < fecha_limite:
            return "No incluido en el modelo"
        elif fecha_ingreso >= fecha_limite and fecha_factura >= fecha_limite:
            return "Incluido en el modelo"
        else:
            return "No incluido en el modelo"
    except:
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
            columnas_existentes = [col for col in columnas_requeridas if col in df.columns]
            
            if len(columnas_existentes) < 4:
                st.warning(f"Hoja '{nombre_hoja}' no tiene todas las columnas requeridas")
                continue
            
            # Clasificar cada registro
            clasificaciones = []
            for idx, row in df.iterrows():
                try:
                    clasificacion = clasificar_registro(
                        row, 
                        row.get('Unidad operativa'), 
                        row.get('Fecha ingreso'), 
                        row.get('Fecha factura')
                    )
                except:
                    clasificacion = "Error en clasificación"
                clasificaciones.append(clasificacion)
            
            df['Clasificacion'] = clasificaciones
            df['Hoja'] = nombre_hoja
            resultados.append(df)
    
    if not resultados:
        return pd.DataFrame()
    
    # Combinar todos los dataframes
    df_combinado = pd.concat(resultados, ignore_index=True, sort=False)
    
    # Convertir fechas
    df_combinado['Fecha ingreso'] = pd.to_datetime(df_combinado['Fecha ingreso'], errors='coerce')
    df_combinado['Fecha factura'] = pd.to_datetime(df_combinado['Fecha factura'], errors='coerce')
    
    # Crear rango de fechas
    fecha_inicio = pd.to_datetime("2025-09-16")
    fecha_fin = pd.to_datetime(fecha_fin_seleccionada)
    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
    
    # Crear dataframe resumen
    resumen = []
    
    for fecha_actual in fechas:
        try:
            # Ingresos (todas las hojas)
            mask_ingresos = (
                (df_combinado['Fecha ingreso'].dt.date == fecha_actual.date()) &
                (df_combinado['Hoja'].isin(['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']))
            )
            ingresos_fecha = df_combinado.loc[mask_ingresos, 'Ingreso'].sum()
            
            # Facturado modelo
            mask_modelo = (
                (df_combinado['Fecha factura'].dt.date == fecha_actual.date()) &
                (df_combinado['Hoja'].isin(['PGP', 'EVENTO'])) &
                (df_combinado['Clasificacion'] == 'Incluido en el modelo')
            )
            fact_modelo = df_combinado.loc[mask_modelo, 'Ingreso'].sum()
            
            # Facturado fuera modelo
            mask_fuera = (
                (df_combinado['Fecha factura'].dt.date == fecha_actual.date()) &
                (df_combinado['Hoja'].isin(['PGP', 'EVENTO'])) &
                (df_combinado['Clasificacion'] == 'No incluido en el modelo')
            )
            fact_fuera = df_combinado.loc[mask_fuera, 'Ingreso'].sum()
            
            resumen.append({
                'fecha': fecha_actual.strftime('%Y-%m-%d'),
                'semana': fecha_actual.isocalendar()[1],
                'año': fecha_actual.year,
                'ingresos': float(ingresos_fecha) if not pd.isna(ingresos_fecha) else 0,
                'facturado_modelo': float(fact_modelo) if not pd.isna(fact_modelo) else 0,
                'facturado_fuera_modelo': float(fact_fuera) if not pd.isna(fact_fuera) else 0,
            })
        except:
            continue
    
    df_resumen = pd.DataFrame(resumen)
    if not df_resumen.empty:
        df_resumen['Facturado_total'] = df_resumen['facturado_modelo'] + df_resumen['facturado_fuera_modelo']
    
    return df_resumen, df_combinado

# Interfaz principal
col1, col2 = st.columns([2, 1])

with col1:
    archivo_subido = st.file_uploader(
        "Cargar archivo Excel", 
        type=['xlsx', 'xls'],
        help="Selecciona el archivo Excel con las hojas: PGP, EVENTO, PDTE PGP, PDTE EVENTO"
    )

with col2:
    fecha_max = date.today()
    fecha_fin = st.date_input(
        "Fecha fin para el análisis",
        value=date(2025, 12, 31),
        min_value=date(2025, 9, 16),
        max_value=fecha_max
    )

if archivo_subido is not None:
    try:
        with st.spinner('Procesando archivo...'):
            excel_file = pd.ExcelFile(archivo_subido)
            hojas = {}
            
            for hoja in ['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']:
                if hoja in excel_file.sheet_names:
                    hojas[hoja] = pd.read_excel(archivo_subido, sheet_name=hoja)
                    st.success(f"✅ Hoja '{hoja}' cargada")
            
            if hojas:
                df_resumen, df_detalle = procesar_archivo_excel(hojas, fecha_fin)
                
                if not df_resumen.empty:
                    st.markdown("---")
                    st.subheader("📈 Tabla Resumen")
                    
                    # Métricas
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Ingresos", f"${df_resumen['ingresos'].sum():,.0f}")
                    with col2:
                        st.metric("Facturado Modelo", f"${df_resumen['facturado_modelo'].sum():,.0f}")
                    with col3:
                        st.metric("Facturado Fuera Modelo", f"${df_resumen['facturado_fuera_modelo'].sum():,.0f}")
                    with col4:
                        st.metric("Facturado Total", f"${df_resumen['Facturado_total'].sum():,.0f}")
                    
                    # Tabla
                    st.dataframe(
                        df_resumen,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "fecha": "Fecha",
                            "semana": "Semana",
                            "año": "Año",
                            "ingresos": st.column_config.NumberColumn("Ingresos", format="$%.0f"),
                            "facturado_modelo": st.column_config.NumberColumn("Fact. Modelo", format="$%.0f"),
                            "facturado_fuera_modelo": st.column_config.NumberColumn("Fact. Fuera", format="$%.0f"),
                            "Facturado_total": st.column_config.NumberColumn("Fact. Total", format="$%.0f")
                        }
                    )
                    
                    # Gráficos simples
                    st.markdown("---")
                    st.subheader("📊 Visualizaciones")
                    
                    if len(df_resumen) > 0:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Evolución de Ingresos")
                            chart_data = df_resumen.set_index('fecha')[['ingresos']]
                            st.line_chart(chart_data)
                        
                        with col2:
                            st.subheader("Facturado Modelo vs Fuera")
                            chart_data2 = df_resumen.set_index('fecha')[['facturado_modelo', 'facturado_fuera_modelo']]
                            st.bar_chart(chart_data2)
                    
                    # Botón descarga
                    csv = df_resumen.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar CSV",
                        data=csv,
                        file_name=f"resumen_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                    
            else:
                st.error("No se encontraron hojas válidas")
                
    except Exception as e:
        st.error(f"Error: {str(e)}")

else:
    st.info("👆 Carga un archivo Excel para comenzar")

# Instrucciones
with st.expander("📋 Instrucciones"):
    st.markdown("""
    **Reglas:**
    - Manizales: fecha límite 16/09/2025
    - Armenia: fecha límite 20/11/2025
    
    **Columnas necesarias:**
    - Fecha ingreso, Fecha factura, Unidad operativa, Ingreso
    """)
