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
    
    # MOSTRAR INFORMACIÓN DIAGNÓSTICA DEL DATAFRAME ORIGINAL
    st.subheader("Información del DataFrame Original")
    st.write(f"Número total de filas: {len(df)}")
    st.write(f"Columnas disponibles: {list(df.columns)}")
    
    if 'EMPRESA' in df.columns:
        st.write(f"Empresas únicas: {df['EMPRESA'].unique()}")
    if 'Ubicación' in df.columns:
        st.write(f"Ubicaciones únicas: {df['Ubicación'].unique()}")
    if 'Fecha Programación' in df.columns:
        st.write(f"Rango de fechas en 'Fecha Programación': {df['Fecha Programación'].min()} to {df['Fecha Programación'].max()}")

    # Preprocessing steps
    # Sort the DataFrame by 'Numero de Identificación' in ascending order
    df = df.sort_values(by='Numero de Identificación', ascending=True).reset_index(drop=True)

    # Create a new column 'Ubicación' based on the 'Consultorio' column
    df['Ubicación'] = df['Consultorio'].apply(lambda x: 'Procedimiento' if pd.isna(x) or str(x).strip() == '' else 'Consulta')

    # Convert 'Fecha Cita' and 'Hora Cita' to datetime objects
    df['Fecha Hora Cita'] = pd.to_datetime(df['Fecha Cita'].astype(str) + ' ' + df['Hora Cita'].astype(str), errors='coerce')

    # Sort the DataFrame by the grouping columns and the new datetime column for 'Identificador Servicio'
    df_sorted_id = df.sort_values(by=['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación', 'Fecha Hora Cita'])

    # Create a new column 'Identificador Servicio'
    df_sorted_id['Identificador Servicio'] = 'unico'

    # Identify groups with duplicate combinations
    duplicates_group_id = df_sorted_id.duplicated(subset=['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación'], keep=False)

    # Within these duplicate groups, identify the first occurrence based on 'Fecha Hora Cita'
    df_sorted_id.loc[duplicates_group_id, 'occurrence'] = df_sorted_id[duplicates_group_id].groupby(['Numero de Identificación', 'Fecha Cita', 'Sede', 'Ubicación']).cumcount()

    # Mark the first occurrence as 'primer servicio'
    df_sorted_id.loc[duplicates_group_id & (df_sorted_id['occurrence'] == 0), 'Identificador Servicio'] = 'primer servicio'
    # Mark subsequent occurrences as 'servicio posterior'
    df_sorted_id.loc[duplicates_group_id & (df_sorted_id['occurrence'] > 0), 'Identificador Servicio'] = 'servicio posterior'

    # Drop the temporary 'occurrence' column
    df_sorted_id = df_sorted_id.drop(columns=['occurrence'])

    # Update the original DataFrame with the new 'Identificador Servicio' column
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
    df['Fecha Programación'] = pd.to_datetime(df['Fecha Programación'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
    df['Hora Cita'] = df['Hora Cita'].astype(str)
    df['Especialista'] = df['Especialista'].astype(str)
    df['Direccion Final'] = df['Direccion Final'].astype(str)
    df['Ubicación'] = df['Ubicación'].astype(str)
    df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)

    # Convert 'Hora Cita' to datetime objects to format it to 12-hour format
    df['Hora Cita Formatted'] = pd.to_datetime(df['Hora Cita'], errors='coerce').dt.strftime('%I:%M %p')
    df['Hora Cita Formatted'] = df['Hora Cita Formatted'].fillna('')

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

        # Set default date inputs based on the date range in the dataframe
        df['Fecha Programación_dt'] = pd.to_datetime(df['Fecha Programación'], errors='coerce')
        min_date = df['Fecha Programación_dt'].min()
        max_date = df['Fecha Programación_dt'].max()
        
        # MOSTRAR INFORMACIÓN DE FECHAS PARA DIAGNÓSTICO
        st.write(f"📅 Rango de fechas en los datos: {min_date} a {max_date}")
        
        df = df.drop(columns=['Fecha Programación_dt'])

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

            # DIAGNÓSTICO DETALLADO DE FILTROS
            st.subheader(f"🔍 Diagnóstico - Filtros para Archivo {i+1}")
            st.write(f"Empresas seleccionadas: {file_filters['empresas']}")
            st.write(f"Ubicaciones seleccionadas: {file_filters['ubicaciones']}")
            st.write(f"Rango de fechas: {file_filters['start_date']} a {file_filters['end_date']}")

            # Start with a boolean mask that includes all rows
            combined_filter_mask = pd.Series(True, index=filtered_df.index)

            # Apply Empresa filter
            empresa_rows_before = len(filtered_df)
            if file_filters['empresas']:
                empresa_mask = filtered_df['EMPRESA'].isin(file_filters['empresas'])
                combined_filter_mask = combined_filter_mask & empresa_mask
                empresa_rows_after = empresa_mask.sum()
                st.write(f"📊 Filas después de filtro de empresa: {empresa_rows_after}/{empresa_rows_before}")

            # Apply Ubicación filter
            ubicacion_rows_before = len(filtered_df)
            if file_filters['ubicaciones']:
                ubicacion_mask = filtered_df['Ubicación'].isin(file_filters['ubicaciones'])
                combined_filter_mask = combined_filter_mask & ubicacion_mask
                ubicacion_rows_after = ubicacion_mask.sum()
                st.write(f"📍 Filas después de filtro de ubicación: {ubicacion_rows_after}/{ubicacion_rows_before}")

            # Apply Date Range filter
            filtered_df['Fecha Programación_dt'] = pd.to_datetime(filtered_df['Fecha Programación'], errors='coerce')

            # Convert selected dates to pandas Timestamps for consistent comparison
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
                st.info("💡 **Sugerencias para solucionar:**")
                st.info("- Verifica que los nombres de empresas coincidan exactamente")
                st.info("- Revisa que las ubicaciones seleccionadas existan en los datos")
                st.info("- Asegúrate de que el rango de fechas incluya datos existentes")
                continue
                
            buffer = io.BytesIO()

            # Verificar y seleccionar columnas existentes
            base_confirmacion_cols = ['TELEFONO CONFIRMACIÓN', 'VARIABLE']
            pacientes_cols = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 'Fecha Programación', 'Hora Cita', 'Actividad Médica']

            # Crear 'Nombre completo' si no existe
            if 'Nombre completo' not in filtered_df.columns:
                filtered_df['Nombre completo'] = filtered_df['Nombres'].astype(str) + ' ' + filtered_df['Apellidos'].astype(str)

            # Asegurar que 'Hora Cita Formatted' esté disponible
            if 'Hora Cita Formatted' not in filtered_df.columns:
                filtered_df['Hora Cita Formatted'] = pd.to_datetime(filtered_df['Hora Cita'], errors='coerce').dt.strftime('%I:%M %p').fillna('')
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_df.loc[filtered_df['Unidad Funcional'] == 'INVESTIGACION MARAYA', 'Hora Cita Formatted'] = '-'

            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Para Base confirmación
                base_confirmacion_cols_existing = [col for col in base_confirmacion_cols if col in filtered_df.columns]
                if base_confirmacion_cols_existing:
                    base_confirmacion_df = filtered_df[base_confirmacion_cols_existing]
                    base_confirmacion_df.to_excel(writer, sheet_name='Base confirmación', index=False)
                    st.success(f"✅ Hoja 'Base confirmación' creada con {len(base_confirmacion_df)} filas")
                else:
                    st.warning(f"⚠️ No se encontraron las columnas necesarias para 'Base confirmación'")

                # Para Pacientes
                pacientes_cols_existing = [col for col in pacientes_cols if col in filtered_df.columns]
                
                # Manejar el renombrado de Hora Cita
                pacientes_df = filtered_df[pacientes_cols_existing].copy()
                if 'Hora Cita Formatted' in filtered_df.columns and 'Hora Cita' not in pacientes_df.columns:
                    pacientes_df['Hora Cita'] = filtered_df['Hora Cita Formatted']

                if len(pacientes_df.columns) > 0:
                    pacientes_df.to_excel(writer, sheet_name='Pacientes', index=False)
                    st.success(f"✅ Hoja 'Pacientes' creada con {len(pacientes_df)} filas")
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
