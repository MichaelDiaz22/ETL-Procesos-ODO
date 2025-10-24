import streamlit as st
import pandas as pd
import numpy as np
import io

st.title('Excel File Partitioner - Back Office ODO')

uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx', 'xls'])

num_partitions = st.number_input("Enter the number of partitions (number of back office employees)", min_value=1, value=3)

# Lista de todas las unidades funcionales disponibles
todas_unidades_funcionales = [
    'CONSULTA ESPECIALIZADA SAN MARCEL',
    'IMAGENES DIAGNOSTICAS SAN MARCEL',
    'PROCEDIMIENTOS MENORES CONSULTA SAN MARCEL',
    'LABORATORIO CLINICO SAN MARCEL'
]

# Selector de unidades funcionales
st.subheader("Selecciona las Unidades Funcionales a incluir")
unidades_seleccionadas = st.multiselect(
    "Unidades Funcionales:",
    options=todas_unidades_funcionales,
    default=todas_unidades_funcionales,  # Por defecto selecciona todas
    help="Selecciona las unidades funcionales que deseas incluir en el reporte"
)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)

        selected_columns = ['Especialidad', 'Centro Atención', 'Unidad Funcional', 'Identificación', 'Nombre Paciente', 'Entidad', 'F. Inicial cita', 'Nom. Actividad', 'Modalidad', 'Tipo cita', 'Estado cita', 'Cod. CUPS', 'CUPS']
        
        # Verificar que las columnas seleccionadas existen en el DataFrame
        columnas_existentes = [col for col in selected_columns if col in df.columns]
        if len(columnas_existentes) != len(selected_columns):
            columnas_faltantes = set(selected_columns) - set(columnas_existentes)
            st.warning(f"Las siguientes columnas no se encontraron en el archivo: {', '.join(columnas_faltantes)}")
        
        df_subset = df[columnas_existentes].copy() # Use .copy() to avoid SettingWithCopyWarning

        # Mostrar información sobre las unidades funcionales disponibles
        unidades_en_archivo = df_subset['Unidad Funcional'].unique()
        st.info(f"Unidades funcionales encontradas en el archivo: {len(unidades_en_archivo)}")
        
        # Filtrar por unidades funcionales seleccionadas
        if unidades_seleccionadas:
            df_filtered = df_subset[df_subset['Unidad Funcional'].isin(unidades_seleccionadas)].copy()
            
            st.success(f"Filtrado aplicado: {len(unidades_seleccionadas)} unidad(es) funcional(es) seleccionada(s)")
            st.write(f"**Unidades seleccionadas:** {', '.join(unidades_seleccionadas)}")
            
            # Mostrar conteo por unidad funcional
            st.subheader("Conteo por Unidad Funcional:")
            conteo_unidades = df_filtered['Unidad Funcional'].value_counts()
            for unidad, count in conteo_unidades.items():
                st.write(f"- {unidad}: {count} registros")
            
        else:
            st.warning("Por favor selecciona al menos una unidad funcional")
            df_filtered = pd.DataFrame()  # DataFrame vacío

        if not df_filtered.empty:
            df_filtered['Estado'] = ''
            df_filtered['Observación'] = ''

            estado_cita_filter = ['Asignada', 'PreAsignada']
            df_estado_filtered = df_filtered[df_filtered['Estado cita'].isin(estado_cita_filter)].copy()

            if num_partitions < 1:
                st.error("Please enter a valid number of partitions (at least 1).")
            else:
                # Mostrar resumen antes de particionar
                st.subheader("Resumen antes de particionar:")
                st.write(f"- Total de registros filtrados: {len(df_estado_filtered)}")
                st.write(f"- Total de pacientes únicos: {df_estado_filtered['Identificación'].nunique()}")
                st.write(f"- Número de particiones: {num_partitions}")

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
                        
                        # Mostrar estadísticas de cada partición
                        st.write(f"**Partition {i+1}**: {len(identification_sublist)} pacientes únicos, {len(partition_df)} registros totales")
                        
                        # Mostrar distribución por unidad funcional en cada partición
                        distribucion = partition_df['Unidad Funcional'].value_counts()
                        for unidad, count in distribucion.items():
                            st.write(f"  - {unidad}: {count} registros")

                    # Generate Excel file in memory
                    output_buffer = io.BytesIO()
                    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                        for i, part_df in enumerate(partitioned_dfs):
                            part_df.to_excel(writer, sheet_name=f'Part {i+1}', index=False)
                        
                        # Agregar una hoja de resumen
                        resumen_data = {
                            'Partición': [f'Part {i+1}' for i in range(num_partitions)],
                            'Pacientes Únicos': [len(list_of_identification_sublists[i]) for i in range(num_partitions)],
                            'Total Registros': [len(partitioned_dfs[i]) for i in range(num_partitions)]
                        }
                        for unidad in unidades_seleccionadas:
                            resumen_data[unidad] = [
                                len(partitioned_dfs[i][partitioned_dfs[i]['Unidad Funcional'] == unidad]) 
                                for i in range(num_partitions)
                            ]
                        
                        resumen_df = pd.DataFrame(resumen_data)
                        resumen_df.to_excel(writer, sheet_name='Resumen', index=False)

                    output_buffer.seek(0)

                    st.success("Data processed and partitioned successfully!")

                    st.download_button(
                        label="Download Excel file",
                        data=output_buffer,
                        file_name='ReporteConsultaCitas_Partitions.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
        else:
            if unidades_seleccionadas:
                st.warning("No se encontraron registros para las unidades funcionales seleccionadas")

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")

else:
    st.info("Please upload an Excel file to get started.")
