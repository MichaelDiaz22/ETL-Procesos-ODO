import streamlit as st
import pandas as pd
import numpy as np
import io
from collections import defaultdict

st.title('Excel File Partitioner - Back Office ODO')

uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx', 'xls'])

# Inicializar variables
unidades_disponibles = []
df_loaded = False

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df_loaded = True
        
        selected_columns = ['Especialidad', 'Profesional', 'Centro Atención', 'Unidad Funcional', 'Identificación', 'Nombre Paciente', 'Entidad', 'F. Inicial cita', 'Nom. Actividad', 'Modalidad', 'Tipo cita', 'Estado cita', 'Cod. CUPS', 'CUPS']
        
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

# Función para partición equitativa
def particion_equitativa(df_filtered, num_partitions, unidades_seleccionadas):
    """Divide los pacientes asegurando que cada partición tenga la misma cantidad de pacientes de cada unidad funcional"""
    
    # Diccionario para almacenar pacientes por unidad funcional
    pacientes_por_unidad = {}
    
    for unidad in unidades_seleccionadas:
        df_unidad = df_filtered[df_filtered['Unidad Funcional'] == unidad]
        pacientes_unidad = df_unidad['Identificación'].drop_duplicates().values
        pacientes_por_unidad[unidad] = pacientes_unidad
    
    # Inicializar listas para cada partición
    particiones = [[] for _ in range(num_partitions)]
    
    # Distribuir pacientes de cada unidad funcional equitativamente
    for unidad, pacientes in pacientes_por_unidad.items():
        num_pacientes = len(pacientes)
        
        # Calcular cuántos pacientes por partición
        pacientes_por_particion = num_pacientes // num_partitions
        resto = num_pacientes % num_partitions
        
        # Distribuir pacientes
        idx = 0
        for i in range(num_partitions):
            num_asignar = pacientes_por_particion + (1 if i < resto else 0)
            if num_asignar > 0 and idx < num_pacientes:
                particiones[i].extend(pacientes[idx:idx + num_asignar])
                idx += num_asignar
    
    # Crear DataFrames de partición
    partitioned_dfs = []
    for i, pacientes_particion in enumerate(particiones):
        partition_df = df_filtered[df_filtered['Identificación'].isin(pacientes_particion)]
        partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
        partitioned_dfs.append(partition_df)
    
    return partitioned_dfs, [len(p) for p in particiones]

# Función para partición personalizada
def particion_personalizada(df_filtered, num_partitions, unidades_seleccionadas):
    """Permite asignar unidades funcionales específicas a cada partición"""
    
    st.subheader("🔧 Configuración de Partición Personalizada")
    st.info("Para cada partición, selecciona las unidades funcionales que deseas asignar. Si una unidad aparece en múltiples particiones, sus pacientes se dividirán equitativamente entre esas particiones.")
    
    # Diccionario para almacenar las unidades seleccionadas por partición
    unidades_por_particion = {}
    
    for i in range(num_partitions):
        st.markdown(f"**Partición {i+1}**")
        unidades_particion = st.multiselect(
            f"Selecciona unidades funcionales para la Partición {i+1}:",
            options=unidades_seleccionadas,
            key=f"particion_{i}",
            help="Selecciona una o más unidades funcionales para esta partición"
        )
        unidades_por_particion[i] = unidades_particion
    
    if st.button("Confirmar Asignación y Generar Particiones"):
        # Verificar que todas las unidades hayan sido asignadas al menos una vez
        todas_unidades_asignadas = set()
        for unidades in unidades_por_particion.values():
            todas_unidades_asignadas.update(unidades)
        
        unidades_no_asignadas = set(unidades_seleccionadas) - todas_unidades_asignadas
        if unidades_no_asignadas:
            st.warning(f"⚠️ Las siguientes unidades funcionales no fueron asignadas a ninguna partición: {', '.join(unidades_no_asignadas)}")
            return None, None
        
        # Para cada unidad funcional, determinar en qué particiones aparece
        apariciones_por_unidad = defaultdict(list)
        for particion_id, unidades in unidades_por_particion.items():
            for unidad in unidades:
                apariciones_por_unidad[unidad].append(particion_id)
        
        # Obtener pacientes por unidad funcional
        pacientes_por_unidad = {}
        for unidad in unidades_seleccionadas:
            df_unidad = df_filtered[df_filtered['Unidad Funcional'] == unidad]
            pacientes_unidad = df_unidad['Identificación'].drop_duplicates().values
            pacientes_por_unidad[unidad] = pacientes_unidad
        
        # Inicializar listas para cada partición
        particiones = [[] for _ in range(num_partitions)]
        
        # Distribuir pacientes según las reglas
        for unidad, particiones_destino in apariciones_por_unidad.items():
            pacientes = pacientes_por_unidad.get(unidad, [])
            num_pacientes = len(pacientes)
            num_particiones_asignadas = len(particiones_destino)
            
            if num_particiones_asignadas == 0:
                continue
            elif num_particiones_asignadas == 1:
                # Si aparece en una sola partición, asignar todos los pacientes a esa partición
                particion_id = particiones_destino[0]
                particiones[particion_id].extend(pacientes)
            else:
                # Si aparece en múltiples particiones, dividir pacientes equitativamente
                pacientes_por_particion = num_pacientes // num_particiones_asignadas
                resto = num_pacientes % num_particiones_asignadas
                
                idx = 0
                for j, particion_id in enumerate(particiones_destino):
                    num_asignar = pacientes_por_particion + (1 if j < resto else 0)
                    if num_asignar > 0 and idx < num_pacientes:
                        particiones[particion_id].extend(pacientes[idx:idx + num_asignar])
                        idx += num_asignar
        
        # Crear DataFrames de partición
        partitioned_dfs = []
        for i, pacientes_particion in enumerate(particiones):
            if len(pacientes_particion) > 0:
                partition_df = df_filtered[df_filtered['Identificación'].isin(pacientes_particion)]
                partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
                partitioned_dfs.append(partition_df)
            else:
                # Partición vacía
                partitioned_dfs.append(pd.DataFrame())
        
        return partitioned_dfs, [len(p) for p in particiones]
    
    return None, None

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
        default=unidades_disponibles_ordenadas,
        help="Selecciona las unidades funcionales que deseas incluir en el reporte"
    )
    
    # Nuevo selector de tipo de partición
    st.subheader("Selecciona el tipo de partición")
    tipo_particion = st.radio(
        "Tipo de partición:",
        options=["Partición de unidades funcionales en cantidades iguales", "Partición personalizada"],
        help="Selecciona cómo deseas distribuir las unidades funcionales entre las particiones"
    )
    
    # Botón para procesar
    if st.button("Procesar y Particionar Datos"):
        if not unidades_seleccionadas:
            st.warning("Por favor selecciona al menos una unidad funcional")
        else:
            try:
                # Filtrar por unidades funcionales seleccionadas
                df_filtered = df_subset[df_subset['Unidad Funcional'].isin(unidades_seleccionadas)].copy()
                
                # ELIMINAR REGISTROS DONDE 'Nom. Actividad' SEA 'ADMINISTRACION RADIOTERAPIA' (MÚLTIPLES VARIACIONES)
                if 'Nom. Actividad' in df_filtered.columns:
                    # Contar registros antes de eliminar
                    registros_antes = len(df_filtered)
                    
                    # Crear una máscara para identificar TODAS las variaciones de ADMINISTRACION RADIOTERAPIA
                    mask_radioterapia = (
                        df_filtered['Nom. Actividad'].str.contains('ADMINISTRACION RADIOTERAPIA', case=False, na=False) |
                        df_filtered['Nom. Actividad'].str.contains('CONSULTA DE TERMINACION DE RADIOTERAPIA', case=False, na=False)
                    )
                    
                    # Aplicar el filtro inverso (mantener solo los que NO son radioterapia)
                    df_filtered = df_filtered[~mask_radioterapia]
                    
                    # Contar registros después de eliminar
                    registros_despues = len(df_filtered)
                    registros_eliminados = registros_antes - registros_despues
                    
                    if registros_eliminados > 0:
                        st.success(f"✅ Se eliminaron {registros_eliminados} registros relacionados con RADIOTERAPIA")
                
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
                    
                    # Seleccionar método de partición
                    if tipo_particion == "Partición de unidades funcionales en cantidades iguales":
                        st.info("📊 Generando particiones equitativas por unidad funcional...")
                        partitioned_dfs, pacientes_por_particion = particion_equitativa(
                            df_estado_filtered, num_partitions, unidades_seleccionadas
                        )
                    else:  # Partición personalizada
                        partitioned_dfs, pacientes_por_particion = particion_personalizada(
                            df_estado_filtered, num_partitions, unidades_seleccionadas
                        )
                        
                        # Si no se confirmó la asignación, detener el proceso
                        if partitioned_dfs is None:
                            st.stop()
                    
                    # Verificar que se generaron particiones
                    if not partitioned_dfs or all(len(df) == 0 for df in partitioned_dfs):
                        st.warning("No se pudieron generar particiones. Verifica la asignación de unidades funcionales.")
                        st.stop()
                    
                    # Mostrar resumen de particiones
                    st.subheader("📊 Resumen de Particiones")
                    for i, partition_df in enumerate(partitioned_dfs):
                        num_pacientes = pacientes_por_particion[i] if i < len(pacientes_por_particion) else 0
                        st.write(f"**Partition {i+1}**: {num_pacientes} pacientes únicos, {len(partition_df)} registros")
                        
                        # Mostrar desglose por unidad funcional
                        if len(partition_df) > 0 and 'Unidad Funcional' in partition_df.columns:
                            unidades_en_particion = partition_df['Unidad Funcional'].value_counts()
                            for unidad, count in unidades_en_particion.items():
                                pacientes_unidad = partition_df[partition_df['Unidad Funcional'] == unidad]['Identificación'].nunique()
                                st.write(f"   - {unidad}: {pacientes_unidad} pacientes, {count} registros")

                    # Generate Excel file in memory
                    output_buffer = io.BytesIO()
                    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                        for i, part_df in enumerate(partitioned_dfs):
                            # Limitar el nombre de la hoja a 31 caracteres (límite de Excel)
                            sheet_name = f'Part {i+1}'[:31]
                            
                            # Asegurar que todas las columnas estén presentes en el orden correcto
                            columnas_a_exportar = [col for col in columnas_existentes if col in part_df.columns]
                            columnas_adicionales = ['Estado', 'Observación']
                            columnas_finales = columnas_a_exportar + [col for col in columnas_adicionales if col in part_df.columns]
                            
                            # Reordenar el DataFrame para la exportación
                            part_df_export = part_df[columnas_finales] if len(part_df) > 0 else pd.DataFrame(columns=columnas_finales)
                            part_df_export.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Agregar una hoja de resumen
                        resumen_data = {
                            'Partición': [f'Part {i+1}' for i in range(num_partitions)],
                            'Pacientes Únicos': pacientes_por_particion,
                            'Total Registros': [len(partitioned_dfs[i]) for i in range(num_partitions)]
                        }
                        
                        # Agregar columnas para cada unidad funcional seleccionada
                        for unidad in unidades_seleccionadas:
                            resumen_data[unidad] = [
                                len(partitioned_dfs[i][partitioned_dfs[i]['Unidad Funcional'] == unidad]) if len(partitioned_dfs[i]) > 0 else 0
                                for i in range(num_partitions)
                            ]
                        
                        resumen_df = pd.DataFrame(resumen_data)
                        resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
                        
                        # Agregar hoja de configuración para partición personalizada
                        if tipo_particion == "Partición personalizada":
                            config_data = []
                            # Obtener la configuración del session state o recrearla
                            for i in range(num_partitions):
                                # Recuperar las unidades seleccionadas para cada partición
                                unidades_key = f"particion_{i}"
                                if unidades_key in st.session_state:
                                    for unidad in st.session_state[unidades_key]:
                                        config_data.append({
                                            'Partición': f'Part {i+1}',
                                            'Unidad Funcional': unidad
                                        })
                            
                            if config_data:
                                config_df = pd.DataFrame(config_data)
                                config_df.to_excel(writer, sheet_name='Configuración_Particiones', index=False)

                    output_buffer.seek(0)

                    st.success("🎉 Data processed and partitioned successfully!")
                    
                    st.download_button(
                        label="📥 Download Excel File",
                        data=output_buffer,
                        file_name='ReporteConsultaCitas_Partitions.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        type='primary'
                    )

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
                st.exception(e)

elif df_loaded and not unidades_disponibles:
    st.error("No se pudieron identificar unidades funcionales en el archivo. Verifica que la columna 'Unidad Funcional' exista y contenga datos.")
