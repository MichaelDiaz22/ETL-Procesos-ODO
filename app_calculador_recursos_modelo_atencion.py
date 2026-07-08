import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import re
import calendar

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

def redondear_hora_5_minutos(hora_str):
    """
    Redondea una hora al siguiente intervalo de 5 minutos
    """
    try:
        if pd.isna(hora_str) or hora_str is None:
            return None
        hora_dt = datetime.strptime(hora_str, '%H:%M')
        minutos = hora_dt.minute
        # Redondear hacia arriba al siguiente múltiplo de 5
        minutos_redondeados = ((minutos + 4) // 5) * 5
        if minutos_redondeados >= 60:
            hora_dt = hora_dt.replace(hour=hora_dt.hour + 1, minute=0)
        else:
            hora_dt = hora_dt.replace(minute=minutos_redondeados)
        return hora_dt.strftime('%H:%M')
    except:
        return hora_str

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

def contar_dias_mes(fecha):
    """
    Cuenta cuántos días del mismo día de la semana tiene el mes
    """
    try:
        dia_semana = fecha.weekday()
        mes = fecha.month
        año = fecha.year
        
        # Contar cuántos días del mismo día de la semana hay en el mes
        count = 0
        for dia in range(1, calendar.monthrange(año, mes)[1] + 1):
            fecha_temp = datetime(año, mes, dia)
            if fecha_temp.weekday() == dia_semana:
                count += 1
        return count
    except:
        return 1

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
    
    # Redondear hora ingreso a cita al siguiente intervalo de 5 minutos
    df_cita_filtrado['hora ingreso redondeada'] = df_cita_filtrado['hora ingreso a cita'].apply(redondear_hora_5_minutos)
    
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
    
    # Convertir fecha cita a datetime
    df_cita_filtrado['fecha_cita_dt'] = pd.to_datetime(df_cita_filtrado['fecha cita'], errors='coerce')
    
    # Eliminar registros con fecha inválida
    df_cita_filtrado = df_cita_filtrado.dropna(subset=['fecha_cita_dt'])
    
    # Agregar información de fecha
    df_cita_filtrado['dia_semana'] = df_cita_filtrado['fecha_cita_dt'].dt.weekday
    df_cita_filtrado['mes'] = df_cita_filtrado['fecha_cita_dt'].dt.month
    df_cita_filtrado['año'] = df_cita_filtrado['fecha_cita_dt'].dt.year
    
    return df_cita_filtrado, df_registro_filtrado

def generar_tablas_resumen(df_cita_proc, unidades_seleccionadas):
    """
    Genera las tablas de resumen por día de la semana
    """
    # Nombres de los días de la semana
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    # Generar tabla base de horas
    df_base = generar_tabla_horas()
    
    # Diccionario para almacenar las tablas
    tablas = {}
    
    # Procesar por cada día de la semana
    for dia_idx, dia_nombre in enumerate(dias_semana):
        # Filtrar por día de la semana
        df_dia = df_cita_proc[df_cita_proc['dia_semana'] == dia_idx].copy()
        
        if len(df_dia) == 0:
            # Si no hay datos para este día, crear tabla vacía
            df_resultado = df_base.copy()
            for unidad in unidades_seleccionadas:
                df_resultado[f'En cola de admisiones {unidad}'] = 0
            tablas[dia_nombre] = df_resultado
            continue
        
        # Crear tabla de resumen para este día
        df_resultado = df_base.copy()
        
        # Para cada unidad funcional
        for unidad in unidades_seleccionadas:
            # Filtrar por unidad
            df_unidad = df_dia[df_dia['unidad funcional'] == unidad].copy()
            
            if len(df_unidad) == 0:
                df_resultado[f'En cola de admisiones {unidad}'] = 0
                continue
            
            # Agrupar por fecha, profesional y centro para obtener conteos únicos
            df_agrupado = df_unidad.groupby(['fecha_cita_dt', 'profesional', 'centro de atencion', 'hora ingreso redondeada']).size().reset_index(name='conteo')
            
            # Calcular días del mismo día de la semana en el mes para cada fecha
            df_agrupado['dias_mes'] = df_agrupado['fecha_cita_dt'].apply(contar_dias_mes)
            
            # Calcular el valor ajustado (conteo / días_mes)
            df_agrupado['valor_ajustado'] = df_agrupado['conteo'] / df_agrupado['dias_mes']
            
            # Agrupar por hora redondeada sumando los valores ajustados
            df_horas = df_agrupado.groupby('hora ingreso redondeada')['valor_ajustado'].sum().reset_index()
            
            # Mapear los valores a las horas
            df_resultado[f'En cola de admisiones {unidad}'] = df_resultado['Hora'].map(
                dict(zip(df_horas['hora ingreso redondeada'], df_horas['valor_ajustado']))
            ).fillna(0)
        
        tablas[dia_nombre] = df_resultado
    
    return tablas

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
                        
                        # Generar tablas de resumen (solo lunes a viernes)
                        tablas_resumen = generar_tablas_resumen(df_cita_proc, unidades_seleccionadas)
                        
                        # Guardar datos procesados
                        st.session_state.dfs_procesados = {
                            'TABLAS': tablas_resumen,
                            'CITA_PROCESADA': df_cita_proc,
                            'REGISTRO_PROCESADO': df_registro_proc
                        }
                        st.session_state.process_clicked = True
                        st.session_state.unidades_seleccionadas = unidades_seleccionadas
                    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")
        st.exception(e)

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
        
        st.header("📊 Tablas de Resumen por Día")
        
        tablas = st.session_state.dfs_procesados['TABLAS']
        
        # Crear pestañas solo para lunes a viernes (sin promedio)
        nombres_tabs = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
        tabs = st.tabs(nombres_tabs)
        
        for i, tab in enumerate(tabs):
            with tab:
                nombre_tab = nombres_tabs[i]
                df = tablas[nombre_tab]
                
                st.subheader(f"📊 {nombre_tab}")
                
                # Mostrar estadísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    # Sumar todas las columnas de unidades
                    total = 0
                    for col in df.columns:
                        if col != 'Hora':
                            total += df[col].sum()
                    st.metric("Total", f"{total:.1f}")
                with col2:
                    # Contar horas con actividad en cualquier unidad
                    horas_con_actividad = 0
                    for idx, row in df.iterrows():
                        tiene_actividad = False
                        for col in df.columns:
                            if col != 'Hora' and row[col] > 0:
                                tiene_actividad = True
                                break
                        if tiene_actividad:
                            horas_con_actividad += 1
                    st.metric("Horas con Actividad", f"{horas_con_actividad}")
                with col3:
                    # Hora pico (sumando todas las unidades)
                    df['total'] = df[[col for col in df.columns if col != 'Hora']].sum(axis=1)
                    hora_max = df.loc[df['total'].idxmax(), 'Hora'] if df['total'].max() > 0 else "N/A"
                    st.metric("Hora Pico", hora_max)
                    # Eliminar columna temporal
                    df = df.drop('total', axis=1)
                
                # Mostrar el DataFrame
                st.dataframe(df, use_container_width=True, height=600)
        
        # Opción para descargar todas las tablas
        st.divider()
        st.subheader("📥 Descargar Tablas de Resumen")
        col1, col2, col3 = st.columns(3)
        with col2:
            # Crear archivo Excel con todas las tablas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for nombre, df in tablas.items():
                    df.to_excel(writer, sheet_name=nombre, index=False)
                # También guardar los datos procesados
                st.session_state.dfs_procesados['CITA_PROCESADA'].to_excel(writer, sheet_name='CITAS_FILTRADAS', index=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Descargar Tablas Resumen (Excel)",
                data=output,
                file_name="tablas_resumen.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Mensaje informativo cuando el archivo está cargado pero no se ha procesado
elif st.session_state.data_loaded and not st.session_state.process_clicked:
    st.info("📌 Selecciona las unidades funcionales y haz clic en el botón 'Procesar' para generar las tablas de resumen")

# Si no hay archivo cargado
else:
    st.info("📂 Por favor, carga un archivo Excel para comenzar")
