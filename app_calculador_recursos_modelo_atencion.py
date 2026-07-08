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
        
        # Si es un número (formato Excel)
        if isinstance(valor, (int, float)):
            # Si el número es mayor a 40000, es una fecha completa de Excel
            if valor > 40000:
                # Convertir número de Excel a datetime
                # Excel usa el 1/1/1900 como base (con un bug para 1900)
                base_date = datetime(1899, 12, 30)
                fecha_excel = base_date + timedelta(days=valor)
                return fecha_excel
            # Si es un número entre 0 y 1, es solo una hora
            elif 0 <= valor <= 1:
                total_seconds = valor * 86400  # 86400 segundos en un día
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return datetime(2000, 1, 1, hours, minutes)
        
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
        
        return None
    except Exception as e:
        print(f"Error al convertir hora: {valor}, Error: {e}")
        return None

def extraer_hora_de_fecha(fecha_datetime):
    """
    Extrae solo la hora de un objeto datetime
    """
    if fecha_datetime is None:
        return None
    return datetime(2000, 1, 1, fecha_datetime.hour, fecha_datetime.minute)

def generar_tabla_resumen(df_cita, df_registro):
    """
    Genera una tabla de resumen con las horas desde 06:30 hasta 19:00 cada 5 minutos
    """
    # Crear el rango de horas
    horas = []
    hora_actual = datetime(2000, 1, 1, 6, 30)  # 06:30
    hora_fin = datetime(2000, 1, 1, 19, 0)     # 19:00
    
    while hora_actual <= hora_fin:
        horas.append(hora_actual.strftime('%H:%M'))
        hora_actual += timedelta(minutes=5)
    
    # Crear DataFrame de resumen
    resumen_df = pd.DataFrame({'Hora': horas})
    
    # Procesar FECHA DE CITA
    def contar_citas_por_hora(hora_str):
        try:
            hora_dt = datetime.strptime(hora_str, '%H:%M')
            # Buscar citas que coincidan con esta hora
            count = 0
            for idx, row in df_cita.iterrows():
                if pd.isna(row['hora ingreso a cita']):
                    continue
                # Convertir hora ingreso a datetime
                hora_ingreso = datetime.strptime(row['hora ingreso a cita'], '%H:%M')
                # Verificar si la hora de ingreso coincide con la hora actual
                if hora_ingreso.hour == hora_dt.hour and hora_ingreso.minute == hora_dt.minute:
                    count += 1
            return count
        except:
            return 0
    
    # Aplicar el conteo para cada hora
    resumen_df['Citas Programadas'] = resumen_df['Hora'].apply(contar_citas_por_hora)
    
    # Procesar FECHA DE REGISTRO
    def contar_registros_por_hora(hora_str):
        try:
            hora_dt = datetime.strptime(hora_str, '%H:%M')
            # Buscar registros que coincidan con esta hora
            count = 0
            for idx, row in df_registro.iterrows():
                # Convertir hora inicio cita a datetime
                hora_inicio = convertir_a_hora(row['hora inicio cita'])
                if hora_inicio is None:
                    continue
                hora_inicio_solo = extraer_hora_de_fecha(hora_inicio)
                if hora_inicio_solo is None:
                    continue
                # Verificar si la hora de inicio coincide con la hora actual
                if hora_inicio_solo.hour == hora_dt.hour and hora_inicio_solo.minute == hora_dt.minute:
                    count += 1
            return count
        except:
            return 0
    
    # Aplicar el conteo para cada hora
    resumen_df['Registros'] = resumen_df['Hora'].apply(contar_registros_por_hora)
    
    return resumen_df

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
            
            # Extraer solo la hora si es una fecha completa
            hora_solo = extraer_hora_de_fecha(hora_dt)
            
            # Restar 30 minutos
            nueva_hora = hora_solo - timedelta(minutes=30)
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
            
            # Extraer solo la hora si es una fecha completa
            hora_solo = extraer_hora_de_fecha(hora_dt)
            
            return hora_solo.strftime('%H:%M')
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
            
            # Botón para procesar
            if st.button("🔄 Procesar", type="primary", use_container_width=True):
                with st.spinner("Procesando datos..."):
                    # Procesar los datos
                    df_cita_proc, df_registro_proc, df_usuarios_proc = procesar_datos(
                        df_cita, df_registro, df_usuarios
                    )
                    
                    # Generar tabla de resumen
                    df_resumen = generar_tabla_resumen(df_cita_proc, df_registro_proc)
                    
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
        st.header("📊 Tabla de Resumen de Citas y Registros")
        st.write("Distribución de citas programadas y registros por hora (desde 06:30 hasta 19:00 cada 5 minutos)")
        
        df = st.session_state.dfs_procesados['RESUMEN']
        
        # Mostrar estadísticas del resumen
        col1, col2, col3 = st.columns(3)
        with col1:
            total_citas = df['Citas Programadas'].sum()
            st.metric("Total Citas Programadas", f"{total_citas:,}")
        with col2:
            total_registros = df['Registros'].sum()
            st.metric("Total Registros", f"{total_registros:,}")
        with col3:
            horas_con_datos = len(df[(df['Citas Programadas'] > 0) | (df['Registros'] > 0)])
            st.metric("Horas con Actividad", f"{horas_con_datos}")
        
        # Mostrar el DataFrame completo
        st.dataframe(df, use_container_width=True, height=600)
        
        # Opción para descargar la tabla de resumen
        st.divider()
        st.subheader("📥 Descargar Tabla de Resumen")
        col1, col2, col3 = st.columns(3)
        with col2:
            # Crear archivo Excel con la tabla de resumen
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='TABLA RESUMEN', index=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Descargar Tabla Resumen (Excel)",
                data=output,
                file_name="tabla_resumen_horas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Mensaje informativo cuando el archivo está cargado pero no se ha procesado
elif st.session_state.data_loaded and not st.session_state.process_clicked:
    st.info("📌 Haz clic en el botón 'Procesar' para generar la tabla de resumen")
