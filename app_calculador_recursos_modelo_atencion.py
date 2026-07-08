import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

st.set_page_config(page_title="Procesador de Excel", layout="wide")

st.title("📊 Procesador de Archivos Excel")
st.write("Carga un archivo Excel con las hojas: **FECHA DE CITA**, **FECHA DE REGISTRO** y **USUARIOS**")

# Inicializar estado de sesión
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'dfs' not in st.session_state:
    st.session_state.dfs = {}
if 'process_clicked' not in st.session_state:
    st.session_state.process_clicked = False

def generar_tabla_horas():
    """
    Genera una tabla con las horas desde 06:30 hasta 19:00 cada 5 minutos
    """
    horas = []
    hora_actual = datetime(2000, 1, 1, 6, 30)  # 06:30
    hora_fin = datetime(2000, 1, 1, 19, 0)     # 19:00
    
    while hora_actual <= hora_fin:
        horas.append(hora_actual.strftime('%H:%M'))
        hora_actual += timedelta(minutes=5)
    
    # Crear DataFrame solo con la columna Hora
    resumen_df = pd.DataFrame({'Hora': horas})
    
    return resumen_df

# Cargar archivo
uploaded_file = st.file_uploader(
    "Selecciona un archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: FECHA DE CITA, FECHA DE REGISTRO y USUARIOS"
)

if uploaded_file is not None:
    try:
        # Leer todas las hojas del Excel
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        # Verificar que existan las hojas requeridas
        required_sheets = ['FECHA DE CITA', 'FECHA DE REGISTRO', 'USUARIOS']
        missing_sheets = [sheet for sheet in required_sheets if sheet not in sheet_names]
        
        if missing_sheets:
            st.error(f"❌ Faltan las siguientes hojas en el archivo: {', '.join(missing_sheets)}")
            st.info(f"Hojas encontradas: {', '.join(sheet_names)}")
        else:
            # Leer cada hoja
            df_cita = pd.read_excel(uploaded_file, sheet_name='FECHA DE CITA')
            df_registro = pd.read_excel(uploaded_file, sheet_name='FECHA DE REGISTRO')
            df_usuarios = pd.read_excel(uploaded_file, sheet_name='USUARIOS')
            
            # Guardar en estado de sesión
            st.session_state.dfs = {
                'FECHA DE CITA': df_cita,
                'FECHA DE REGISTRO': df_registro,
                'USUARIOS': df_usuarios
            }
            st.session_state.data_loaded = True
            st.session_state.process_clicked = False
            
            # Mostrar información básica
            st.success("✅ Archivo cargado correctamente")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📋 FECHA DE CITA", f"{len(df_cita)} registros")
            with col2:
                st.metric("📋 FECHA DE REGISTRO", f"{len(df_registro)} registros")
            with col3:
                st.metric("👥 USUARIOS", f"{len(df_usuarios)} registros")
            
            # Botón para procesar
            if st.button("🔄 Procesar", type="primary", use_container_width=True):
                with st.spinner("Generando tabla de resumen..."):
                    # Generar tabla con las horas
                    df_resumen = generar_tabla_horas()
                    
                    # Guardar datos procesados
                    st.session_state.dfs_procesados = {
                        'RESUMEN': df_resumen
                    }
                    st.session_state.process_clicked = True
                    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")

# Mostrar resumen SOLO si se ha presionado el botón "Procesar"
if st.session_state.process_clicked and st.session_state.data_loaded:
    if 'dfs_procesados' in st.session_state:
        st.divider()
        st.header("📊 Tabla de Resumen")
        st.write("Horarios desde 06:30 hasta 19:00 (cada 5 minutos)")
        
        df = st.session_state.dfs_procesados['RESUMEN']
        
        # Mostrar estadísticas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Horas", f"{len(df)}")
        with col2:
            st.metric("Hora Inicio", "06:30")
            st.metric("Hora Fin", "19:00")
        
        # Mostrar el DataFrame completo
        st.dataframe(df, use_container_width=True, height=600)
        
        # Opción para descargar la tabla
        st.divider()
        st.subheader("📥 Descargar Tabla")
        col1, col2, col3 = st.columns(3)
        with col2:
            # Crear archivo Excel con la tabla de horas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='HORAS', index=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Descargar Tabla de Horas (Excel)",
                data=output,
                file_name="tabla_horas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Mensaje informativo cuando el archivo está cargado pero no se ha procesado
elif st.session_state.data_loaded and not st.session_state.process_clicked:
    st.info("📌 Haz clic en el botón 'Procesar' para generar la tabla de horas")

# Si no hay archivo cargado
else:
    st.info("📂 Por favor, carga un archivo Excel para comenzar")
