import streamlit as st
import pandas as pd
import openpyxl
import io
import xlsxwriter
from datetime import datetime

st.title("Excel Data Filtering and Export App")

uploaded_file = st.file_uploader("Upload your Excel file", type=".xlsx")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # Load the data into a pandas DataFrame
    df = pd.read_excel(uploaded_file)

    # Preprocessing steps

    # Sort the DataFrame by 'Numero de Identificación' in ascending order
    df = df.sort_values(by='Numero de Identificación', ascending=True).reset_index(drop=True)

    # Create a new column 'Ubicación' based on the 'Consultorio' column
    df['Ubicación'] = df['Consultorio'].apply(lambda x: 'Procedimiento' if pd.isna(x) or str(x).strip() == '' else 'Consulta')

    # Convert 'Fecha Cita' and 'Hora Cita' to datetime objects
    # Use errors='coerce' to handle potential parsing issues and set invalid dates to NaT
    # Convert both columns to string first to avoid potential type issues
    # Attempt to parse 'Fecha Cita' and 'Hora Cita' with a list of common formats
    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y']
    time_formats = ['%H:%M:%S', '%H:%M', '%I:%M %p']

    def parse_datetime_robust(date_str, time_str):
        # Ensure inputs are strings
        date_str = str(date_str) if not pd.isna(date_str) else ''
        time_str = str(time_str) if not pd.isna(time_str) else ''

        for d_fmt in date_formats:
            for t_fmt in time_formats:
                try:
                    # Combine date and time strings and attempt parsing
                    datetime_str = f"{date_str} {time_str}"
                    return pd.to_datetime(datetime_str, format=f"{d_fmt} {t_fmt}")
                except (ValueError, TypeError):
                    continue
        return pd.NaT # Return Not a Time if no format matches

    df['Fecha Hora Cita'] = df.apply(lambda row: parse_datetime_robust(row['Fecha Cita'], row['Hora Cita']), axis=1)


    # Sort the DataFrame by the grouping columns and the new datetime column for 'Identificador Servicio'
    df_sorted_id = df.sort_values(by=['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación', 'Fecha Hora Cita'])

    # Create a new column 'Identificador Servicio'
    # Initialize with 'unico'
    df_sorted_id['Identificador Servicio'] = 'unico'

    # Identify groups with duplicate combinations of 'Numero de Identificación', 'Fecha Cita', 'Sede', and 'Ubicación'
    duplicates_group_id = df_sorted_id.duplicated(subset=['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación'], keep=False)

    # Within these duplicate groups, identify the first occurrence based on 'Fecha Hora Cita'
    # Use cumcount to get the occurrence number within each group of duplicates
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
            'Carrera 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA', # This entry seems like a duplicate based on the address. Let's remove one to match the length of 'Sede'.
            'Calle 50 N° 13-10, MARAYA - PEREIRA',
            'Calle 10 N° 2C-10B, CLÍNICA AVIDANTI -  MANIZALES',
            'Carrera 23 N° 46 Esquina, CLÍNICA LA PRESENTACIÓN - MANIZALES',
            'Calle 92 N°  29-75,  SAN MARCEL -  MANIZALES'
        ]
    })

    # Merge df with direcciones_sede to get the address based on 'Sede'
    df = pd.merge(df, direcciones_sede, on='Sede', how='left', suffixes=('', '_merged'))

    # Create the new column with the address, initially taking values from the merged 'Dirección' column
    # Use the merged column if it exists, otherwise use the original 'Dirección Centro Atención'
    if 'Dirección_merged' in df.columns:
        df['Direccion Final'] = df['Dirección_merged']
        df = df.drop(columns=['Dirección_merged']) # Drop the merged column after use
    else:
        # Check if the original 'Dirección Centro Atención' column exists before using it
        if 'Dirección Centro Atención' in df.columns:
            df['Direccion Final'] = df['Dirección Centro Atención']
        else:
            df['Direccion Final'] = '' # Or handle missing original column appropriately


    # Apply the condition: if 'Modalidad' is 'Teleconsulta', set 'Direccion Final' to 'Teleconsulta'
    df.loc[df['Modalidad'] == 'Teleconsulta', 'Direccion Final'] = 'Teleconsulta'

    # Ensure the necessary columns are treated as strings for concatenation
    df['Nombres'] = df['Nombres'].astype(str)
    df['Apellidos'] = df['Apellidos'].astype(str)
    df['Actividad Médica'] = df['Actividad Médica'].astype(str)

    # Convert 'Fecha Programación' to datetime objects - Attempt with multiple formats
    date_formats_prog = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y']
    def parse_date_prog_robust(date_str):
        date_str = str(date_str) if not pd.isna(date_str) else ''
        for fmt in date_formats_prog:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except (ValueError, TypeError):
                continue
        return pd.NaT # Return Not a Time if no format matches

    df['Fecha Programación_dt'] = df['Fecha Programación'].apply(lambda x: parse_date_prog_robust(str(x)))
    df['Fecha Programación'] = df['Fecha Programación_dt'].dt.strftime('%Y-%m-%d').fillna('') # Format after parsing


    df['Hora Cita'] = df['Hora Cita'].astype(str)
    df['Especialista'] = df['Especialista'].astype(str)
    df['Direccion Final'] = df['Direccion Final'].astype(str)
    df['Ubicación'] = df['Ubicación'].astype(str)
    df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)


    # Convert 'Hora Cita' to datetime objects to format it to 12-hour format - Attempt with multiple formats
    time_formats_cita = ['%H:%M:%S', '%H:%M', '%I:%M %p']
    def parse_time_cita_robust(time_str):
         time_str = str(time_str) if not pd.isna(time_str) else ''
         for fmt in time_formats_cita:
             try:
                 # Need a dummy date to combine with time for datetime conversion
                 # pd.to_datetime can sometimes infer date if only time is provided, but being explicit is safer
                 return pd.to_datetime(time_str, format=fmt)
             except (ValueError, TypeError):
                 continue
         return pd.NaT # Return Not a Time if no format matches

    # Apply the time parsing function
    time_parsed_series = df['Hora Cita'].apply(lambda x: parse_time_cita_robust(str(x)))

    # Add debugging to check the result of time parsing
    # st.write("Sample of time_parsed_series:", time_parsed_series.head())
    # st.write("Dtype of time_parsed_series:", time_parsed_series.dtype)
    # st.write("Number of NaT in time_parsed_series:", time_parsed_series.isna().sum())


    # Format the time only if the parsing was successful (the result is datetime-like)
    # Check if the series contains any datetime-like values before using .dt
    if pd.api.types.is_datetime64_any_dtype(time_parsed_series):
        df['Hora Cita Formatted'] = time_parsed_series.dt.strftime('%I:%M %p').fillna('')
    else:
        # If parsing failed for all rows, fill with empty string or a placeholder
        df['Hora Cita Formatted'] = '' # Or fill with original value or specific placeholder


    # If 'Unidad Funcional' is 'INVESTIGACION MARAYA', set 'Hora Cita Formatted' to '-'
    df.loc[df['Unidad Funcional'] == 'INVESTIGACION MARAYA', 'Hora Cita Formatted'] = '-'


    # Create the 'variable_mensaje' column based on the 'Ubicación'
    df['VARIABLE'] = df.apply(
        lambda row: f"{row['Nombres']} {row['Apellidos']}|{row['Actividad Médica']}|{row['Fecha Programación']}|{row['Hora Cita Formatted']}|{row['Especialista']}|{row['Direccion Final']}",
        axis=1
    )

    # Drop the temporary 'Hora Cita Formatted' column
    # Keep Hora Cita Formatted as it's needed for the Pacientes sheet
    # df = df.drop(columns=['Hora Cita Formatted'])


    # Ensure phone number columns are treated as strings and handle potential missing values
    df['Telefono Movil'] = df['Telefono Movil'].astype(str).str.strip()
    df['Telefono Fijo'] = df['Telefono Fijo'].astype(str).str.strip()

    # Create the new column 'TELEFONO CONFIRMACIÓN'
    df['TELEFONO CONFIRMACIÓN'] = 'sin número para enviar mensaje' # Initialize with the default value

    # Condition 1: If 'Telefono Movil' is empty, evaluate 'Telefono Fijo'
    movil_is_empty = (df['Telefono Movil'].isna()) | (df['Telefono Movil'] == '') | (df['Telefono Movil'] == 'nan') # Added check for string 'nan'

    # If 'Telefono Movil' is empty, check 'Telefono Fijo'
    # Condition 2 (nested within Condition 1): If 'Telefono Fijo' is NOT empty and does NOT start with '60', use 'Telefono Fijo'
    fijo_is_valid_fallback = (~df['Telefono Fijo'].isna()) & (df['Telefono Fijo'] != '') & (df['Telefono Fijo'] != 'nan') & (~df['Telefono Fijo'].str.startswith('60', na=False)) # Added check for string 'nan'

    df.loc[movil_is_empty & fijo_is_valid_fallback, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_empty & fijo_is_valid_fallback, 'Telefono Fijo']


    # Condition 3: If 'Telefono Movil' is NOT empty AND does NOT start with '60' AND starts with '3', use 'Telefono Movil'
    movil_is_valid_and_starts_with_3 = (~movil_is_empty) & (~df['Telefono Movil'].str.startswith('60', na=False)) & (df['Telefono Movil'].str.startswith('3', na=False))

    df.loc[movil_is_valid_and_starts_with_3, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_valid_and_starts_with_3, 'Telefono Movil']

    # If neither of the above conditions are met, the value remains 'sin número para enviar mensaje' (already initialized)


    # Convert the column to string and remove '.0' if present
    df['TELEFONO CONFIRMACIÓN'] = df['TELEFONO CONFIRMACIÓN'].astype(str).str.replace(r'\.0$', '', regex=True)


    # After loading and preprocessing, populate the options for the multiselect filters
    all_empresas = df['EMPRESA'].unique().tolist()
    all_ubicaciones = df['Ubicación'].unique().tolist()

    num_files = st.number_input("Number of output files to generate", min_value=1, value=1, key='num_files_input')

    # Collect filter selections outside the button click to retain state
    filters = []
    for i in range(num_files):
        st.subheader(f"Filters for Output File {i+1}")
        col1, col2 = st.columns(2)
        with col1:
            # Default to all options selected
            selected_empresas = st.multiselect(f"Select Empresa(s) for File {i+1}", options=all_empresas, key=f"empresa_{i}", default=all_empresas)
        with col2:
            # Default to all options selected
            selected_ubicaciones = st.multiselect(f"Select Ubicación(s) for File {i+1}", options=all_ubicaciones, key=f"ubicacion_{i}", default=all_ubicaciones)

        # Set default date inputs based on the date range in the dataframe
        # Ensure 'Fecha Programación_dt' is treated as datetime for finding min/max
        # Use the already created 'Fecha Programación_dt' from preprocessing
        min_date = df['Fecha Programación_dt'].min()
        max_date = df['Fecha Programación_dt'].max()


        # Ensure min_date and max_date are not NaT before setting default values
        default_start_date = min_date.date() if pd.notna(min_date) else datetime.today().date()
        default_end_date = max_date.date() if pd.notna(max_date) else datetime.today().date()


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

            # Start with a boolean mask that includes all rows
            combined_filter_mask = pd.Series(True, index=filtered_df.index)

            # Apply Empresa filter - only filter if specific companies are selected
            if file_filters['empresas']:
                empresa_mask = filtered_df['EMPRESA'].str.upper().isin([e.upper() for e in file_filters['empresas']])
                # st.write(f"Rows after Empresa filter for file {i+1}: {empresa_mask.sum()}") # Debugging line
                combined_filter_mask = combined_filter_mask & empresa_mask
            else:
                # If no specific companies are selected, the mask remains True for this filter
                pass # No change to combined_filter_mask

            # Apply Ubicación filter - only filter if specific locations are selected
            if file_filters['ubicaciones']:
                ubicacion_mask = filtered_df['Ubicación'].str.upper().isin([u.upper() for u in file_filters['ubicaciones']])
                # st.write(f"Rows after Ubicación filter for file {i+1}: {ubicacion_mask.sum()}") # Debugging line
                combined_filter_mask = combined_filter_mask & ubicacion_mask
            else:
                 # If no specific locations are selected, the mask remains True for this filter
                 pass # No change to combined_filter_mask


            # Apply Date Range filter (using 'Fecha Programación_dt')
            # Ensure 'Fecha Programación_dt' is in datetime format for comparison
            # It should already be datetime from preprocessing, but let's be safe
            filtered_df['Fecha Programación_dt'] = pd.to_datetime(filtered_df['Fecha Programación_dt'], errors='coerce')


            # Convert selected dates to pandas Timestamps for consistent comparison
            start_date_ts = pd.Timestamp(file_filters['start_date'])
            end_date_ts = pd.Timestamp(file_filters['end_date'])

            # Perform the comparison using pandas Timestamp objects
            date_mask = (filtered_df['Fecha Programación_dt'] >= start_date_ts) & (filtered_df['Fecha Programación_dt'] <= end_date_ts)
            # st.write(f"Rows after Date Range filter for file {i+1}: {date_mask.sum()}") # Debugging line
            combined_filter_mask = combined_filter_mask & date_mask


            # Apply the combined filter mask to the DataFrame
            filtered_df = filtered_df.loc[combined_filter_mask].copy() # Use .loc and .copy() to avoid SettingWithCopyWarning

            # Add debugging line to check the number of rows after filtering
            st.write(f"Número de filas en filtered_df para el archivo {i+1}: {len(filtered_df)}")


            # Drop the temporary datetime column used for filtering
            # Keep the original 'Fecha Programación' string column for output
            filtered_df = filtered_df.drop(columns=['Fecha Programación_dt'])


            filtered_dfs.append(filtered_df)

        # Now, generate and download the filtered files
        for i, filtered_df in enumerate(filtered_dfs):
            buffer = io.BytesIO()

            # Define columns for each sheet in the desired order
            base_confirmacion_cols_ordered = ['TELEFONO CONFIRMACIÓN', 'VARIABLE']
            pacientes_cols_ordered = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 'Fecha Programación', 'Hora Cita Formatted', 'Actividad Médica'] # Use 'Hora Cita Formatted' here


            # Create 'Nombre completo' by concatenating 'Nombres' and 'Apellidos' for the 'Pacientes' sheet if it doesn't exist
            if 'Nombre completo' not in filtered_df.columns and 'Nombres' in filtered_df.columns and 'Apellidos' in filtered_df.columns:
                 filtered_df['Nombre completo'] = filtered_df['Nombres'].astype(str) + ' ' + filtered_df['Apellidos'].astype(str)
            elif 'Nombre completo' not in filtered_df.columns:
                 filtered_df['Nombre completo'] = '' # Handle case where Nombres or Apellidos are missing

            # Ensure 'Hora Cita Formatted' is available for the Pacientes sheet
            # Re-apply time parsing and formatting after filtering
            time_formats_cita = ['%H:%M:%S', '%H:%M', '%I:%M %p']
            def parse_time_cita_robust(time_str):
                 time_str = str(time_str) if not pd.isna(time_str) else ''
                 for fmt in time_formats_cita:
                     try:
                         return pd.to_datetime(time_str, format=fmt).time() # Parse to time object
                     except (ValueError, TypeError):
                         continue
                 return pd.NaT # Return Not a Time if no format matches

            # Apply the time parsing function to get time objects
            time_objects_series = filtered_df['Hora Cita'].apply(lambda x: parse_time_cita_robust(str(x)))

            # Format the time objects to '%I:%M %p'
            # Check if the series contains any time objects before formatting
            if pd.api.types.is_datetime64_any_dtype(time_objects_series):
                 # Convert to datetime first for strftime
                 filtered_df['Hora Cita Formatted'] = pd.to_datetime(time_objects_series.astype(str)).dt.strftime('%I:%M %p').fillna('')
            elif pd.api.types.is_object_dtype(time_objects_series) and all(isinstance(x, datetime.time) or pd.isna(x) for x in time_objects_series):
                 # If it's a series of time objects, convert to string and then try to parse as datetime for formatting
                 try:
                     filtered_df['Hora Cita Formatted'] = pd.to_datetime(time_objects_series.astype(str), format='%H:%M:%S').dt.strftime('%I:%M %p').fillna('')
                 except (ValueError, TypeError):
                      filtered_df['Hora Cita Formatted'] = time_objects_series.astype(str) # Fallback to string representation
            else:
                # If parsing failed for all rows or resulted in non-time objects, fill with empty string or a placeholder
                filtered_df['Hora Cita Formatted'] = ''


            # If 'Unidad Funcional' is 'INVESTIGACION MARAYA', set 'Hora Cita Formatted' to '-'
            if 'Unidad Funcional' in filtered_df.columns:
                filtered_df.loc[filtered_df['Unidad Funcional'] == 'INVESTIGACION MARAYA', 'Hora Cita Formatted'] = '-'


            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Write to "Base confirmación" sheet with specified columns and order
                # Ensure all base_confirmacion_cols_ordered exist in the dataframe before writing
                base_confirmacion_df = filtered_df.reindex(columns=[col for col in base_confirmacion_cols_ordered if col in filtered_df.columns])
                base_confirmacion_df.to_excel(writer, sheet_name='Base confirmación', index=False)

                # Write to "Pacientes" sheet with specified columns and order
                # Ensure all pacientes_cols_ordered exist in the dataframe before writing
                pacientes_df = filtered_df.reindex(columns=[col for col in pacientes_cols_ordered if col in filtered_df.columns])
                # Rename 'Hora Cita Formatted' to 'Hora Cita' for consistency in the output sheet if it exists
                if 'Hora Cita Formatted' in pacientes_df.columns:
                     pacientes_df = pacientes_df.rename(columns={'Hora Cita Formatted': 'Hora Cita'})

                # Ensure 'Actividad Médica' is included in the Pacientes sheet if it exists
                if 'Actividad Médica' in filtered_df.columns and 'Actividad Médica' not in pacientes_df.columns:
                    pacientes_df['Actividad Médica'] = filtered_df['Actividad Médica']


                pacientes_df.to_excel(writer, sheet_name='Pacientes', index=False)


            # Generate filename based on filters
            empresas_str = "_".join(filters[i]['empresas']) if filters[i]['empresas'] else "All_Empresas"
            ubicaciones_str = "_".join(filters[i]['ubicaciones']) if filters[i]['ubicaciones'] else "All_Ubicaciones"
            start_date_str = filters[i]['start_date'].strftime('%Y-%m-%d')
            end_date_str = filters[i]['end_date'].strftime('%Y-%m-%d')
            # Extract month and year for filename - assuming start_date is representative
            month_year_str = filters[i]['start_date'].strftime('%B_%Y')


            # Filename format: [EMPRESA]_[ubicación]_[dia inicial]_al_[dia final]_[mes]_[año].xlsx
            filename = f"{empresas_str}_Confirmacion_{ubicaciones_str}_{filters[i]['start_date'].day}_al_{filters[i]['end_date'].day}_{filters[i]['start_date'].strftime('%B')}_{filters[i]['start_date'].year}.xlsx"


            # Create download button
            st.download_button(
                label=f"Download File {i+1}: {filename}",
                data=buffer.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheet.sheet"
            )

            buffer.close() # Close the buffer after use
