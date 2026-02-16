import streamlit as st
st.set_page_config(page_title="Clasificador Modelo", page_layout="wide")

import pandas as pd
import numpy as np
from datetime import datetime, date

st.title("📊 Clasificador de Modelo PGP y EVENTO")
st.markdown("---")

def clasificar(unidad, fecha_ingreso, fecha_factura):
    try:
        if pd.isna(unidad) or pd.isna(fecha_ingreso) or pd.isna(fecha_factura):
            return "No clasificado"
        
        f_ingreso = pd.to_datetime(fecha_ingreso)
        f_factura = pd.to_datetime(fecha_factura)
        u = str(unidad).upper()
        
        if "MANIZALES" in u:
            limite = pd.to_datetime("2025-09-16")
        elif "ARMENIA" in u:
            limite = pd.to_datetime("2025-11-20")
        else:
            return "No clasificado"
        
        if f_ingreso < limite and f_factura < limite:
            return "No incluido"
        elif f_ingreso >= limite and f_factura >= limite:
            return "Incluido"
        else:
            return "No incluido"
    except:
        return "Error"

def procesar(archivo, fecha_fin):
    excel = pd.ExcelFile(archivo)
    datos = []
    
    for hoja in ['PGP', 'EVENTO', 'PDTE PGP', 'PDTE EVENTO']:
        if hoja in excel.sheet_names:
            df = pd.read_excel(archivo, sheet_name=hoja)
            cols = ['Fecha ingreso', 'Fecha factura', 'Unidad operativa', 'Ingreso']
            if all(c in df.columns for c in cols):
                df['clasificacion'] = df.apply(lambda x: clasificar(
                    x['Unidad operativa'], 
                    x['Fecha ingreso'], 
                    x['Fecha factura']
                ), axis=1)
                df['hoja'] = hoja
                datos.append(df)
    
    if not datos:
        return pd.DataFrame()
    
    todo = pd.concat(datos, ignore_index=True)
    todo['Fecha ingreso'] = pd.to_datetime(todo['Fecha ingreso'], errors='coerce')
    todo['Fecha factura'] = pd.to_datetime(todo['Fecha factura'], errors='coerce')
    
    fechas = pd.date_range("2025-09-16", fecha_fin)
    resumen = []
    
    for f in fechas:
        ingresos = todo[(todo['Fecha ingreso'].dt.date == f.date())]['Ingreso'].sum()
        fact_modelo = todo[
            (todo['Fecha factura'].dt.date == f.date()) & 
            (todo['hoja'].isin(['PGP', 'EVENTO'])) & 
            (todo['clasificacion'] == 'Incluido')
        ]['Ingreso'].sum()
        fact_fuera = todo[
            (todo['Fecha factura'].dt.date == f.date()) & 
            (todo['hoja'].isin(['PGP', 'EVENTO'])) & 
            (todo['clasificacion'] == 'No incluido')
        ]['Ingreso'].sum()
        
        resumen.append({
            'fecha': f.strftime('%Y-%m-%d'),
            'semana': f.isocalendar()[1],
            'año': f.year,
            'ingresos': float(ingresos) if not pd.isna(ingresos) else 0,
            'fact_modelo': float(fact_modelo) if not pd.isna(fact_modelo) else 0,
            'fact_fuera': float(fact_fuera) if not pd.isna(fact_fuera) else 0,
        })
    
    df_res = pd.DataFrame(resumen)
    if not df_res.empty:
        df_res['fact_total'] = df_res['fact_modelo'] + df_res['fact_fuera']
    return df_res

col1, col2 = st.columns([2,1])
with col1:
    archivo = st.file_uploader("Cargar Excel", type=['xlsx','xls'])
with col2:
    fecha_fin = st.date_input("Fecha fin", value=date(2025,12,31), min_value=date(2025,9,16), max_value=date.today())

if archivo:
    try:
        with st.spinner('Procesando...'):
            df = procesar(archivo, fecha_fin)
            
            if not df.empty:
                st.subheader("📈 Resumen")
                
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("Ingresos", f"${df['ingresos'].sum():,.0f}")
                m2.metric("Fact Modelo", f"${df['fact_modelo'].sum():,.0f}")
                m3.metric("Fact Fuera", f"${df['fact_fuera'].sum():,.0f}")
                m4.metric("Fact Total", f"${df['fact_total'].sum():,.0f}")
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.line_chart(df.set_index('fecha')[['ingresos']])
                with col2:
                    st.bar_chart(df.set_index('fecha')[['fact_modelo','fact_fuera']])
                
                csv = df.to_csv(index=False)
                st.download_button("📥 Descargar CSV", csv, "resumen.csv")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Carga un archivo Excel")

with st.expander("ℹ️ Instrucciones"):
    st.write("""
    **Reglas:**
    - Manizales: fecha límite 16/09/2025
    - Armenia: fecha límite 20/11/2025
    **Hojas:** PGP, EVENTO, PDTE PGP, PDTE EVENTO
    **Columnas:** Fecha ingreso, Fecha factura, Unidad operativa, Ingreso
    """)
