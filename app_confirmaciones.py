import streamlit as st
import pandas as pd
import openpyxl
import io
import xlsxwriter
from datetime import datetime
import datetime as dt
import numpy as np

st.title("Excel Data Filtering and Export App")

uploaded_file = st.file_uploader("Upload your Excel file", type=".xlsx")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # Load the data into a pandas DataFrame
    df = pd.read_excel(uploaded_file)
    
    st.info(f"📊 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")

    # Preprocessing steps

    # Sort the DataFrame by 'Numero de Identificación' in ascending order
    df = df.sort_values(by='Numero de Identificación', ascending=True).reset_index(drop=True)

    # Create a new column 'Ubicación' based on the 'Consultorio' column
    df['Ubicación'] = df['Consultorio'].apply(lambda x: 'Procedimiento' if pd.isna(x) or str(x).strip() == '' else 'Consulta')

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

    df['Fecha Hora Cita'] = df.apply(lambda row: parse_datetime_robust(row['Fecha Cita'], row['Hora Cita']), axis=1)

    # CORRECCIÓN: Función mejorada para identificar y filtrar solo el primer servicio
    def identificar_primer_servicio(df_filtrado):
        """
        Identifica y mantiene solo el primer servicio por paciente, sede, especialidad, fecha y hora más temprana
        """
        if len(df_filtrado) == 0:
            return df_filtrado
        
        # Crear una copia para no modificar el original
        df_temp = df_filtrado.copy()
        
        # Asegurarse de que tenemos la columna de especialidad
        if 'Especialidad Cita' not in df_temp.columns:
            st.warning("⚠️ No se encontró la columna 'Especialidad Cita'")
            return df_temp
        
        # Ordenar por fecha y hora de cita
        df_temp = df_temp.sort_values(['Numero de Identificación', 'Fecha Hora Cita', 'Sede', 'Especialidad Cita'])
        
        # Crear una clave única para identificar duplicados
        df_temp['clave_duplicado'] = (
            df_temp['Numero de Identificación'].astype(str) + '|' + 
            df_temp['Sede'].astype(str) + '|' + 
            df_temp['Especialidad Cita'].astype(str) + '|' + 
            df_temp['Fecha Hora Cita'].dt.date.astype(str)
        )
        
        # Mantener solo el primer registro (el más temprano) por cada clave
        df_final = df_temp.drop_duplicates(subset=['clave_duplicado'], keep='first')
        
        # Eliminar la columna temporal
        df_final = df_final.drop(columns=['clave_duplicado'])
        
        st.info(f"✅ Después de filtrar servicios duplicados: {len(df_final)} filas (se eliminaron {len(df_temp) - len(df_final)} duplicados)")
        
        return df_final

    # Load the direcciones_sede DataFrame
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
            'Carrera 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
            'Carrera 4 N° 11-41 CENTRO - LA DORADA',
            'Carrera 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
            'Calle 50 N° 13-10, MARAYA - PEREIRA',
            'Calle 10 N° 2C-10B, CLÍNICA AVIDANTI -  MANIZALES',
            'Carrera 23 N° 46 Esquina, CLÍNICA LA PRESENTACIÓN - MANIZALES',
            'Calle 92 N°  29-75,  SAN MARCEL -  MANIZALES'
        ]
    })

    # Merge df with direcciones_sede to get the address based on 'Sede'
    df = pd.merge(df, direcciones_sede, on='Sede', how='left', suffixes=('', '_merged'))

    # Create the new column with the address
    if 'Dirección_merged' in df.columns:
        df['Direccion Final'] = df['Dirección_merged']
        df = df.drop(columns=['Dirección_merged'])
    else:
        if 'Dirección Centro Atención' in df.columns:
            df['Direccion Final'] = df['Dirección Centro Atención']
        else:
            df['Direccion Final'] = ''

    # Apply the condition: if 'Modalidad' is 'Teleconsulta', set 'Direccion Final' to 'Teleconsulta'
    df.loc[df['Modalidad'] == 'Teleconsulta', 'Direccion Final'] = 'Teleconsulta'

    # Ensure the necessary columns are treated as strings for concatenation
    df['Nombres'] = df['Nombres'].astype(str)
    df['Apellidos'] = df['Apellidos'].astype(str)
    df['Actividad Médica'] = df['Actividad Médica'].astype(str)

    # CORRECCIÓN: Conversión robusta de fechas sin mostrar diagnóstico
    def parse_spanish_date(date_str):
        if pd.isna(date_str) or str(date_str).strip() == '':
            return pd.NaT
            
        date_str = str(date_str).strip().lower()
        
        # Mapeo de meses en español a inglés
        months_map = {
            'enero': 'January', 'febrero': 'February', 'marzo': 'March', 'abril': 'April',
            'mayo': 'May', 'junio': 'June', 'julio': 'July', 'agosto': 'August',
            'septiembre': 'September', 'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
        }
        
        # Mapeo de días en español a inglés
        days_map = {
            'lunes': 'Monday', 'martes': 'Tuesday', 'miércoles': 'Wednesday', 'miercoles': 'Wednesday',
            'jueves': 'Thursday', 'viernes': 'Friday', 'sábado': 'Saturday', 'sabado': 'Saturday',
            'domingo': 'Sunday'
        }
        
        try:
            # Remover el día de la semana (lunes, martes, etc.)
            for day_es, day_en in days_map.items():
                if date_str.startswith(day_es):
                    # Remover el día de la semana y la coma
                    date_str = date_str.replace(day_es, '').replace(',', '').strip()
                    break
            
            # Reemplazar meses en español por meses en inglés
            for month_es, month_en in months_map.items():
                if month_es in date_str:
                    date_str = date_str.replace(month_es, month_en)
                    break
            
            # Parsear la fecha en formato inglés
            return pd.to_datetime(date_str, format='%d de %B de %Y')
            
        except Exception:
            return pd.NaT

    # Aplicar la conversión de fecha sin mostrar diagnóstico
    df['Fecha Programación_dt'] = df['Fecha Programación'].apply(parse_spanish_date)
    
    # Si la conversión falla, intentar con Fecha Cita
    if df['Fecha Programación_dt'].isna().all():
        df['Fecha Programación_dt'] = df['Fecha Cita'].apply(parse_spanish_date)

    # Formatear para mostrar (mantener formato original para exportación)
    df['Fecha Programación'] = df['Fecha Programación_dt'].dt.strftime('%Y-%m-%d').fillna('')

    # CORRECCIÓN MEJORADA: Conversión de horas decimales a formato de tiempo
    def convert_decimal_to_time(decimal_time):
        """
        Convierte tiempo decimal (0.5 = 12:00 PM) a formato 12 horas
        """
        try:
            if pd.isna(decimal_time) or str(decimal_time).strip() in ['', 'nan', 'NaT']:
                return ''
            
            # Si ya es un string con formato de hora, retornar tal cual
            if isinstance(decimal_time, str) and (':' in decimal_time or 'AM' in decimal_time.upper() or 'PM' in decimal_time.upper()):
                return decimal_time
            
            # Convertir a float y calcular horas y minutos
            decimal_val = float(decimal_time)
            total_minutes = int(decimal_val * 24 * 60)
            
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            # Crear objeto datetime
            time_obj = dt.time(hours, minutes)
            
            # Formatear a 12 horas
            return time_obj.strftime('%I:%M %p').lstrip('0')
            
        except (ValueError, TypeError):
            return str(decimal_time)

    # Aplicar la conversión de hora sin mostrar diagnóstico
    df['Hora Cita Formatted'] = df['Hora Cita'].apply(convert_decimal_to_time)

    # If 'Unidad Funcional' is 'INVESTIGACION MARAYA', set 'Hora Cita Formatted' to '-'
    if 'Unidad Funcional' in df.columns:
        investigacion_mask = df['Unidad Funcional'] == 'INVESTIGACION MARAYA'
        df.loc[investigacion_mask, 'Hora Cita Formatted'] = '-'

    df['Especialista'] = df['Especialista'].astype(str)
    df['Direccion Final'] = df['Direccion Final'].astype(str)
    df['Ubicación'] = df['Ubicación'].astype(str)
    df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)

    # Create the 'variable_mensaje' column based on the 'Ubicación'
    df['VARIABLE'] = df.apply(
        lambda row: f"{row['Nombres']} {row['Apellidos']}|{row['Actividad Médica']}|{row['Fecha Programación']}|{row['Hora Cita Formatted']}|{row['Especialista']}|{row['Direccion Final']}",
        axis=1
    )

    # Ensure phone number columns are treated as strings and handle potential missing values
    df['Telefono Movil'] = df['Telefono Movil'].astype(str).str.strip()
    df['Telefono Fijo'] = df['Telefono Fijo'].astype(str).str.strip()

    # Create the new column 'TELEFONO CONFIRMACIÓN'
    df['TELEFONO CONFIRMACIÓN'] = 'sin número para enviar mensaje'

    # Condition 1: If 'Telefono Movil' is empty, evaluate 'Telefono Fijo'
    movil_is_empty = (df['Telefono Movil'].isna()) | (df['Telefono Movil'] == '') | (df['Telefono Movil'] == 'nan')

    # Condition 2: If 'Telefono Fijo' is NOT empty and does NOT start with '60', use 'Telefono Fijo'
    fijo_is_valid_fallback = (~df['Telefono Fijo'].isna()) & (df['Telefono Fijo'] != '') & (df['Telefono Fijo'] != 'nan') & (~df['Telefono Fijo'].str.startswith('60', na=False))

    df.loc[movil_is_empty & fijo_is_valid_fallback, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_empty & fijo_is_valid_fallback, 'Telefono Fijo']

    # Condition 3: If 'Telefono Movil' is NOT empty AND does NOT start with '60' AND starts with '3', use 'Telefono Movil'
    movil_is_valid_and_starts_with_3 = (~movil_is_empty) & (~df['Telefono Movil'].str.startswith('60', na=False)) & (df['Telefono Movil'].str.startswith('3', na=False))

    df.loc[movil_is_valid_and_starts_with_3, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_valid_and_starts_with_3, 'Telefono Movil']

    # Convert the column to string and remove '.0' if present
    df['TELEFONO CONFIRMACIÓN'] = df['TELEFONO CONFIRMACIÓN'].astype(str).str.replace(r'\.0$', '', regex=True)

    # After loading and preprocessing, populate the options for the multiselect filters
    all_empresas = df['EMPRESA'].unique().tolist()
    all_ubicaciones = df['Ubicación'].unique().tolist()

    # Obtener el rango de fechas REAL de los datos convertidos
    min_date = df['Fecha Programación_dt'].min()
    max_date = df['Fecha Programación_dt'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        st.info(f"📅 Rango de fechas en los datos: {min_date.date()} a {max_date.date()}")
    else:
        st.warning("⚠️ No se pudieron detectar fechas válidas en los datos")

    num_files = st.number_input("Number of output files to generate", min_value=1, value=1, key='num_files_input')

    # Collect filter selections outside the button click to retain state
    filters = []
    for i in range(num_files):
        st.subheader(f"Filters for Output File {i+1}")
        col1, col2 = st.columns(2)
        with col1:
            selected_empresas = st.multiselect(f"Select Empresa(s) for File {i+1}", options=all_empresas, key=f"empresa_{i}", default=all_empresas)
        with col2:
            selected_ubicaciones = st.multiselect(f"Select Ubicación(s) for File {i+1}", options=all_ubicaciones, key=f"ubicacion_{i}", default=all_ubicaciones)

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
            'start_date': start_date,
            'end_date': end_date
        })

    if st.button("Generate and Download Files"):
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
            
            start_date_ts = pd.Timestamp(file_filters['start_date'])
            end_date_ts = pd.Timestamp(file_filters['end_date'])
            date_mask = (filtered_df['Fecha Programación_dt'] >= start_date_ts) & (filtered_df['Fecha Programación_dt'] <= end_date_ts)
            mask = mask & date_mask
            
            filtered_df = filtered_df.loc[mask].copy()
            
            st.success(f"📁 Archivo {i+1}: {len(filtered_df)} filas después del filtrado inicial")
            
            # CORRECCIÓN CRÍTICA: Aplicar filtro de primer servicio después del filtrado normal
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
            pacientes_cols = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 'Fecha Programación', 'Hora Cita Formatted', 'Actividad Médica']

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
