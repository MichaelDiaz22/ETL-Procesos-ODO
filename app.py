import streamlit as st
import pandas as pd
import numpy as np
import io

st.title('Excel File Partitioner - Back Office ODO')

uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx', 'xls'])

# Inicializar variables
unidades_disponibles = []
df_loaded = False

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df_loaded = True
        
        selected_columns = ['Especialidad', 'Centro Atención', 'Unidad Funcional', 'Identificación', 'Nombre Paciente', 'Entidad', 'F. Inicial cita', 'Nom. Actividad', 'Modalidad', 'Tipo cita', 'Estado cita', 'Cod. CUPS', 'CUPS']
        
        # Verificar que las columnas seleccionadas existen en el DataFrame
        columnas_existentes = [col for col in selected_columns if col in df.columns]
        if len(columnas_existentes) != len(selected_columns):
            columnas_faltantes = set(selected_columns) - set(columnas_existentes)
            st.warning(f"Las siguientes columnas no se encontraron en el archivo: {', '.join(columnas_faltantes)}")
        
        df_subset = df[columnas_existentes].copy()
        
        # Identificar automáticamente las unidades funcionales del archivo
        if 'Unidad Funcional' in df_subset.columns:
            unidades_disponibles = sorted(df_subset['Unidad Funcional'].dropna().unique())
            st.success(f"✅ Se identificaron {len(unidades_disponibles)} unidades funcionales en el archivo")
        else:
            st.error("No se encontró la columna 'Unidad Funcional' en el archivo")
            
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
else:
    st.info("Please upload an Excel file to get started.")

# Solo mostrar el número de particiones y selector de unidades si el archivo está cargado
if df_loaded and unidades_disponibles:
    num_partitions = st.number_input("Enter the number of partitions (number of back office employees)", min_value=1, value=3)

    # Selector de unidades funcionales basado en el archivo cargado
    st.subheader("Selecciona las Unidades Funcionales a incluir")
    
    # Ordenar las unidades y seleccionar todas por defecto
    unidades_disponibles_ordenadas = sorted(unidades_disponibles)
    
    unidades_seleccionadas = st.multiselect(
        "Unidades Funcionales encontradas en el archivo:",
        options=unidades_disponibles_ordenadas,
        default=unidades_disponibles_ordenadas,  # Selecciona todas por defecto
        help="Selecciona las unidades funcionales que deseas incluir en el reporte"
    )
    
    # Mostrar información sobre las unidades disponibles
    st.subheader("Información del Archivo")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Total unidades funcionales:** {len(unidades_disponibles)}")
        st.write(f"**Unidades seleccionadas:** {len(unidades_seleccionadas)}")
    with col2:
        st.write(f"**Total registros:** {len(df_subset)}")
        st.write(f"**Total pacientes únicos:** {df_subset['Identificación'].nunique()}")

    # Botón para procesar
    if st.button("Procesar y Particionar Datos"):
        if not unidades_seleccionadas:
            st.warning("Por favor selecciona al menos una unidad funcional")
        else:
            try:
                # Filtrar por unidades funcionales seleccionadas
                df_filtered = df_subset[df_subset['Unidad Funcional'].isin(unidades_seleccionadas)].copy()
                
                st.success(f"✅ Filtrado aplicado: {len(unidades_seleccionadas)} unidad(es) funcional(es) seleccionada(s)")
                
                # Mostrar conteo por unidad funcional seleccionada
                st.subheader("Distribución por Unidad Funcional Seleccionada")
                conteo_unidades = df_filtered['Unidad Funcional'].value_counts()
                
                col1, col2 = st.columns(2)
                with col1:
                    for unidad, count in list(conteo_unidades.items())[:len(conteo_unidades)//2]:
                        st.write(f"• {unidad}: **{count}** registros")
                with col2:
                    for unidad, count in list(conteo_unidades.items())[len(conteo_unidades)//2:]:
                        st.write(f"• {unidad}: **{count}** registros")
                
                # Aplicar filtro de estado de cita
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
                        st.subheader("📊 Distribución de Particiones")
                        
                        for i, identification_sublist in enumerate(list_of_identification_sublists):
                            partition_df = df_estado_filtered[df_estado_filtered['Identificación'].isin(identification_sublist)]
                            # Reordenar la partición para mantener el orden por entidad
                            partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
                            partitioned_dfs.append(partition_df)
                            
                            # Mostrar estadísticas de cada partición
                            with st.expander(f"Partition {i+1} - {len(identification_sublist)} pacientes únicos, {len(partition_df)} registros"):
                                distribucion = partition_df['Unidad Funcional'].value_counts()
                                for unidad, count in distribucion.items():
                                    st.write(f"  - {unidad}: {count} registros")
                                
                                # Mostrar entidades en esta partición
                                entidades = partition_df['Entidad'].unique()
                                st.write(f"  - Entidades: {len(entidades)}")

                        # Generate Excel file in memory
                        output_buffer = io.BytesIO()
                        with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                            for i, part_df in enumerate(partitioned_dfs):
                                # Limitar el nombre de la hoja a 31 caracteres (límite de Excel)
                                sheet_name = f'Part {i+1}'[:31]
                                part_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            
                            # Agregar una hoja de resumen
                            resumen_data = {
                                'Partición': [f'Part {i+1}' for i in range(num_partitions)],
                                'Pacientes Únicos': [len(list_of_identification_sublists[i]) for i in range(num_partitions)],
                                'Total Registros': [len(partitioned_dfs[i]) for i in range(num_partitions)]
                            }
                            
                            # Agregar columnas para cada unidad funcional seleccionada
                            for unidad in unidades_seleccionadas:
                                resumen_data[unidad] = [
                                    len(partitioned_dfs[i][partitioned_dfs[i]['Unidad Funcional'] == unidad]) 
                                    for i in range(num_partitions)
                                ]
                            
                            resumen_df = pd.DataFrame(resumen_data)
                            resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
                            
                            # Agregar hoja con todas las unidades disponibles
                            todas_unidades_df = pd.DataFrame({
                                'Unidades Funcionales en Archivo': unidades_disponibles
                            })
                            todas_unidades_df.to_excel(writer, sheet_name='Todas Unidades', index=False)

                        output_buffer.seek(0)

                        st.success("🎉 Data processed and partitioned successfully!")

                        # Información del archivo a descargar
                        st.info(f"El archivo contiene {num_partitions} particiones y {len(unidades_seleccionadas)} unidades funcionales")

                        st.download_button(
                            label="📥 Download Excel File",
                            data=output_buffer,
                            file_name='ReporteConsultaCitas_Partitions.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            type='primary'
                        )

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")

elif df_loaded and not unidades_disponibles:
    st.error("No se pudieron identificar unidades funcionales en el archivo. Verifica que la columna 'Unidad Funcional' exista y contenga datos.")
