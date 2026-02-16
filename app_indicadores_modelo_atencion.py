import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos y Llamados", layout="wide")

st.title("📊 Visualizador de Registros con Filtros Dinámicos")

# Crear pestañas
tab1, tab2 = st.tabs(["📋 Análisis de Ingresos", "📞 Análisis de Llamados"])

# ============================================================================
# PESTAÑA 1: ANÁLISIS DE INGRESOS
# ============================================================================
with tab1:
    st.header("📋 Análisis de Ingresos")
    
    # --- SECCIÓN DE FILTROS EN SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Configuración Pestaña 1")
        
        # 1. Carga de archivo en la sidebar
        uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", 
                                        type=["xlsx"], 
                                        help="Archivo debe contener columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'",
                                        key="tab1_file")

    if uploaded_file is not None:
        try:
            # Leer el archivo
            df = pd.read_excel(uploaded_file)
            
            # --- PROCESAMIENTO DE FECHAS ---
            # Convertimos la columna a datetime para poder operar
            df["FECHA CREACION"] = pd.to_datetime(df["FECHA CREACION"], errors='coerce')
            
            # Eliminamos filas con fechas nulas para evitar errores en el selector
            df = df.dropna(subset=["FECHA CREACION"])

            # Identificamos los límites reales del archivo
            fecha_minima_archivo = df["FECHA CREACION"].min().date()
            fecha_maxima_archivo = df["FECHA CREACION"].max().date()

            # --- CONTINUACIÓN DE FILTROS EN SIDEBAR ---
            with st.sidebar:
                # 2. Filtro de Fechas (Rango basado en el archivo)
                st.subheader("Rango de Evaluación")
                
                # Crear dos selectores separados para fecha inicial y final
                col1, col2 = st.columns(2)
                
                with col1:
                    fecha_inicio = st.date_input(
                        "Fecha de inicio:",
                        value=fecha_minima_archivo,
                        min_value=fecha_minima_archivo,
                        max_value=fecha_maxima_archivo,
                        key="tab1_fecha_inicio"
                    )
                
                with col2:
                    fecha_fin = st.date_input(
                        "Fecha de fin:",
                        value=fecha_maxima_archivo,
                        min_value=fecha_minima_archivo,
                        max_value=fecha_maxima_archivo,
                        key="tab1_fecha_fin"
                    )
                
                # Validar que la fecha de inicio sea menor o igual a la fecha de fin
                if fecha_inicio > fecha_fin:
                    st.error("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin")
                    st.info(f"Selecciona fechas entre: **{fecha_minima_archivo}** y **{fecha_maxima_archivo}**")
                else:
                    st.success(f"✅ Rango válido: {fecha_inicio} a {fecha_fin}")

                # 3. Filtro de Centro de Atención
                centros = sorted(df["CENTRO ATENCION"].dropna().unique())
                centro_sel = st.multiselect(
                    "Centro de Atención:", 
                    options=centros,
                    help="Selecciona uno o más centros de atención",
                    key="tab1_centro"
                )

                # 4. Filtro de Usuario Crea Ingreso
                usuarios = sorted(df["USUARIO CREA INGRESO"].dropna().unique())
                usuario_sel = st.multiselect(
                    "Usuario que Creó Ingreso:", 
                    options=usuarios,
                    help="Selecciona uno o más usuarios",
                    key="tab1_usuario"
                )

                # 5. Selector de día de la semana para el procesamiento
                st.subheader("Configuración de Procesamiento")
                dia_semana_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
                dia_seleccionado = st.selectbox(
                    "Día de la semana a analizar:",
                    options=dia_semana_opciones,
                    index=7,  # Por defecto selecciona "Todos los días (L-V)"
                    help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                    key="tab1_dia"
                )

            # --- APLICACIÓN DE FILTROS ---
            df_filtrado = df.copy()

            # Filtrado por Rango de Fechas (solo si las fechas son válidas)
            if fecha_inicio <= fecha_fin:
                df_filtrado = df_filtrado[
                    (df_filtrado["FECHA CREACION"].dt.date >= fecha_inicio) & 
                    (df_filtrado["FECHA CREACION"].dt.date <= fecha_fin)
                ]
            
            # Filtrado por Centro
            if centro_sel:
                df_filtrado = df_filtrado[df_filtrado["CENTRO ATENCION"].isin(centro_sel)]
            
            # Filtrado por Usuario
            if usuario_sel:
                df_filtrado = df_filtrado[df_filtrado["USUARIO CREA INGRESO"].isin(usuario_sel)]

            # --- PROCESAMIENTO AVANZADO (siempre que haya datos) ---
            if not df_filtrado.empty and fecha_inicio <= fecha_fin:
                st.divider()
                
                # Mostrar configuración seleccionada
                st.info(f"""
                **Configuración de análisis:**
                - **Rango:** {fecha_inicio} a {fecha_fin}
                - **Día analizado:** {dia_seleccionado}
                - **Centros:** {', '.join(centro_sel) if centro_sel else 'Todos'}
                - **Usuarios:** {', '.join(usuario_sel) if usuario_sel else 'Todos'}
                """)
                
                # Preparar datos para el procesamiento
                df_proceso = df_filtrado.copy()
                
                # Extraer información de fecha y hora
                df_proceso['FECHA'] = df_proceso['FECHA CREACION'].dt.date
                df_proceso['HORA'] = df_proceso['FECHA CREACION'].dt.hour
                df_proceso['DIA_SEMANA'] = df_proceso['FECHA CREACION'].dt.day_name()  # Esto da nombres en inglés
                df_proceso['DIA_SEMANA_NUM'] = df_proceso['FECHA CREACION'].dt.dayofweek  # 0=Lunes, 6=Domingo
                
                # Mapeo de días en español a inglés
                mapa_dias = {
                    'Lunes': 'Monday',
                    'Martes': 'Tuesday',
                    'Miércoles': 'Wednesday',
                    'Jueves': 'Thursday',
                    'Viernes': 'Friday',
                    'Sábado': 'Saturday',
                    'Domingo': 'Sunday'
                }
                
                # Verificar si se seleccionó un día específico o todos los días
                if dia_seleccionado == "Todos los días (L-V)":
                    # Filtrar solo lunes a viernes
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA_NUM'] < 5]
                    dias_analizados = "Lunes a Viernes"
                    dia_label = "L-V"
                    
                    # Verificar si hay datos después del filtro
                    if df_proceso.empty:
                        st.warning(f"No hay registros para el rango seleccionado (Lunes a Viernes).")
                        st.stop()
                else:
                    # Obtener el nombre del día en inglés
                    dia_ingles = mapa_dias[dia_seleccionado]
                    
                    # Filtrar por día específico usando el nombre en inglés
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_ingles]
                    dias_analizados = dia_seleccionado
                    dia_label = dia_seleccionado[:3]
                    
                    # Verificar si hay al menos un registro
                    if df_proceso.empty:
                        st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado}) en el rango filtrado.")
                        st.stop()
                    
                    # Mostrar información sobre cuántos días se están promediando
                    dias_unicos = df_proceso['FECHA'].nunique()
                    st.caption(f"📊 Promediando {dias_unicos} día(s) de {dia_seleccionado} en el rango seleccionado")
                
                # Identificar horas con registros
                horas_con_registros = sorted(df_proceso['HORA'].unique())
                
                # Obtener lista de usuarios únicos
                usuarios_proceso = sorted(df_proceso["USUARIO CREA INGRESO"].dropna().unique())
                
                if not usuarios_proceso:
                    st.warning("No hay usuarios en los datos filtrados.")
                    st.stop()
                
                # Crear estructura para la tabla dinámica
                tabla_resultados = pd.DataFrame(index=usuarios_proceso, columns=horas_con_registros)
                
                # Calcular promedios para cada usuario y hora
                for usuario in usuarios_proceso:
                    df_usuario = df_proceso[df_proceso["USUARIO CREA INGRESO"] == usuario]
                    
                    for hora in horas_con_registros:
                        # Filtrar registros para esta hora específica
                        df_hora = df_usuario[df_usuario['HORA'] == hora]
                        
                        if not df_hora.empty:
                            # Contar registros por fecha única
                            conteo_por_dia = df_hora.groupby('FECHA').size()
                            
                            # Excluir días con 0 registros para evitar sesgos
                            conteo_por_dia = conteo_por_dia[conteo_por_dia > 0]
                            
                            if not conteo_por_dia.empty:
                                promedio = conteo_por_dia.mean()
                                tabla_resultados.at[usuario, hora] = round(promedio, 2)
                            else:
                                tabla_resultados.at[usuario, hora] = None
                        else:
                            tabla_resultados.at[usuario, hora] = None
                
                # Formatear nombres de columnas (horas)
                horas_formateadas = [f"{h}:00" for h in horas_con_registros]
                tabla_resultados.columns = horas_formateadas
                
                # Reemplazar None por 0 para la suma
                tabla_resultados_suma = tabla_resultados.fillna(0)
                
                # Agregar columna de total por usuario
                tabla_resultados_suma['TOTAL'] = tabla_resultados_suma.sum(axis=1)
                
                # Ordenar por total descendente
                tabla_resultados = tabla_resultados.reindex(tabla_resultados_suma.sort_values('TOTAL', ascending=False).index)
                tabla_resultados_suma = tabla_resultados_suma.reindex(tabla_resultados_suma.sort_values('TOTAL', ascending=False).index)
                
                # --- TABLA 1: PROMEDIOS DE REGISTROS ---
                st.subheader("Ingresos promedio abiertos por Admisionista")
                st.markdown("*Cantidad de ingresos que realizan por hora*")

                # Mostrar tabla con formato
                tabla_visual = tabla_resultados.fillna(0)
                st.dataframe(
                    tabla_visual.style
                    .background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[:, horas_formateadas])
                    .format("{:.2f}")
                    .set_properties(**{'text-align': 'center'}),
                    use_container_width=True,
                    height=min(400, 50 + (len(usuarios_proceso) * 35))
                )
                
                # --- TABLA 2: TIEMPOS PROMEDIOS DE ADMISIÓN ---
                st.subheader("Tiempos Promedios de Admisión")
                st.markdown("*Tiempo promedio (minutos) que tardan en hacer un ingreso cada hora*")
                
                # Crear tabla de tiempos promedios
                tabla_tiempos = pd.DataFrame(index=usuarios_proceso, columns=horas_formateadas)
                
                # Calcular tiempo promedio = 60 / promedio de registros
                for usuario in usuarios_proceso:
                    for hora_col in horas_formateadas:
                        promedio_registros = tabla_resultados.at[usuario, hora_col]
                        if promedio_registros is not None and promedio_registros > 0:
                            tiempo_promedio = 60 / promedio_registros
                            tabla_tiempos.at[usuario, hora_col] = round(tiempo_promedio, 1)
                        else:
                            tabla_tiempos.at[usuario, hora_col] = None
                
                # Agregar columna de tiempo promedio total
                for usuario in usuarios_proceso:
                    tiempos_usuario = [v for v in tabla_tiempos.loc[usuario, horas_formateadas].values if v is not None]
                    if tiempos_usuario:
                        tiempo_promedio_total = np.mean(tiempos_usuario)
                        tabla_tiempos.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = round(tiempo_promedio_total, 1)
                    else:
                        tabla_tiempos.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = None
                
                # Mostrar tabla de tiempos
                st.dataframe(
                    tabla_tiempos.style
                    .background_gradient(cmap='YlOrRd_r', axis=1, subset=pd.IndexSlice[:, horas_formateadas])
                    .set_properties(**{'text-align': 'center'})
                    .format("{:.1f}", na_rep="-")
                    .format("{:.1f}", subset=['TIEMPO_PROMEDIO_TOTAL']),
                    use_container_width=True,
                    height=min(400, 50 + (len(usuarios_proceso) * 35))
                )
                
                # --- ESTADÍSTICAS RESUMEN CON ESTÁNDARES ---
                st.subheader("Estadísticas Resumen vs Estándares")
                
                # Calcular promedios generales
                valores_validos = []
                for col in horas_formateadas:
                    for usuario in usuarios_proceso:
                        valor = tabla_resultados.at[usuario, col]
                        if valor is not None and valor > 0:
                            valores_validos.append(valor)
                
                if valores_validos:
                    promedio_general = np.mean(valores_validos)
                else:
                    promedio_general = 0
                
                # Calcular tiempo promedio general
                tiempos_todos = []
                for usuario in usuarios_proceso:
                    for hora_col in horas_formateadas:
                        valor = tabla_tiempos.at[usuario, hora_col]
                        if valor is not None:
                            tiempos_todos.append(valor)
                
                # ESTÁNDARES DEFINIDOS
                ESTANDAR_REGISTROS_HORA = 13
                ESTANDAR_TIEMPO_ADMISION = 4
                
                # Calcular diferencias vs estándar
                diferencia_registros = promedio_general - ESTANDAR_REGISTROS_HORA
                diferencia_registros_porcentaje = (diferencia_registros / ESTANDAR_REGISTROS_HORA) * 100 if ESTANDAR_REGISTROS_HORA > 0 else 0
                
                if tiempos_todos:
                    tiempo_promedio_general = np.mean(tiempos_todos)
                    diferencia_tiempo = tiempo_promedio_general - ESTANDAR_TIEMPO_ADMISION
                    diferencia_tiempo_porcentaje = (diferencia_tiempo / ESTANDAR_TIEMPO_ADMISION) * 100 if ESTANDAR_TIEMPO_ADMISION > 0 else 0
                else:
                    tiempo_promedio_general = None
                    diferencia_tiempo = None
                    diferencia_tiempo_porcentaje = None
                
                # Mostrar métricas
                col1, col2 = st.columns(2)
                
                with col1:
                    delta_registros = f"{diferencia_registros:+.2f} vs estándar ({diferencia_registros_porcentaje:+.1f}%)"
                    color_delta_registros = "inverse" if diferencia_registros > 0 else "normal"
                    
                    st.metric(
                        label="📈 Promedio registros/hora", 
                        value=f"{promedio_general:.2f}",
                        delta=delta_registros,
                        delta_color=color_delta_registros,
                        help=f"Estándar: {ESTANDAR_REGISTROS_HORA} registros/hora"
                    )
                    
                    st.caption(f"**Estándar:** {ESTANDAR_REGISTROS_HORA} registros por hora")
                
                with col2:
                    if tiempo_promedio_general is not None:
                        delta_tiempo = f"{diferencia_tiempo:+.1f} min vs estándar ({diferencia_tiempo_porcentaje:+.1f}%)"
                        color_delta_tiempo = "inverse" if diferencia_tiempo > 0 else "normal"
                        
                        st.metric(
                            label="⏱️ Tiempo promedio admisión", 
                            value=f"{tiempo_promedio_general:.1f} min",
                            delta=delta_tiempo,
                            delta_color=color_delta_tiempo,
                            help=f"Estándar: {ESTANDAR_TIEMPO_ADMISION} minutos por admisión"
                        )
                        
                        st.caption(f"**Estándar:** {ESTANDAR_TIEMPO_ADMISION} minutos por admisión")
                    else:
                        st.metric(
                            label="⏱️ Tiempo promedio admisión", 
                            value="-",
                            help="No hay datos suficientes para calcular el tiempo promedio"
                        )
                        st.caption(f"**Estándar:** {ESTANDAR_TIEMPO_ADMISION} minutos por admisión")
                
                # --- GRÁFICO DE BARRAS: TOP USUARIOS ---
                st.subheader("🏆 Top 10 Usuarios por Actividad Promedio")
                
                top_n = min(10, len(tabla_resultados_suma))
                top_usuarios = tabla_resultados_suma.head(top_n)
                
                top_usuarios_chart = pd.DataFrame({
                    'Usuario': top_usuarios.index,
                    'Promedio Diario': top_usuarios['TOTAL'].values
                }).set_index('Usuario')
                
                st.bar_chart(
                    top_usuarios_chart,
                    height=400,
                    use_container_width=True
                )
                
                st.divider()
                st.subheader("📤 Exportar Resultados")
                
                st.info("""
                **Nota:** Streamlit no tiene funcionalidad nativa para exportar a PDF.
                **Alternativas sugeridas:**
                1. Use los botones de descarga CSV/Excel y convierta a PDF desde Excel
                2. Tome capturas de pantalla de las tablas importantes
                3. Use la funcionalidad de impresión del navegador (Ctrl+P) para guardar como PDF
                """)

        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.info("Verifica que el archivo tenga las columnas necesarias: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
    else:
        st.info("👆 Usa la barra lateral para subir un archivo Excel y activar los filtros.")
        st.caption("El archivo debe contener al menos las columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")

# ============================================================================
# PESTAÑA 2: ANÁLISIS DE LLAMADOS
# ============================================================================
with tab2:
    st.header("📞 Análisis de Llamados")
    
    # --- SECCIÓN DE FILTROS EN SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Configuración Pestaña 2")
        
        # 1. Carga de archivo en la sidebar
        uploaded_file_tab2 = st.file_uploader("Sube tu archivo Excel (.xlsx)", 
                                            type=["xlsx"], 
                                            help="Archivo debe contener columnas relacionadas con llamados: Hora Llegada, Servicio, Usuario Atención",
                                            key="tab2_file")

    if uploaded_file_tab2 is not None:
        try:
            # Leer y procesar el archivo
            df_preview = pd.read_excel(uploaded_file_tab2, nrows=5)
            
            # Verificar si la primera fila contiene los nombres esperados
            nombres_esperados = ['Turno', 'Doc Pac', 'Paciente', 'Sede', 'Sala Espera', 'Servicio', 
                                'Llamados', 'Tipo', 'Hora Llegada', 'Hora Atención', 'Hora Finalización',
                                'Tiempo Espera', 'Tiempo Atención', 'Modulo Atención', 'Usuario Atención',
                                'Especialidad', 'ID Usuario', 'Estado']
            
            # Comprobar si la primera fila (datos, no encabezados) contiene estos valores
            primera_fila_vals = df_preview.iloc[0].astype(str).str.strip().tolist() if len(df_preview) > 0 else []
            
            # Contar coincidencias con nombres esperados en la primera fila
            coincidencias = sum(1 for val in primera_fila_vals[:len(nombres_esperados)] 
                              if val in nombres_esperados)
            
            # Si hay suficientes coincidencias, probablemente la primera fila es el encabezado real
            usar_segunda_fila_como_encabezado = coincidencias >= 3
            
            # Leer el archivo con la estrategia correcta
            if usar_segunda_fila_como_encabezado:
                df_tab2 = pd.read_excel(uploaded_file_tab2, skiprows=1)
            else:
                df_tab2 = pd.read_excel(uploaded_file_tab2)
            
            # Limpiar nombres de columnas
            df_tab2.columns = df_tab2.columns.astype(str).str.strip()
            
            # Función para encontrar columnas por nombres alternativos
            def encontrar_columna(df, nombres_alternativos):
                columnas_df = [str(col).strip() for col in df.columns]
                for nombre in nombres_alternativos:
                    nombre_clean = nombre.strip()
                    if nombre_clean in columnas_df:
                        return nombre_clean
                    for col in columnas_df:
                        if col.lower() == nombre_clean.lower():
                            return col
                    for col in columnas_df:
                        if nombre_clean.lower() in col.lower():
                            return col
                return None
            
            # Nombres alternativos
            nombres_hora_llegada = ['Hora Llegada', 'HORA LLEGADA', 'Hora llegada', 'HORA_LLEGADA']
            nombres_servicio = ['Servicio', 'SERVICIO', 'servicio']
            nombres_usuario_atencion = ['Usuario Atención', 'USUARIO ATENCIÓN', 'Usuario atención']
            nombres_tipo = ['Tipo', 'TIPO', 'tipo']
            
            # Encontrar las columnas reales
            col_hora_llegada = encontrar_columna(df_tab2, nombres_hora_llegada)
            col_servicio = encontrar_columna(df_tab2, nombres_servicio)
            col_usuario_atencion = encontrar_columna(df_tab2, nombres_usuario_atencion)
            col_tipo = encontrar_columna(df_tab2, nombres_tipo)
            
            # Verificar columnas necesarias
            if not all([col_hora_llegada, col_servicio, col_usuario_atencion]):
                st.error("No se encontraron las columnas necesarias. Verifica que el archivo tenga: Hora Llegada, Servicio, Usuario Atención")
                st.stop()
            
            # Renombrar columnas para uso interno
            rename_dict = {
                col_hora_llegada: 'HORA_LLEGADA',
                col_servicio: 'SERVICIO',
                col_usuario_atencion: 'USUARIO_ATENCION'
            }
            
            if col_tipo:
                rename_dict[col_tipo] = 'TIPO_LLAMADO'
            
            df_tab2 = df_tab2.rename(columns=rename_dict)
            
            # --- PROCESAMIENTO DE FECHAS ---
            df_tab2["HORA_LLEGADA"] = pd.to_datetime(df_tab2["HORA_LLEGADA"], errors='coerce')
            df_tab2_limpio = df_tab2.dropna(subset=["HORA_LLEGADA"])

            if df_tab2_limpio.empty:
                st.warning("No hay registros con fechas válidas en la columna de hora de llegada.")
                st.stop()
            
            # Identificar los límites reales del archivo
            fecha_minima_archivo_tab2 = df_tab2_limpio["HORA_LLEGADA"].min().date()
            fecha_maxima_archivo_tab2 = df_tab2_limpio["HORA_LLEGADA"].max().date()

            # --- FILTROS PRINCIPALES EN SIDEBAR ---
            with st.sidebar:
                # Filtro de Fechas
                st.subheader("Rango de Evaluación")
                
                col1_tab2, col2_tab2 = st.columns(2)
                
                with col1_tab2:
                    fecha_inicio_tab2 = st.date_input(
                        "Fecha de inicio:",
                        value=fecha_minima_archivo_tab2,
                        min_value=fecha_minima_archivo_tab2,
                        max_value=fecha_maxima_archivo_tab2,
                        key="tab2_fecha_inicio"
                    )
                
                with col2_tab2:
                    fecha_fin_tab2 = st.date_input(
                        "Fecha de fin:",
                        value=fecha_maxima_archivo_tab2,
                        min_value=fecha_minima_archivo_tab2,
                        max_value=fecha_maxima_archivo_tab2,
                        key="tab2_fecha_fin"
                    )
                
                if fecha_inicio_tab2 > fecha_fin_tab2:
                    st.error("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin")
                else:
                    st.success(f"✅ Rango válido")

                # LISTA DESPLEGABLE DE SERVICIOS
                servicios = sorted(df_tab2_limpio["SERVICIO"].dropna().unique())
                servicio_sel = st.multiselect(
                    "Servicio:", 
                    options=servicios,
                    help="Selecciona uno o más servicios",
                    key="tab2_servicio"
                )

                # Filtro de Usuario Atención
                usuarios_tab2 = sorted(df_tab2_limpio["USUARIO_ATENCION"].dropna().unique())
                usuario_sel_tab2 = st.multiselect(
                    "Usuario Atención:", 
                    options=usuarios_tab2,
                    help="Selecciona uno o más usuarios",
                    key="tab2_usuario"
                )

                # Selector de día de la semana
                st.subheader("Configuración de Procesamiento")
                dia_semana_opciones_tab2 = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
                dia_seleccionado_tab2 = st.selectbox(
                    "Día de la semana a analizar:",
                    options=dia_semana_opciones_tab2,
                    index=6,  # Por defecto selecciona "Todos los días (L-V)"
                    help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                    key="tab2_dia"
                )

            # --- APLICACIÓN DE FILTROS ---
            df_filtrado_tab2 = df_tab2_limpio.copy()

            if fecha_inicio_tab2 <= fecha_fin_tab2:
                df_filtrado_tab2 = df_filtrado_tab2[
                    (df_filtrado_tab2["HORA_LLEGADA"].dt.date >= fecha_inicio_tab2) & 
                    (df_filtrado_tab2["HORA_LLEGADA"].dt.date <= fecha_fin_tab2)
                ]
            
            if servicio_sel:
                df_filtrado_tab2 = df_filtrado_tab2[df_filtrado_tab2["SERVICIO"].isin(servicio_sel)]
            
            if usuario_sel_tab2:
                df_filtrado_tab2 = df_filtrado_tab2[df_filtrado_tab2["USUARIO_ATENCION"].isin(usuario_sel_tab2)]

            # --- PROCESAMIENTO AUTOMÁTICO ---
            if not df_filtrado_tab2.empty and fecha_inicio_tab2 <= fecha_fin_tab2:
                st.divider()
                
                # Mostrar configuración seleccionada
                st.info(f"""
                **Configuración de análisis:**
                - **Rango:** {fecha_inicio_tab2} a {fecha_fin_tab2}
                - **Día analizado:** {dia_seleccionado_tab2}
                - **Servicios:** {', '.join(servicio_sel) if servicio_sel else 'Todos'}
                - **Usuarios:** {', '.join(usuario_sel_tab2) if usuario_sel_tab2 else 'Todos'}
                - **Registros analizados:** {len(df_filtrado_tab2):,}
                """)
                
                # Preparar datos para el procesamiento
                df_proceso_tab2 = df_filtrado_tab2.copy()
                
                # Extraer información de fecha y hora
                df_proceso_tab2['FECHA'] = df_proceso_tab2['HORA_LLEGADA'].dt.date
                df_proceso_tab2['HORA'] = df_proceso_tab2['HORA_LLEGADA'].dt.hour
                df_proceso_tab2['DIA_SEMANA'] = df_proceso_tab2['HORA_LLEGADA'].dt.day_name()  # Nombres en inglés
                df_proceso_tab2['DIA_SEMANA_NUM'] = df_proceso_tab2['HORA_LLEGADA'].dt.dayofweek
                
                # Mapeo de días en español a inglés
                mapa_dias = {
                    'Lunes': 'Monday',
                    'Martes': 'Tuesday',
                    'Miércoles': 'Wednesday',
                    'Jueves': 'Thursday',
                    'Viernes': 'Friday',
                    'Sábado': 'Saturday',
                    'Domingo': 'Sunday'
                }
                
                # Verificar si se seleccionó un día específico o todos los días
                if dia_seleccionado_tab2 == "Todos los días (L-V)":
                    # Filtrar solo lunes a viernes
                    df_proceso_tab2 = df_proceso_tab2[df_proceso_tab2['DIA_SEMANA_NUM'] < 5]
                    dias_analizados_tab2 = "Lunes a Viernes"
                    dia_label_tab2 = "L-V"
                    
                    # Verificar si hay datos después del filtro
                    if df_proceso_tab2.empty:
                        st.warning(f"No hay registros para el rango seleccionado (Lunes a Viernes).")
                        st.stop()
                else:
                    # Obtener el nombre del día en inglés
                    dia_ingles = mapa_dias[dia_seleccionado_tab2]
                    
                    # Filtrar por día específico usando el nombre en inglés
                    df_proceso_tab2 = df_proceso_tab2[df_proceso_tab2['DIA_SEMANA'] == dia_ingles]
                    dias_analizados_tab2 = dia_seleccionado_tab2
                    dia_label_tab2 = dia_seleccionado_tab2[:3]
                    
                    # Verificar si hay al menos un registro
                    if df_proceso_tab2.empty:
                        st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado_tab2}) en el rango filtrado.")
                        st.stop()
                    
                    # Mostrar información sobre cuántos días se están promediando
                    dias_unicos = df_proceso_tab2['FECHA'].nunique()
                    st.caption(f"📊 Promediando {dias_unicos} día(s) de {dia_seleccionado_tab2} en el rango seleccionado")
                
                # ============================================================
                # 1. TABLA DE PROMEDIO DE LLAMADOS POR AGENTE POR HORA Y DÍA
                # ============================================================
                st.subheader("Promedio de Llamados por Agente, Hora y Día")
                
                # Obtener usuarios únicos
                usuarios_proceso_tab2 = sorted(df_proceso_tab2["USUARIO_ATENCION"].dropna().unique())
                horas_con_registros_tab2 = sorted(df_proceso_tab2['HORA'].unique())
                
                if not usuarios_proceso_tab2:
                    st.warning("No hay usuarios en los datos filtrados.")
                    st.stop()
                
                # Crear tabla de promedios
                tabla_promedios = pd.DataFrame(index=usuarios_proceso_tab2, columns=horas_con_registros_tab2)
                
                for usuario in usuarios_proceso_tab2:
                    df_usuario = df_proceso_tab2[df_proceso_tab2["USUARIO_ATENCION"] == usuario]
                    
                    for hora in horas_con_registros_tab2:
                        df_hora = df_usuario[df_usuario['HORA'] == hora]
                        
                        if not df_hora.empty:
                            # Contar registros por fecha única
                            conteo_por_dia = df_hora.groupby('FECHA').size()
                            
                            conteo_por_dia = conteo_por_dia[conteo_por_dia > 0]
                            
                            if not conteo_por_dia.empty:
                                promedio = conteo_por_dia.mean()
                                tabla_promedios.at[usuario, hora] = round(promedio, 2)
                            else:
                                tabla_promedios.at[usuario, hora] = None
                        else:
                            tabla_promedios.at[usuario, hora] = None
                
                # Formatear horas
                horas_formateadas_tab2 = [f"{h}:00" for h in horas_con_registros_tab2]
                tabla_promedios.columns = horas_formateadas_tab2
                
                # Reemplazar None por 0 para la suma
                tabla_promedios_suma = tabla_promedios.fillna(0)
                
                # Agregar columna de total por usuario
                tabla_promedios_suma['TOTAL'] = tabla_promedios_suma.sum(axis=1)
                
                # Ordenar por total descendente
                tabla_promedios = tabla_promedios.reindex(tabla_promedios_suma.sort_values('TOTAL', ascending=False).index)
                tabla_promedios_suma = tabla_promedios_suma.reindex(tabla_promedios_suma.sort_values('TOTAL', ascending=False).index)
                
                # Mostrar tabla
                tabla_visual = tabla_promedios.fillna(0)
                st.dataframe(
                    tabla_visual.style
                    .background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[:, horas_formateadas_tab2])
                    .format("{:.2f}")
                    .set_properties(**{'text-align': 'center'}),
                    use_container_width=True,
                    height=min(400, 50 + (len(usuarios_proceso_tab2) * 35))
                )
                
                # ============================================================
                # 2. TABLA DE LLAMADOS MANUALES VS AUTO
                # ============================================================
                st.subheader("Llamados Manuales vs Automáticos por Usuario")
                
                # Verificar si existe columna de tipo
                if 'TIPO_LLAMADO' in df_proceso_tab2.columns:
                    # Normalizar valores de tipo
                    df_proceso_tab2['TIPO_NORMALIZADO'] = df_proceso_tab2['TIPO_LLAMADO'].astype(str).str.lower().str.strip()
                    
                    # Identificar manuales y auto
                    manual_keywords = ['manual', 'm', 'man', 'manuales']
                    auto_keywords = ['auto', 'a', 'aut', 'automático', 'automatico', 'automáticos']
                    
                    # Crear clasificación
                    def clasificar_tipo(valor):
                        if pd.isna(valor):
                            return 'NO_CLASIFICADO'
                        valor_str = str(valor).lower().strip()
                        if any(kw in valor_str for kw in manual_keywords):
                            return 'MANUAL'
                        elif any(kw in valor_str for kw in auto_keywords):
                            return 'AUTO'
                        else:
                            return 'NO_CLASIFICADO'
                    
                    df_proceso_tab2['CLASIFICACION'] = df_proceso_tab2['TIPO_LLAMADO'].apply(clasificar_tipo)
                    
                    # Crear tabla de conteo
                    tabla_tipos = pd.DataFrame(index=usuarios_proceso_tab2)
                    
                    for usuario in usuarios_proceso_tab2:
                        df_usuario = df_proceso_tab2[df_proceso_tab2["USUARIO_ATENCION"] == usuario]
                        
                        conteos = df_usuario['CLASIFICACION'].value_counts()
                        
                        manuales = conteos.get('MANUAL', 0)
                        automaticos = conteos.get('AUTO', 0)
                        total = manuales + automaticos
                        
                        tabla_tipos.at[usuario, 'TOTAL_LLAMADOS'] = total
                        tabla_tipos.at[usuario, 'MANUALES'] = manuales
                        tabla_tipos.at[usuario, 'AUTOMATICOS'] = automaticos
                    
                    # Calcular porcentajes
                    for usuario in usuarios_proceso_tab2:
                        total = tabla_tipos.at[usuario, 'TOTAL_LLAMADOS']
                        manuales = tabla_tipos.at[usuario, 'MANUALES']
                        
                        if total > 0:
                            tabla_tipos.at[usuario, '% MANUAL'] = (manuales / total * 100).round(1)
                            tabla_tipos.at[usuario, '% AUTO'] = (100 - (manuales / total * 100)).round(1)
                        else:
                            tabla_tipos.at[usuario, '% MANUAL'] = 0.0
                            tabla_tipos.at[usuario, '% AUTO'] = 0.0
                    
                    # Ordenar por total
                    tabla_tipos = tabla_tipos.sort_values('TOTAL_LLAMADOS', ascending=False)
                    
                    # Mostrar tabla
                    st.dataframe(
                        tabla_tipos.style
                        .format("{:.0f}", subset=['TOTAL_LLAMADOS', 'MANUALES', 'AUTOMATICOS'])
                        .format("{:.1f}%", subset=['% MANUAL', '% AUTO'])
                        .set_properties(**{'text-align': 'center'}),
                        use_container_width=True
                    )
                    
                    # Resumen de totales
                    st.markdown("**Resumen de Totales:**")
                    col_res1, col_res2, col_res3 = st.columns(3)
                    with col_res1:
                        st.metric("Total Manuales", f"{int(tabla_tipos['MANUALES'].sum()):,}")
                    with col_res2:
                        st.metric("Total Automáticos", f"{int(tabla_tipos['AUTOMATICOS'].sum()):,}")
                    with col_res3:
                        st.metric("Total General", f"{int(tabla_tipos['TOTAL_LLAMADOS'].sum()):,}")
                    
                    # ============================================================
                    # 3. GRÁFICA DE LÍNEA DE TIEMPO
                    # ============================================================
                    st.subheader("Evolución Temporal de Llamados Manuales vs Automáticos")
                    
                    # Preparar datos para la gráfica
                    df_temporal = df_proceso_tab2.copy()
                    df_temporal['FECHA_DT'] = pd.to_datetime(df_temporal['FECHA'])
                    
                    # Agrupar por fecha y clasificación
                    df_manual = df_temporal[df_temporal['CLASIFICACION'] == 'MANUAL'].groupby('FECHA_DT').size().reset_index(name='MANUALES')
                    df_auto = df_temporal[df_temporal['CLASIFICACION'] == 'AUTO'].groupby('FECHA_DT').size().reset_index(name='AUTOMATICOS')
                    df_total = df_temporal[df_temporal['CLASIFICACION'].isin(['MANUAL', 'AUTO'])].groupby('FECHA_DT').size().reset_index(name='TOTAL')
                    
                    # Combinar dataframes
                    df_agrupado = pd.merge(df_total, df_manual, on='FECHA_DT', how='left')
                    df_agrupado = pd.merge(df_agrupado, df_auto, on='FECHA_DT', how='left')
                    
                    # Rellenar NaN con 0
                    df_agrupado['MANUALES'] = df_agrupado['MANUALES'].fillna(0)
                    df_agrupado['AUTOMATICOS'] = df_agrupado['AUTOMATICOS'].fillna(0)
                    
                    # Configurar índice para el gráfico
                    df_grafico = df_agrupado.set_index('FECHA_DT')[['MANUALES', 'AUTOMATICOS', 'TOTAL']]
                    
                    # Gráfico de líneas
                    st.line_chart(
                        df_grafico,
                        height=400,
                        use_container_width=True
                    )
                    
                else:
                    st.warning("⚠️ No se encontró la columna 'Tipo' para clasificar llamados manuales/automáticos")
                
                # ============================================================
                # ESTADÍSTICAS RESUMEN
                # ============================================================
                st.divider()
                st.subheader("Estadísticas Resumen")
                
                # Calcular estadísticas
                valores_validos = []
                for col in horas_formateadas_tab2:
                    for usuario in usuarios_proceso_tab2:
                        valor = tabla_promedios.at[usuario, col]
                        if valor is not None and valor > 0:
                            valores_validos.append(valor)
                
                if valores_validos:
                    promedio_general_tab2 = np.mean(valores_validos)
                else:
                    promedio_general_tab2 = 0
                
                # Calcular tiempo promedio de atención
                tiempos_validos = []
                for usuario in usuarios_proceso_tab2:
                    for hora_col in horas_formateadas_tab2:
                        promedio_registros = tabla_promedios.at[usuario, hora_col]
                        if promedio_registros is not None and promedio_registros > 0:
                            tiempo_promedio = 60 / promedio_registros
                            tiempos_validos.append(tiempo_promedio)
                
                if tiempos_validos:
                    tiempo_promedio_general_tab2 = np.mean(tiempos_validos)
                else:
                    tiempo_promedio_general_tab2 = None
                
                # Mostrar métricas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Promedio Llamados/Hora", f"{promedio_general_tab2:.2f}")
                with col2:
                    if tiempo_promedio_general_tab2:
                        st.metric("Tiempo Promedio Atención", f"{tiempo_promedio_general_tab2:.1f} min")
                    else:
                        st.metric("Tiempo Promedio Atención", "-")
                
                # ============================================================
                # GRÁFICO DE BARRAS TOP USUARIOS
                # ============================================================
                st.subheader("🏆 Top 10 Usuarios por Actividad")
                
                top_n_tab2 = min(10, len(tabla_promedios_suma))
                top_usuarios_tab2 = tabla_promedios_suma.head(top_n_tab2)
                
                top_usuarios_chart = pd.DataFrame({
                    'Usuario': top_usuarios_tab2.index,
                    'Promedio Diario': top_usuarios_tab2['TOTAL'].values
                }).set_index('Usuario')
                
                st.bar_chart(
                    top_usuarios_chart,
                    height=400,
                    use_container_width=True
                )
                
                st.divider()
                st.subheader("📤 Exportar Resultados")
                
                st.info("""
                **Nota:** Streamlit no tiene funcionalidad nativa para exportar a PDF.
                **Alternativas sugeridas:**
                1. Use los botones de descarga CSV/Excel y convierta a PDF desde Excel
                2. Tome capturas de pantalla de las tablas importantes
                3. Use la funcionalidad de impresión del navegador (Ctrl+P) para guardar como PDF
                """)

        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("👆 Usa la barra lateral para subir un archivo Excel y activar los filtros.")
        st.caption("El archivo debe contener columnas relacionadas con llamados: Hora de Llegada, Servicio, Usuario que Atiende")
