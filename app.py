import streamlit as st
import pandas as pd
import numpy as np
import io

st.title('Excel File Partitioner - Back Office ODO')

uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx', 'xls'])

# Inicializar variables
sedes_disponibles = []
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
        
        # Identificar automáticamente las sedes y unidades funcionales del archivo
        if 'Centro Atención' in df_subset.columns:
            sedes_disponibles = sorted(df_subset['Centro Atención'].dropna().unique())
            st.success(f"✅ Se identificaron {len(sedes_disponibles)} sedes en el archivo")
        else:
            st.warning("No se encontró la columna 'Centro Atención' en el archivo")
            
        if 'Unidad Funcional' in df_subset.columns:
            unidades_disponibles = sorted(df_subset['Unidad Funcional'].dropna().unique())
            st.success(f"✅ Se identificaron {len(unidades_disponibles)} unidades funcionales en el archivo")
        else:
            st.error("No se encontró la columna 'Unidad Funcional' en el archivo")
            
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
else:
    st.info("Please upload an Excel file to get started.")

# Solo mostrar los filtros y número de particiones si el archivo está cargado
if df_loaded and (sedes_disponibles or unidades_disponibles):
    num_partitions = st.number_input("Enter the number of partitions (number of back office employees)", min_value=1, value=3)

    # Filtros por sede y unidad funcional
    st.subheader("Filtros de Datos")
    
    # Selector de sedes
    if sedes_disponibles:
        sedes_seleccionadas = st.multiselect(
            "Sedes disponibles:",
            options=sedes_disponibles,
            default=sedes_disponibles,  # Selecciona todas por defecto
            help="Selecciona las sedes que deseas incluir en el reporte"
        )
    else:
        sedes_seleccionadas = []
        st.info("No hay datos de sedes disponibles para filtrar")
    
    # Selector de unidades funcionales
    if unidades_disponibles:
        unidades_seleccionadas = st.multiselect(
            "Unidades Funcionales disponibles:",
            options=unidades_disponibles,
            default=unidades_disponibles,  # Selecciona todas por defecto
            help="Selecciona las unidades funcionales que deseas incluir en el reporte"
        )
    else:
        unidades_seleccionadas = []
        st.error("No hay unidades funcionales disponibles para filtrar")

    # Mostrar información básica del archivo
    st.subheader("Información del Archivo")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Total sedes:** {len(sedes_disponibles)}")
        st.write(f"**Sedes seleccionadas:** {len(sedes_seleccionadas)}")
    with col2:
        st.write(f"**Total unidades:** {len(unidades_disponibles)}")
        st.write(f"**Unidades seleccionadas:** {len(unidades_seleccionadas)}")
    with col3:
        st.write(f"**Total registros:** {len(df_subset)}")
        st.write(f"**Total pacientes únicos:** {df_subset['Identificación'].nunique()}")

    # Botón para procesar
    if st.button("Procesar y Particionar Datos"):
        if not unidades_seleccionadas:
            st.warning("Por favor selecciona al menos una unidad funcional")
        else:
            try:
                # Aplicar filtros combinados
                df_filtered = df_subset.copy()
                
                # Filtrar por sedes seleccionadas (si hay sedes disponibles)
                if sedes_seleccionadas and 'Centro Atención' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['Centro Atención'].isin(sedes_seleccionadas)]
                    st.success(f"✅ Filtro de sedes aplicado: {len(sedes_seleccionadas)} sede(s) seleccionada(s)")
                
                # Filtrar por unidades funcionales seleccionadas
                if unidades_seleccionadas and 'Unidad Funcional' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['Unidad Funcional'].isin(unidades_seleccionadas)]
                    st.success(f"✅ Filtro de unidades aplicado: {len(unidades_seleccionadas)} unidad(es) funcional(es) seleccionada(s)")
                
                # Mostrar resumen del filtrado
                st.info(f"**Datos después del filtrado:** {len(df_filtered)} registros, {df_filtered['Identificación'].nunique()} pacientes únicos")
                
                # Aplicar filtro de estado de cita
                df_filtered['Estado'] = ''
                df_filtered['Observación'] = ''

                estado_cita_filter = ['Asignada', 'PreAsignada']
                df_estado_filtered = df_filtered[df_filtered['Estado cita'].isin(estado_cita_filter)].copy()

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
                        
                        # Mostrar resumen detallado de particiones
                        st.subheader("📊 Resumen Detallado de Particiones")
                        for i, identification_sublist in enumerate(list_of_identification_sublists):
                            partition_df = df_estado_filtered[df_estado_filtered['Identificación'].isin(identification_sublist)]
                            # Reordenar la partición para mantener el orden por entidad
                            partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
                            partitioned_dfs.append(partition_df)
                            
                            # Mostrar información detallada de cada partición
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**Partition {i+1}**")
                                st.write(f"Pacientes: {len(identification_sublist)}")
                                st.write(f"Registros: {len(partition_df)}")
                            with col2:
                                # Contar sedes en esta partición
                                if 'Centro Atención' in partition_df.columns:
                                    sedes_partition = partition_df['Centro Atención'].nunique()
                                    st.write(f"Sedes: {sedes_partition}")
                                # Contar unidades en esta partición
                                unidades_partition = partition_df['Unidad Funcional'].nunique()
                                st.write(f"Unidades: {unidades_partition}")
                            with col3:
                                # Mostrar entidades en esta partición
                                entidades_partition = partition_df['Entidad'].nunique()
                                st.write(f"Entidades: {entidades_partition}")

                        # Generate Excel file in memory
                        output_buffer = io.BytesIO()
                        with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                            for i, part_df in enumerate(partitioned_dfs):
                                # Limitar el nombre de la hoja a 31 caracteres (límite de Excel)
                                sheet_name = f'Part {i+1}'[:31]
                                part_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            
                            # Agregar una hoja de resumen detallado
                            resumen_data = {
                                'Partición': [f'Part {i+1}' for i in range(num_partitions)],
                                'Pacientes Únicos': [len(list_of_identification_sublists[i]) for i in range(num_partitions)],
                                'Total Registros': [len(partitioned_dfs[i]) for i in range(num_partitions)]
                            }
                            
                            # Agregar columnas para cada sede seleccionada
                            if sedes_seleccionadas:
                                for sede in sedes_seleccionadas:
                                    resumen_data[f'Sede_{sede}'] = [
                                        len(partitioned_dfs[i][partitioned_dfs[i]['Centro Atención'] == sede]) 
                                        for i in range(num_partitions)
                                    ]
                            
                            # Agregar columnas para cada unidad funcional seleccionada
                            for unidad in unidades_seleccionadas:
                                resumen_data[f'Unidad_{unidad}'] = [
                                    len(partitioned_dfs[i][partitioned_dfs[i]['Unidad Funcional'] == unidad]) 
                                    for i in range(num_partitions)
                                ]
                            
                            resumen_df = pd.DataFrame(resumen_data)
                            resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
                            
                            # Agregar hoja con configuración de filtros aplicados
                            filtros_aplicados = pd.DataFrame({
                                'Parámetro': ['Sedes Seleccionadas', 'Unidades Funcionales Seleccionadas', 'Número de Particiones'],
                                'Valor': [', '.join(map(str, sedes_seleccionadas)) if sedes_seleccionadas else 'Todas', 
                                         ', '.join(map(str, unidades_seleccionadas)), 
                                         str(num_partitions)]
                            })
                            filtros_aplicados.to_excel(writer, sheet_name='Filtros Aplicados', index=False)

                        output_buffer.seek(0)

                        st.success("🎉 Data processed and partitioned successfully!")

                        # Información del archivo a descargar
                        st.info(f"El archivo contiene:")
                        st.info(f"- {num_partitions} particiones")
                        st.info(f"- {len(sedes_seleccionadas)} sedes seleccionadas")
                        st.info(f"- {len(unidades_seleccionadas)} unidades funcionales seleccionadas")
                        st.info(f"- {len(df_estado_filtered)} registros totales después de filtros")

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
