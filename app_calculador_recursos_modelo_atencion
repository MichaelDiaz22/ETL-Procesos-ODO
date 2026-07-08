import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Procesador de Excel", layout="wide")

st.title("📊 Procesador de Archivos Excel")
st.write("Carga un archivo Excel con las hojas: **FECHA DE CITA**, **FECHA DE REGISTRO** y **USUARIOS**")

# Inicializar estado de sesión
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'dfs' not in st.session_state:
    st.session_state.dfs = {}

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
                st.session_state.data_loaded = True
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")

# Mostrar resumen si los datos están cargados
if st.session_state.data_loaded and st.session_state.dfs:
    st.divider()
    st.header("📊 Resumen de Datos")
    
    # Crear tabs para cada hoja
    tab1, tab2, tab3 = st.tabs(["📅 FECHA DE CITA", "📝 FECHA DE REGISTRO", "👥 USUARIOS"])
    
    with tab1:
        df = st.session_state.dfs['FECHA DE CITA']
        st.subheader(f"Primeros 10 registros de FECHA DE CITA (Total: {len(df)})")
        if len(df) > 0:
            st.dataframe(df.head(10), use_container_width=True)
        else:
            st.info("La hoja está vacía")
    
    with tab2:
        df = st.session_state.dfs['FECHA DE REGISTRO']
        st.subheader(f"Primeros 10 registros de FECHA DE REGISTRO (Total: {len(df)})")
        if len(df) > 0:
            st.dataframe(df.head(10), use_container_width=True)
        else:
            st.info("La hoja está vacía")
    
    with tab3:
        df = st.session_state.dfs['USUARIOS']
        st.subheader(f"Primeros 10 registros de USUARIOS (Total: {len(df)})")
        if len(df) > 0:
            st.dataframe(df.head(10), use_container_width=True)
        else:
            st.info("La hoja está vacía")
    
    # Opción para descargar el resumen
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("📥 Descargar Resumen (CSV)", use_container_width=True):
            # Crear un archivo CSV con los primeros 10 registros de cada hoja
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, df in st.session_state.dfs.items():
                    df.head(10).to_excel(writer, sheet_name=sheet_name, index=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Descargar Resumen (Excel)",
                data=output,
                file_name="resumen_datos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    if not st.session_state.data_loaded and uploaded_file is not None:
        st.info("📌 Haz clic en el botón 'Procesar' para mostrar el resumen de los datos")
