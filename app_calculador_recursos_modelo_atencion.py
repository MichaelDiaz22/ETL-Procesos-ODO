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
            if valor > 40000:
                base_date = datetime(1899, 12, 30)
                fecha_excel = base_date + timedelta(days=valor)
                return fecha_excel
            elif 0 <= valor <= 1:
                total_seconds = valor * 86400
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return datetime(2000, 1, 1, hours, minutes)
        
        # Si es string
        if isinstance(valor, str):
            valor = valor.strip()
            
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
            
            match = re.search(r'(\d{1,2}):(\d{2})', valor)
            if match:
                hora = int(match.group(1))
                minuto = int(match.group(2))
                return datetime(2000, 1, 1, hora, minuto)
            
            return None
        
        if isinstance(valor, (datetime, pd.Timestamp)):
            return valor
        
        if hasattr(valor, 'hour') and hasattr(valor, 'minute'):
            return datetime(2000, 1, 1, valor.hour, valor.minute)
        
        if isinstance(valor, timedelta):
            total_seconds = valor.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return datetime(2000, 1, 1, hours, minutes)
        
        return None
    except Exception as e:
        return None

def extraer_hora_de_fecha(fecha_datetime):
    """
    Extrae solo la hora de un objeto datetime
    """
    if fecha_datetime is None:
        return None
    return datetime(2000, 1, 1, fecha_datetime.hour, fecha_datetime.minute)

def generar_tabla_horas():
    """
    Genera una tabla con las horas desde 06:30 hasta 19:00 cada 5 minutos
    """
    horas = []
    hora_actual = datetime(2000, 1, 1, 6, 30)
    hora_fin = datetime(2000, 1, 1, 19, 0)
    
    while hora_actual <= hora_fin:
        horas.append(hora_actual.strftime('%H:%M'))
        hora_actual += timedelta(minutes=5)
    
    return pd.DataFrame({'Hora': horas})

def procesar_datos(df_cita, df_registro, df_usuarios, unidades_seleccionadas):
    """
    Procesa los datos filtrando por unidades funcionales y estado cumplida
    """
    # Filtrar por unidades funcionales seleccionadas
    df_cita_filtrado = df_cita[df_cita['unidad funcional'].isin(unidades_seleccionadas)].copy()
    df_registro_filtrado = df_registro[df_registro['unidad funcional'].isin(unidades_seleccionadas)].copy()
    
    # Filtrar FECHA DE CITA por estado "Cumplida"
    df_cita_filtrado = df_cita_filtrado[df_cita_filtrado['estado cita'] == 'Cumplida'].copy()
    
    # Cruzar datos de usuarios
    usuario_rol_map = dict(zip(df_usuarios['usuario registra'], df_usuarios['rol']))
    df_cita_filtrado['rol'] = df_cita_filtrado['usuario registra'].map(usuario_rol_map)
    df_registro_filtrado['rol'] = df_registro_filtrado['usuario registra'].map(usuario_rol_map)
    
    # Calcular hora ingreso a cita (hora inicio cita - 30 minutos)
    def calcular_hora_ingreso(hora_valor):
        try:
            hora_dt = convertir_a_hora(hora_valor)
            if hora_dt is None:
                return None
            hora_solo = extraer_hora_de_fecha(hora_dt)
            if hora_solo is None:
                return None
            nueva_hora = hora_solo - timedelta(minutes=30)
            return nueva_hora.strftime('%H:%M')
        except Exception as e:
            return None
    
    df_cita_filtrado['hora ingreso a cita'] = df_cita_filtrado['hora inicio cita'].apply(calcular_hora_ingreso)
    
    # Calcular hora entrega documentos
    def convertir_hora_entrega(hora_valor):
        try:
            hora_dt = convertir_a_hora(hora_valor)
            if hora_dt is None:
                return None
            hora_solo = extraer_hora_de_fecha(hora_dt)
            if hora_solo is None:
                return None
            return hora_solo.strftime('%H:%M')
        except Exception as e:
            return None
    
    df_cita_filtrado['hora entrega documentos'] = df_cita_filtrado['hora final cita'].apply(convertir_hora_entrega)
    
    return df_cita_filtrado, df_registro_filtrado

def generar_tabla_resumen_con_conteo(df_cita_proc, df_registro_proc):
    """
    Genera la tabla de resumen con el conteo de "En cola de admisiones"
    """
    # Generar tabla base de horas
    df_resumen = generar_tabla_horas()
    
    # Contar registros de FECHA DE CITA por hora de ingreso
    if 'hora ingreso a cita' in df_cita_proc.columns:
        citas_validas = df_cita_proc['hora ingreso a cita'].dropna()
        conteo_citas = citas_validas.value_counts()
        df_resumen['En cola de admisiones'] = df_resumen['Hora'].map(conteo_citas).fillna(0).astype(int)
    else:
        df_resumen['En cola de admisiones'] = 0
    
    return df_resumen

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
            
            # Obtener unidades funcionales únicas de ambas hojas
            unidades_cita = set(df_cita['unidad funcional'].dropna().unique())
            unidades_registro = set(df_registro['unidad funcional'].dropna().unique())
            unidades_disponibles = sorted(list(unidades_cita.union(unidades_registro)))
            
            # Selector de unidades funcionales
            st.subheader("🏥 Selección de Unidades Funcionales")
            unidades_seleccionadas = st.multiselect(
                "Selecciona una o más unidades funcionales:",
                options=unidades_disponibles,
                help="Puedes seleccionar múltiples unidades funcionales"
            )
            
            # Mostrar cantidad de unidades seleccionadas
            if unidades_seleccionadas:
                st.info(f"✅ {len(unidades_seleccionadas)} unidad(es) funcional(es) seleccionada(s)")
            else:
                st.warning("⚠️ Por favor, selecciona al menos una unidad funcional")
            
            # Botón para procesar
            if st.button("🔄 Procesar", type="primary", use_container_width=True):
                if not unidades_seleccionadas:
                    st.error("❌ Debes seleccionar al menos una unidad funcional")
                else:
                    with st.spinner("Procesando datos..."):
                        # Procesar los datos con los filtros
                        df_cita_proc, df_registro_proc = procesar_datos(
                            df_cita, df_registro, df_usuarios, unidades_seleccionadas
                        )
                        
                        # Generar tabla de resumen con conteo
                        df_resumen = generar_tabla_resumen_con_conteo(df_cita_proc, df_registro_proc)
                        
                        # Guardar datos procesados
                        st.session_state.dfs_procesados = {
                            'RESUMEN': df_resumen,
                            'CITA_PROCESADA': df_cita_proc,
                            'REGISTRO_PROCESADO': df_registro_proc
                        }
                        st.session_state.process_clicked = True
                        st.session_state.unidades_seleccionadas = unidades_seleccionadas
                    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")

# Mostrar resumen SOLO si se ha presionado el botón "Procesar"
if st.session_state.process_clicked and st.session_state.data_loaded:
    if 'dfs_procesados' in st.session_state:
        st.divider()
        
        # Mostrar filtros aplicados
        st.subheader("🔍 Filtros Aplicados")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Unidades Funcionales:** {', '.join(st.session_state.unidades_seleccionadas)}")
        with col2:
            df_cita = st.session_state.dfs_procesados['CITA_PROCESADA']
            st.write(f"**Registros FECHA DE CITA (Cumplidas):** {len(df_cita)}")
        
        st.header("📊 Tabla de Resumen")
        st.write("Distribución de citas en cola de admisiones por hora")
        
        df = st.session_state.dfs_procesados['RESUMEN']
        
        # Mostrar estadísticas del resumen
        col1, col2, col3 = st.columns(3)
        with col1:
            total_citas = df['En cola de admisiones'].sum()
            st.metric("Total en Cola de Admisiones", f"{total_citas:,}")
        with col2:
            horas_con_actividad = len(df[df['En cola de admisiones'] > 0])
            st.metric("Horas con Actividad", f"{horas_con_actividad}")
        with col3:
            hora_max = df.loc[df['En cola de admisiones'].idxmax(), 'Hora'] if df['En cola de admisiones'].max() > 0 else "N/A"
            st.metric("Hora Pico", hora_max)
        
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
                df.to_excel(writer, sheet_name='RESUMEN', index=False)
                # También guardar los datos procesados
                st.session_state.dfs_procesados['CITA_PROCESADA'].to_excel(writer, sheet_name='CITAS_FILTRADAS', index=False)
                st.session_state.dfs_procesados['REGISTRO_PROCESADO'].to_excel(writer, sheet_name='REGISTROS_FILTRADOS', index=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Descargar Tabla Resumen (Excel)",
                data=output,
                file_name="tabla_resumen.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Mensaje informativo cuando el archivo está cargado pero no se ha procesado
elif st.session_state.data_loaded and not st.session_state.process_clicked:
    st.info("📌 Selecciona las unidades funcionales y haz clic en el botón 'Procesar' para generar la tabla de resumen")

# Si no hay archivo cargado
else:
    st.info("📂 Por favor, carga un archivo Excel para comenzar")
