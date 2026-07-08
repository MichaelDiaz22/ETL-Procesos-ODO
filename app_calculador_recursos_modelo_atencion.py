import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import re

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

def convertir_a_hora(valor):
    """
    Convierte diferentes formatos a objeto datetime
    """
    try:
        if pd.isna(valor) or valor == '' or valor is None:
            return None
        
        # Si es string
        if isinstance(valor, str):
            # Limpiar el string
            valor = valor.strip()
            
            # Intentar diferentes formatos
            formatos = [
                '%H:%M:%S',
                '%H:%M',
                '%I:%M:%S %p',
                '%I:%M %p',
                '%H:%M:%S.%f',
                '%I:%M:%S.%f %p',
                '%H:%M:%S %p',
                '%I:%M:%S.%f',
                '%I:%M'
            ]
            
            for formato in formatos:
                try:
                    return datetime.strptime(valor, formato)
                except:
                    continue
            
            # Intentar extraer hora con regex
            match = re.search(r'(\d{1,2}):(\d{2})', valor)
            if match:
                hora = int(match.group(1))
                minuto = int(match.group(2))
                return datetime(2000, 1, 1, hora, minuto)
            
            return None
        
        # Si es datetime o Timestamp
        if isinstance(valor, (datetime, pd.Timestamp)):
            return valor
        
        # Si es time
        if hasattr(valor, 'hour') and hasattr(valor, 'minute'):
            return datetime(2000, 1, 1, valor.hour, valor.minute)
        
        # Si es timedelta
        if isinstance(valor, timedelta):
            total_seconds = valor.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return datetime(2000, 1, 1, hours, minutes)
        
        # Si es un número (posiblemente hora en formato Excel)
        if isinstance(valor, (int, float)):
            # Si es un número entre 0 y 1, es una fracción de día
            if 0 <= valor <= 1:
                total_seconds = valor * 86400  # 86400 segundos en un día
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return datetime(2000, 1, 1, hours, minutes)
        
        return None
    except Exception as e:
        print(f"Error al convertir hora: {valor}, Error: {e}")
        return None

def procesar_datos(df_cita, df_registro, df_usuarios):
    """
    Función que procesa los datos realizando todas las transformaciones necesarias
    """
    # Crear copias para no modificar los originales
    df_cita_proc = df_cita.copy()
    df_registro_proc = df_registro.copy()
    df_usuarios_proc = df_usuarios.copy()
    
    # 1. Cruzar datos de usuarios con las otras hojas
    usuario_rol_map = dict(zip(df_usuarios_proc['usuario registra'], df_usuarios_proc['rol']))
    
    # Agregar columna 'rol' a FECHA DE CITA
    df_cita_proc['rol'] = df_cita_proc['usuario registra'].map(usuario_rol_map)
    
    # Agregar columna 'rol' a FECHA DE REGISTRO
    df_registro_proc['rol'] = df_registro_proc['usuario registra'].map(usuario_rol_map)
    
    # 2. Calcular "hora ingreso a cita" (hora inicio cita - 30 minutos)
    def calcular_hora_ingreso(hora_valor):
        try:
            # Convertir a datetime
            hora_dt = convertir_a_hora(hora_valor)
            if hora_dt is None:
                return None
            
            # Restar 30 minutos
            nueva_hora = hora_dt - timedelta(minutes=30)
            return nueva_hora.strftime('%H:%M')
        except Exception as e:
            print(f"Error calculando hora ingreso: {e}")
            return None
    
    # Aplicar la función a la columna 'hora inicio cita'
    df_cita_proc['hora ingreso a cita'] = df_cita_proc['hora inicio cita'].apply(calcular_hora_ingreso)
    
    # 3. Calcular "hora entrega documentos" (hora final cita en formato HH:MM)
    def convertir_hora_entrega(hora_valor):
        try:
            # Convertir a datetime
            hora_dt = convertir_a_hora(hora_valor)
            if hora_dt is None:
                return None
            
            return hora_dt.strftime('%H:%M')
        except Exception as e:
            print(f"Error convirtiendo hora entrega: {e}")
            return None
    
    # Aplicar la función a la columna 'hora final cita'
    df_cita_proc['hora entrega documentos'] = df_cita_proc['hora final cita'].apply(convertir_hora_entrega)
    
    return df_cita_proc, df_registro_proc, df_usuarios_proc

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
            st.session_state.dfs_original = {
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
            
            # Mostrar información detallada de las columnas de hora
            with st.expander("🔍 Información de depuración - Columnas de hora", expanded=True):
                st.subheader("📊 Datos de muestra - 'hora inicio cita'")
                st.write("**Primeros 5 valores:**")
                st.write(df_cita['hora inicio cita'].head(10).tolist())
                
                st.write("**Tipo de datos de la columna:**", df_cita['hora inicio cita'].dtype)
                
                st.write("**Valores únicos (primeros 10):**")
                st.write(df_cita['hora inicio cita'].unique()[:10].tolist())
                
                st.subheader("📊 Datos de muestra - 'hora final cita'")
                st.write("**Primeros 5 valores:**")
                st.write(df_cita['hora final cita'].head(10).tolist())
                
                st.write("**Tipo de datos de la columna:**", df_cita['hora final cita'].dtype)
                
                st.write("**Valores únicos (primeros 10):**")
                st.write(df_cita['hora final cita'].unique()[:10].tolist())
                
                # Probar la conversión en algunos valores
                st.subheader("🧪 Prueba de conversión")
                test_values = df_cita['hora inicio cita'].head(5).tolist()
                test_results = []
                for val in test_values:
                    result = convertir_a_hora(val)
                    test_results.append({
                        'Original': val,
                        'Convertido': result.strftime('%H:%M') if result else 'None',
                        'Tipo': type(val)
                    })
                st.dataframe(pd.DataFrame(test_results))
            
            # Botón para procesar
            if st.button("🔄 Procesar", type="primary", use_container_width=True):
                with st.spinner("Procesando datos..."):
                    # Procesar los datos
                    df_cita_proc, df_registro_proc, df_usuarios_proc = procesar_datos(
                        df_cita, df_registro, df_usuarios
                    )
                    
                    # Guardar datos procesados
                    st.session_state.dfs_procesados = {
                        'FECHA DE CITA': df_cita_proc,
                        'FECHA DE REGISTRO': df_registro_proc,
                        'USUARIOS': df_usuarios_proc
                    }
                    st.session_state.process_clicked = True
                    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")

# Mostrar resumen SOLO si se ha presionado el botón "Procesar"
if st.session_state.process_clicked and st.session_state.data_loaded:
    if 'dfs_procesados' in st.session_state:
        st.divider()
        st.header("📊 Resumen de Datos Procesados")
        
        # Información de las transformaciones realizadas
        with st.expander("ℹ️ Transformaciones realizadas", expanded=False):
            st.markdown("""
            **Transformaciones aplicadas:**
            1. ✅ **Cruce con USUARIOS**: Se agregó la columna 'rol' a las hojas FECHA DE CITA y FECHA DE REGISTRO
            2. ✅ **Hora ingreso a cita**: Se calculó restando 30 minutos a 'hora inicio cita' (formato HH:MM)
            3. ✅ **Hora entrega documentos**: Se convirtió 'hora final cita' a formato HH:MM
            """)
        
        # Crear tabs para cada hoja
        tab1, tab2, tab3 = st.tabs(["📅 FECHA DE CITA", "📝 FECHA DE REGISTRO", "👥 USUARIOS"])
        
        with tab1:
            df = st.session_state.dfs_procesados['FECHA DE CITA']
            
            # Mostrar estadísticas de la hoja
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total registros", len(df))
            with col2:
                roles_asignados = df['rol'].notna().sum()
                st.metric("Roles asignados", f"{roles_asignados}/{len(df)}")
            with col3:
                horas_ingreso = df['hora ingreso a cita'].notna().sum()
                st.metric("Horas ingreso", f"{horas_ingreso}/{len(df)}")
            with col4:
                horas_entrega = df['hora entrega documentos'].notna().sum()
                st.metric("Horas entrega", f"{horas_entrega}/{len(df)}")
            
            st.subheader(f"Primeros 10 registros de FECHA DE CITA (Total: {len(df)})")
            
            # Mostrar columnas relevantes para esta hoja
            columnas_mostrar = ['centro de atencion', 'unidad funcional', 'identificación paciente', 
                              'nombre paciente', 'profesional', 'especialidad', 'fecha cita', 
                              'hora inicio cita', 'hora final cita', 'hora ingreso a cita', 
                              'hora entrega documentos', 'estado cita', 'usuario registra', 'rol']
            
            # Filtrar solo las columnas que existen
            columnas_existentes = [col for col in columnas_mostrar if col in df.columns]
            
            if len(df) > 0:
                st.dataframe(df[columnas_existentes].head(10), use_container_width=True)
                
                # Mostrar comparación de horas en formato más claro
                st.subheader("📊 Comparación de horas calculadas (primeros 10 registros)")
                comparacion_df = df[['hora inicio cita', 'hora ingreso a cita', 'hora final cita', 'hora entrega documentos']].head(10)
                st.dataframe(comparacion_df, use_container_width=True)
            else:
                st.info("La hoja está vacía")
        
        with tab2:
            df = st.session_state.dfs_procesados['FECHA DE REGISTRO']
            
            # Mostrar estadísticas de la hoja
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total registros", len(df))
            with col2:
                roles_asignados = df['rol'].notna().sum()
                st.metric("Roles asignados", f"{roles_asignados}/{len(df)}")
            
            st.subheader(f"Primeros 10 registros de FECHA DE REGISTRO (Total: {len(df)})")
            
            # Mostrar columnas relevantes para esta hoja
            columnas_mostrar = ['centro de atencion', 'unidad funcional', 'identificación paciente', 
                              'nombre paciente', 'profesional', 'especialidad', 'fecha cita', 
                              'hora inicio cita', 'hora final cita', 'estado cita', 
                              'usuario registra', 'rol']
            
            # Filtrar solo las columnas que existen
            columnas_existentes = [col for col in columnas_mostrar if col in df.columns]
            
            if len(df) > 0:
                st.dataframe(df[columnas_existentes].head(10), use_container_width=True)
            else:
                st.info("La hoja está vacía")
        
        with tab3:
            df = st.session_state.dfs_procesados['USUARIOS']
            st.subheader(f"Primeros 10 registros de USUARIOS (Total: {len(df)})")
            
            if len(df) > 0:
                st.dataframe(df.head(10), use_container_width=True)
            else:
                st.info("La hoja está vacía")
        
        # Opción para descargar el resumen procesado
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col2:
            # Crear archivo Excel con el resumen procesado
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, df in st.session_state.dfs_procesados.items():
                    df.head(10).to_excel(writer, sheet_name=sheet_name, index=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Descargar Resumen Procesado (Excel)",
                data=output,
                file_name="resumen_datos_procesados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Mensaje informativo cuando el archivo está cargado pero no se ha procesado
elif st.session_state.data_loaded and not st.session_state.process_clicked:
    st.info("📌 Haz clic en el botón 'Procesar' para aplicar las transformaciones y mostrar el resumen de los datos")
