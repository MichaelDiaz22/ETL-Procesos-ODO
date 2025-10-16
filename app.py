import streamlit as st
import pandas as pd
import numpy as np
import io

st.title('Excel File Partitioner - Back Office ODO')

uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx', 'xls'])

num_partitions = st.number_input("Enter the number of partitions (number of back office employees)", min_value=1, value=3)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)

        selected_columns = ['Especialidad', 'Centro Atención', 'Unidad Funcional', 'Identificación', 'Nombre Paciente', 'Entidad', 'F. Inicial cita', 'Nom. Actividad', 'Modalidad', 'Tipo cita', 'Estado cita', 'Cod. CUPS', 'CUPS']
        df_subset = df[selected_columns].copy() # Use .copy() to avoid SettingWithCopyWarning

        unidades_funcionales_filter = [
            'CONSULTA ESPECIALIZADA SAN MARCEL',
            'IMAGENES DIAGNOSTICAS SAN MARCEL',
            'PROCEDIMIENTOS MENORES CONSULTA SAN MARCEL',
            'LABORATORIO CLINICO SAN MARCEL'
        ]
        df_filtered = df_subset[df_subset['Unidad Funcional'].isin(unidades_funcionales_filter)].copy() # Use .copy()

        df_filtered['Estado'] = ''
        df_filtered['Observación'] = ''

        estado_cita_filter = ['Asignada', 'PreAsignada']
        df_estado_filtered = df_filtered[df_filtered['Estado cita'].isin(estado_cita_filter)].copy() # Use .copy()

        if num_partitions < 1:
            st.error("Please enter a valid number of partitions (at least 1).")
        else:
            # ORDENAR POR ENTIDAD ANTES DE PARTICIONAR
            df_estado_filtered = df_estado_filtered.sort_values(by='Entidad')
            
            # Obtener identificaciones únicas manteniendo el orden
            unique_identifications = df_estado_filtered['Identificación'].drop_duplicates().values
            num_identifications = len(unique_identifications)

            if num_identifications == 0:
                st.warning("No relevant data found after filtering.")
            else:
                size_of_each_list = num_identifications // num_partitions
                remainder = num_identifications % num_partitions

                list_of_identification_sublists = []
                start = 0
                for i in range(num_partitions):
                    end = start + size_of_each_list + (1 if i < remainder else 0)
                    list_of_identification_sublists.append(unique_identifications[start:end].tolist())
                    start = end

                partitioned_dfs = []
                for i, identification_sublist in enumerate(list_of_identification_sublists):
                    partition_df = df_estado_filtered[df_estado_filtered['Identificación'].isin(identification_sublist)]
                    # Reordenar la partición para mantener el orden por entidad
                    partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
                    partitioned_dfs.append(partition_df)
                    st.write(f"Partition {i+1} created with {len(identification_sublist)} unique identifications and {len(partition_df)} rows.")

                # Generate Excel file in memory
                output_buffer = io.BytesIO()
                with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                    for i, part_df in enumerate(partitioned_dfs):
                        part_df.to_excel(writer, sheet_name=f'Part {i+1}', index=False)

                output_buffer.seek(0)

                st.success("Data processed and partitioned successfully!")

                st.download_button(
                    label="Download Excel file",
                    data=output_buffer,
                    file_name='ReporteConsultaCitas_Partitions.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")

else:
    st.info("Please upload an Excel file to get started.")
