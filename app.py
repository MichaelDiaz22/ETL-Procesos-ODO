import streamlit as st
import pandas as pd
import numpy as np
import io
from collections import defaultdict
import random

st.title('Excel File Partitioner - Back Office ODO')

# Inicializar variables de sesión para mantener el estado
if 'configuracion_personalizada' not in st.session_state:
    st.session_state.configuracion_personalizada = {}
if 'tipo_particion' not in st.session_state:
    st.session_state.tipo_particion = "Partición equitativa por paciente"

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

def particion_equitativa_por_paciente(df_filtered, num_partitions, unidades_seleccionadas, semilla=42):
    """
    Divide los pacientes asegurando que:
    1. Cada paciente aparezca en UNA SOLA partición
    2. Las particiones tengan cantidades EQUITATIVAS de pacientes
    3. TODOS los registros de un paciente (de todas sus unidades funcionales) vayan a la misma partición
    """
    
    # Establecer semilla para reproducibilidad
    random.seed(semilla)
    
    # Obtener TODOS los pacientes únicos del conjunto filtrado
    todos_los_pacientes = df_filtered['Identificación'].drop_duplicates().tolist()
    
    # Mezclar los pacientes para distribución aleatoria
    pacientes_mezclados = todos_los_pacientes.copy()
    random.shuffle(pacientes_mezclados)
    
    # Calcular cuántos pacientes por partición
    num_pacientes = len(pacientes_mezclados)
    pacientes_por_particion = num_pacientes // num_partitions
    resto = num_pacientes % num_partitions
    
    # Distribuir pacientes equitativamente
    asignacion_pacientes = {}
    idx = 0
    for i in range(num_partitions):
        num_asignar = pacientes_por_particion + (1 if i < resto else 0)
        if num_asignar > 0 and idx < num_pacientes:
            pacientes_asignados = pacientes_mezclados[idx:idx + num_asignar]
            asignacion_pacientes[i] = pacientes_asignados
            idx += num_asignar
        else:
            asignacion_pacientes[i] = []
    
    # Crear DataFrames para cada partición con TODOS los registros de los pacientes asignados
    partitioned_dfs = []
    pacientes_por_particion_list = []
    
    for i in range(num_partitions):
        pacientes_particion = asignacion_pacientes[i]
        
        if len(pacientes_particion) > 0:
            # Tomar TODOS los registros de estos pacientes (de todas las unidades funcionales)
            partition_df = df_filtered[df_filtered['Identificación'].isin(pacientes_particion)]
            partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
            partitioned_dfs.append(partition_df)
            pacientes_por_particion_list.append(len(pacientes_particion))
        else:
            partitioned_dfs.append(pd.DataFrame())
            pacientes_por_particion_list.append(0)
    
    return partitioned_dfs, pacientes_por_particion_list

def procesar_particion_personalizada(df_filtered, num_partitions, unidades_seleccionadas, configuracion, semilla=42):
    """
    Procesa la partición personalizada según la configuración guardada.
    
    Lógica:
    1. Cada unidad funcional se asigna a UNA O MÁS particiones (según configuración)
    2. Los pacientes de cada unidad se dividen EQUITATIVAMENTE entre las particiones donde está asignada
    3. Cada paciente aparece en UNA SOLA partición (si tiene múltiples unidades, se asigna a la primera)
    4. TODOS los registros del paciente van a la misma partición
    """
    
    random.seed(semilla)
    
    # PASO 1: Asignar cada paciente a UNA SOLA unidad funcional (la primera que aparece en el orden de selección)
    pacientes_asignados = {}
    for unidad in unidades_seleccionadas:
        df_unidad = df_filtered[df_filtered['Unidad Funcional'] == unidad]
        pacientes_unidad = df_unidad['Identificación'].drop_duplicates().tolist()
        
        for paciente in pacientes_unidad:
            if paciente not in pacientes_asignados:
                pacientes_asignados[paciente] = unidad
    
    # PASO 2: Agrupar pacientes por su unidad funcional principal
    pacientes_por_unidad = defaultdict(list)
    for paciente, unidad in pacientes_asignados.items():
        pacientes_por_unidad[unidad].append(paciente)
    
    # PASO 3: Determinar en qué particiones aparece cada unidad según la configuración
    unidades_por_particion = defaultdict(list)
    for particion_id, unidades in configuracion.items():
        for unidad in unidades:
            if unidad in unidades_seleccionadas:
                unidades_por_particion[unidad].append(particion_id)
    
    # Verificar que todas las unidades seleccionadas tengan al menos una partición asignada
    unidades_sin_particion = set(unidades_seleccionadas) - set(unidades_por_particion.keys())
    if unidades_sin_particion:
        st.error(f"Error: Las siguientes unidades no tienen particiones asignadas: {', '.join(unidades_sin_particion)}")
        return [], []
    
    # PASO 4: Inicializar asignación de pacientes a particiones
    asignacion_pacientes = {i: [] for i in range(num_partitions)}
    
    # PASO 5: Para cada unidad, distribuir sus pacientes EQUITATIVAMENTE entre las particiones asignadas
    for unidad, pacientes in pacientes_por_unidad.items():
        particiones_destino = unidades_por_particion.get(unidad, [])
        num_pacientes = len(pacientes)
        num_particiones = len(particiones_destino)
        
        if num_pacientes == 0:
            continue
        
        if num_particiones == 1:
            # Si aparece en UNA sola partición, TODOS los pacientes van a esa partición
            particion_id = particiones_destino[0]
            asignacion_pacientes[particion_id].extend(pacientes)
        else:
            # Si aparece en MÚLTIPLES particiones, dividir pacientes EQUITATIVAMENTE
            pacientes_mezclados = pacientes.copy()
            random.shuffle(pacientes_mezclados)
            
            # Calcular distribución equitativa
            pacientes_por_particion = num_pacientes // num_particiones
            resto = num_pacientes % num_particiones
            
            # Distribuir pacientes entre las particiones asignadas
            idx = 0
            particiones_ordenadas = sorted(particiones_destino)
            for j, particion_id in enumerate(particiones_ordenadas):
                # Asignar pacientes extra a las primeras particiones (las de menor índice)
                num_asignar = pacientes_por_particion + (1 if j < resto else 0)
                if num_asignar > 0 and idx < num_pacientes:
                    pacientes_a_asignar = pacientes_mezclados[idx:idx + num_asignar]
                    asignacion_pacientes[particion_id].extend(pacientes_a_asignar)
                    idx += num_asignar
    
    # PASO 6: Crear DataFrames para cada partición con TODOS los registros de los pacientes asignados
    partitioned_dfs = []
    pacientes_por_particion_list = []
    
    for i in range(num_partitions):
        pacientes_particion = asignacion_pacientes[i]
        pacientes_unicos = list(set(pacientes_particion))  # Eliminar duplicados
        
        if len(pacientes_unicos) > 0:
            # Tomar TODOS los registros de estos pacientes (de todas sus unidades funcionales)
            partition_df = df_filtered[df_filtered['Identificación'].isin(pacientes_unicos)]
            partition_df = partition_df.sort_values(by=['Entidad', 'Identificación'])
            partitioned_dfs.append(partition_df)
            pacientes_por_particion_list.append(len(pacientes_unicos))
        else:
            partitioned_dfs.append(pd.DataFrame())
            pacientes_por_particion_list.append(0)
    
    return partitioned_dfs, pacientes_por_particion_list

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
    
    # Selector de tipo de partición
    st.subheader("Selecciona el tipo de partición")
    tipo_particion = st.radio(
        "Tipo de partición:",
        options=[
            "Partición equitativa por paciente", 
            "Partición personalizada"
        ],
        help="Selecciona cómo deseas distribuir los pacientes entre las particiones",
        key="tipo_particion_selector"
    )
    
    # Si es partición personalizada, mostrar los selectores de unidades ANTES del botón
    if tipo_particion == "Partición personalizada":
        st.subheader("🔧 Configuración de Partición Personalizada")
        st.info("""
        **Instrucciones:**
        1. Para cada partición, selecciona las unidades funcionales que deseas asignar
        2. Los pacientes de CADA unidad se dividirán EQUITATIVAMENTE entre las particiones donde esa unidad está asignada
        3. Cada paciente aparecerá en UNA SOLA partición con TODOS sus registros
        """)
        
        # Mostrar selectores para cada partición
        configuracion_personalizada = {}
        for i in range(num_partitions):
            st.markdown(f"**Partición {i+1}**")
            
            # Usar una clave única basada en el número de particiones para evitar conflictos
            config_key = f"config_particion_{num_partitions}_{i}"
            
            unidades_particion = st.multiselect(
                f"Selecciona unidades funcionales para la Partición {i+1}:",
                options=unidades_seleccionadas,
                key=config_key,
                help="Selecciona una o más unidades funcionales para esta partición"
            )
            configuracion_personalizada[i] = unidades_particion
        
        # Guardar en session state
        st.session_state.configuracion_personalizada = configuracion_personalizada
        
        # Validar que todas las unidades estén asignadas al menos una vez
        todas_unidades_asignadas = set()
        for unidades in configuracion_personalizada.values():
            todas_unidades_asignadas.update(unidades)
        
        unidades_no_asignadas = set(unidades_seleccionadas) - todas_unidades_asignadas
        
        if unidades_no_asignadas and unidades_seleccionadas:
            st.warning(f"⚠️ Las siguientes unidades funcionales no han sido asignadas a ninguna partición: {', '.join(unidades_no_asignadas)}")
        elif unidades_seleccionadas:
            st.success("✅ Todas las unidades funcionales han sido asignadas correctamente")
            
            # Mostrar cómo se distribuirán las unidades
            st.subheader("📊 Vista previa de la distribución")
            distribucion_data = []
            for i in range(num_partitions):
                unidades = configuracion_personalizada.get(i, [])
                for unidad in unidades:
                    distribucion_data.append({
                        'Partición': f'Part {i+1}',
                        'Unidad Funcional': unidad
                    })
            
            if distribucion_data:
                df_distribucion = pd.DataFrame(distribucion_data)
                st.dataframe(df_distribucion, use_container_width=True)
            
            st.info("💡 Las unidades asignadas a múltiples particiones distribuirán sus pacientes EQUITATIVAMENTE entre ellas.")
    
    # Botón para procesar
    if st.button("Procesar y Particionar Datos"):
        if not unidades_seleccionadas:
            st.warning("Por favor selecciona al menos una unidad funcional")
        else:
            try:
                # Filtrar por unidades funcionales seleccionadas
                df_filtered = df_subset[df_subset['Unidad Funcional'].isin(unidades_seleccionadas)].copy()
                
                # ELIMINAR REGISTROS DONDE 'Nom. Actividad' SEA 'ADMINISTRACION RADIOTERAPIA'
                if 'Nom. Actividad' in df_filtered.columns:
                    mask_radioterapia = (
                        df_filtered['Nom. Actividad'].str.contains('ADMINISTRACION RADIOTERAPIA', case=False, na=False) |
                        df_filtered['Nom. Actividad'].str.contains('CONSULTA DE TERMINACION DE RADIOTERAPIA', case=False, na=False)
                    )
                    
                    df_filtered = df_filtered[~mask_radioterapia]
                
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
                    if tipo_particion == "Partición equitativa por paciente":
                        partitioned_dfs, pacientes_por_particion = particion_equitativa_por_paciente(
                            df_estado_filtered, num_partitions, unidades_seleccionadas
                        )
                    else:  # Partición personalizada
                        # Validar que todas las unidades estén asignadas antes de procesar
                        todas_unidades_asignadas = set()
                        for unidades in st.session_state.configuracion_personalizada.values():
                            todas_unidades_asignadas.update(unidades)
                        
                        unidades_no_asignadas_proc = set(unidades_seleccionadas) - todas_unidades_asignadas
                        
                        if unidades_no_asignadas_proc:
                            st.error(f"No se puede procesar. Las siguientes unidades no están asignadas: {', '.join(unidades_no_asignadas_proc)}")
                            st.stop()
                        
                        partitioned_dfs, pacientes_por_particion = procesar_particion_personalizada(
                            df_estado_filtered, num_partitions, unidades_seleccionadas, st.session_state.configuracion_personalizada
                        )
                        
                        if not partitioned_dfs:
                            st.stop()
                    
                    # Verificar que se generaron particiones
                    if not partitioned_dfs or all(len(df) == 0 for df in partitioned_dfs):
                        st.warning("No se pudieron generar particiones. Verifica la asignación de unidades funcionales.")
                        st.stop()
                    
                    # Mostrar resumen de particiones como TABLA SIMPLIFICADA
                    st.subheader("📊 Resumen de Particiones por Unidad Funcional")
                    
                    # Crear datos para la tabla con unidades como filas
                    tabla_datos = []
                    
                    # Obtener totales por partición
                    totales_pacientes = pacientes_por_particion
                    totales_registros = [len(partitioned_dfs[i]) for i in range(num_partitions)]
                    
                    # Para cada unidad funcional, crear una fila
                    for unidad in unidades_seleccionadas:
                        fila = {'Unidad Funcional': unidad}
                        
                        # Obtener datos de cada partición para esta unidad
                        for i in range(num_partitions):
                            partition_df = partitioned_dfs[i]
                            if len(partition_df) > 0 and 'Unidad Funcional' in partition_df.columns:
                                df_unidad = partition_df[partition_df['Unidad Funcional'] == unidad]
                                if len(df_unidad) > 0:
                                    pacientes = df_unidad['Identificación'].nunique()
                                    registros = len(df_unidad)
                                    fila[f'Part {i+1}'] = f"{pacientes} ({registros})"
                                else:
                                    fila[f'Part {i+1}'] = "0 (0)"
                            else:
                                fila[f'Part {i+1}'] = "0 (0)"
                        
                        # Calcular totales por unidad
                        total_registros_unidad = 0
                        total_pacientes_unidad = 0
                        for i in range(num_partitions):
                            partition_df = partitioned_dfs[i]
                            if len(partition_df) > 0 and 'Unidad Funcional' in partition_df.columns:
                                df_unidad = partition_df[partition_df['Unidad Funcional'] == unidad]
                                if len(df_unidad) > 0:
                                    total_registros_unidad += len(df_unidad)
                                    total_pacientes_unidad += df_unidad['Identificación'].nunique()
                        
                        fila['Total'] = f"{total_pacientes_unidad} ({total_registros_unidad})"
                        tabla_datos.append(fila)
                    
                    # Agregar fila de totales generales
                    fila_totales = {'Unidad Funcional': 'TOTALES'}
                    for i in range(num_partitions):
                        fila_totales[f'Part {i+1}'] = f"{totales_pacientes[i]} ({totales_registros[i]})"
                    
                    total_pacientes_general = sum(totales_pacientes)
                    total_registros_general = sum(totales_registros)
                    fila_totales['Total'] = f"{total_pacientes_general} ({total_registros_general})"
                    
                    tabla_datos.append(fila_totales)
                    
                    # Crear DataFrame y mostrarlo como tabla
                    df_resumen = pd.DataFrame(tabla_datos)
                    st.dataframe(df_resumen, use_container_width=True)
                    
                    # Nota aclaratoria debajo de la tabla
                    st.caption("📌 **Nota:** El valor **fuera del paréntesis** corresponde a la cantidad de **pacientes**, y el valor **dentro del paréntesis** corresponde a la cantidad de **registros (CUPS)**.")

                    # Generate Excel file in memory
                    output_buffer = io.BytesIO()
                    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                        for i, part_df in enumerate(partitioned_dfs):
                            sheet_name = f'Part {i+1}'[:31]
                            
                            columnas_a_exportar = [col for col in columnas_existentes if col in part_df.columns]
                            columnas_adicionales = ['Estado', 'Observación']
                            columnas_finales = columnas_a_exportar + [col for col in columnas_adicionales if col in part_df.columns]
                            
                            part_df_export = part_df[columnas_finales] if len(part_df) > 0 else pd.DataFrame(columns=columnas_finales)
                            part_df_export.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Agregar una hoja de resumen simplificada
                        resumen_data = {
                            'Unidad Funcional': unidades_seleccionadas + ['TOTALES']
                        }
                        
                        # Agregar columnas por partición (formato simplificado)
                        for i in range(num_partitions):
                            col_name = f'Part {i+1}'
                            resumen_data[col_name] = []
                            
                            for unidad in unidades_seleccionadas:
                                df_part = partitioned_dfs[i]
                                if len(df_part) > 0 and 'Unidad Funcional' in df_part.columns:
                                    df_unidad = df_part[df_part['Unidad Funcional'] == unidad]
                                    if len(df_unidad) > 0:
                                        pacientes = df_unidad['Identificación'].nunique()
                                        registros = len(df_unidad)
                                        resumen_data[col_name].append(f"{pacientes} ({registros})")
                                    else:
                                        resumen_data[col_name].append("0 (0)")
                                else:
                                    resumen_data[col_name].append("0 (0)")
                            
                            # Agregar totales
                            resumen_data[col_name].append(f"{totales_pacientes[i]} ({totales_registros[i]})")
                        
                        # Agregar columna de totales
                        resumen_data['Total'] = []
                        for unidad in unidades_seleccionadas:
                            total_reg = 0
                            total_pac = 0
                            for i in range(num_partitions):
                                df_part = partitioned_dfs[i]
                                if len(df_part) > 0 and 'Unidad Funcional' in df_part.columns:
                                    df_unidad = df_part[df_part['Unidad Funcional'] == unidad]
                                    if len(df_unidad) > 0:
                                        total_reg += len(df_unidad)
                                        total_pac += df_unidad['Identificación'].nunique()
                            resumen_data['Total'].append(f"{total_pac} ({total_reg})")
                        
                        # Agregar totales generales
                        resumen_data['Total'].append(f"{total_pacientes_general} ({total_registros_general})")
                        
                        resumen_df = pd.DataFrame(resumen_data)
                        resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
                        
                        # Agregar hoja de configuración para partición personalizada
                        if tipo_particion == "Partición personalizada":
                            config_data = []
                            for i in range(num_partitions):
                                for unidad in st.session_state.configuracion_personalizada.get(i, []):
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
