# Verify Python code clean structure
import streamlit as st
import pandas as pd
import openpyxl
import io
import xlsxwriter
from datetime import datetime
import datetime as dt
import numpy as np

st.set_page_config(page_title="Excel Data Filtering", layout="wide")

st.title("Excel Data Filtering and Export App")

uploaded_file = st.file_uploader("Upload your Excel file", type=".xlsx")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # Load the data into a pandas DataFrame
    df = pd.read_excel(uploaded_file)
    
    st.info(f"📊 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")

    # Preprocessing steps

    # Sort the DataFrame by 'Numero de Identificación' in ascending order
    if 'Numero de Identificación' in df.columns:
        df = df.sort_values(by='Numero de Identificación', ascending=True).reset_index(drop=True)

    # NUEVA LÓGICA MEJORADA: Crear columna 'Ubicación' basada en 'Actividad Médica'
    if 'Actividad Médica' in df.columns:
        df['Actividad Médica_clean'] = df['Actividad Médica'].fillna('').astype(str).str.strip().str.lower()
        df['Ubicación'] = df['Actividad Médica_clean'].apply(
            lambda x: 'Consulta' if x.startswith('consulta') else 'Procedimiento'
        )
        df = df.drop(columns=['Actividad Médica_clean'])
    else:
        df['Ubicación'] = 'Desconocido'

    # Convert 'Fecha Cita' and 'Hora Cita' to datetime objects
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

    if 'Fecha Cita' in df.columns and 'Hora Cita' in df.columns:
        df['Fecha Hora Cita'] = df.apply(lambda row: parse_datetime_robust(row['Fecha Cita'], row['Hora Cita']), axis=1)

    # CORRECCIÓN: Conversión robusta de fechas sin mostrar diagnóstico
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

    if 'Fecha Programación' in df.columns:
        df['Fecha Programación_dt'] = df['Fecha Programación'].apply(parse_spanish_date)
    else:
        df['Fecha Programación_dt'] = pd.NaT

    if df['Fecha Programación_dt'].isna().all() and 'Fecha Cita' in df.columns:
        df['Fecha Programación_dt'] = df['Fecha Cita'].apply(parse_spanish_date)

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

    if 'Hora Cita' in df.columns:
        df['Hora Cita Formatted'] = df['Hora Cita'].apply(convert_decimal_to_time)
    else:
        df['Hora Cita Formatted'] = ''

    if 'Unidad Funcional' in df.columns:
        investigacion_mask = df['Unidad Funcional'] == 'INVESTIGACION MARAYA'
        df.loc[investigacion_mask, 'Hora Cita Formatted'] = '-'

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

    if 'Sede' in df.columns:
        df = pd.merge(df, direcciones_sede, on='Sede', how='left')

    if 'Dirección' in df.columns:
        df['Direccion Final'] = df['Dirección']
    elif 'Dirección Centro Atención' in df.columns:
        df['Direccion Final'] = df['Dirección Centro Atención']
    else:
        df['Direccion Final'] = ''

    if 'Modalidad' in df.columns:
        df.loc[df['Modalidad'] == 'Teleconsulta', 'Direccion Final'] = 'Teleconsulta'

    for col in ['Nombres', 'Apellidos', 'Actividad Médica', 'Especialista', 'Direccion Final', 'Ubicación']:
        if col in df.columns:
            df[col] = df[col].astype(str)
        else:
            df[col] = ''

    if 'Unidad Funcional' in df.columns:
        df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)

    df['VARIABLE'] = df.apply(
        lambda row: f"{row.get('Nombres','') } {row.get('Apellidos','')}|{row.get('Actividad Médica','')}|{row.get('Fecha Programación Formateada','')}|{row.get('Hora Cita Formatted','')}|{row.get('Especialista','')}|{row.get('Direccion Final','')}",
        axis=1
    )

    if 'Telefono Movil' in df.columns:
        df['Telefono Movil'] = df['Telefono Movil'].astype(str).str.strip()
    else:
        df['Telefono Movil'] = ''

    if 'Telefono Fijo' in df.columns:
        df['Telefono Fijo'] = df['Telefono Fijo'].astype(str).str.strip()
    else:
        df['Telefono Fijo'] = ''

    df['TELEFONO CONFIRMACIÓN'] = 'sin número para enviar mensaje'

    movil_is_empty = (df['Telefono Movil'].isna()) | (df['Telefono Movil'] == '') | (df['Telefono Movil'] == 'nan')
    fijo_is_valid_fallback = (~df['Telefono Fijo'].isna()) & (df['Telefono Fijo'] != '') & (df['Telefono Fijo'] != 'nan') & (~df['Telefono Fijo'].str.startswith('60', na=False))

    df.loc[movil_is_empty & fijo_is_valid_fallback, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_empty & fijo_is_valid_fallback, 'Telefono Fijo']

    movil_is_valid_and_starts_with_3 = (~movil_is_empty) & (~df['Telefono Movil'].str.startswith('60', na=False)) & (df['Telefono Movil'].str.startswith('3', na=False))

    df.loc[movil_is_valid_and_starts_with_3, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_valid_and_starts_with_3, 'Telefono Movil']

    df['TELEFONO CONFIRMACIÓN'] = df['TELEFONO CONFIRMACIÓN'].astype(str).str.replace(r'\\.0$', '', regex=True)

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
        
        st.success(f"✅ Después de filtrar citas duplicadas: {len(df_final)} filas (se eliminaron {len(df_temp) - len(df_final)} duplicados)")
        
        return df_final

    all_empresas = df['EMPRESA'].unique().tolist() if 'EMPRESA' in df.columns else []
    all_ubicaciones = df['Ubicación'].unique().tolist() if 'Ubicación' in df.columns else []
    all_sedes = df['Sede'].unique().tolist() if 'Sede' in df.columns else []
    
    if 'Unidad Funcional' in df.columns:
        all_unidades_funcionales = df['Unidad Funcional'].unique().tolist()
    else:
        all_unidades_funcionales = []

    min_date = df['Fecha Programación_dt'].min()
    max_date = df['Fecha Programación_dt'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        st.info(f"📅 Rango de fechas en los datos: {min_date.date()} a {max_date.date()}")
    else:
        st.warning("⚠️ No se pudieron detectar fechas válidas en los datos")

    num_files = st.number_input("Number of output files to generate", min_value=1, value=1, key='num_files_input')

    def get_filtered_options(selected_empresas, selected_sedes=None):
        if not selected_empresas:
            filtered_sedes = all_sedes
            if selected_sedes:
                filtered_df = df[df['Sede'].isin(selected_sedes)]
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_unidades = filtered_df['Unidad Funcional'].unique().tolist()
                else:
                    filtered_unidades = []
            else:
                filtered_unidades = all_unidades_funcionales
        else:
            filtered_df = df[df['EMPRESA'].isin(selected_empresas)]
            filtered_sedes = filtered_df['Sede'].unique().tolist()
            
            if selected_sedes:
                valid_sedes = [sede for sede in selected_sedes if sede in filtered_sedes]
                if valid_sedes:
                    filtered_df = filtered_df[filtered_df['Sede'].isin(valid_sedes)]
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_unidades = filtered_df['Unidad Funcional'].unique().tolist()
                else:
                    filtered_unidades = []
            else:
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_unidades = filtered_df['Unidad Funcional'].unique().tolist()
                else:
                    filtered_unidades = []
        
        return filtered_sedes, filtered_unidades

    filters = []
    for i in range(num_files):
        st.subheader(f"Filters for Output File {i+1}")
        col1, col2 = st.columns(2)
        with col1:
            selected_empresas = st.multiselect(
                f"Select Empresa(s) for File {i+1}", 
                options=all_empresas, 
                key=f"empresa_{i}", 
                default=all_empresas
            )
            
            filtered_sedes, _ = get_filtered_options(selected_empresas)
            
            # Sanitización de opciones para Streamlit / React DOM
            default_sedes = [s for s in filtered_sedes]
            
            selected_sedes = st.multiselect(
                f"Select Sede(s) for File {i+1}", 
                options=filtered_sedes, 
                key=f"sede_{i}", 
                default=default_sedes
            )
            
        with col2:
            selected_ubicaciones = st.multiselect(
                f"Select Ubicación(s) for File {i+1}", 
                options=all_ubicaciones, 
                key=f"ubicacion_{i}", 
                default=all_ubicaciones
            )
            
            _, filtered_unidades = get_filtered_options(selected_empresas, selected_sedes)
            
            # Sanitización de opciones para Streamlit / React DOM
            default_unidades = [u for u in filtered_unidades]
            
            selected_unidades = st.multiselect(
                f"Select Unidad Funcional(es) for File {i+1}", 
                options=filtered_unidades, 
                key=f"unidad_{i}", 
                default=default_unidades
            )

        if pd.notna(min_date) and pd.notna(max_date):
            default_start_date = min_date.date()
            default_end_date = max_date.date()
        else:
            default_start_date = datetime(2025, 10, 15).date()
            default_end_date = datetime(2025, 10, 16).date()

        start_date = st.date_input(f"Select Start Date for File {i+1}", key=f"start_date_{i}", value=default_start_date)
        end_date = st.date_input(f"Select End Date for File {i+1}", key=f"end_date_{i}", value=default_end_date)

        filters.append({
            'empresas': selected_empresas,
            'ubicaciones': selected_ubicaciones,
            'sedes': selected_sedes,
            'unidades_funcionales': selected_unidades,
            'start_date': start_date,
            'end_date': end_date
        })

    if st.button("Generate and Download Files"):
        # Contenedor dedicado para evitar conflictos de renderizado en React DOM
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        filtered_dfs = []
        for i, file_filters in enumerate(filters):
            status_text.text(f"Procesando archivo {i+1} de {len(filters)}...")
            
            filtered_df = df.copy()
            
            mask = pd.Series(True, index=filtered_df.index)
            
            if file_filters['empresas']:
                empresa_mask = filtered_df['EMPRESA'].isin(file_filters['empresas'])
                mask = mask & empresa_mask
            
            if file_filters['ubicaciones']:
                ubicacion_mask = filtered_df['Ubicación'].isin(file_filters['ubicaciones'])
                mask = mask & ubicacion_mask
            
            if file_filters['sedes']:
                sede_mask = filtered_df['Sede'].isin(file_filters['sedes'])
                mask = mask & sede_mask
            
            if file_filters['unidades_funcionales'] and 'Unidad Funcional' in filtered_df.columns:
                unidad_mask = filtered_df['Unidad Funcional'].isin(file_filters['unidades_funcionales'])
                mask = mask & unidad_mask
            
            start_date_ts = pd.Timestamp(file_filters['start_date'])
            end_date_ts = pd.Timestamp(file_filters['end_date'])
            date_mask = (filtered_df['Fecha Programación_dt'] >= start_date_ts) & (filtered_df['Fecha Programación_dt'] <= end_date_ts)
            mask = mask & date_mask
            
            filtered_df = filtered_df.loc[mask].copy()
            
            st.success(f"📁 Archivo {i+1}: {len(filtered_df)} filas después del filtrado inicial")
            
            filtered_df = identificar_primer_servicio(filtered_df)
            
            if 'Fecha Programación_dt' in filtered_df.columns:
                filtered_df = filtered_df.drop(columns=['Fecha Programación_dt'])
            
            filtered_dfs.append((filtered_df, file_filters))
            progress_bar.progress((i + 1) / len(filters))
        
        status_text.text("✅ Procesamiento completado")

        for i, (filtered_df, file_filters) in enumerate(filtered_dfs):
            if len(filtered_df) == 0:
                st.error(f"❌ El archivo {i+1} no contiene datos con los filtros aplicados.")
                continue
                
            buffer = io.BytesIO()

            base_confirmacion_cols = ['TELEFONO CONFIRMACIÓN', 'VARIABLE']
            pacientes_cols = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 'Fecha Programación Formateada', 'Hora Cita Formatted', 'Actividad Médica']

            if 'Nombre completo' not in filtered_df.columns and 'Nombres' in filtered_df.columns and 'Apellidos' in filtered_df.columns:
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

            empresas_str = "_".join(file_filters['empresas']) if file_filters['empresas'] else "All_Empresas"
            ubicaciones_str = "_".join(file_filters['ubicaciones']) if file_filters['ubicaciones'] else "All_Ubicaciones"
            
            filename = f"{empresas_str}_Confirmacion_{ubicaciones_str}_{file_filters['start_date'].day}_al_{file_filters['end_date'].day}_{file_filters['start_date'].strftime('%B')}_{file_filters['start_date'].year}.xlsx"

            st.download_button(
                label=f"📥 Download File {i+1}: {filename}",
                data=buffer.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheet.sheet",
                key=f"download_{i}"
            )

            buffer.close()

compile(code, "<string>", "exec")
print("Syntax check passed successfully!")
