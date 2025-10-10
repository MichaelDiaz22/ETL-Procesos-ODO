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
    df['Fecha Hora Cita'] = pd.to_datetime(df['Fecha Cita'].astype(str) + ' ' + df['Hora Cita'].astype(str), errors='coerce')

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
            'Carrera 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
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
    # Convert to datetime before string conversion to handle potential NaT values gracefully
    df['Fecha Programación'] = pd.to_datetime(df['Fecha Programación'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
    df['Hora Cita'] = df['Hora Cita'].astype(str)
    df['Especialista'] = df['Especialista'].astype(str)
    df['Direccion Final'] = df['Direccion Final'].astype(str)
    df['Ubicación'] = df['Ubicación'].astype(str)
    df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)


    # Convert 'Hora Cita' to datetime objects to format it to 12-hour format
    # Use errors='coerce' to handle potential parsing issues and set invalid times to NaT
    df['Hora Cita Formatted'] = pd.to_datetime(df['Hora Cita'], errors='coerce').dt.strftime('%I:%M %p')
    # Fill NaN values that might result from coercion, perhaps with an empty string or a placeholder
    df['Hora Cita Formatted'] = df['Hora Cita Formatted'].fillna('') # Or another suitable placeholder

    # If 'Unidad Funcional' is 'INVESTIGACION MARAYA', set 'Hora Cita Formatted' to '-'
    df.loc[df['Unidad Funcional'] == 'INVESTIGACION MARAYA', 'Hora Cita Formatted'] = '-'


    # Create the 'variable_mensaje' column based on the 'Ubicación'
    df['VARIABLE'] = df.apply(
        lambda row: f"{row['Nombres']} {row['Apellidos']}|{row['Actividad Médica']}|{row['Fecha Programación']}|{row['Hora Cita Formatted']}|{row['Especialista']}|{row['Direccion Final']}",
        axis=1
    )

    # Drop the temporary 'Hora Cita Formatted' column
    df = df.drop(columns=['Hora Cita Formatted'])


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

    # Convert the column to string and remove '.0' if present
    df['TELEFONO CONFIRMACIÓN'] = df['TELEFONO CONFIRMACIÓN'].astype(str).str.replace(r'\.0$', '', regex=True)


    # After loading and preprocessing, populate the options for the multiselect filters
    all_empresas = df['EMPRESA'].unique().tolist()
    all_ubicaciones = df['Ubicación'].unique().tolist()

    num_files = st.number_input("Number of output files to generate", min_value=1, value=1, key='num_files_input')

    filters = []
    for i in range(num_files):
        st.subheader(f"Filters for Output File {i+1}")
        col1, col2 = st.columns(2)
        with col1:
            selected_empresas = st.multiselect(f"Select Empresa(s) for File {i+1}", options=all_empresas, key=f"empresa_{i}", default=all_empresas)
        with col2:
            selected_ubicaciones = st.multiselect(f"Select Ubicación(s) for File {i+1}", options=all_ubicaciones, key=f"ubicacion_{i}", default=all_ubicaciones)

        # Set default date inputs based on the date range in the dataframe
        # Ensure 'Fecha Programación' is treated as datetime for finding min/max
        df['Fecha Programación_dt'] = pd.to_datetime(df['Fecha Programación'], errors='coerce')
        min_date = df['Fecha Programación_dt'].min()
        max_date = df['Fecha Programación_dt'].max()
        df = df.drop(columns=['Fecha Programación_dt']) # Drop the temporary datetime column


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

            # Apply Empresa filter
            if file_filters['empresas']: # If the list is not empty
                filtered_df = filtered_df[filtered_df['EMPRESA'].isin(file_filters['empresas'])]

            # Apply Ubicación filter
            if file_filters['ubicaciones']: # If the list is not empty
                filtered_df = filtered_df[filtered_df['Ubicación'].isin(file_filters['ubicaciones'])]

            # Apply Date Range filter (using 'Fecha Programación')
            # Ensure 'Fecha Programación' is in datetime format for comparison
            # Re-convert to datetime.date as it might have been converted to datetime.datetime in previous steps
            filtered_df['Fecha Programación_dt'] = pd.to_datetime(filtered_df['Fecha Programación'], errors='coerce').dt.date

            # Convert selected dates to datetime.date for comparison
            start_date_dt = file_filters['start_date']
            end_date_dt = file_filters['end_date']

            filtered_df = filtered_df[
                (filtered_df['Fecha Programación_dt'] >= start_date_dt) &
                (filtered_df['Fecha Programación_dt'] <= end_date_dt)
            ]

            # Drop the temporary datetime column used for filtering
            filtered_df = filtered_df.drop(columns=['Fecha Programación_dt'])


            filtered_dfs.append(filtered_df)

        # Now, generate and download the filtered files
        for i, filtered_df in enumerate(filtered_dfs):
            buffer = io.BytesIO()

            # Define columns for each sheet
            base_confirmacion_cols = ['Numero de Identificación', 'Nombre completo', 'Telefono Movil', 'Telefono Fijo', 'TELEFONO CONFIRMACIÓN', 'Modalidad', 'Especialista', 'Fecha Programación', 'Hora Cita', 'Consultorio', 'Sede', 'Direccion Final', 'Unidad Funcional', 'Actividad Médica', 'CUPS', 'Riesgo', 'Identificador Servicio', 'Estado de Confirmación']
            pacientes_cols = ['Numero de Identificación', 'Nombre completo', 'Telefono Movil', 'Telefono Fijo', 'TELEFONO CONFIRMACIÓN', 'VARIABLE']

            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Write to "Base confirmación" sheet
                # Ensure all base_confirmacion_cols exist in the dataframe before writing
                base_confirmacion_df = filtered_df.reindex(columns=[col for col in base_confirmacion_cols if col in filtered_df.columns])
                base_confirmacion_df.to_excel(writer, sheet_name='Base confirmación', index=False)

                # Write to "Pacientes" sheet
                # Ensure all pacientes_cols exist in the dataframe before writing
                pacientes_df = filtered_df.reindex(columns=[col for col in pacientes_cols if col in filtered_df.columns])
                pacientes_df.to_excel(writer, sheet_name='Pacientes', index=False)


            # Generate filename based on filters
            empresas_str = "_".join(filters[i]['empresas']) if filters[i]['empresas'] else "All_Empresas"
            ubicaciones_str = "_".join(filters[i]['ubicaciones']) if filters[i]['ubicaciones'] else "All_Ubicaciones"
            start_date_str = filters[i]['start_date'].strftime('%Y-%m-%d')
            end_date_str = filters[i]['end_date'].strftime('%Y-%m-%d')

            filename = f"filtered_data_file_{i+1}_{empresas_str}_{ubicaciones_str}_{start_date_str}_to_{end_date_str}.xlsx"

            # Create download button
            st.download_button(
                label=f"Download File {i+1}: {filename}",
                data=buffer.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheet.sheet"
            )

            buffer.close() # Close the buffer after use