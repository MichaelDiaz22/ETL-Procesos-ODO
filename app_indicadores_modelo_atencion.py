import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos y Llamados", layout="wide")

st.title("📊 Análisis de gestiones del modelo de atención")

# Crear pestañas
tab1, tab2, tab3 = st.tabs(["📋 Análisis de ingresos abiertos", "📆 Análisis de turnos atendidos", "🔍 Auditoría de Admisiones"])

# ============================================================================
# PESTAÑA 1: ANÁLISIS DE INGRESOS
# ============================================================================
with tab1:
    st.header("📋 Análisis de Ingresos")
    
    # --- ÚNICO EXPANDER PARA TODA LA CONFIGURACIÓN ---
    with st.expander("⚙️ Configuración y Filtros", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Carga de archivo
            uploaded_file = st.file_uploader("📁 Sube tu archivo Excel (.xlsx)", 
                                            type=["xlsx"], 
                                            help="Archivo debe contener columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'",
                                            key="tab1_file")
        
        with col2:
            st.markdown("##### 📊 Configuración de análisis")
            st.markdown("*Actualice el informe ODO_ESTADISTICO_INGRESOS con el periodo requerido, almacene la información en un excel en blanco y cargue el archivo para analizar*")
            st.markdown("*Posteriormente, seleccione un rango de fechas, un centro de atención y los usuarios (Gestores de acceso) a analizar*")

        # Si hay archivo cargado, mostrar los filtros dentro del MISMO expander
        if uploaded_file is not None:
            try:
                # Leer el archivo para obtener opciones de filtros
                df_temp = pd.read_excel(uploaded_file)
                df_temp["FECHA CREACION"] = pd.to_datetime(df_temp["FECHA CREACION"], errors='coerce')
                df_temp = df_temp.dropna(subset=["FECHA CREACION"])
                
                fecha_minima = df_temp["FECHA CREACION"].min().date()
                fecha_maxima = df_temp["FECHA CREACION"].max().date()
                centros_disponibles = sorted(df_temp["CENTRO ATENCION"].dropna().unique())
                usuarios_disponibles = sorted(df_temp["USUARIO CREA INGRESO"].dropna().unique())
                
                st.markdown("---")
                st.markdown("#### 📊 Filtros de selección")
                
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    st.markdown("##### 📅 Rango de fechas")
                    fecha_inicio = st.date_input(
                        "Fecha inicio:",
                        value=fecha_minima,
                        min_value=fecha_minima,
                        max_value=fecha_maxima,
                        key="tab1_fecha_inicio"
                    )
                    fecha_fin = st.date_input(
                        "Fecha fin:",
                        value=fecha_maxima,
                        min_value=fecha_minima,
                        max_value=fecha_maxima,
                        key="tab1_fecha_fin"
                    )
                    
                    if fecha_inicio > fecha_fin:
                        st.error("⚠️ Fecha inicio no puede ser mayor que fecha fin")
                
                with col_f2:
                    st.markdown("##### 🏥 Centros de atención")
                    centro_sel = st.multiselect(
                        "Seleccionar centros:", 
                        options=centros_disponibles,
                        help="Selecciona uno o más centros",
                        key="tab1_centro"
                    )
                
                with col_f3:
                    st.markdown("##### 👤 Usuarios (Gestor de acceso)")
                    usuario_sel = st.multiselect(
                        "Seleccionar usuarios:", 
                        options=usuarios_disponibles,
                        help="Selecciona uno o más usuarios",
                        key="tab1_usuario"
                    )
            
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.stop()

    # --- PROCESAMIENTO PRINCIPAL (fuera del expander) ---
    if uploaded_file is not None and 'fecha_inicio' in locals() and fecha_inicio <= fecha_fin:
        try:
            # Leer el archivo nuevamente para procesamiento
            df = pd.read_excel(uploaded_file)
            df["FECHA CREACION"] = pd.to_datetime(df["FECHA CREACION"], errors='coerce')
            df = df.dropna(subset=["FECHA CREACION"])
            
            # Aplicar filtros
            df_filtrado = df[
                (df["FECHA CREACION"].dt.date >= fecha_inicio) & 
                (df["FECHA CREACION"].dt.date <= fecha_fin)
            ]
            
            if centro_sel:
                df_filtrado = df_filtrado[df_filtrado["CENTRO ATENCION"].isin(centro_sel)]
            
            if usuario_sel:
                df_filtrado = df_filtrado[df_filtrado["USUARIO CREA INGRESO"].isin(usuario_sel)]

            if not df_filtrado.empty:
                st.divider()
                
                # Mostrar configuración seleccionada
                st.info(f"""
                **Configuración de análisis:**
                - **Rango:** {fecha_inicio} a {fecha_fin}
                - **Centros:** {', '.join(centro_sel) if centro_sel else 'Todos'}
                - **Usuarios:** {', '.join(usuario_sel) if usuario_sel else 'Todos'}
                - **Registros analizados:** {len(df_filtrado):,}
                """)
                
                # --- SELECTOR DE DÍA (fuera del expander, después del resumen) ---
                st.markdown("### 📅 Selección de día para análisis")
                dia_semana_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
                dia_seleccionado = st.selectbox(
                    "Día de la semana a analizar:",
                    options=dia_semana_opciones,
                    index=7,
                    help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                    key="tab1_dia"
                )
                
                # Preparar datos
                df_proceso = df_filtrado.copy()
                df_proceso['FECHA'] = df_proceso['FECHA CREACION'].dt.date
                df_proceso['HORA'] = df_proceso['FECHA CREACION'].dt.hour
                df_proceso['DIA_SEMANA'] = df_proceso['FECHA CREACION'].dt.day_name()
                df_proceso['DIA_SEMANA_NUM'] = df_proceso['FECHA CREACION'].dt.dayofweek
                
                # Mapeo de días
                mapa_dias = {
                    'Lunes': 'Monday', 'Martes': 'Tuesday', 'Miércoles': 'Wednesday',
                    'Jueves': 'Thursday', 'Viernes': 'Friday', 'Sábado': 'Saturday', 'Domingo': 'Sunday'
                }
                
                # Filtrar por día
                if dia_seleccionado == "Todos los días (L-V)":
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA_NUM'] < 5]
                    if df_proceso.empty:
                        st.warning("No hay registros para Lunes a Viernes.")
                        st.stop()
                else:
                    dia_ingles = mapa_dias[dia_seleccionado]
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_ingles]
                    if df_proceso.empty:
                        st.warning(f"No hay registros para {dia_seleccionado}.")
                        st.stop()
                    dias_unicos = df_proceso['FECHA'].nunique()
                    st.caption(f"📊 Promediando {dias_unicos} día(s) de {dia_seleccionado}")
                
                # Identificar horas
                horas_con_registros = sorted(df_proceso['HORA'].unique())
                horas_formateadas = [f"{h}:00" for h in horas_con_registros]
                
                # Obtener usuarios
                usuarios_proceso = sorted(df_proceso["USUARIO CREA INGRESO"].dropna().unique())
                
                if not usuarios_proceso:
                    st.warning("No hay usuarios en los datos filtrados.")
                    st.stop()
                
                # Crear tabla de promedios
                data = []
                for usuario in usuarios_proceso:
                    df_usuario = df_proceso[df_proceso["USUARIO CREA INGRESO"] == usuario]
                    fila = []
                    for hora in horas_con_registros:
                        df_hora = df_usuario[df_usuario['HORA'] == hora]
                        if not df_hora.empty:
                            conteo_por_dia = df_hora.groupby('FECHA').size()
                            conteo_por_dia = conteo_por_dia[conteo_por_dia > 0]
                            promedio = conteo_por_dia.mean() if not conteo_por_dia.empty else 0
                            fila.append(round(promedio, 2))
                        else:
                            fila.append(0)
                    data.append(fila)
                
                tabla_resultados = pd.DataFrame(data, index=usuarios_proceso, columns=horas_formateadas)
                
                # Calcular estadísticas
                tabla_resultados['TOTAL'] = tabla_resultados[horas_formateadas].sum(axis=1).round(2)
                
                minimos = []
                for idx in tabla_resultados.index:
                    valores_fila = tabla_resultados.loc[idx, horas_formateadas]
                    valores_positivos = valores_fila[valores_fila > 0]
                    if len(valores_positivos) > 0:
                        minimos.append(valores_positivos.min())
                    else:
                        minimos.append(0)
                tabla_resultados['MÍNIMO'] = [round(x, 2) for x in minimos]
                
                tabla_resultados['MÁXIMO'] = tabla_resultados[horas_formateadas].max(axis=1).round(2)
                
                # Ordenar por TOTAL descendente para que el gráfico de barras también salga ordenado
                tabla_resultados = tabla_resultados.sort_values('TOTAL', ascending=False)
                
                # Totales por hora
                totales_por_hora = tabla_resultados[horas_formateadas].sum(axis=0).round(2)
                
                # Fila de totales
                datos_fila_total = {'TOTAL': totales_por_hora.sum()}
                for hora in horas_formateadas:
                    datos_fila_total[hora] = totales_por_hora[hora]
                datos_fila_total['MÍNIMO'] = ''
                datos_fila_total['MÁXIMO'] = ''
                
                fila_total = pd.DataFrame([datos_fila_total], index=['TOTAL'])
                tabla_resultados_con_total = pd.concat([tabla_resultados, fila_total])
                
                # --- TABLA 1: PROMEDIOS ---
                st.subheader("📊 Ingresos promedio abiertos por Admisionista")
                st.markdown("*Cantidad de ingresos que realizan por hora*")

                styler = tabla_resultados_con_total.style
                mascara_usuarios = tabla_resultados_con_total.index != 'TOTAL'
                styler = styler.format("{:.2f}", subset=pd.IndexSlice[tabla_resultados_con_total.index[mascara_usuarios], horas_formateadas + ['TOTAL', 'MÍNIMO', 'MÁXIMO']])
                styler = styler.format("{:.2f}", subset=pd.IndexSlice[['TOTAL'], horas_formateadas + ['TOTAL']])
                styler = styler.background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[tabla_resultados.index, horas_formateadas])
                styler = styler.set_properties(**{'text-align': 'center'})
                
                st.dataframe(styler, use_container_width=True, height=min(400, 50 + (len(usuarios_proceso) * 35)))
                
                # --- TABLA 2: TIEMPOS ---
                st.subheader("⏱️ Tiempos Promedios de Admisión")
                st.markdown("*Tiempo promedio (minutos) que tardan en hacer un ingreso cada hora*")
                
                tiempos_data = []
                for usuario in usuarios_proceso:
                    fila_tiempos = []
                    for hora in horas_formateadas:
                        promedio = tabla_resultados.loc[usuario, hora]
                        if promedio > 0:
                            tiempo = round(60 / promedio, 1)
                            fila_tiempos.append(tiempo)
                        else:
                            fila_tiempos.append(0)
                    tiempos_data.append(fila_tiempos)
                
                tabla_tiempos = pd.DataFrame(tiempos_data, index=usuarios_proceso, columns=horas_formateadas)
                
                # Calcular estadísticas de tiempos
                tabla_tiempos['PROMEDIO'] = None
                tabla_tiempos['MÍNIMO'] = None
                tabla_tiempos['MÁXIMO'] = None
                
                for usuario in usuarios_proceso:
                    tiempos_usuario_min = [tabla_tiempos.loc[usuario, hora] for hora in horas_formateadas 
                                          if tabla_tiempos.loc[usuario, hora] > 0]
                    
                    tiempos_usuario_max = [tabla_tiempos.loc[usuario, hora] for hora in horas_formateadas 
                                          if tabla_tiempos.loc[usuario, hora] > 0 and tabla_tiempos.loc[usuario, hora] != 60]
                    
                    tiempos_usuario_prom = [tabla_tiempos.loc[usuario, hora] for hora in horas_formateadas 
                                           if tabla_tiempos.loc[usuario, hora] > 0]
                    
                    if tiempos_usuario_prom:
                        tabla_tiempos.loc[usuario, 'PROMEDIO'] = round(np.mean(tiempos_usuario_prom), 1)
                    else:
                        tabla_tiempos.loc[usuario, 'PROMEDIO'] = 0
                    
                    if tiempos_usuario_min:
                        tabla_tiempos.loc[usuario, 'MÍNIMO'] = round(min(tiempos_usuario_min), 1)
                    else:
                        tabla_tiempos.loc[usuario, 'MÍNIMO'] = 0
                    
                    if tiempos_usuario_max:
                        tabla_tiempos.loc[usuario, 'MÁXIMO'] = round(max(tiempos_usuario_max), 1)
                    else:
                        tabla_tiempos.loc[usuario, 'MÁXIMO'] = 0
                
                # Ordenar por el mismo orden que la tabla anterior
                tabla_tiempos = tabla_tiempos.loc[tabla_resultados.index]
                
                styler_tiempos = tabla_tiempos.style
                styler_tiempos = styler_tiempos.format("{:.1f}", na_rep="-")
                styler_tiempos = styler_tiempos.background_gradient(cmap='YlOrRd_r', axis=1, 
                                                                   subset=pd.IndexSlice[usuarios_proceso, horas_formateadas])
                styler_tiempos = styler_tiempos.set_properties(**{'text-align': 'center'})
                
                st.dataframe(styler_tiempos, use_container_width=True, height=min(400, 50 + (len(usuarios_proceso) * 35)))
                
                # --- ESTADÍSTICAS RESUMEN ---
                st.subheader("📈 Estadísticas Resumen vs Estándares")
                
                # Calcular estadísticas
                valores_validos = []
                for col in horas_formateadas:
                    for usuario in usuarios_proceso:
                        valor = tabla_resultados.loc[usuario, col]
                        if valor > 0:
                            valores_validos.append(valor)
                
                promedio_general = np.mean(valores_validos) if valores_validos else 0
                
                tiempos_todos = []
                for usuario in usuarios_proceso:
                    for hora in horas_formateadas:
                        valor = tabla_tiempos.loc[usuario, hora]
                        if valor > 0 and valor != 60:
                            tiempos_todos.append(valor)
                
                # Máximos y mínimos
                max_registros = 0
                usuario_max = "N/A"
                hora_max = "N/A"
                
                for col in horas_formateadas:
                    for usuario in usuarios_proceso:
                        valor = tabla_resultados.loc[usuario, col]
                        if valor > max_registros:
                            max_registros = valor
                            usuario_max = usuario
                            hora_max = col
                
                min_tiempo = float('inf')
                usuario_min = "N/A"
                hora_min = "N/A"
                
                for col in horas_formateadas:
                    for usuario in usuarios_proceso:
                        valor = tabla_tiempos.loc[usuario, col]
                        if valor > 0 and valor < min_tiempo:
                            min_tiempo = valor
                            usuario_min = usuario
                            hora_min = col
                
                min_tiempo = None if min_tiempo == float('inf') else min_tiempo
                
                # Estándares
                ESTANDAR_REGISTROS = 13
                ESTANDAR_TIEMPO = 4
                
                diff_registros = promedio_general - ESTANDAR_REGISTROS
                diff_registros_pct = (diff_registros / ESTANDAR_REGISTROS) * 100 if ESTANDAR_REGISTROS > 0 else 0
                
                tiempo_promedio_general = np.mean(tiempos_todos) if tiempos_todos else None
                
                if tiempo_promedio_general:
                    diff_tiempo = tiempo_promedio_general - ESTANDAR_TIEMPO
                    diff_tiempo_pct = (diff_tiempo / ESTANDAR_TIEMPO) * 100 if ESTANDAR_TIEMPO > 0 else 0
                
                # Mostrar métricas
                col_est1, col_est2 = st.columns(2)
                
                with col_est1:
                    st.markdown("### 📈 Promedio General vs Estándar")
                    delta_reg = f"{diff_registros:+.2f} vs estándar ({diff_registros_pct:+.1f}%)"
                    st.metric("Promedio registros/hora", f"{promedio_general:.2f}", 
                             delta=delta_reg, delta_color="inverse" if diff_registros > 0 else "normal")
                    st.markdown(f"**Estándar:** {ESTANDAR_REGISTROS}")
                    
                    st.markdown("### 📈 Máximo Registros/Hora")
                    st.metric("Máximo alcanzado", f"{max_registros:.2f}")
                    st.markdown(f"**Usuario:** {usuario_max}")
                    st.markdown(f"**Hora:** {hora_max}")
                
                with col_est2:
                    st.markdown("### ⏱️ Tiempo Promedio vs Estándar")
                    if tiempo_promedio_general:
                        delta_t = f"{diff_tiempo:+.1f} min vs estándar ({diff_tiempo_pct:+.1f}%)"
                        st.metric("Tiempo promedio admisión", f"{tiempo_promedio_general:.1f} min",
                                 delta=delta_t, delta_color="inverse" if diff_tiempo > 0 else "normal")
                    else:
                        st.metric("Tiempo promedio admisión", "-")
                    st.markdown(f"**Estándar:** {ESTANDAR_TIEMPO} min")
                    
                    st.markdown("### ⏱️ Mínimo Tiempo de Admisión")
                    if min_tiempo:
                        st.metric("Mínimo alcanzado", f"{min_tiempo:.1f} min")
                        st.markdown(f"**Usuario:** {usuario_min}")
                        st.markdown(f"**Hora:** {hora_min}")
                    else:
                        st.metric("Mínimo alcanzado", "N/A")
                
                # --- GRÁFICO DE BARRAS ---
                st.subheader("🏆 Top 10 Usuarios por Actividad Promedio")
                
                top_n = min(10, len(tabla_resultados))
                top_usuarios = tabla_resultados.head(top_n)
                
                # Crear DataFrame para el gráfico - ya viene ordenado por tabla_resultados.sort_values('TOTAL', ascending=False)
                chart_data = pd.DataFrame({
                    'Usuario': top_usuarios.index,
                    'Promedio Diario': top_usuarios['TOTAL'].values
                }).set_index('Usuario')
                
                st.bar_chart(chart_data, height=400)
                #st.caption("📊 Ordenado de mayor a menor promedio de registros")
                
                # --- EXPORTAR ---
                st.divider()
                st.subheader("📤 Exportar Resultados a Excel")
                
                def crear_excel():
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        tabla_resultados_con_total.to_excel(writer, sheet_name='Ingresos Promedio')
                        tabla_tiempos.to_excel(writer, sheet_name='Tiempos Promedio')
                        
                        stats_df = pd.DataFrame({
                            'Métrica': ['Promedio registros/hora', 'Máximo registros/hora', 
                                       'Tiempo promedio admisión', 'Mínimo tiempo admisión'],
                            'Valor': [
                                f"{promedio_general:.2f}",
                                f"{max_registros:.2f} (Usuario: {usuario_max}, Hora: {hora_max})",
                                f"{tiempo_promedio_general:.1f} min" if tiempo_promedio_general else "N/A",
                                f"{min_tiempo:.1f} min (Usuario: {usuario_min}, Hora: {hora_min})" if min_tiempo else "N/A"
                            ]
                        })
                        stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
                        
                        config_df = pd.DataFrame({
                            'Parámetro': ['Rango', 'Día', 'Centros', 'Usuarios', 'Registros'],
                            'Valor': [
                                f"{fecha_inicio} a {fecha_fin}",
                                dia_seleccionado,
                                'Todos' if not centro_sel else ', '.join(centro_sel),
                                'Todos' if not usuario_sel else ', '.join(usuario_sel),
                                len(df_proceso)
                            ]
                        })
                        config_df.to_excel(writer, sheet_name='Configuración', index=False)
                    
                    output.seek(0)
                    return output
                
                st.download_button(
                    label="📥 Descargar Excel",
                    data=crear_excel(),
                    file_name=f"analisis_ingresos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.info("Verifica las columnas del archivo")
    elif uploaded_file is not None:
        st.warning("⚠️ Corrige los errores en los filtros para continuar")
    else:
        st.info("👆 Configura los parámetros y sube un archivo Excel para comenzar el análisis")

# ============================================================================
# PESTAÑA 2: ANÁLISIS DE LLAMADOS
# ============================================================================
with tab2:
    st.header("📞 Análisis de Llamados")
    
    # --- ÚNICO EXPANDER PARA TODA LA CONFIGURACIÓN ---
    with st.expander("⚙️ Configuración y Filtros", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Carga de archivo
            uploaded_file_tab2 = st.file_uploader("📁 Sube tu archivo Excel (.xlsx)", 
                                                type=["xlsx"], 
                                                help="Archivo con información de llamados",
                                                key="tab2_file")
        
        with col2:
            st.markdown("##### 📊 Configuración de análisis")
            st.markdown("*Extraiga de Tramita un informe de atenciones del gestor de turnos con el periodo requerido. Cargue el archivo generado por tramita para analizar*")
            st.markdown("*Posteriormente, seleccione un rango de fechas, un servicio y los usuarios (Gestores de acceso) a analizar*")
        
        # Si hay archivo cargado, mostrar los filtros dentro del MISMO expander
        if uploaded_file_tab2 is not None:
            try:
                # Leer archivo saltando la primera fila
                df_temp = pd.read_excel(uploaded_file_tab2, skiprows=1)
                df_temp.columns = df_temp.columns.astype(str).str.strip()
                
                # Función para encontrar columna
                def encontrar_columna(df, posibles_nombres):
                    columnas_lower = {col: col.lower() for col in df.columns}
                    for posible in posibles_nombres:
                        posible_lower = posible.lower()
                        for col_original, col_lower in columnas_lower.items():
                            if col_lower == posible_lower or posible_lower in col_lower:
                                return col_original
                    return None
                
                # Buscar columnas
                col_hora = encontrar_columna(df_temp, ['hora llegada', 'hora_llegada', 'hora'])
                col_servicio = encontrar_columna(df_temp, ['servicio'])
                col_usuario = encontrar_columna(df_temp, ['usuario atención', 'usuario_atencion', 'usuario'])
                col_tipo = encontrar_columna(df_temp, ['tipo'])
                
                if not all([col_hora, col_servicio, col_usuario]):
                    columnas_encontradas = df_temp.columns.tolist()
                    st.error(f"No se encontraron las columnas necesarias. Columnas disponibles: {', '.join(columnas_encontradas)}")
                    st.stop()
                
                # Renombrar temporalmente para obtener datos
                rename_dict_temp = {
                    col_hora: 'HORA_LLEGADA',
                    col_servicio: 'SERVICIO',
                    col_usuario: 'USUARIO_ATENCION'
                }
                if col_tipo:
                    rename_dict_temp[col_tipo] = 'TIPO'
                
                df_temp = df_temp.rename(columns=rename_dict_temp)
                
                # Procesar fechas
                df_temp["HORA_LLEGADA"] = pd.to_datetime(df_temp["HORA_LLEGADA"], errors='coerce')
                df_temp = df_temp.dropna(subset=["HORA_LLEGADA"])
                
                if df_temp.empty:
                    st.warning("No hay registros con fechas válidas")
                    st.stop()
                
                fecha_min = df_temp["HORA_LLEGADA"].min().date()
                fecha_max = df_temp["HORA_LLEGADA"].max().date()
                servicios_disponibles = sorted(df_temp["SERVICIO"].dropna().unique())
                usuarios_disponibles = sorted(df_temp["USUARIO_ATENCION"].dropna().unique())
                
                st.markdown("---")
                st.markdown("#### 📊 Filtros de selección")
                
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    st.markdown("##### 📅 Rango de fechas")
                    fecha_ini = st.date_input("Inicio", fecha_min, min_value=fecha_min, max_value=fecha_max, key="tab2_fecha_ini")
                    fecha_fin = st.date_input("Fin", fecha_max, min_value=fecha_min, max_value=fecha_max, key="tab2_fecha_fin")
                    
                    if fecha_ini > fecha_fin:
                        st.error("⚠️ Fecha inicio no puede ser mayor que fecha fin")
                
                with col_f2:
                    st.markdown("##### 🏥 Servicios")
                    if servicios_disponibles:
                        servicio_sel = st.multiselect("Seleccionar servicios:", servicios_disponibles, key="tab2_servicios")
                    else:
                        servicio_sel = []
                        st.info("No hay servicios disponibles")
                
                with col_f3:
                    st.markdown("##### 👤 Usuarios (Gestor de acceso)")
                    if usuarios_disponibles:
                        usuario_sel = st.multiselect("Seleccionar usuarios:", usuarios_disponibles, key="tab2_usuarios")
                    else:
                        usuario_sel = []
                        st.info("No hay usuarios disponibles")
            
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.stop()

    # --- PROCESAMIENTO PRINCIPAL (fuera del expander) ---
    if uploaded_file_tab2 is not None and 'fecha_ini' in locals() and fecha_ini <= fecha_fin:
        try:
            # Leer archivo nuevamente para procesamiento
            df_tab2 = pd.read_excel(uploaded_file_tab2, skiprows=1)
            df_tab2.columns = df_tab2.columns.astype(str).str.strip()
            
            # Renombrar columnas
            col_hora = encontrar_columna(df_tab2, ['hora llegada', 'hora_llegada', 'hora'])
            col_servicio = encontrar_columna(df_tab2, ['servicio'])
            col_usuario = encontrar_columna(df_tab2, ['usuario atención', 'usuario_atencion', 'usuario'])
            col_tipo = encontrar_columna(df_tab2, ['tipo'])
            
            rename_dict = {
                col_hora: 'HORA_LLEGADA',
                col_servicio: 'SERVICIO',
                col_usuario: 'USUARIO_ATENCION'
            }
            if col_tipo:
                rename_dict[col_tipo] = 'TIPO'
            
            df_tab2 = df_tab2.rename(columns=rename_dict)
            
            # Procesar fechas
            df_tab2["HORA_LLEGADA"] = pd.to_datetime(df_tab2["HORA_LLEGADA"], errors='coerce')
            df_tab2_limpio = df_tab2.dropna(subset=["HORA_LLEGADA"])
            
            # DataFrame para gráfico temporal (sin filtro de usuarios)
            df_grafico = df_tab2_limpio[
                (df_tab2_limpio["HORA_LLEGADA"].dt.date >= fecha_ini) & 
                (df_tab2_limpio["HORA_LLEGADA"].dt.date <= fecha_fin)
            ]
            
            # Aplicar filtro de servicios al gráfico
            if servicio_sel:
                df_grafico = df_grafico[df_grafico["SERVICIO"].isin(servicio_sel)]
            
            # Aplicar filtros completos para el resto del análisis
            df_filtrado = df_grafico.copy()
            
            if usuario_sel:
                df_filtrado = df_filtrado[df_filtrado["USUARIO_ATENCION"].isin(usuario_sel)]
            
            if df_grafico.empty:
                st.warning("No hay datos con los filtros seleccionados")
                st.stop()
            
            # --- PROCESAMIENTO ---
            st.divider()
            st.info(f"""
            **Configuración de análisis:**
            - **Rango:** {fecha_ini} a {fecha_fin}
            - **Servicios:** {len(servicio_sel)} seleccionados
            - **Usuarios:** {len(usuario_sel)} seleccionados
            - **Registros analizados (con filtro usuarios):** {len(df_filtrado):,}
            """)
            
            # ============================================================
            # GRÁFICO DE LÍNEA DE TIEMPO: MANUALES VS AUTOMÁTICOS (SIN FILTRO DE USUARIOS)
            # ============================================================
            if 'TIPO' in df_grafico.columns:
                st.subheader("📈 Evolución Temporal: Llamados Manuales vs Automáticos")
                st.markdown("*Datos sin filtrar por usuarios (solo rango de fechas y servicios)*")
                
                # Clasificar llamados
                def clasificar_llamado(valor):
                    if pd.isna(valor):
                        return 'NO CLASIFICADO'
                    v = str(valor).lower().strip()
                    if any(p in v for p in ['manual', 'm', 'man']):
                        return 'MANUAL'
                    elif any(p in v for p in ['auto', 'a', 'aut', 'autom']):
                        return 'AUTOMÁTICO'
                    return 'OTRO'
                
                df_grafico['CLASIFICACION'] = df_grafico['TIPO'].apply(clasificar_llamado)
                
                # Agrupar por fecha y clasificación
                df_temporal = df_grafico.copy()
                df_temporal['FECHA_DT'] = pd.to_datetime(df_temporal['FECHA'] if 'FECHA' in df_temporal.columns else df_temporal['HORA_LLEGADA'].dt.date)
                
                # Filtrar solo manuales y automáticos
                df_manual = df_temporal[df_temporal['CLASIFICACION'] == 'MANUAL'].groupby('FECHA_DT').size().reset_index(name='MANUALES')
                df_auto = df_temporal[df_temporal['CLASIFICACION'] == 'AUTOMÁTICO'].groupby('FECHA_DT').size().reset_index(name='AUTOMÁTICOS')
                
                # Crear rango completo de fechas
                fecha_inicio_dt = pd.to_datetime(fecha_ini)
                fecha_fin_dt = pd.to_datetime(fecha_fin)
                rango_fechas = pd.date_range(start=fecha_inicio_dt, end=fecha_fin_dt, freq='D')
                
                # Crear DataFrame con todas las fechas
                df_completo = pd.DataFrame({'FECHA_DT': rango_fechas})
                
                # Merge con los datos
                df_completo = df_completo.merge(df_manual, on='FECHA_DT', how='left')
                df_completo = df_completo.merge(df_auto, on='FECHA_DT', how='left')
                
                # Rellenar NaN con 0
                df_completo['MANUALES'] = df_completo['MANUALES'].fillna(0).astype(int)
                df_completo['AUTOMÁTICOS'] = df_completo['AUTOMÁTICOS'].fillna(0).astype(int)
                
                # Calcular totales
                total_manuales = df_completo['MANUALES'].sum()
                total_automaticos = df_completo['AUTOMÁTICOS'].sum()
                total_general = total_manuales + total_automaticos
                
                # Calcular porcentajes
                pct_manual = (total_manuales / total_general * 100) if total_general > 0 else 0
                pct_auto = (total_automaticos / total_general * 100) if total_general > 0 else 0
                
                # Configurar índice para el gráfico
                df_completo.set_index('FECHA_DT', inplace=True)
                
                # Crear gráfico de líneas
                st.line_chart(
                    df_completo[['MANUALES', 'AUTOMÁTICOS']],
                    height=400,
                    use_container_width=True
                )
                
                # Mostrar estadísticas del período con porcentajes
                col_graf1, col_graf2, col_graf3 = st.columns(3)
                with col_graf1:
                    delta_manual = f"{pct_manual:+.1f}% del total"
                    st.metric(
                        "Total Manuales", 
                        f"{total_manuales:,}",
                        delta=delta_manual,
                        delta_color="off"
                    )
                
                with col_graf2:
                    delta_auto = f"{pct_auto:+.1f}% del total"
                    st.metric(
                        "Total Automáticos", 
                        f"{total_automaticos:,}",
                        delta=delta_auto,
                        delta_color="off"
                    )
                
                with col_graf3:
                    st.metric("Total General", f"{total_general:,}")
                
                st.caption(f"📊 Evolución diaria de llamados del {fecha_ini} al {fecha_fin} (sin filtro de usuarios)")
            
            # --- SELECTOR DE DÍA (antes de la tabla de promedios) ---
            st.divider()
            st.markdown("### 📅 Selección de día para análisis de promedios por agente")
            dias_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos (L-V)"]
            dia_sel = st.selectbox("Día a analizar", dias_opciones, index=7, key="tab2_dia")
            
            # Preparar datos para promedios (con filtro de usuarios)
            if df_filtrado.empty:
                st.warning("No hay datos con los filtros seleccionados")
                st.stop()
            
            df_proceso = df_filtrado.copy()
            df_proceso['FECHA'] = df_proceso['HORA_LLEGADA'].dt.date
            df_proceso['HORA'] = df_proceso['HORA_LLEGADA'].dt.hour
            df_proceso['DIA_SEMANA'] = df_proceso['HORA_LLEGADA'].dt.day_name()
            df_proceso['DIA_SEMANA_NUM'] = df_proceso['HORA_LLEGADA'].dt.dayofweek
            
            mapa_dias = {
                'Lunes': 'Monday', 'Martes': 'Tuesday', 'Miércoles': 'Wednesday',
                'Jueves': 'Thursday', 'Viernes': 'Friday', 'Sábado': 'Saturday', 'Domingo': 'Sunday'
            }
            
            # Filtrar por día
            if dia_sel == "Todos (L-V)":
                df_proceso = df_proceso[df_proceso['DIA_SEMANA_NUM'] < 5]
            else:
                df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == mapa_dias[dia_sel]]
            
            if df_proceso.empty:
                st.warning("No hay datos para el día seleccionado")
                st.stop()
            
            if dia_sel != "Todos (L-V)":
                st.caption(f"📊 Promediando {df_proceso['FECHA'].nunique()} día(s) de {dia_sel}")
            
            # Obtener horas y usuarios para tablas de promedios
            horas = sorted(df_proceso['HORA'].unique())
            horas_fmt = [f"{h}:00" for h in horas]
            usuarios_proc = sorted(df_proceso["USUARIO_ATENCION"].unique())
            
            if not usuarios_proc:
                st.warning("No hay usuarios en los datos filtrados")
                st.stop()
            
            # Crear tabla de promedios
            data = []
            for usuario in usuarios_proc:
                df_u = df_proceso[df_proceso["USUARIO_ATENCION"] == usuario]
                fila = []
                for h in horas:
                    df_h = df_u[df_u['HORA'] == h]
                    if not df_h.empty:
                        conteo = df_h.groupby('FECHA').size()
                        conteo = conteo[conteo > 0]
                        prom = conteo.mean() if not conteo.empty else 0
                        fila.append(round(prom, 2))
                    else:
                        fila.append(0)
                data.append(fila)
            
            tabla_llamados = pd.DataFrame(data, index=usuarios_proc, columns=horas_fmt)
            
            # Calcular estadísticas
            tabla_llamados['TOTAL'] = tabla_llamados[horas_fmt].sum(axis=1).round(2)
            
            minimos = []
            for idx in tabla_llamados.index:
                valores_fila = tabla_llamados.loc[idx, horas_fmt]
                valores_positivos = valores_fila[valores_fila > 0]
                if len(valores_positivos) > 0:
                    minimos.append(valores_positivos.min())
                else:
                    minimos.append(0)
            tabla_llamados['MÍNIMO'] = [round(x, 2) for x in minimos]
            
            tabla_llamados['MÁXIMO'] = tabla_llamados[horas_fmt].max(axis=1).round(2)
            
            # Ordenar por TOTAL descendente
            tabla_llamados = tabla_llamados.sort_values('TOTAL', ascending=False)
            
            # Totales por hora
            totales_hora = tabla_llamados[horas_fmt].sum(axis=0).round(2)
            
            # Fila de totales
            datos_fila_total = {'TOTAL': totales_hora.sum()}
            for hora in horas_fmt:
                datos_fila_total[hora] = totales_hora[hora]
            datos_fila_total['MÍNIMO'] = ''
            datos_fila_total['MÁXIMO'] = ''
            
            fila_total = pd.DataFrame([datos_fila_total], index=['TOTAL'])
            tabla_llamados_con_total = pd.concat([tabla_llamados, fila_total])
            
            # Mostrar tabla de promedios
            st.subheader("📞 Promedio de Llamados por Agente")
            st.markdown("*Cantidad promedio de llamados por hora*")
            
            styler = tabla_llamados_con_total.style
            mascara_usuarios = tabla_llamados_con_total.index != 'TOTAL'
            styler = styler.format("{:.2f}", subset=pd.IndexSlice[tabla_llamados_con_total.index[mascara_usuarios], horas_fmt + ['TOTAL', 'MÍNIMO', 'MÁXIMO']])
            styler = styler.format("{:.2f}", subset=pd.IndexSlice[['TOTAL'], horas_fmt + ['TOTAL']])
            styler = styler.background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[tabla_llamados.index, horas_fmt])
            styler = styler.set_properties(**{'text-align': 'center'})
            
            st.dataframe(styler, use_container_width=True, height=min(400, 50 + (len(usuarios_proc) * 35)))
            
            # --- GRÁFICO TOP USUARIOS ---
            st.divider()
            st.subheader("🏆 Top 10 Usuarios por Actividad")
            
            top_n = min(10, len(tabla_llamados))
            top_usuarios = tabla_llamados.head(top_n)
            
            # Crear DataFrame para el gráfico - ya viene ordenado por tabla_llamados.sort_values('TOTAL', ascending=False)
            chart_data = pd.DataFrame({
                'Usuario': top_usuarios.index,
                'Promedio Diario': top_usuarios['TOTAL'].values
            }).set_index('Usuario')
            
            st.bar_chart(chart_data, height=400)
            st.caption("📊 Ordenado de mayor a menor promedio de llamados")
            
            # --- EXPORTAR ---
            st.divider()
            st.subheader("📤 Exportar Resultados")
            
            def crear_excel_tab2():
                out = BytesIO()
                with pd.ExcelWriter(out, engine='openpyxl') as w:
                    tabla_llamados_con_total.to_excel(w, sheet_name='Llamados Promedio')
                    
                    if 'df_completo' in locals():
                        df_completo.reset_index().to_excel(w, sheet_name='Evolución Diaria', index=False)
                    
                    config = pd.DataFrame({
                        'Parámetro': ['Rango', 'Día', 'Servicios', 'Usuarios', 'Registros'],
                        'Valor': [
                            f"{fecha_ini} a {fecha_fin}",
                            dia_sel,
                            ', '.join(servicio_sel) if servicio_sel else 'Todos',
                            ', '.join(usuario_sel) if usuario_sel else 'Todos',
                            len(df_proceso)
                        ]
                    })
                    config.to_excel(w, sheet_name='Configuración', index=False)
                
                out.seek(0)
                return out
            
            st.download_button(
                label="📥 Descargar Excel",
                data=crear_excel_tab2(),
                file_name=f"analisis_llamados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("👆 Configura los parámetros y sube un archivo Excel para comenzar el análisis")


# ============================================================================
# PESTAÑA 3: ANÁLISIS DE AUDITORÍA DE ADMISIONES
# ============================================================================
with tab3:
    st.header("🔍 Auditoría de Admisiones")
    
    # --- ÚNICO EXPANDER PARA TODA LA CONFIGURACIÓN ---
    with st.expander("⚙️ Configuración y Filtros", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Carga de archivo
            uploaded_file_tab3 = st.file_uploader("📁 Sube tu archivo de auditoría (.xlsx)", 
                                                type=["xlsx"], 
                                                help="Archivo debe contener columna 'fechaRegistro' para el análisis",
                                                key="tab3_file")
        
        with col2:
            st.markdown("##### 📊 Configuración de análisis")
            st.markdown("*Cargue el archivo de auditoría de admisiones para analizar los registros por fecha y motivo*")
            st.markdown("*La columna 'fechaRegistro' será utilizada como referencia para los promedios diarios y por hora*")
        
        # Si hay archivo cargado, mostrar los filtros
        if uploaded_file_tab3 is not None:
            try:
                # Leer el archivo para obtener opciones de filtros
                df_temp = pd.read_excel(uploaded_file_tab3)
                
                # Verificar que existe la columna fechaRegistro
                if 'fechaRegistro' not in df_temp.columns:
                    st.error("No se encontró la columna 'fechaRegistro' en el archivo. Esta columna es requerida.")
                    st.stop()
                
                # Procesar fechas
                df_temp["fechaRegistro"] = pd.to_datetime(df_temp["fechaRegistro"], errors='coerce')
                df_temp = df_temp.dropna(subset=["fechaRegistro"])
                
                fecha_minima = df_temp["fechaRegistro"].min().date()
                fecha_maxima = df_temp["fechaRegistro"].max().date()
                
                # Buscar el último campo que contenga 'nombre' (case insensitive)
                columnas_nombre = [col for col in df_temp.columns if 'nombre' in col.lower()]
                if not columnas_nombre:
                    st.error("No se encontró ninguna columna con 'nombre' en el archivo.")
                    st.stop()
                
                # Seleccionar el último campo 'nombre' (el que aparece al final de la tabla)
                col_nombre = columnas_nombre[-1]
                
                # Verificar que existe la columna motivo
                columnas_motivo = [col for col in df_temp.columns if 'motivo' in col.lower()]
                if not columnas_motivo:
                    st.error("No se encontró ninguna columna con 'motivo' en el archivo.")
                    st.stop()
                
                col_motivo = columnas_motivo[0]  # Tomamos la primera columna que contenga 'motivo'
                
                st.markdown("---")
                st.markdown("#### 📊 Filtros de selección")
                
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    st.markdown("##### 📅 Rango de fechas")
                    fecha_inicio_tab3 = st.date_input(
                        "Fecha inicio:",
                        value=fecha_minima,
                        min_value=fecha_minima,
                        max_value=fecha_maxima,
                        key="tab3_fecha_inicio"
                    )
                    fecha_fin_tab3 = st.date_input(
                        "Fecha fin:",
                        value=fecha_maxima,
                        min_value=fecha_minima,
                        max_value=fecha_maxima,
                        key="tab3_fecha_fin"
                    )
                    
                    if fecha_inicio_tab3 > fecha_fin_tab3:
                        st.error("⚠️ Fecha inicio no puede ser mayor que fecha fin")
                
                with col_f2:
                    st.markdown(f"##### 👤 Usuarios (Gestor de acceso - Back Office)")
                    nombres_disponibles = sorted(df_temp[col_nombre].dropna().unique())
                    usuario_sel_tab3 = st.multiselect(
                        "Seleccionar usuarios:", 
                        options=nombres_disponibles,
                        help="Selecciona uno o más usuarios",
                        key="tab3_usuario"
                    )
                
                with col_f3:
                    st.markdown(f"##### 📋 Motivos (campo '{col_motivo}')")
                    motivos_disponibles = sorted(df_temp[col_motivo].dropna().unique())
                    motivo_sel_tab3 = st.multiselect(
                        "Seleccionar motivos:", 
                        options=motivos_disponibles,
                        help="Selecciona uno o más motivos",
                        key="tab3_motivo"
                    )
            
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.stop()

    # --- PROCESAMIENTO PRINCIPAL ---
    if uploaded_file_tab3 is not None and 'fecha_inicio_tab3' in locals() and fecha_inicio_tab3 <= fecha_fin_tab3:
        try:
            # Leer el archivo nuevamente para procesamiento
            df = pd.read_excel(uploaded_file_tab3)
            
            # Identificar columnas nuevamente
            columnas_nombre = [col for col in df.columns if 'nombre' in col.lower()]
            col_nombre = columnas_nombre[-1]  # Último campo 'nombre'
            
            columnas_motivo = [col for col in df.columns if 'motivo' in col.lower()]
            col_motivo = columnas_motivo[0]  # Primer campo 'motivo'
            
            # Procesar fechas
            df["fechaRegistro"] = pd.to_datetime(df["fechaRegistro"], errors='coerce')
            df = df.dropna(subset=["fechaRegistro"])
            
            # Aplicar filtros
            df_filtrado = df[
                (df["fechaRegistro"].dt.date >= fecha_inicio_tab3) & 
                (df["fechaRegistro"].dt.date <= fecha_fin_tab3)
            ]
            
            if usuario_sel_tab3:
                df_filtrado = df_filtrado[df_filtrado[col_nombre].isin(usuario_sel_tab3)]
            
            if motivo_sel_tab3:
                df_filtrado = df_filtrado[df_filtrado[col_motivo].isin(motivo_sel_tab3)]

            if not df_filtrado.empty:
                st.divider()
                
                # Mostrar configuración seleccionada
                st.info(f"""
                **Configuración de análisis:**
                - **Rango:** {fecha_inicio_tab3} a {fecha_fin_tab3}
                - **Usuarios (campo '{col_nombre}'):** {', '.join(usuario_sel_tab3) if usuario_sel_tab3 else 'Todos'}
                - **Motivos (campo '{col_motivo}'):** {', '.join(motivo_sel_tab3) if motivo_sel_tab3 else 'Todos'}
                - **Registros analizados:** {len(df_filtrado):,}
                """)
                
                # --- GRÁFICO DE DISTRIBUCIÓN POR MOTIVO ---
                st.subheader("📊 Distribución de Auditorías por Motivo")
                
                # Calcular distribución por motivo
                motivo_counts = df_filtrado[col_motivo].value_counts()
                
                # Crear DataFrame para el gráfico
                motivo_df = pd.DataFrame({
                    'Motivo': motivo_counts.index,
                    'Cantidad': motivo_counts.values
                })
                
                # Mostrar gráfico de barras
                st.bar_chart(motivo_df.set_index('Motivo'), height=400)
                
                # Mostrar tabla con porcentajes
                st.subheader("📋 Detalle por Motivo")
                total_registros = motivo_counts.sum()
                motivo_pct = (motivo_counts / total_registros * 100).round(1)
                motivo_resumen = pd.DataFrame({
                    'Motivo': motivo_counts.index,
                    'Cantidad': motivo_counts.values,
                    'Porcentaje': [f"{pct}%" for pct in motivo_pct.values]
                }).sort_values('Cantidad', ascending=False)
                
                st.dataframe(motivo_resumen, use_container_width=True, hide_index=True)
                
                st.divider()
                
                # --- GRÁFICO TOP USUARIOS (TOTAL DE REGISTROS) ---
                st.subheader(f"🏆 Top 10 Usuarios por Total de Auditorías (campo '{col_nombre}')")
                
                # Calcular total de registros por usuario (sin promediar por hora)
                usuarios_totales = df_filtrado[col_nombre].value_counts().head(10)
                
                # Crear DataFrame para el gráfico
                top_usuarios_chart = pd.DataFrame({
                    'Usuario': usuarios_totales.index,
                    'Total Registros': usuarios_totales.values
                }).set_index('Usuario')
                
                st.bar_chart(top_usuarios_chart, height=400)
                
                st.divider()
                
                # --- SELECTOR DE DÍA PARA ANÁLISIS DE PROMEDIOS ---
                st.markdown("### 📅 Selección de día para análisis de promedios por hora")
                dia_semana_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
                dia_seleccionado_tab3 = st.selectbox(
                    "Día de la semana a analizar:",
                    options=dia_semana_opciones,
                    index=7,
                    help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                    key="tab3_dia"
                )
                
                # Preparar datos para promedios
                df_proceso = df_filtrado.copy()
                df_proceso['FECHA'] = df_proceso["fechaRegistro"].dt.date
                df_proceso['HORA'] = df_proceso["fechaRegistro"].dt.hour
                df_proceso['DIA_SEMANA'] = df_proceso["fechaRegistro"].dt.day_name()
                df_proceso['DIA_SEMANA_NUM'] = df_proceso["fechaRegistro"].dt.dayofweek
                
                # Mapeo de días
                mapa_dias = {
                    'Lunes': 'Monday', 'Martes': 'Tuesday', 'Miércoles': 'Wednesday',
                    'Jueves': 'Thursday', 'Viernes': 'Friday', 'Sábado': 'Saturday', 'Domingo': 'Sunday'
                }
                
                # Filtrar por día
                if dia_seleccionado_tab3 == "Todos los días (L-V)":
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA_NUM'] < 5]
                    if df_proceso.empty:
                        st.warning("No hay registros para Lunes a Viernes.")
                        st.stop()
                else:
                    dia_ingles = mapa_dias[dia_seleccionado_tab3]
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_ingles]
                    if df_proceso.empty:
                        st.warning(f"No hay registros para {dia_seleccionado_tab3}.")
                        st.stop()
                    dias_unicos = df_proceso['FECHA'].nunique()
                    st.caption(f"📊 Promediando {dias_unicos} día(s) de {dia_seleccionado_tab3}")
                
                # Identificar horas con registros
                horas_con_registros = sorted(df_proceso['HORA'].unique())
                horas_formateadas = [f"{h}:00" for h in horas_con_registros]
                
                # Obtener usuarios del filtro (o todos si no hay filtro)
                usuarios_proceso = sorted(df_proceso[col_nombre].unique())
                
                if not usuarios_proceso:
                    st.warning("No hay usuarios en los datos filtrados.")
                    st.stop()
                
                # Crear tabla de promedios por hora
                data = []
                for usuario in usuarios_proceso:
                    df_usuario = df_proceso[df_proceso[col_nombre] == usuario]
                    fila = []
                    for hora in horas_con_registros:
                        df_hora = df_usuario[df_usuario['HORA'] == hora]
                        if not df_hora.empty:
                            conteo_por_dia = df_hora.groupby('FECHA').size()
                            conteo_por_dia = conteo_por_dia[conteo_por_dia > 0]
                            promedio = conteo_por_dia.mean() if not conteo_por_dia.empty else 0
                            fila.append(round(promedio, 2))
                        else:
                            fila.append(0)
                    data.append(fila)
                
                tabla_resultados = pd.DataFrame(data, index=usuarios_proceso, columns=horas_formateadas)
                
                # Calcular estadísticas
                tabla_resultados['TOTAL'] = tabla_resultados[horas_formateadas].sum(axis=1).round(2)
                
                minimos = []
                for idx in tabla_resultados.index:
                    valores_fila = tabla_resultados.loc[idx, horas_formateadas]
                    valores_positivos = valores_fila[valores_fila > 0]
                    if len(valores_positivos) > 0:
                        minimos.append(valores_positivos.min())
                    else:
                        minimos.append(0)
                tabla_resultados['MÍNIMO'] = [round(x, 2) for x in minimos]
                
                tabla_resultados['MÁXIMO'] = tabla_resultados[horas_formateadas].max(axis=1).round(2)
                
                # Ordenar por TOTAL descendente
                tabla_resultados = tabla_resultados.sort_values('TOTAL', ascending=False)
                
                # Totales por hora
                totales_por_hora = tabla_resultados[horas_formateadas].sum(axis=0).round(2)
                
                # Fila de totales
                datos_fila_total = {'TOTAL': totales_por_hora.sum()}
                for hora in horas_formateadas:
                    datos_fila_total[hora] = totales_por_hora[hora]
                datos_fila_total['MÍNIMO'] = ''
                datos_fila_total['MÁXIMO'] = ''
                
                fila_total = pd.DataFrame([datos_fila_total], index=['TOTAL'])
                tabla_resultados_con_total = pd.concat([tabla_resultados, fila_total])
                
                # Mostrar tabla de promedios
                st.subheader(f"📊 Promedio de Auditorías por Usuario (por hora) - Campo '{col_nombre}'")
                st.markdown("*Cantidad promedio de auditorías realizadas por hora (basado en fechaRegistro)*")
                
                styler = tabla_resultados_con_total.style
                mascara_usuarios = tabla_resultados_con_total.index != 'TOTAL'
                styler = styler.format("{:.2f}", subset=pd.IndexSlice[tabla_resultados_con_total.index[mascara_usuarios], horas_formateadas + ['TOTAL', 'MÍNIMO', 'MÁXIMO']])
                styler = styler.format("{:.2f}", subset=pd.IndexSlice[['TOTAL'], horas_formateadas + ['TOTAL']])
                styler = styler.background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[tabla_resultados.index, horas_formateadas])
                styler = styler.set_properties(**{'text-align': 'center'})
                
                st.dataframe(styler, use_container_width=True, height=min(400, 50 + (len(usuarios_proceso) * 35)))
                
                # --- EXPORTAR ---
                st.divider()
                st.subheader("📤 Exportar Resultados a Excel")
                
                def crear_excel_tab3():
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # Hoja de promedios por hora
                        tabla_resultados_con_total.to_excel(writer, sheet_name='Auditorías Promedio')
                        
                        # Hoja de distribución por motivo
                        motivo_resumen.to_excel(writer, sheet_name='Distribución por Motivo', index=False)
                        
                        # Hoja de totales por usuario
                        totales_usuario = pd.DataFrame({
                            'Usuario': df_filtrado[col_nombre].value_counts().index,
                            'Total Registros': df_filtrado[col_nombre].value_counts().values
                        })
                        totales_usuario.to_excel(writer, sheet_name='Totales por Usuario', index=False)
                        
                        # Hoja de configuración
                        config_df = pd.DataFrame({
                            'Parámetro': ['Rango', 'Día', 'Usuarios', 'Motivos', 'Registros'],
                            'Valor': [
                                f"{fecha_inicio_tab3} a {fecha_fin_tab3}",
                                dia_seleccionado_tab3,
                                'Todos' if not usuario_sel_tab3 else ', '.join(usuario_sel_tab3),
                                'Todos' if not motivo_sel_tab3 else ', '.join(motivo_sel_tab3),
                                len(df_proceso)
                            ]
                        })
                        config_df.to_excel(writer, sheet_name='Configuración', index=False)
                    
                    output.seek(0)
                    return output
                
                st.download_button(
                    label="📥 Descargar Excel",
                    data=crear_excel_tab3(),
                    file_name=f"analisis_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            else:
                st.warning("No hay datos con los filtros seleccionados")
        
        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.info("Verifica las columnas del archivo (debe contener: fechaRegistro, al menos un campo 'nombre' y un campo 'motivo')")
    elif uploaded_file_tab3 is not None:
        st.warning("⚠️ Corrige los errores en los filtros para continuar")
    else:
        st.info("👆 Configura los parámetros y sube un archivo Excel para comenzar el análisis de auditoría")
