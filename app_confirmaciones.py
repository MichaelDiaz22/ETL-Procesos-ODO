import streamlit as st
import pandas as pd
import openpyxl
import io
import xlsxwriter
from datetime import datetime
import datetime as dt
import numpy as np

st.set_page_config(page_title="Excel Data Filtering App", layout="wide")

st.title("Excel Data Filtering and Export App")

# Inicializar estado mínimo
if 'data' not in st.session_state:
    st.session_state.data = None
if 'processed' not in st.session_state:
    st.session_state.processed = False

def process_data(df):
    """Procesa el DataFrame con toda la lógica de negocio"""
    df = df.sort_values(by='Numero de Identificación', ascending=True).reset_index(drop=True)
    
    # Crear columna 'Ubicación'
    df['Actividad Médica_clean'] = df['Actividad Médica'].fillna('').astype(str).str.strip().str.lower()
    df['Ubicación'] = df['Actividad Médica_clean'].apply(
        lambda x: 'Consulta' if x.startswith('consulta') else 'Procedimiento'
    )
    df = df.drop(columns=['Actividad Médica_clean'])
    
    # Convertir fechas
    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y']
    time_formats = ['%H:%M:%S', '%H:%M', '%I:%M %p']
    
    def parse_datetime_robust(date_str, time_str):
        date_str = str(date_str) if not pd.isna(date_str) else ''
        time_str = str(time_str) if not pd.isna(time_str) else ''
        for d_fmt in date_formats:
            for t_fmt in time_formats:
                try:
                    datetime_str = f"{date_str} {time_str}"
                    return pd.to_datetime(datetime_str, format=f"{d_fmt} {t_fmt}")
                except (ValueError, TypeError):
                    continue
        return pd.NaT
    
    df['Fecha Hora Cita'] = df.apply(lambda row: parse_datetime_robust(row['Fecha Cita'], row['Hora Cita']), axis=1)
    
    # Parse fechas en español
    def parse_spanish_date(date_str):
        if pd.isna(date_str) or str(date_str).strip() == '':
            return pd.NaT
        date_str = str(date_str).strip().lower()
        months_map = {
            'enero': 'January', 'febrero': 'February', 'marzo': 'March', 'abril': 'April',
            'mayo': 'May', 'junio': 'June', 'julio': 'July', 'agosto': 'August',
            'septiembre': 'September', 'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
        }
        days_map = {
            'lunes': 'Monday', 'martes': 'Tuesday', 'miércoles': 'Wednesday', 'miercoles': 'Wednesday',
            'jueves': 'Thursday', 'viernes': 'Friday', 'sábado': 'Saturday', 'sabado': 'Saturday',
            'domingo': 'Sunday'
        }
        try:
            for day_es, day_en in days_map.items():
                if date_str.startswith(day_es):
                    date_str = date_str.replace(day_es, '').replace(',', '').strip()
                    break
            for month_es, month_en in months_map.items():
                if month_es in date_str:
                    date_str = date_str.replace(month_es, month_en)
                    break
            return pd.to_datetime(date_str, format='%d de %B de %Y')
        except Exception:
            return pd.NaT
    
    df['Fecha Programación_dt'] = df['Fecha Programación'].apply(parse_spanish_date)
    if df['Fecha Programación_dt'].isna().all():
        df['Fecha Programación_dt'] = df['Fecha Cita'].apply(parse_spanish_date)
    
    # Formato de fecha en español
    def formato_fecha_espanol(fecha_dt):
        if pd.isna(fecha_dt):
            return ""
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        dia_semana = dias_semana[fecha_dt.weekday()]
        dia = fecha_dt.day
        mes = meses[fecha_dt.month - 1]
        año = fecha_dt.year
        return f"{dia_semana}, {dia} de {mes} de {año}"
    
    df['Fecha Programación Formateada'] = df['Fecha Programación_dt'].apply(formato_fecha_espanol)
    
    # Convertir hora decimal a formato 12 horas
    def convert_decimal_to_time(decimal_time):
        try:
            if pd.isna(decimal_time) or str(decimal_time).strip() in ['', 'nan', 'NaT']:
                return ''
            if isinstance(decimal_time, str) and (':' in decimal_time or 'AM' in decimal_time.upper() or 'PM' in decimal_time.upper()):
                return decimal_time
            decimal_val = float(decimal_time)
            total_minutes = int(decimal_val * 24 * 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            time_obj = dt.time(hours, minutes)
            return time_obj.strftime('%I:%M %p').lstrip('0')
        except (ValueError, TypeError):
            return str(decimal_time)
    
    df['Hora Cita Formatted'] = df['Hora Cita'].apply(convert_decimal_to_time)
    
    if 'Unidad Funcional' in df.columns:
        investigacion_mask = df['Unidad Funcional'] == 'INVESTIGACION MARAYA'
        df.loc[investigacion_mask, 'Hora Cita Formatted'] = '-'
    
    # Direcciones
    direcciones_sede = pd.DataFrame({
        'Sede': [
            'SAN MARCEL MANIZALES', 'CENTENARIO ARMENIA', 'MEDISALUD',
            'CLINICA DE ALTA TECNOLOGIA MARAYA PEREIRA', 'CIRCUNVALAR PEREIRA',
            'CARTAGO UNIDAD ONCOLOGICA CARTAGO', 'CLINICA DE ALTA TECNOLOGIA SEDE ARMENIA ARMENIA',
            'ONCOLOGOS SEDE LA DORADA LA DORADA', 'UDC CLINICA DE ALTA TECNOLOGIA ARMENIA ARMENIA',
            'UDC CLINICA MARAYA PEREIRA', 'UDC CLINICA AVIDANTI MANIZALES',
            'UDC CLINICA LA PRESENTACION MANIZALES', 'UDC SAN MARCEL MANIZALES'
        ],
        'Dirección': [
            'Calle 92 N°  29-75,  SAN MARCEL -  MANIZALES',
            'Carrera 6 A N°  2-63, AVENIDA CENTENARIO -  ARMENIA',
            'Carrera 12 N°  0 NORTE-20, EDIFICIO MEDISALUD 6 PISO -  ARMENIA',
            'Calle 50 N° 13-10, MARAYA - PEREIRA',
            'Carrera 13 N° 1- 46, LA REBECA - PEREIRA',
            'Carrera 2 NORTE N° 23 - 12, BARRIO MILAN - CARTAGO',
            'Calle 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
            'Carrera 4 N° 11-41 CENTRO - LA DORADA',
            'Carrera 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
            'Calle 50 N° 13-10, MARAYA - PEREIRA',
            'Calle 10 N° 2C-10B, CLÍNICA AVIDANTI -  MANIZALES',
            'Carrera 23 N° 46 Esquina, CLÍNICA LA PRESENTACIÓN - MANIZALES',
            'Calle 92 N°  29-75,  SAN MARCEL -  MANIZALES'
        ]
    })
    
    df = pd.merge(df, direcciones_sede, on='Sede', how='left')
    
    if 'Dirección' in df.columns:
        df['Direccion Final'] = df['Dirección']
    else:
        if 'Dirección Centro Atención' in df.columns:
            df['Direccion Final'] = df['Dirección Centro Atención']
        else:
            df['Direccion Final'] = ''
    
    if 'Modalidad' in df.columns:
        df.loc[df['Modalidad'] == 'Teleconsulta', 'Direccion Final'] = 'Teleconsulta'
    
    # Columnas como strings
    df['Nombres'] = df['Nombres'].astype(str)
    df['Apellidos'] = df['Apellidos'].astype(str)
    df['Actividad Médica'] = df['Actividad Médica'].astype(str)
    df['Especialista'] = df['Especialista'].astype(str)
    df['Direccion Final'] = df['Direccion Final'].astype(str)
    df['Ubicación'] = df['Ubicación'].astype(str)
    
    if 'Unidad Funcional' in df.columns:
        df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)
    
    # Crear columna VARIABLE
    df['VARIABLE'] = df.apply(
        lambda row: f"{row['Nombres']} {row['Apellidos']}|{row['Actividad Médica']}|{row['Fecha Programación Formateada']}|{row['Hora Cita Formatted']}|{row['Especialista']}|{row['Direccion Final']}",
        axis=1
    )
    
    # Teléfonos
    df['Telefono Movil'] = df['Telefono Movil'].astype(str).str.strip()
    df['Telefono Fijo'] = df['Telefono Fijo'].astype(str).str.strip()
    
    df['TELEFONO CONFIRMACIÓN'] = 'sin número para enviar mensaje'
    
    movil_is_empty = (df['Telefono Movil'].isna()) | (df['Telefono Movil'] == '') | (df['Telefono Movil'] == 'nan')
    fijo_is_valid_fallback = (~df['Telefono Fijo'].isna()) & (df['Telefono Fijo'] != '') & (df['Telefono Fijo'] != 'nan') & (~df['Telefono Fijo'].str.startswith('60', na=False))
    
    df.loc[movil_is_empty & fijo_is_valid_fallback, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_empty & fijo_is_valid_fallback, 'Telefono Fijo']
    
    movil_is_valid_and_starts_with_3 = (~movil_is_empty) & (~df['Telefono Movil'].str.startswith('60', na=False)) & (df['Telefono Movil'].str.startswith('3', na=False))
    
    df.loc[movil_is_valid_and_starts_with_3, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_valid_and_starts_with_3, 'Telefono Movil']
    
    df['TELEFONO CONFIRMACIÓN'] = df['TELEFONO CONFIRMACIÓN'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    return df

def hora_a_decimal(hora_str):
    if pd.isna(hora_str) or hora_str == '' or hora_str == 'nan':
        return 999999
    hora_str = str(hora_str).strip()
    try:
        return float(hora_str)
    except:
        pass
    try:
        hora_lower = hora_str.lower()
        es_pm = 'pm' in hora_lower
        hora_limpia = hora_str.replace('AM', '').replace('PM', '').replace('am', '').replace('pm', '').strip()
        if ':' in hora_limpia:
            partes = hora_limpia.split(':')
            horas = int(partes[0])
            minutos = int(partes[1]) if len(partes) > 1 else 0
        else:
            horas = int(hora_limpia)
            minutos = 0
        if es_pm and horas != 12:
            horas += 12
        elif not es_pm and horas == 12:
            horas = 0
        return horas + minutos / 60.0
    except:
        return 999999

def identificar_primer_servicio(df_filtrado):
    if len(df_filtrado) == 0:
        return df_filtrado
    df_temp = df_filtrado.copy()
    required_cols = ['Numero de Identificación', 'Fecha Programación_dt', 'Sede', 'Hora Cita']
    for col in required_cols:
        if col not in df_temp.columns:
            st.warning(f"⚠️ No se encontró la columna requerida: {col}")
            return df_temp
    df_temp['Fecha_Solo'] = df_temp['Fecha Programación_dt'].dt.date
    df_temp['Hora_para_orden'] = df_temp['Hora Cita'].apply(hora_a_decimal)
    df_temp = df_temp.sort_values([
        'Numero de Identificación', 
        'Sede', 
        'Fecha_Solo',
        'Hora_para_orden'
    ])
    mascara_fecha_valida = df_temp['Fecha_Solo'].notna()
    df_temp['clave_duplicado'] = None
    df_temp.loc[mascara_fecha_valida, 'clave_duplicado'] = (
        df_temp.loc[mascara_fecha_valida, 'Numero de Identificación'].astype(str) + '|' + 
        df_temp.loc[mascara_fecha_valida, 'Sede'].astype(str) + '|' + 
        df_temp.loc[mascara_fecha_valida, 'Fecha_Solo'].astype(str)
    )
    df_temp.loc[~mascara_fecha_valida, 'clave_duplicado'] = df_temp.loc[~mascara_fecha_valida].index.astype(str) + '_sin_fecha'
    df_final = df_temp.drop_duplicates(subset=['clave_duplicado'], keep='first')
    df_final = df_final.drop(columns=['clave_duplicado', 'Fecha_Solo', 'Hora_para_orden'])
    return df_final

# Uploader de archivos
uploaded_file = st.file_uploader("Upload your Excel file", type=".xlsx")

if uploaded_file is not None:
    if not st.session_state.processed:
        with st.spinner("Procesando archivo..."):
            df = pd.read_excel(uploaded_file)
            st.info(f"📊 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
            st.session_state.data = process_data(df)
            st.session_state.processed = True
            st.success("✅ Archivo procesado correctamente!")

# Mostrar la interfaz solo si hay datos procesados
if st.session_state.processed and st.session_state.data is not None:
    df = st.session_state.data
    
    # Obtener valores para filtros
    all_empresas = df['EMPRESA'].unique().tolist()
    all_ubicaciones = df['Ubicación'].unique().tolist()
    min_date = df['Fecha Programación_dt'].min()
    max_date = df['Fecha Programación_dt'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        st.info(f"📅 Rango de fechas en los datos: {min_date.date()} a {max_date.date()}")
    
    # Filtros - TODOS con keys fijas
    st.subheader("📋 Configuración de Filtros")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_empresas = st.multiselect(
            "Select Empresa(s)", 
            options=all_empresas,
            default=all_empresas
        )
    
    with col2:
        selected_ubicaciones = st.multiselect(
            "Select Ubicación(s)", 
            options=all_ubicaciones,
            default=all_ubicaciones
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        start_date = st.date_input(
            "Start Date",
            value=min_date.date() if pd.notna(min_date) else datetime.now().date()
        )
    
    with col4:
        end_date = st.date_input(
            "End Date",
            value=max_date.date() if pd.notna(max_date) else datetime.now().date()
        )
    
    num_files = st.selectbox(
        "Number of files to generate",
        options=list(range(1, 6)),
        index=0
    )
    
    # Botón de generación
    if st.button("🚀 Generate Files", use_container_width=True):
        # Usar un contenedor para los resultados
        results_container = st.container()
        
        with results_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            files_generated = []
            
            for i in range(num_files):
                status_text.text(f"Procesando archivo {i+1} de {num_files}...")
                
                filtered_df = df.copy()
                mask = pd.Series(True, index=filtered_df.index)
                
                if selected_empresas:
                    mask = mask & filtered_df['EMPRESA'].isin(selected_empresas)
                
                if selected_ubicaciones:
                    mask = mask & filtered_df['Ubicación'].isin(selected_ubicaciones)
                
                start_date_ts = pd.Timestamp(start_date)
                end_date_ts = pd.Timestamp(end_date)
                mask = mask & (filtered_df['Fecha Programación_dt'] >= start_date_ts) & (filtered_df['Fecha Programación_dt'] <= end_date_ts)
                
                filtered_df = filtered_df.loc[mask].copy()
                filtered_df = identificar_primer_servicio(filtered_df)
                
                if 'Fecha Programación_dt' in filtered_df.columns:
                    filtered_df = filtered_df.drop(columns=['Fecha Programación_dt'])
                
                if len(filtered_df) > 0:
                    buffer = io.BytesIO()
                    
                    base_confirmacion_cols = ['TELEFONO CONFIRMACIÓN', 'VARIABLE']
                    pacientes_cols = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 
                                    'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 
                                    'Fecha Programación Formateada', 'Hora Cita Formatted', 'Actividad Médica']
                    
                    if 'Nombre completo' not in filtered_df.columns:
                        filtered_df['Nombre completo'] = filtered_df['Nombres'].astype(str) + ' ' + filtered_df['Apellidos'].astype(str)
                    
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        base_confirmacion_cols_existing = [col for col in base_confirmacion_cols if col in filtered_df.columns]
                        if base_confirmacion_cols_existing:
                            base_confirmacion_df = filtered_df[base_confirmacion_cols_existing]
                            base_confirmacion_df.to_excel(writer, sheet_name='Base confirmación', index=False)
                        
                        pacientes_cols_existing = [col for col in pacientes_cols if col in filtered_df.columns]
                        if pacientes_cols_existing:
                            pacientes_df = filtered_df[pacientes_cols_existing].copy()
                            if 'Hora Cita Formatted' in pacientes_df.columns:
                                pacientes_df = pacientes_df.rename(columns={'Hora Cita Formatted': 'Hora Cita'})
                            if 'Fecha Programación Formateada' in pacientes_df.columns:
                                pacientes_df = pacientes_df.rename(columns={'Fecha Programación Formateada': 'Fecha Programación'})
                            pacientes_df.to_excel(writer, sheet_name='Pacientes', index=False)
                    
                    empresas_str = "_".join(selected_empresas) if selected_empresas else "All"
                    ubicaciones_str = "_".join(selected_ubicaciones) if selected_ubicaciones else "All"
                    
                    filename = f"{empresas_str}_{ubicaciones_str}_{start_date.day}_{end_date.day}_{start_date.strftime('%B')}_{start_date.year}_part{i+1}.xlsx"
                    
                    files_generated.append({
                        'data': buffer.getvalue(),
                        'filename': filename,
                        'rows': len(filtered_df)
                    })
                    
                    buffer.close()
                
                progress_bar.progress((i + 1) / num_files)
            
            status_text.text("✅ Procesamiento completado!")
            
            # Mostrar resultados
            if files_generated:
                st.subheader("📥 Archivos Generados")
                
                for idx, file_info in enumerate(files_generated):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.success(f"✅ Archivo {idx+1}: {file_info['rows']} filas")
                    with col2:
                        st.download_button(
                            label=f"📥 Descargar",
                            data=file_info['data'],
                            file_name=file_info['filename'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheet.sheet",
                            key=f"download_{idx}"
                        )
            else:
                st.warning("⚠️ No se generaron archivos con los filtros seleccionados")
