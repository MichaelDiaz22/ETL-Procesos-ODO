import streamlit as st
import pandas as pd
import openpyxl
import io
import xlsxwriter
from datetime import datetime
import datetime as dt
import locale

st.title("Excel Data Filtering and Export App")

uploaded_file = st.file_uploader("Upload your Excel file", type=".xlsx")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # Load the data into a pandas DataFrame
    df = pd.read_excel(uploaded_file)
    
    # DIAGNÓSTICO: Mostrar información del DataFrame original
    st.subheader("🔍 Información del DataFrame Original")
    st.write(f"📊 Número total de filas: {len(df)}")
    st.write(f"📋 Columnas disponibles: {list(df.columns)}")
    
    if 'EMPRESA' in df.columns:
        st.write(f"🏢 Empresas únicas: {df['EMPRESA'].unique()}")
    if 'Ubicación' in df.columns:
        st.write(f"📍 Ubicaciones únicas: {df['Ubicación'].unique()}")

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

    # Sort the DataFrame by the grouping columns and the new datetime column for 'Identificador Servicio'
    df_sorted_id = df.sort_values(by=['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación', 'Fecha Hora Cita'])

    # Create a new column 'Identificador Servicio'
    df_sorted_id['Identificador Servicio'] = 'unico'

    # Identify groups with duplicate combinations of 'Numero de Identificación', 'Fecha Cita', 'Sede', and 'Ubicación'
    duplicates_group_id = df_sorted_id.duplicated(subset=['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación'], keep=False)

    # Within these duplicate groups, identify the first occurrence based on 'Fecha Hora Cita'
    df_sorted_id.loc[duplicates_group_id, 'occurrence'] = df_sorted_id[duplicates_group_id].groupby(['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación']).cumcount()

    # Mark the first occurrence (occurrence == 0) in a duplicate group as 'primer servicio'
    df_sorted_id.loc[duplicates_group_id & (df_sorted_id['occurrence'] == 0), 'Identificador Servicio'] = 'primer servicio'
    # Mark subsequent occurrences (occurrence > 0) in a duplicate group as 'servicio posterior'
    df_sorted_id.loc[duplicates_group_id & (df_sorted_id['occurrence'] > 0), 'Identificador Servicio'] = 'servicio posterior'

    # Drop the temporary 'occurrence' column
    df_sorted_id = df_sorted_id.drop(columns=['occurrence'])

    # Update the original DataFrame with the new 'Identificador Servicio' column based on the sorted DataFrame's index
    df['Identificador Servicio'] = df_sorted_id.sort_index()['Identificador Servicio']

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

    # CORRECCIÓN CRÍTICA: Convertir fechas en formato español completo
    st.subheader("📅 Conversión de Fechas en Español")
    
    # Función específica para fechas en formato español completo
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
            
        except Exception as e:
            st.write(f"❌ Error parseando fecha '{date_str}': {e}")
            return pd.NaT

    # Aplicar la conversión de fecha
    st.write("🔄 Convirtiendo fechas en formato español...")
    df['Fecha Programación_dt'] = df['Fecha Programación'].apply(parse_spanish_date)
    
    # DIAGNÓSTICO DE FECHAS - MUY IMPORTANTE
    st.subheader("📅 Diagnóstico de Fechas")
    st.write(f"📆 Muestra de 'Fecha Programación' original: {df['Fecha Programación'].head(3).tolist()}")
    st.write(f"🔍 Muestra de 'Fecha Programación_dt' convertida: {df['Fecha Programación_dt'].head(3).tolist()}")
    
    # Verificar si la conversión fue exitosa
    valid_dates = df['Fecha Programación_dt'].notna()
    st.write(f"✅ Número de fechas convertidas exitosamente: {valid_dates.sum()}")
    st.write(f"❌ Número de fechas inválidas (NaT): {df['Fecha Programación_dt'].isna().sum()}")
    
    if valid_dates.sum() > 0:
        st.write(f"📈 Rango de fechas convertidas: {df['Fecha Programación_dt'].min()} to {df['Fecha Programación_dt'].max()}")
    else:
        st.error("🚨 No se pudieron convertir las fechas. Usando fechas alternativas...")
        # Intentar con Fecha Cita como alternativa
        st.write("🔄 Intentando con columna 'Fecha Cita'...")
        df['Fecha Programación_dt'] = df['Fecha Cita'].apply(parse_spanish_date)
        st.write(f"📆 Muestra de 'Fecha Cita' original: {df['Fecha Cita'].head(3).tolist()}")
        st.write(f"🔍 Muestra de 'Fecha Cita' convertida: {df['Fecha Programación_dt'].head(3).tolist()}")

    # Formatear para mostrar (mantener formato original para exportación)
    df['Fecha Programación'] = df['Fecha Programación_dt'].dt.strftime('%Y-%m-%d').fillna('')

    df['Hora Cita'] = df['Hora Cita'].astype(str)
    df['Especialista'] = df['Especialista'].astype(str)
    df['Direccion Final'] = df['Direccion Final'].astype(str)
    df['Ubicación'] = df['Ubicación'].astype(str)
    df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)

    # Convert 'Hora Cita' to datetime objects to format it to 12-hour format
    time_formats_cita = ['%H:%M:%S', '%H:%M', '%I:%M %p']
    def parse_time_cita_robust(time_str):
         time_str = str(time_str) if not pd.isna(time_str) else ''
         for fmt in time_formats_cita:
             try:
                 return pd.to_datetime(time_str, format=fmt)
             except (ValueError, TypeError):
                 continue
         return pd.NaT

    time_parsed_series = df['Hora Cita'].apply(lambda x: parse_time_cita_robust(str(x)))

    if pd.api.types.is_datetime64_any_dtype(time_parsed_series):
        df['Hora Cita Formatted'] = time_parsed_series.dt.strftime('%I:%M %p').fillna('')
    else:
        df['Hora Cita Formatted'] = ''

    # If 'Unidad Funcional' is 'INVESTIGACION MARAYA', set 'Hora Cita Formatted' to '-'
    df.loc[df['Unidad Funcional'] == 'INVESTIGACION MARAYA', 'Hora Cita Formatted'] = '-'

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

    # CORRECCIÓN: Obtener el rango de fechas REAL de los datos convertidos
    min_date = df['Fecha Programación_dt'].min()
    max_date = df['Fecha Programación_dt'].max()
    
    st.subheader("📅 Rango de Fechas Real en los Datos")
    st.write(f"Fecha mínima: {min_date}")
    st.write(f"Fecha máxima: {max_date}")

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

        # CORRECCIÓN: Usar el rango real de fechas para los valores por defecto
        if pd.notna(min_date) and pd.notna(max_date):
            default_start_date = min_date.date()
            default_end_date = max_date.date()
        else:
            # Si no hay fechas válidas, usar fechas por defecto
            default_start_date = datetime(2025, 10, 15).date()
            default_end_date = datetime(2025, 10, 16).date()
            st.warning("⚠️ Usando fechas por defecto ya que no se pudieron detectar fechas válidas")

        st.info(f"💡 Rango de fechas disponible en datos: {default_start_date} a {default_end_date}")

        start_date = st.date_input(f"Select Start Date for File {i+1}", key=f"start_date_{i}", value=default_start_date)
        end_date = st.date_input(f"Select End Date for File {i+1}", key=f"end_date_{i}", value=default_end_date)

        filters.append({
            'empresas': selected_empresas,
            'ubicaciones': selected_ubicaciones,
            'start_date': start_date,
            'end_date': end_date
        })

    if st.button("Generate and Download Files"):
        filtered_dfs = []
        for i, file_filters in enumerate(filters):
            filtered_df = df.copy()

            # DIAGNÓSTICO DETALLADO
            st.subheader(f"🔍 Diagnóstico - Filtros para Archivo {i+1}")
            st.write(f"🏢 Empresas seleccionadas: {file_filters['empresas']}")
            st.write(f"📍 Ubicaciones seleccionadas: {file_filters['ubicaciones']}")
            st.write(f"📅 Rango de fechas seleccionado: {file_filters['start_date']} a {file_filters['end_date']}")

            # Start with a boolean mask that includes all rows
            combined_filter_mask = pd.Series(True, index=filtered_df.index)

            # Apply Empresa filter
            empresa_rows_before = len(filtered_df)
            if file_filters['empresas']:
                empresa_mask = filtered_df['EMPRESA'].str.upper().isin([e.upper() for e in file_filters['empresas']])
                combined_filter_mask = combined_filter_mask & empresa_mask
                empresa_rows_after = empresa_mask.sum()
                st.write(f"📊 Filas después de filtro de empresa: {empresa_rows_after}/{empresa_rows_before}")

            # Apply Ubicación filter
            ubicacion_rows_before = len(filtered_df)
            if file_filters['ubicaciones']:
                ubicacion_mask = filtered_df['Ubicación'].str.upper().isin([u.upper() for u in file_filters['ubicaciones']])
                combined_filter_mask = combined_filter_mask & ubicacion_mask
                ubicacion_rows_after = ubicacion_mask.sum()
                st.write(f"📍 Filas después de filtro de ubicación: {ubicacion_rows_after}/{ubicacion_rows_before}")

            # Apply Date Range filter - CORRECCIÓN: Usar la columna datetime ya convertida
            start_date_ts = pd.Timestamp(file_filters['start_date'])
            end_date_ts = pd.Timestamp(file_filters['end_date'])

            # Perform the comparison using pandas Timestamp objects
            date_mask = (filtered_df['Fecha Programación_dt'] >= start_date_ts) & (filtered_df['Fecha Programación_dt'] <= end_date_ts)
            combined_filter_mask = combined_filter_mask & date_mask
            
            date_rows_after = date_mask.sum()
            st.write(f"📅 Filas después de filtro de fecha: {date_rows_after}/{len(filtered_df)}")

            # Apply the combined filter mask to the DataFrame
            filtered_df = filtered_df.loc[combined_filter_mask].copy()

            # Add debugging line to check the number of rows after filtering
            st.write(f"✅ **Número final de filas en filtered_df para el archivo {i+1}: {len(filtered_df)}**")

            # Mostrar muestra de datos filtrados si hay resultados
            if len(filtered_df) > 0:
                st.write("📋 Muestra de datos filtrados:")
                st.dataframe(filtered_df[['EMPRESA', 'Ubicación', 'Fecha Programación']].head())

            # Drop the temporary datetime column used for filtering
            filtered_df = filtered_df.drop(columns=['Fecha Programación_dt'])

            filtered_dfs.append(filtered_df)

        # Now, generate and download the filtered files
        for i, filtered_df in enumerate(filtered_dfs):
            if len(filtered_df) == 0:
                st.error(f"❌ El archivo {i+1} no contiene datos con los filtros aplicados. No se generará archivo.")
                st.info("💡 **Sugerencias:** Ajusta el rango de fechas para que coincida con tus datos reales")
                continue
                
            buffer = io.BytesIO()

            # CORRECCIÓN PRINCIPAL: Usar selección directa en lugar de reindex
            base_confirmacion_cols = ['TELEFONO CONFIRMACIÓN', 'VARIABLE']
            pacientes_cols = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 'Fecha Programación', 'Hora Cita Formatted', 'Actividad Médica']

            # Crear 'Nombre completo' si no existe
            if 'Nombre completo' not in filtered_df.columns:
                filtered_df['Nombre completo'] = filtered_df['Nombres'].astype(str) + ' ' + filtered_df['Apellidos'].astype(str)

            # Asegurar que 'Hora Cita Formatted' esté disponible
            if 'Hora Cita Formatted' not in filtered_df.columns:
                time_parsed_series = filtered_df['Hora Cita'].apply(lambda x: parse_time_cita_robust(str(x)))
                if pd.api.types.is_datetime64_any_dtype(time_parsed_series):
                    filtered_df['Hora Cita Formatted'] = time_parsed_series.dt.strftime('%I:%M %p').fillna('')
                else:
                    filtered_df['Hora Cita Formatted'] = ''

            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # CORRECIÓN: Seleccionar columnas existentes directamente
                base_confirmacion_cols_existing = [col for col in base_confirmacion_cols if col in filtered_df.columns]
                
                if base_confirmacion_cols_existing:
                    base_confirmacion_df = filtered_df[base_confirmacion_cols_existing]
                    base_confirmacion_df.to_excel(writer, sheet_name='Base confirmación', index=False)
                    st.success(f"✅ Hoja 'Base confirmación' creada con {len(base_confirmacion_df)} filas y {len(base_confirmacion_df.columns)} columnas")
                else:
                    st.warning(f"⚠️ No se encontraron las columnas necesarias para 'Base confirmación'")

                # CORRECIÓN: Para la hoja Pacientes
                pacientes_cols_existing = [col for col in pacientes_cols if col in filtered_df.columns]
                
                if pacientes_cols_existing:
                    pacientes_df = filtered_df[pacientes_cols_existing].copy()
                    
                    # Renombrar 'Hora Cita Formatted' a 'Hora Cita' si existe
                    if 'Hora Cita Formatted' in pacientes_df.columns:
                        pacientes_df = pacientes_df.rename(columns={'Hora Cita Formatted': 'Hora Cita'})
                    
                    pacientes_df.to_excel(writer, sheet_name='Pacientes', index=False)
                    st.success(f"✅ Hoja 'Pacientes' creada con {len(pacientes_df)} filas y {len(pacientes_df.columns)} columnas")
                else:
                    st.warning(f"⚠️ No se encontraron las columnas necesarias para 'Pacientes'")

            # Generate filename based on filters
            empresas_str = "_".join(file_filters['empresas']) if file_filters['empresas'] else "All_Empresas"
            ubicaciones_str = "_".join(file_filters['ubicaciones']) if file_filters['ubicaciones'] else "All_Ubicaciones"
            
            filename = f"{empresas_str}_Confirmacion_{ubicaciones_str}_{file_filters['start_date'].day}_al_{file_filters['end_date'].day}_{file_filters['start_date'].strftime('%B')}_{file_filters['start_date'].year}.xlsx"

            # Create download button
            st.download_button(
                label=f"📥 Download File {i+1}: {filename}",
                data=buffer.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheet.sheet",
                key=f"download_{i}"
            )

            buffer.close()

