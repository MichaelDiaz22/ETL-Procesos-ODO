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
# PESTAÑA 1: ANÁLISIS DE INGRESOS (VERSIÓN COMPLETA)
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
                    if centros_disponibles:
                        centro_sel = st.multiselect(
                            "Seleccionar centros:", 
                            options=centros_disponibles,
                            help="Selecciona uno o más centros para filtrar los datos",
                            key="tab1_centro"
                        )
                    else:
                        centro_sel = []
                        st.info("No hay centros disponibles")
                
                with col_f3:
                    st.markdown("##### 👤 Usuarios (Gestor de acceso)")
                    
                    # Aplicar filtros de fecha y centros para obtener usuarios disponibles
                    df_filtro_base = df_temp[
                        (df_temp["FECHA CREACION"].dt.date >= fecha_inicio) & 
                        (df_temp["FECHA CREACION"].dt.date <= fecha_fin)
                    ].copy()
                    
                    # Aplicar filtro de centros si hay alguno seleccionado
                    if centro_sel:
                        df_filtro_base = df_filtro_base[df_filtro_base["CENTRO ATENCION"].isin(centro_sel)]
                    
                    # Obtener usuarios únicos que tienen registros en el rango de fechas y centros seleccionados
                    usuarios_disponibles_filtrados = sorted(df_filtro_base["USUARIO CREA INGRESO"].dropna().unique())
                    
                    # Mostrar información de cuántos usuarios están disponibles
                    st.caption(f"📊 {len(usuarios_disponibles_filtrados)} usuarios disponibles para los filtros seleccionados")
                    
                    if usuarios_disponibles_filtrados:
                        usuario_sel = st.multiselect(
                            "Seleccionar usuarios:", 
                            options=usuarios_disponibles_filtrados,
                            help=f"Usuarios con registros en el rango de fechas y centros seleccionados (dejar vacío para mostrar todos)",
                            key="tab1_usuario"
                        )
                    else:
                        usuario_sel = []
                        st.info("No hay usuarios disponibles para los filtros seleccionados")
            
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
            
            # DataFrame base con filtros de fecha y centros
            df_base = df[
                (df["FECHA CREACION"].dt.date >= fecha_inicio) & 
                (df["FECHA CREACION"].dt.date <= fecha_fin)
            ]
            
            if centro_sel:
                df_base = df_base[df_base["CENTRO ATENCION"].isin(centro_sel)]
            
            # Aplicar filtro de usuarios SOLO si hay selección
            if usuario_sel:
                df_filtrado = df_base[df_base["USUARIO CREA INGRESO"].isin(usuario_sel)]
                st.info(f"✅ Mostrando datos solo para {len(usuario_sel)} usuario(s) seleccionado(s)")
            else:
                df_filtrado = df_base.copy()
                st.info(f"📊 Mostrando datos para TODOS los usuarios ({len(df_base['USUARIO CREA INGRESO'].unique())} usuarios)")

            if not df_filtrado.empty:
                st.divider()
                
                # Mostrar configuración seleccionada
                st.info(f"""
                **Configuración de análisis:**
                - **Rango:** {fecha_inicio} a {fecha_fin}
                - **Centros seleccionados:** {len(centro_sel)} centros
                - **Usuarios disponibles en filtros:** {len(usuarios_disponibles_filtrados) if 'usuarios_disponibles_filtrados' in locals() else 0}
                - **Usuarios seleccionados:** {len(usuario_sel) if usuario_sel else 'TODOS'}
                - **Usuarios en datos mostrados:** {df_filtrado['USUARIO CREA INGRESO'].nunique()}
                - **Registros analizados:** {len(df_filtrado):,}
                """)
                
                # --- SELECTOR DE DÍA ---
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
                
                # Crear DataFrame para el gráfico
                chart_data = pd.DataFrame({
                    'Usuario': top_usuarios.index,
                    'Promedio Diario': top_usuarios['TOTAL'].values
                }).set_index('Usuario')
                
                st.bar_chart(chart_data, height=400)
                
                # ============================================================
                # NUEVA TABLA: Detalle de usuarios con totales y porcentajes
                # ============================================================
                st.divider()
                st.subheader("📊 Detalle de Registros por Usuario")

                # Determinar qué usuarios mostrar
                if usuario_sel:
                    usuarios_detalle = usuario_sel
                    titulo_detalle = "Usuarios Seleccionados"
                else:
                    usuarios_detalle = sorted(usuarios_proceso)
                    titulo_detalle = "Todos los Usuarios"

                if usuarios_detalle:
                    # Calcular total de registros para cada usuario (sin promediar, total real)
                    total_registros_por_usuario = []
                    
                    for usuario in usuarios_detalle:
                        df_usuario = df_filtrado[df_filtrado["USUARIO CREA INGRESO"] == usuario]
                        total_registros = len(df_usuario)
                        total_registros_por_usuario.append(total_registros)
                    
                    # Crear DataFrame de detalle
                    detalle_usuarios_df = pd.DataFrame({
                        'Usuario': usuarios_detalle,
                        'Total Registros': total_registros_por_usuario,
                        'Promedio Diario': [tabla_resultados.loc[usuario, 'TOTAL'] if usuario in tabla_resultados.index else 0 for usuario in usuarios_detalle]
                    })
                    
                    # Calcular el gran total para porcentajes
                    gran_total = detalle_usuarios_df['Total Registros'].sum()
                    
                    # Calcular porcentaje
                    detalle_usuarios_df['Porcentaje del Total'] = (detalle_usuarios_df['Total Registros'] / gran_total * 100).round(1).astype(str) + '%'
                    
                    # Ordenar por total de registros descendente
                    detalle_usuarios_df = detalle_usuarios_df.sort_values('Total Registros', ascending=False)
                    
                    # Mostrar la tabla
                    st.dataframe(
                        detalle_usuarios_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Usuario": "👤 Usuario",
                            "Total Registros": st.column_config.NumberColumn("📊 Total Registros", format="%d"),
                            "Promedio Diario": st.column_config.NumberColumn("📈 Promedio Diario", format="%.2f"),
                            "Porcentaje del Total": "📊 % del Total"
                        }
                    )
                    
                    # Mostrar estadísticas
                    col_det1, col_det2, col_det3, col_det4 = st.columns(4)
                    with col_det1:
                        st.metric("Total Usuarios", len(usuarios_detalle))
                    with col_det2:
                        st.metric("Total Registros", f"{gran_total:,}")
                    with col_det3:
                        usuario_top = detalle_usuarios_df.iloc[0]['Usuario'] if not detalle_usuarios_df.empty else "N/A"
                        st.metric("Usuario con más registros", usuario_top)
                    with col_det4:
                        pct_top = detalle_usuarios_df.iloc[0]['Porcentaje del Total'] if not detalle_usuarios_df.empty else "0%"
                        st.metric("% del Top", pct_top)
                    
                    # Mostrar información de centros
                    st.caption(f"📊 Basado en {len(centro_sel)} centro(s) seleccionado(s): {', '.join(centro_sel) if centro_sel else 'Todos'}")

                else:
                    st.info("No hay usuarios para mostrar")

                # ============================================================
                # TABLA: Distribución de ingresos por ENTIDAD y usuario
                # ============================================================
                st.divider()
                st.subheader("📋 Distribución de Ingresos por Entidad y Usuario")

                # Verificar si existe la columna ENTIDAD en los datos
                if 'ENTIDAD' in df_filtrado.columns:
                    # Usar los usuarios seleccionados en el filtro (usuario_sel)
                    if usuario_sel:
                        # Filtrar datos para los usuarios seleccionados
                        df_entidades = df_filtrado[df_filtrado['USUARIO CREA INGRESO'].isin(usuario_sel)].copy()
                        
                        if not df_entidades.empty:
                            # Crear tabla pivote: ENTIDAD vs USUARIOS
                            tabla_pivote = pd.pivot_table(
                                df_entidades,
                                values='FECHA CREACION',
                                index='ENTIDAD',
                                columns='USUARIO CREA INGRESO',
                                aggfunc='count',
                                fill_value=0
                            ).reset_index()
                            
                            # Asegurar que todas las columnas de usuarios estén presentes
                            for usuario in usuario_sel:
                                if usuario not in tabla_pivote.columns:
                                    tabla_pivote[usuario] = 0
                            
                            # Reordenar columnas
                            columnas_ordenadas = ['ENTIDAD'] + [u for u in usuario_sel if u in tabla_pivote.columns]
                            tabla_pivote = tabla_pivote[columnas_ordenadas]
                            
                            # Agregar columna de total por entidad
                            tabla_pivote['TOTAL'] = tabla_pivote[usuario_sel].sum(axis=1)
                            
                            # Ordenar por total descendente
                            tabla_pivote = tabla_pivote.sort_values('TOTAL', ascending=False)
                            
                            # Mostrar la tabla
                            st.dataframe(
                                tabla_pivote,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "ENTIDAD": "🏢 Entidad",
                                    "TOTAL": "📊 Total"
                                }
                            )
                            
                            # Mostrar estadísticas de la tabla
                            col_ent1, col_ent2, col_ent3 = st.columns(3)
                            with col_ent1:
                                st.metric("Total Entidades", len(tabla_pivote))
                            with col_ent2:
                                st.metric("Total Registros", tabla_pivote['TOTAL'].sum())
                            with col_ent3:
                                entidad_top = tabla_pivote.iloc[0]['ENTIDAD'] if not tabla_pivote.empty else "N/A"
                                st.metric("Entidad con más registros", entidad_top)
                            
                            # Mostrar información sobre centros seleccionados
                            st.caption(f"📊 Basado en {len(centro_sel)} centro(s) seleccionado(s): {', '.join(centro_sel) if centro_sel else 'Todos'}")
                        
                        else:
                            st.info("No hay registros para los usuarios seleccionados en el filtro")
                    
                    else:
                        st.info("👆 Selecciona usuarios en el filtro para ver la distribución por entidad")

                else:
                    st.warning("No se encontró la columna 'ENTIDAD' en el archivo cargado")
                    with st.expander("Ver columnas disponibles en el archivo"):
                        st.write(df_filtrado.columns.tolist())
                
                # --- EXPORTAR ---
                st.divider()
                st.subheader("📤 Exportar Resultados a Excel")
                
                def crear_excel():
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        tabla_resultados_con_total.to_excel(writer, sheet_name='Ingresos Promedio')
                        tabla_tiempos.to_excel(writer, sheet_name='Tiempos Promedio')
                        
                        if 'detalle_usuarios_df' in locals() and not detalle_usuarios_df.empty:
                            detalle_usuarios_df.to_excel(writer, sheet_name='Detalle Usuarios', index=False)
                        
                        if 'tabla_pivote' in locals() and not tabla_pivote.empty:
                            tabla_pivote.to_excel(writer, sheet_name='Distribución por Entidad', index=False)
                        
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
                            'Parámetro': ['Rango', 'Día', 'Centros', 'Usuarios disponibles', 'Usuarios seleccionados', 'Usuarios mostrados', 'Registros'],
                            'Valor': [
                                f"{fecha_inicio} a {fecha_fin}",
                                dia_seleccionado,
                                ', '.join(centro_sel) if centro_sel else 'Todos',
                                str(len(usuarios_disponibles_filtrados)) if 'usuarios_disponibles_filtrados' in locals() else '0',
                                ', '.join(usuario_sel) if usuario_sel else 'TODOS',
                                str(len(detalle_usuarios_df)) if 'detalle_usuarios_df' in locals() else '0',
                                str(len(df_proceso))
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
# PESTAÑA 2: ANÁLISIS DE TURNOS ATENDIDOS (VERSIÓN COMPLETA)
# ============================================================================
with tab2:
    st.header("📆 Análisis de turnos atendidos")
    
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
                
                # Función mejorada para encontrar columna
                def encontrar_columna(df, posibles_nombres):
                    """
                    Busca una columna en el DataFrame que coincida con alguno de los nombres posibles
                    """
                    columnas_lower = {col: col.lower().strip() for col in df.columns}
                    for posible in posibles_nombres:
                        posible_lower = posible.lower().strip()
                        for col_original, col_lower in columnas_lower.items():
                            if col_lower == posible_lower or posible_lower in col_lower:
                                return col_original
                    return None
                
                # Buscar columnas
                col_hora_llegada = encontrar_columna(df_temp, ['hora llegada', 'hora_llegada', 'hora'])
                col_hora_finalizacion = encontrar_columna(df_temp, ['hora finalización', 'hora_finalizacion', 'hora fin', 'hora final', 'fechafin'])
                col_servicio = encontrar_columna(df_temp, ['servicio'])
                col_usuario = encontrar_columna(df_temp, ['user atención', 'user_atencion', 'usuario atención', 'usuario_atencion', 'usuario', 'user'])
                col_tipo = encontrar_columna(df_temp, ['tipo'])
                col_tiempo_atencion = encontrar_columna(df_temp, ['tiempo atención', 'tiempo_atencion', 'tiempo de atención', 'duración atención'])
                col_llamados = encontrar_columna(df_temp, ['llamados', 'cantidad llamados', 'num llamados', 'número llamados', 'nro llamados'])
                
                # Verificar si encontramos las columnas necesarias
                if not all([col_hora_llegada, col_servicio]):
                    st.error(f"No se encontraron las columnas de hora y servicio. Hora Llegada: {col_hora_llegada}, Servicio: {col_servicio}")
                    st.stop()
                
                if not col_usuario:
                    st.error("No se encontró la columna de usuario. Buscamos: 'User Atención', 'usuario atención', etc.")
                    st.stop()
                
                if not col_hora_finalizacion:
                    st.warning("No se encontró la columna de hora finalización. El tiempo de espera entre atenciones no podrá calcularse correctamente.")
                
                # Renombrar temporalmente para obtener datos
                rename_dict_temp = {
                    col_hora_llegada: 'HORA_LLEGADA',
                    col_servicio: 'SERVICIO',
                    col_usuario: 'USUARIO_ATENCION'
                }
                if col_tipo:
                    rename_dict_temp[col_tipo] = 'TIPO'
                if col_hora_finalizacion:
                    rename_dict_temp[col_hora_finalizacion] = 'HORA_FINALIZACION'
                if col_tiempo_atencion:
                    rename_dict_temp[col_tiempo_atencion] = 'TIEMPO_ATENCION'
                if col_llamados:
                    rename_dict_temp[col_llamados] = 'LLAMADOS'
                
                df_temp = df_temp.rename(columns=rename_dict_temp)
                
                # Procesar fechas
                df_temp["HORA_LLEGADA"] = pd.to_datetime(df_temp["HORA_LLEGADA"], errors='coerce')
                if 'HORA_FINALIZACION' in df_temp.columns:
                    df_temp["HORA_FINALIZACION"] = pd.to_datetime(df_temp["HORA_FINALIZACION"], errors='coerce')
                
                df_temp = df_temp.dropna(subset=["HORA_LLEGADA"])
                
                # Procesar tiempo de atención (convertir a minutos si es necesario)
                if 'TIEMPO_ATENCION' in df_temp.columns:
                    if df_temp['TIEMPO_ATENCION'].dtype == 'object':
                        def tiempo_a_minutos(t):
                            if pd.isna(t):
                                return np.nan
                            try:
                                if isinstance(t, str):
                                    partes = t.split(':')
                                    if len(partes) == 3:
                                        return int(partes[0]) * 60 + int(partes[1]) + int(partes[2]) / 60
                                    elif len(partes) == 2:
                                        return int(partes[0]) * 60 + int(partes[1])
                                return float(t)
                            except:
                                return np.nan
                        
                        df_temp['TIEMPO_ATENCION'] = df_temp['TIEMPO_ATENCION'].apply(tiempo_a_minutos)
                    else:
                        df_temp['TIEMPO_ATENCION'] = pd.to_numeric(df_temp['TIEMPO_ATENCION'], errors='coerce')
                
                # Procesar llamados (asegurar que sea numérico)
                if 'LLAMADOS' in df_temp.columns:
                    df_temp['LLAMADOS'] = pd.to_numeric(df_temp['LLAMADOS'], errors='coerce').fillna(1).astype(int)
                else:
                    # Si no existe la columna, asumir que cada registro es 1 llamado
                    df_temp['LLAMADOS'] = 1
                
                if df_temp.empty:
                    st.warning("No hay registros con fechas válidas")
                    st.stop()
                
                fecha_min = df_temp["HORA_LLEGADA"].min().date()
                fecha_max = df_temp["HORA_LLEGADA"].max().date()
                servicios_disponibles = sorted(df_temp["SERVICIO"].dropna().unique())
                
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
                        servicio_sel = st.multiselect(
                            "Seleccionar servicios:", 
                            servicios_disponibles, 
                            key="tab2_servicios",
                            help="Selecciona uno o más servicios para filtrar los datos"
                        )
                    else:
                        servicio_sel = []
                        st.info("No hay servicios disponibles")
                
                with col_f3:
                    st.markdown("##### 👤 Usuarios (Gestor de acceso)")
                    
                    # Aplicar filtros de fecha y servicios para obtener usuarios disponibles
                    df_filtro_base = df_temp[
                        (df_temp["HORA_LLEGADA"].dt.date >= fecha_ini) & 
                        (df_temp["HORA_LLEGADA"].dt.date <= fecha_fin)
                    ].copy()
                    
                    # Aplicar filtro de servicios si hay alguno seleccionado
                    if servicio_sel:
                        df_filtro_base = df_filtro_base[df_filtro_base["SERVICIO"].isin(servicio_sel)]
                    
                    # Obtener usuarios únicos que tienen registros en el rango de fechas y servicios seleccionados
                    usuarios_disponibles_filtrados = sorted([str(u) for u in df_filtro_base["USUARIO_ATENCION"].dropna().unique()])
                    
                    # Mostrar información de cuántos usuarios están disponibles
                    st.caption(f"📊 {len(usuarios_disponibles_filtrados)} usuarios disponibles para los filtros seleccionados")
                    
                    if usuarios_disponibles_filtrados:
                        usuario_sel = st.multiselect(
                            "Seleccionar usuarios:", 
                            options=usuarios_disponibles_filtrados,
                            help=f"Usuarios con registros en el rango de fechas y servicios seleccionados (dejar vacío para mostrar todos)",
                            key="tab2_usuarios"
                        )
                    else:
                        usuario_sel = []
                        st.info("No hay usuarios disponibles para los filtros seleccionados")
            
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.stop()

    # --- PROCESAMIENTO PRINCIPAL (fuera del expander) ---
    if uploaded_file_tab2 is not None and 'fecha_ini' in locals() and fecha_ini <= fecha_fin:
        try:
            # Leer archivo nuevamente para procesamiento
            df_tab2 = pd.read_excel(uploaded_file_tab2, skiprows=1)
            df_tab2.columns = df_tab2.columns.astype(str).str.strip()
            
            # Renombrar columnas (usando la misma lógica)
            col_hora_llegada = encontrar_columna(df_tab2, ['hora llegada', 'hora_llegada', 'hora'])
            col_hora_finalizacion = encontrar_columna(df_tab2, ['hora finalización', 'hora_finalizacion', 'hora fin', 'hora final', 'fechafin'])
            col_servicio = encontrar_columna(df_tab2, ['servicio'])
            col_usuario = encontrar_columna(df_tab2, ['user atención', 'user_atencion', 'usuario atención', 'usuario_atencion', 'usuario', 'user'])
            col_tipo = encontrar_columna(df_tab2, ['tipo'])
            col_tiempo_atencion = encontrar_columna(df_tab2, ['tiempo atención', 'tiempo_atencion', 'tiempo de atención', 'duración atención'])
            col_llamados = encontrar_columna(df_tab2, ['llamados', 'cantidad llamados', 'num llamados', 'número llamados', 'nro llamados'])
            
            rename_dict = {
                col_hora_llegada: 'HORA_LLEGADA',
                col_servicio: 'SERVICIO',
                col_usuario: 'USUARIO_ATENCION'
            }
            if col_tipo:
                rename_dict[col_tipo] = 'TIPO'
            if col_hora_finalizacion:
                rename_dict[col_hora_finalizacion] = 'HORA_FINALIZACION'
            if col_tiempo_atencion:
                rename_dict[col_tiempo_atencion] = 'TIEMPO_ATENCION'
            if col_llamados:
                rename_dict[col_llamados] = 'LLAMADOS'
            
            df_tab2 = df_tab2.rename(columns=rename_dict)
            
            # Procesar fechas
            df_tab2["HORA_LLEGADA"] = pd.to_datetime(df_tab2["HORA_LLEGADA"], errors='coerce')
            if 'HORA_FINALIZACION' in df_tab2.columns:
                df_tab2["HORA_FINALIZACION"] = pd.to_datetime(df_tab2["HORA_FINALIZACION"], errors='coerce')
            
            df_tab2_limpio = df_tab2.dropna(subset=["HORA_LLEGADA"])
            
            # Procesar tiempo de atención
            if 'TIEMPO_ATENCION' in df_tab2_limpio.columns:
                if df_tab2_limpio['TIEMPO_ATENCION'].dtype == 'object':
                    def tiempo_a_minutos(t):
                        if pd.isna(t):
                            return np.nan
                        try:
                            if isinstance(t, str):
                                partes = t.split(':')
                                if len(partes) == 3:
                                    return int(partes[0]) * 60 + int(partes[1]) + int(partes[2]) / 60
                                elif len(partes) == 2:
                                    return int(partes[0]) * 60 + int(partes[1])
                            return float(t)
                        except:
                            return np.nan
                    
                    df_tab2_limpio['TIEMPO_ATENCION'] = df_tab2_limpio['TIEMPO_ATENCION'].apply(tiempo_a_minutos)
                else:
                    df_tab2_limpio['TIEMPO_ATENCION'] = pd.to_numeric(df_tab2_limpio['TIEMPO_ATENCION'], errors='coerce')
            
            # Procesar llamados
            if 'LLAMADOS' in df_tab2_limpio.columns:
                df_tab2_limpio['LLAMADOS'] = pd.to_numeric(df_tab2_limpio['LLAMADOS'], errors='coerce').fillna(1).astype(int)
            else:
                df_tab2_limpio['LLAMADOS'] = 1
            
            # DataFrame base para análisis (con filtros de fecha y servicios)
            df_base = df_tab2_limpio[
                (df_tab2_limpio["HORA_LLEGADA"].dt.date >= fecha_ini) & 
                (df_tab2_limpio["HORA_LLEGADA"].dt.date <= fecha_fin)
            ]
            
            # Aplicar filtro de servicios
            if servicio_sel:
                df_base = df_base[df_base["SERVICIO"].isin(servicio_sel)]
            
            # Aplicar filtro de usuarios SOLO si hay selección
            if usuario_sel:
                df_filtrado = df_base[df_base["USUARIO_ATENCION"].isin(usuario_sel)]
                st.info(f"✅ Mostrando datos solo para {len(usuario_sel)} usuario(s) seleccionado(s)")
            else:
                df_filtrado = df_base.copy()
                st.info(f"📊 Mostrando datos para TODOS los usuarios ({len(df_base['USUARIO_ATENCION'].unique())} usuarios)")
            
            if df_base.empty:
                st.warning("No hay datos con los filtros de fecha y servicios seleccionados")
                st.stop()
            
            # --- PROCESAMIENTO ---
            st.divider()
            
            # Contar usuarios únicos en los datos filtrados
            usuarios_en_datos = df_filtrado["USUARIO_ATENCION"].nunique()
            
            st.info(f"""
            **Configuración de análisis:**
            - **Rango:** {fecha_ini} a {fecha_fin}
            - **Servicios:** {len(servicio_sel)} seleccionados
            - **Usuarios disponibles en filtros:** {len(usuarios_disponibles_filtrados) if 'usuarios_disponibles_filtrados' in locals() else 0}
            - **Usuarios seleccionados:** {len(usuario_sel) if usuario_sel else 'TODOS'}
            - **Usuarios en datos mostrados:** {usuarios_en_datos}
            - **Registros analizados:** {len(df_filtrado):,}
            """)
            
            # ============================================================
            # GRÁFICO DE LÍNEA DE TIEMPO: MANUALES VS AUTOMÁTICOS
            # ============================================================
            if 'TIPO' in df_base.columns:
                st.subheader("📈 Evolución Temporal: Llamados Manuales vs Automáticos")
                
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
                
                df_base['CLASIFICACION'] = df_base['TIPO'].apply(clasificar_llamado)
                
                # Agrupar por fecha y clasificación
                df_temporal = df_base.copy()
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
                
                st.caption(f"📊 Evolución diaria de llamados del {fecha_ini} al {fecha_fin}")
                
                # ============================================================
                # TABLA: Usuarios con conteo de llamados y tiempos promedio
                # ============================================================
                st.divider()
                st.subheader("👥 Detalle de Llamados por Usuario")

                # Determinar qué usuarios mostrar en la tabla
                if usuario_sel:
                    # Si hay usuarios seleccionados, mostrar solo esos
                    usuarios_para_tabla = usuario_sel
                    titulo_tabla = "Usuarios Seleccionados"
                else:
                    # Si no hay selección, mostrar todos los usuarios
                    usuarios_para_tabla = sorted([str(u) for u in df_filtrado["USUARIO_ATENCION"].unique()])
                    titulo_tabla = "Todos los Usuarios"

                if usuarios_para_tabla:
                    # Crear DataFrame con los usuarios
                    usuarios_df = pd.DataFrame({
                        'Usuario': usuarios_para_tabla
                    })
                    
                    # Calcular conteos y promedios para cada usuario
                    conteos_manuales = []
                    conteos_automaticos = []
                    tiempos_promedio_atencion = []
                    tiempos_promedio_espera_entre_atenciones = []
                    
                    for usuario in usuarios_para_tabla:
                        # Filtrar datos para este usuario específico
                        df_usuario = df_filtrado[df_filtrado['USUARIO_ATENCION'] == usuario].copy()
                        
                        # Clasificar llamados para este usuario (para conteos)
                        if not df_usuario.empty and 'TIPO' in df_usuario.columns:
                            df_usuario['CLASIF'] = df_usuario['TIPO'].apply(clasificar_llamado)
                            
                            # Contar manuales (TODOS los registros, sin exclusiones)
                            manuales = len(df_usuario[df_usuario['CLASIF'] == 'MANUAL'])
                            conteos_manuales.append(manuales)
                            
                            # Contar automáticos (TODOS los registros, sin exclusiones)
                            automaticos = len(df_usuario[df_usuario['CLASIF'] == 'AUTOMÁTICO'])
                            conteos_automaticos.append(automaticos)
                        else:
                            conteos_manuales.append(0)
                            conteos_automaticos.append(0)
                        
                        # Calcular tiempo promedio de atención (por llamado individual) - CON EXCLUSIONES
                        if 'TIEMPO_ATENCION' in df_usuario.columns:
                            # Filtrar valores válidos (no nulos y mayores que 0)
                            df_tiempos_validos = df_usuario[df_usuario['TIEMPO_ATENCION'].notna() & (df_usuario['TIEMPO_ATENCION'] > 0)]
                            
                            if not df_tiempos_validos.empty:
                                # Calcular tiempo por llamado individual
                                tiempos_por_llamado = []
                                
                                for _, row in df_tiempos_validos.iterrows():
                                    # Verificar si es viernes (4) - excluir para tiempo de atención
                                    dia_semana = row['HORA_LLEGADA'].weekday()
                                    if dia_semana == 4:  # 4 = viernes
                                        continue  # Excluir viernes
                                    
                                    # Verificar si es después de las 3 PM (15:00)
                                    hora_dia = row['HORA_LLEGADA'].hour
                                    if hora_dia >= 15:  # 15 = 3 PM
                                        continue  # Excluir después de 3 PM
                                    
                                    tiempo_atencion = row['TIEMPO_ATENCION']
                                    llamados = row['LLAMADOS'] if pd.notna(row['LLAMADOS']) and row['LLAMADOS'] > 0 else 1
                                    
                                    # Tiempo por llamado individual
                                    tiempo_por_llamado = tiempo_atencion / llamados
                                    
                                    # Solo considerar tiempos razonables (menos de 60 minutos por llamado)
                                    if 0 < tiempo_por_llamado < 60:
                                        tiempos_por_llamado.append(tiempo_por_llamado)
                                
                                if tiempos_por_llamado:
                                    # Promedio simple de tiempos por llamado
                                    tiempo_prom_atencion = round(sum(tiempos_por_llamado) / len(tiempos_por_llamado), 1)
                                else:
                                    tiempo_prom_atencion = 0
                            else:
                                tiempo_prom_atencion = 0
                        else:
                            tiempo_prom_atencion = 0
                        tiempos_promedio_atencion.append(tiempo_prom_atencion)
                        
                        # Calcular tiempo promedio de espera entre atenciones (por llamado individual) - CON EXCLUSIONES
                        if 'HORA_FINALIZACION' in df_usuario.columns and not df_usuario.empty:
                            # Ordenar por hora de llegada
                            df_usuario = df_usuario.sort_values('HORA_LLEGADA')
                            
                            tiempos_espera_por_llamado = []  # Lista para almacenar los tiempos de espera por llamado
                            
                            fecha_anterior = None
                            hora_finalizacion_anterior = None
                            
                            for idx, row in df_usuario.iterrows():
                                fecha_actual = row['HORA_LLEGADA'].date()
                                hora_llegada_actual = row['HORA_LLEGADA']
                                hora_finalizacion_actual = row['HORA_FINALIZACION'] if pd.notna(row['HORA_FINALIZACION']) else None
                                llamados_actual = row['LLAMADOS'] if pd.notna(row['LLAMADOS']) and row['LLAMADOS'] > 0 else 1
                                
                                # Verificar si es viernes (4) - excluir para tiempo de espera
                                dia_semana = row['HORA_LLEGADA'].weekday()
                                if dia_semana == 4:  # 4 = viernes
                                    fecha_anterior = fecha_actual
                                    if hora_finalizacion_actual is not None:
                                        hora_finalizacion_anterior = hora_finalizacion_actual
                                    continue  # Excluir viernes
                                
                                # Verificar si es sábado (5) o domingo (6) - excluir para tiempo de espera
                                if dia_semana >= 5:  # 5 = sábado, 6 = domingo
                                    fecha_anterior = fecha_actual
                                    if hora_finalizacion_actual is not None:
                                        hora_finalizacion_anterior = hora_finalizacion_actual
                                    continue  # Excluir fines de semana
                                
                                # Verificar si es después de las 3 PM (15:00) - excluir para tiempo de espera
                                hora_dia = row['HORA_LLEGADA'].hour
                                if hora_dia >= 15:  # 15 = 3 PM
                                    fecha_anterior = fecha_actual
                                    if hora_finalizacion_actual is not None:
                                        hora_finalizacion_anterior = hora_finalizacion_actual
                                    continue  # Excluir después de 3 PM
                                
                                # Si tenemos un registro anterior del mismo día
                                if hora_finalizacion_anterior is not None and fecha_anterior == fecha_actual:
                                    # Calcular tiempo de espera = hora_llegada_actual - hora_finalizacion_anterior
                                    tiempo_espera = (hora_llegada_actual - hora_finalizacion_anterior).total_seconds() / 60  # en minutos
                                    
                                    # Solo considerar tiempos positivos, menores a 50 minutos y mayores que 0
                                    if 0 < tiempo_espera < 50:  # Excluir tiempos >= 50 minutos
                                        # Dividir el tiempo de espera por la cantidad de llamados
                                        # para obtener el tiempo de espera por llamado individual
                                        tiempo_espera_por_llamado = tiempo_espera / llamados_actual
                                        
                                        # Solo considerar tiempos razonables
                                        if 0 < tiempo_espera_por_llamado < 60:
                                            # Agregar el tiempo por llamado (cada llamado tiene el mismo peso)
                                            for _ in range(llamados_actual):
                                                tiempos_espera_por_llamado.append(tiempo_espera_por_llamado)
                                
                                # Actualizar para el siguiente registro
                                fecha_anterior = fecha_actual
                                if hora_finalizacion_actual is not None:
                                    hora_finalizacion_anterior = hora_finalizacion_actual
                                else:
                                    # Si no hay hora de finalización, usar la hora de llegada como aproximación
                                    hora_finalizacion_anterior = hora_llegada_actual
                            
                            # Calcular promedio simple de tiempos de espera por llamado
                            if tiempos_espera_por_llamado:
                                tiempo_promedio_espera = round(sum(tiempos_espera_por_llamado) / len(tiempos_espera_por_llamado), 1)
                            else:
                                tiempo_promedio_espera = 0
                        else:
                            tiempo_promedio_espera = 0
                        
                        tiempos_promedio_espera_entre_atenciones.append(tiempo_promedio_espera)
                    
                    # Agregar columnas al DataFrame
                    usuarios_df['Llamados Manuales'] = conteos_manuales
                    usuarios_df['Llamados Automáticos'] = conteos_automaticos
                    usuarios_df['TOTAL Registros'] = usuarios_df['Llamados Manuales'] + usuarios_df['Llamados Automáticos']
                    usuarios_df['⏱️ Tiempo promedio atención (min)'] = tiempos_promedio_atencion
                    usuarios_df['⏱️ Tiempo promedio de espera entre atenciones (min)'] = tiempos_promedio_espera_entre_atenciones
                    
                    # Ordenar por total descendente
                    usuarios_df = usuarios_df.sort_values('TOTAL Registros', ascending=False)
                    
                    # Mostrar la tabla
                    st.dataframe(
                        usuarios_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Usuario": "👤 Usuario Atención",
                            "Llamados Manuales": st.column_config.NumberColumn("Manuales", format="%d"),
                            "Llamados Automáticos": st.column_config.NumberColumn("Automáticos", format="%d"),
                            "TOTAL Registros": st.column_config.NumberColumn("📊 Total", format="%d"),
                            "⏱️ Tiempo promedio atención (min)": st.column_config.NumberColumn(
                                "⏱️ Tiempo prom. atención", 
                                format="%.1f min",
                                help="Promedio del tiempo por llamado (tiempo_atencion / cantidad_llamados) - Excluye viernes y después de 3 PM"
                            ),
                            "⏱️ Tiempo promedio de espera entre atenciones (min)": st.column_config.NumberColumn(
                                "⏱️ Tiempo prom. espera entre atenciones", 
                                format="%.1f min",
                                help="Promedio del tiempo de espera por llamado (mismo día, excluye viernes, fines de semana, después de 3 PM y tiempos > 50 min)"
                            )
                        }
                    )
                    
                    # Calcular totales generales (SIN EXCLUSIONES - usando df_filtrado directamente)
                    # Clasificar todos los registros para obtener totales precisos
                    df_clasificado = df_filtrado.copy()
                    if 'TIPO' in df_clasificado.columns:
                        df_clasificado['CLASIF_TOTAL'] = df_clasificado['TIPO'].apply(clasificar_llamado)
                        total_manuales_gral = len(df_clasificado[df_clasificado['CLASIF_TOTAL'] == 'MANUAL'])
                        total_automaticos_gral = len(df_clasificado[df_clasificado['CLASIF_TOTAL'] == 'AUTOMÁTICO'])
                    else:
                        # Si no hay columna TIPO, asumir que todos son manuales o no clasificados
                        total_manuales_gral = len(df_filtrado)
                        total_automaticos_gral = 0
                    
                    total_general_llamados = len(df_filtrado)
                    
                    # Calcular porcentajes para los totales
                    pct_manual_gral = (total_manuales_gral / total_general_llamados * 100) if total_general_llamados > 0 else 0
                    pct_auto_gral = (total_automaticos_gral / total_general_llamados * 100) if total_general_llamados > 0 else 0
                    
                    # Calcular promedios generales de tiempo (CON EXCLUSIONES - de los cálculos por usuario)
                    tiempos_atencion_todos = [t for t in tiempos_promedio_atencion if t > 0]
                    prom_atencion_gral = round(sum(tiempos_atencion_todos) / len(tiempos_atencion_todos), 1) if tiempos_atencion_todos else 0
                    
                    tiempos_espera_todos = [t for t in tiempos_promedio_espera_entre_atenciones if t > 0]
                    prom_espera_gral = round(sum(tiempos_espera_todos) / len(tiempos_espera_todos), 1) if tiempos_espera_todos else 0
                    
                    # Estándares
                    ESTANDAR_ATENCION = 2.5  # minutos
                    ESTANDAR_ESPERA = 5.0    # minutos
                    
                    # Calcular diferencias con estándares
                    diff_atencion = prom_atencion_gral - ESTANDAR_ATENCION if prom_atencion_gral > 0 else 0
                    diff_atencion_pct = (diff_atencion / ESTANDAR_ATENCION * 100) if ESTANDAR_ATENCION > 0 else 0
                    
                    diff_espera = prom_espera_gral - ESTANDAR_ESPERA if prom_espera_gral > 0 else 0
                    diff_espera_pct = (diff_espera / ESTANDAR_ESPERA * 100) if ESTANDAR_ESPERA > 0 else 0
                    
                    # Mostrar totales con porcentajes y comparaciones con estándares
                    st.markdown("##### 📊 Resumen General")
                    
                    col_total1, col_total2, col_total3, col_total4, col_total5, col_total6 = st.columns(6)
                    
                    with col_total1:
                        st.metric(f"Total {titulo_tabla}", len(usuarios_para_tabla))
                    
                    with col_total2:
                        delta_manual = f"{pct_manual_gral:+.1f}% del total"
                        st.metric(
                            "Total Llamados Manuales", 
                            f"{total_manuales_gral:,}",
                            delta=delta_manual,
                            delta_color="off"
                        )
                    
                    with col_total3:
                        delta_auto = f"{pct_auto_gral:+.1f}% del total"
                        st.metric(
                            "Total Llamados Automáticos", 
                            f"{total_automaticos_gral:,}",
                            delta=delta_auto,
                            delta_color="off"
                        )
                    
                    with col_total4:
                        st.metric("Total General", f"{total_general_llamados:,}")
                    
                    with col_total5:
                        if prom_atencion_gral > 0:
                            delta_atencion = f"{diff_atencion:+.1f} min vs estándar ({diff_atencion_pct:+.1f}%)"
                            st.metric(
                                "⏱️ Prom. atención general", 
                                f"{prom_atencion_gral} min",
                                delta=delta_atencion,
                                delta_color="inverse" if diff_atencion > 0 else "normal"
                            )
                            st.caption(f"Estándar: {ESTANDAR_ATENCION} min")
                        else:
                            st.metric("⏱️ Prom. atención general", "N/A")
                    
                    with col_total6:
                        if prom_espera_gral > 0:
                            delta_espera = f"{diff_espera:+.1f} min vs estándar ({diff_espera_pct:+.1f}%)"
                            st.metric(
                                "⏱️ Prom. espera general", 
                                f"{prom_espera_gral} min",
                                delta=delta_espera,
                                delta_color="inverse" if diff_espera > 0 else "normal"
                            )
                            st.caption(f"Estándar: {ESTANDAR_ESPERA} min")
                        else:
                            st.metric("⏱️ Prom. espera general", "N/A")
                    
                    # Mostrar información adicional
                    st.caption(f"📊 Basado en {len(servicio_sel)} servicio(s) seleccionado(s): {', '.join(servicio_sel) if servicio_sel else 'Todos'}")
                    
                    # Mostrar advertencias si no se encontraron columnas
                    if 'TIEMPO_ATENCION' not in df_filtrado.columns:
                        st.warning("⚠️ No se encontró la columna 'Tiempo Atención' en el archivo. Los valores de tiempo promedio de atención aparecen como 0.")
                    
                    if 'HORA_FINALIZACION' not in df_filtrado.columns:
                        st.warning("⚠️ No se encontró la columna 'Hora Finalización' en el archivo. El tiempo de espera entre atenciones no pudo calcularse correctamente.")
                    
                    # Mostrar explicación del cálculo
                    with st.expander("ℹ️ ¿Cómo se calculan los indicadores?"):
                        st.markdown(f"""
                        **Metodología de cálculo:**
                        
                        **📊 Totales de llamados (Manuales, Automáticos y General):**
                        - Se calculan sobre **TODOS los registros** filtrados (fecha, servicios y usuarios)
                        - No aplican exclusiones de días ni horarios
                        - Coinciden con los totales mostrados en el gráfico "Evolución Temporal"
                        
                        **⏱️ Tiempo promedio de atención:**
                        - Se calcula como **tiempo por llamado individual**: Tiempo_Atención / Cantidad_Llamados
                        - Luego se promedian todos estos valores por llamado
                        - **Exclusiones:** Se excluyen registros de viernes y después de las 3:00 PM
                        - **Estándar de comparación:** {ESTANDAR_ATENCION} minutos por llamado
                        
                        **⏱️ Tiempo promedio de espera entre atenciones:**
                        - Se calcula: Hora Llegada (siguiente) - Hora Finalización (anterior)
                        - Luego se divide entre la cantidad de llamados del registro actual
                        - Finalmente se promedian todos estos valores por llamado
                        
                        **Reglas de exclusión para tiempo de espera:**
                        - ❌ Se excluyen los registros de **viernes, sábados y domingos**
                        - ❌ Se excluyen las atenciones **después de las 3:00 PM**
                        - ❌ Se excluyen tiempos de espera **mayores o iguales a 50 minutos**
                        - ✅ Solo se consideran cuando ambas atenciones ocurren el **mismo día**
                        - **Estándar de comparación:** {ESTANDAR_ESPERA} minutos por llamado
                        
                        Este enfoque asegura que los totales de llamados reflejen toda la actividad, mientras que los tiempos promedio reflejan el rendimiento en condiciones normales de operación.
                        """)

                else:
                    st.info("No hay usuarios para mostrar")
            
            # --- SELECTOR DE DÍA (antes de la tabla de promedios) ---
            st.divider()
            st.markdown("### 📅 Selección de día para análisis de promedios por agente")
            dias_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos (L-V)"]
            dia_sel = st.selectbox("Día a analizar", dias_opciones, index=7, key="tab2_dia")
            
            # Preparar datos para promedios
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
            
            # Convertir todos los usuarios a string para evitar errores de ordenamiento
            usuarios_proc = sorted([str(u) for u in df_proceso["USUARIO_ATENCION"].unique()])
            
            if not usuarios_proc:
                st.warning("No hay usuarios en los datos filtrados")
                st.stop()
            
            # Crear tabla de promedios (ponderada por cantidad de llamados)
            data = []
            for usuario in usuarios_proc:
                df_u = df_proceso[df_proceso["USUARIO_ATENCION"] == usuario]
                fila = []
                for h in horas:
                    df_h = df_u[df_u['HORA'] == h]
                    if not df_h.empty:
                        # Promedio ponderado por cantidad de llamados
                        total_llamados_hora = df_h['LLAMADOS'].sum()
                        dias_con_registros = df_h['FECHA'].nunique()
                        promedio = total_llamados_hora / dias_con_registros if dias_con_registros > 0 else 0
                        fila.append(round(promedio, 2))
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
            st.markdown("*Cantidad promedio de llamados por hora (ponderado por la cantidad de llamados por registro)*")
            
            # Información sobre qué usuarios se están mostrando
            if usuario_sel:
                st.caption(f"📊 Mostrando promedios para {len(usuario_sel)} usuario(s) seleccionado(s)")
            else:
                st.caption(f"📊 Mostrando promedios para TODOS los usuarios ({len(usuarios_proc)} usuarios)")
            
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
            
            # Crear DataFrame para el gráfico
            chart_data = pd.DataFrame({
                'Usuario': top_usuarios.index,
                'Promedio Diario': top_usuarios['TOTAL'].values
            }).set_index('Usuario')
            
            st.bar_chart(chart_data, height=400)
            st.caption("📊 Ordenado de mayor a menor promedio de llamados (ponderado)")
            
            # --- EXPORTAR ---
            st.divider()
            st.subheader("📤 Exportar Resultados")
            
            def crear_excel_tab2():
                out = BytesIO()
                with pd.ExcelWriter(out, engine='openpyxl') as w:
                    tabla_llamados_con_total.to_excel(w, sheet_name='Llamados Promedio')
                    
                    if 'df_completo' in locals():
                        df_completo.reset_index().to_excel(w, sheet_name='Evolución Diaria', index=False)
                    
                    # Agregar la tabla de usuarios con totales y tiempos promedio
                    if 'usuarios_df' in locals() and not usuarios_df.empty:
                        usuarios_df.to_excel(w, sheet_name='Detalle Usuarios', index=False)
                    
                    config = pd.DataFrame({
                        'Parámetro': ['Rango', 'Día', 'Servicios', 'Usuarios seleccionados', 'Usuarios mostrados', 'Registros'],
                        'Valor': [
                            f"{fecha_ini} a {fecha_fin}",
                            dia_sel,
                            ', '.join(servicio_sel) if servicio_sel else 'Todos',
                            ', '.join(usuario_sel) if usuario_sel else 'TODOS',
                            str(len(usuarios_proc)),
                            str(len(df_proceso))
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
            st.markdown("*Cargue el archivo de auditoría de admisiones obtenido de Tramita para analizar los registros por fecha y motivo*")
            st.markdown("*Posteriormente, seleccione un rango de fechas, sede y los usuarios (Gestores de acceso - Back Office) a analizar*")
        
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
                
                # Verificar que existe la columna sede (para filtrar)
                columnas_sede = [col for col in df_temp.columns if 'sede' in col.lower()]
                if not columnas_sede:
                    st.error("No se encontró ninguna columna con 'sede' en el archivo.")
                    st.stop()
                
                col_sede = columnas_sede[0]  # Tomamos la primera columna que contenga 'sede'
                
                # Verificar que existe la columna motivo (para los gráficos)
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
                    st.markdown("##### 🏢 Sedes")
                    # Primero filtramos por fecha para obtener sedes disponibles en el rango
                    df_fecha_filtrado = df_temp[
                        (df_temp["fechaRegistro"].dt.date >= fecha_inicio_tab3) & 
                        (df_temp["fechaRegistro"].dt.date <= fecha_fin_tab3)
                    ]
                    sedes_disponibles = sorted(df_fecha_filtrado[col_sede].dropna().unique())
                    
                    sede_sel_tab3 = st.multiselect(
                        "Seleccionar sedes:", 
                        options=sedes_disponibles,
                        help="Selecciona una o más sedes para filtrar los datos",
                        key=f"tab3_sede_{fecha_inicio_tab3}_{fecha_fin_tab3}"
                    )
                
                with col_f3:
                    st.markdown("##### 👤 Usuario (Gestor de acceso - Back Office)")
                    
                    # Aplicar filtros de fecha y sede para obtener usuarios disponibles
                    df_filtro_usuarios = df_temp[
                        (df_temp["fechaRegistro"].dt.date >= fecha_inicio_tab3) & 
                        (df_temp["fechaRegistro"].dt.date <= fecha_fin_tab3)
                    ].copy()
                    
                    # Aplicar filtro de sedes si hay alguna seleccionada
                    if sede_sel_tab3:
                        df_filtro_usuarios = df_filtro_usuarios[df_filtro_usuarios[col_sede].isin(sede_sel_tab3)]
                    
                    # Obtener usuarios únicos que tienen registros en el rango de fechas y sedes seleccionadas
                    # Excluimos valores nulos para el filtro de usuarios
                    nombres_disponibles = sorted(df_filtro_usuarios[col_nombre].dropna().unique())
                    
                    # Mostrar información de cuántos usuarios están disponibles
                    st.caption(f"📊 {len(nombres_disponibles)} usuarios disponibles para las sedes seleccionadas")
                    
                    # Multiselect de usuarios con clave dinámica
                    usuario_sel_tab3 = st.multiselect(
                        "Seleccionar usuarios:", 
                        options=nombres_disponibles,
                        help="Usuarios con registros en el rango de fechas y sedes seleccionadas",
                        key=f"tab3_usuario_{fecha_inicio_tab3}_{fecha_fin_tab3}_{len(sede_sel_tab3)}_{len(nombres_disponibles)}"
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
            
            columnas_sede = [col for col in df.columns if 'sede' in col.lower()]
            col_sede = columnas_sede[0]  # Primer campo 'sede'
            
            columnas_motivo = [col for col in df.columns if 'motivo' in col.lower()]
            col_motivo = columnas_motivo[0]  # Primer campo 'motivo'
            
            # Procesar fechas
            df["fechaRegistro"] = pd.to_datetime(df["fechaRegistro"], errors='coerce')
            df = df.dropna(subset=["fechaRegistro"])
            
            # NIVEL 1: FILTROS BASE (fecha y sede) - para análisis de motivos
            # Incluye todos los registros, incluso aquellos sin usuario
            df_base_filtrado = df[
                (df["fechaRegistro"].dt.date >= fecha_inicio_tab3) & 
                (df["fechaRegistro"].dt.date <= fecha_fin_tab3)
            ]
            
            if sede_sel_tab3:
                df_base_filtrado = df_base_filtrado[df_base_filtrado[col_sede].isin(sede_sel_tab3)]
            
            # NIVEL 2: FILTROS COMPLETOS (fecha, sede y usuario) - excluye registros sin usuario
            # Primero filtramos registros que tienen usuario asignado
            df_con_usuario = df_base_filtrado[df_base_filtrado[col_nombre].notna()].copy()
            
            # Luego aplicamos filtro de usuarios si hay selección
            df_completo_filtrado = df_con_usuario.copy()
            if usuario_sel_tab3:
                df_completo_filtrado = df_completo_filtrado[df_completo_filtrado[col_nombre].isin(usuario_sel_tab3)]

            if not df_base_filtrado.empty:
                st.divider()
                
                # Calcular registros sin usuario para información
                registros_sin_usuario = len(df_base_filtrado) - len(df_con_usuario)
                
                # Mostrar configuración seleccionada con todos los niveles
                st.info(f"""
                **Configuración de análisis por niveles:**
                
                **Nivel 1 - Análisis de Motivos (fecha + sede):**
                - Total registros: {len(df_base_filtrado):,}
                - Registros sin usuario: {registros_sin_usuario:,} (excluidos del análisis de rendimiento)
                
                **Nivel 2 - Base para Rendimiento (fecha + sede + usuario):**
                - Registros con usuario: {len(df_con_usuario):,}
                - Registros después de filtro de usuarios: {len(df_completo_filtrado):,}
                
                **Detalles de filtros:**
                - **Rango:** {fecha_inicio_tab3} a {fecha_fin_tab3}
                - **Sedes seleccionadas:** {', '.join(sede_sel_tab3) if sede_sel_tab3 else 'Todas las sedes'}
                - **Usuarios disponibles:** {len(nombres_disponibles) if 'nombres_disponibles' in locals() else 0}
                - **Usuarios seleccionados:** {', '.join(usuario_sel_tab3) if usuario_sel_tab3 else 'Todos los disponibles'}
                """)
                
                # --- GRÁFICO DE DISTRIBUCIÓN POR MOTIVO (NIVEL 1) ---
                st.subheader("📊 Distribución de Auditorías por Motivo")
                st.markdown(f"*Análisis basado en filtros de fecha y sede (incluye {registros_sin_usuario:,} registros sin usuario)*")
                
                # Calcular distribución por motivo
                motivo_counts = df_base_filtrado[col_motivo].value_counts()
                
                # Crear DataFrame para el gráfico
                motivo_df = pd.DataFrame({
                    'Motivo': motivo_counts.index,
                    'Cantidad': motivo_counts.values
                })
                
                # Mostrar gráfico de barras
                if not motivo_df.empty:
                    st.bar_chart(motivo_df.set_index('Motivo'), height=400)
                else:
                    st.warning("No hay datos de motivos para mostrar")
                
                # Mostrar tabla con porcentajes y métricas
                st.subheader("📋 Detalle por Motivo")
                total_registros_motivos = motivo_counts.sum()
                
                if total_registros_motivos > 0:
                    motivo_pct = (motivo_counts / total_registros_motivos * 100).round(1)
                    motivo_resumen = pd.DataFrame({
                        'Motivo': motivo_counts.index,
                        'Cantidad': motivo_counts.values,
                        'Porcentaje': [f"{pct}%" for pct in motivo_pct.values]
                    }).sort_values('Cantidad', ascending=False)
                    
                    st.dataframe(motivo_resumen, use_container_width=True, hide_index=True)
                    
                    # Métricas de totales
                    col_met1, col_met2, col_met3 = st.columns(3)
                    with col_met1:
                        st.metric("Total de Registros", f"{total_registros_motivos:,}")
                    with col_met2:
                        st.metric("Motivos Distintos", f"{len(motivo_counts)}")
                    with col_met3:
                        motivo_mas_frecuente = motivo_counts.index[0] if not motivo_counts.empty else "N/A"
                        st.metric("Motivo más Frecuente", motivo_mas_frecuente)
                else:
                    st.warning("No hay registros para mostrar en el análisis de motivos")
                
                st.divider()
                
                # --- ANÁLISIS DE RENDIMIENTO POR USUARIO (NIVEL 2) ---
                if not df_completo_filtrado.empty:
                
                    # --- SELECTOR DE DÍA (NIVEL 3) ---
                    st.markdown("### 📅 Selección de día para análisis de promedios por hora")
                    st.markdown(f"*Base inicial: {len(df_completo_filtrado):,} registros con usuario (fecha + sede + filtro de usuarios)*")
                    
                    dia_semana_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
                    dia_seleccionado_tab3 = st.selectbox(
                        "Día de la semana a analizar:",
                        options=dia_semana_opciones,
                        index=7,
                        help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                        key=f"tab3_dia_{fecha_inicio_tab3}_{fecha_fin_tab3}_{len(usuario_sel_tab3)}"
                    )
                    
                    # Preparar datos para promedios
                    df_proceso = df_completo_filtrado.copy()
                    df_proceso['FECHA'] = df_proceso["fechaRegistro"].dt.date
                    df_proceso['HORA'] = df_proceso["fechaRegistro"].dt.hour
                    df_proceso['DIA_SEMANA'] = df_proceso["fechaRegistro"].dt.day_name()
                    df_proceso['DIA_SEMANA_NUM'] = df_proceso["fechaRegistro"].dt.dayofweek
                    
                    # Mapeo de días
                    mapa_dias = {
                        'Lunes': 'Monday', 'Martes': 'Tuesday', 'Miércoles': 'Wednesday',
                        'Jueves': 'Thursday', 'Viernes': 'Friday', 'Sábado': 'Saturday', 'Domingo': 'Sunday'
                    }
                    
                    # Guardar total antes del filtro de día para referencia
                    total_antes_filtro_dia = len(df_proceso)
                    
                    # Filtrar por día
                    if dia_seleccionado_tab3 == "Todos los días (L-V)":
                        df_proceso = df_proceso[df_proceso['DIA_SEMANA_NUM'] < 5]
                        if df_proceso.empty:
                            st.warning("No hay registros para Lunes a Viernes.")
                            st.stop()
                        else:
                            st.caption(f"📊 Filtrando días Lunes a Viernes: {len(df_proceso):,} de {total_antes_filtro_dia:,} registros")
                    else:
                        dia_ingles = mapa_dias[dia_seleccionado_tab3]
                        df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_ingles]
                        if df_proceso.empty:
                            st.warning(f"No hay registros para {dia_seleccionado_tab3}.")
                            st.stop()
                        dias_unicos = df_proceso['FECHA'].nunique()
                        st.caption(f"📊 Promediando {dias_unicos} día(s) de {dia_seleccionado_tab3} - {len(df_proceso):,} registros")
                    
                    # Identificar horas con registros
                    horas_con_registros = sorted(df_proceso['HORA'].unique())
                    horas_formateadas = [f"{h}:00" for h in horas_con_registros]
                    
                    # Obtener usuarios del filtro
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
                    st.subheader("📊 Promedio de Auditorías por Usuario (por hora)")
                    st.markdown(f"*Cantidad promedio de auditorías realizadas por hora - Base: {len(df_proceso):,} registros*")
                    
                    if not tabla_resultados.empty:
                        styler = tabla_resultados_con_total.style
                        mascara_usuarios = tabla_resultados_con_total.index != 'TOTAL'
                        styler = styler.format("{:.2f}", subset=pd.IndexSlice[tabla_resultados_con_total.index[mascara_usuarios], horas_formateadas + ['TOTAL', 'MÍNIMO', 'MÁXIMO']])
                        styler = styler.format("{:.2f}", subset=pd.IndexSlice[['TOTAL'], horas_formateadas + ['TOTAL']])
                        styler = styler.background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[tabla_resultados.index, horas_formateadas])
                        styler = styler.set_properties(**{'text-align': 'center'})
                        
                        st.dataframe(styler, use_container_width=True, height=min(400, 50 + (len(usuarios_proceso) * 35)))
                    else:
                        st.warning("No hay datos para mostrar en la tabla de promedios")
                    
                    # --- ESTADÍSTICAS RESUMEN VS ESTÁNDAR ---
                    st.subheader("📈 Estadísticas Resumen vs Estándar")
                    
                    # Calcular estadísticas generales (excluyendo valores 0)
                    valores_validos = []
                    for col in horas_formateadas:
                        for usuario in usuarios_proceso:
                            if usuario in tabla_resultados.index:
                                valor = tabla_resultados.loc[usuario, col]
                                if valor > 0:
                                    valores_validos.append(valor)
                    
                    promedio_general = np.mean(valores_validos) if valores_validos else 0
                    
                    # Total de registros en el período analizado (CON FILTRO DE DÍA Y USUARIO)
                    total_registros_periodo = len(df_proceso)
                    
                    # Días analizados
                    dias_trabajados = df_proceso['FECHA'].nunique()
                    
                    # Estándar de 14 gestiones por hora
                    ESTANDAR_GESTIONES = 14
                    
                    diff_gestiones = promedio_general - ESTANDAR_GESTIONES
                    diff_gestiones_pct = (diff_gestiones / ESTANDAR_GESTIONES) * 100 if ESTANDAR_GESTIONES > 0 else 0
                    
                    # Encontrar máximo y mínimo
                    max_registros_hora = 0
                    usuario_max = "N/A"
                    hora_max = "N/A"
                    
                    for col in horas_formateadas:
                        for usuario in usuarios_proceso:
                            if usuario in tabla_resultados.index:
                                valor = tabla_resultados.loc[usuario, col]
                                if valor > max_registros_hora:
                                    max_registros_hora = valor
                                    usuario_max = usuario
                                    hora_max = col
                    
                    min_registros_hora = float('inf')
                    usuario_min = "N/A"
                    hora_min = "N/A"
                    
                    for col in horas_formateadas:
                        for usuario in usuarios_proceso:
                            if usuario in tabla_resultados.index:
                                valor = tabla_resultados.loc[usuario, col]
                                if valor > 0 and valor < min_registros_hora:
                                    min_registros_hora = valor
                                    usuario_min = usuario
                                    hora_min = col
                    
                    min_registros_hora = None if min_registros_hora == float('inf') else min_registros_hora
                    
                    # Mostrar métricas
                    col_est1, col_est2, col_est3 = st.columns(3)
                    
                    with col_est1:
                        st.markdown("### 📊 Promedio General")
                        delta = f"{diff_gestiones:+.2f} vs estándar ({diff_gestiones_pct:+.1f}%)"
                        st.metric("Promedio gestiones/hora", f"{promedio_general:.2f}", 
                                 delta=delta, delta_color="inverse" if diff_gestiones > 0 else "normal")
                        st.markdown(f"**Estándar:** {ESTANDAR_GESTIONES} gestiones/hora")
                    
                    with col_est2:
                        st.markdown("### 📅 Resumen del Período")
                        st.metric("Total registros analizados", f"{total_registros_periodo:,}")
                        st.metric("Días analizados", f"{dias_trabajados}")
                        st.metric("Horas con actividad", f"{len(horas_con_registros)}")
                    
                    with col_est3:
                        st.markdown("### 📈 Extremos por Hora")
                        st.metric("Máximo gestiones/hora", f"{max_registros_hora:.2f}")
                        st.caption(f"👤 {usuario_max} - {hora_max}")
                        
                        if min_registros_hora:
                            st.metric("Mínimo gestiones/hora", f"{min_registros_hora:.2f}")
                            st.caption(f"👤 {usuario_min} - {hora_min}")
                        else:
                            st.metric("Mínimo gestiones/hora", "N/A")
                    
                    st.divider()
                    
                    # --- TOP 10 USUARIOS ---
                    st.subheader("🏆 Top 10 Usuarios por Total de Auditorías")
                    st.markdown(f"*Basado en los {len(df_proceso):,} registros del período analizado (con usuario y filtro de día)*")
                    
                    # Calcular total de registros por usuario con los mismos datos filtrados
                    usuarios_totales = df_proceso[col_nombre].value_counts().head(10)
                    
                    if not usuarios_totales.empty:
                        # Gráfico de barras
                        top_usuarios_chart = pd.DataFrame({
                            'Usuario': usuarios_totales.index,
                            'Total Registros': usuarios_totales.values
                        }).set_index('Usuario')
                        
                        st.bar_chart(top_usuarios_chart, height=400)
                        
                        # Tabla detalle
                        st.subheader("📋 Detalle Top 10 Usuarios")
                        
                        # Calcular porcentajes sobre el total de registros del análisis de motivos (Nivel 1)
                        total_registros_motivos = len(df_base_filtrado)
                        usuarios_pct = (usuarios_totales / total_registros_motivos * 100).round(1)
                        
                        top_usuarios_tabla = pd.DataFrame({
                            'Usuario': usuarios_totales.index,
                            'Cantidad': usuarios_totales.values,
                            'Porcentaje del Total General': [f"{pct}%" for pct in usuarios_pct.values]
                        }).reset_index(drop=True)
                        
                        st.dataframe(top_usuarios_tabla, use_container_width=True, hide_index=True)
                        
                        # Métricas
                        col_top1, col_top2, col_top3 = st.columns(3)
                        with col_top1:
                            st.metric("Total Registros Top 10", f"{usuarios_totales.sum():,}")
                        with col_top2:
                            st.metric("% del Total General", f"{(usuarios_totales.sum()/total_registros_motivos*100):.1f}%")
                        with col_top3:
                            usuario_top = usuarios_totales.index[0]
                            st.metric("Usuario con más registros", usuario_top)
                        
                        st.caption(f"📊 Total general de registros (incluye {registros_sin_usuario:,} sin usuario): {total_registros_motivos:,}")
                    else:
                        st.warning("No hay datos suficientes para mostrar el top de usuarios")
                    
                    st.divider()
                    
                    # --- EXPORTAR ---
                    st.subheader("📤 Exportar Resultados a Excel")
                    
                    def crear_excel_tab3():
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            # Hoja de promedios por hora
                            if not tabla_resultados.empty:
                                tabla_resultados_con_total.to_excel(writer, sheet_name='Auditorías Promedio')
                            
                            # Hoja de distribución por motivo
                            if 'motivo_resumen' in locals():
                                motivo_resumen.to_excel(writer, sheet_name='Distribución por Motivo', index=False)
                            
                            # Hoja de top 10 usuarios
                            if not usuarios_totales.empty:
                                top_usuarios_export = pd.DataFrame({
                                    'Usuario': usuarios_totales.index,
                                    'Total Registros': usuarios_totales.values,
                                    'Porcentaje del Total General': [f"{(valor/total_registros_motivos*100):.1f}%" for valor in usuarios_totales.values]
                                })
                                top_usuarios_export.to_excel(writer, sheet_name='Top 10 Usuarios', index=False)
                            
                            # Hoja de estadísticas
                            stats_df = pd.DataFrame({
                                'Métrica': [
                                    'Promedio gestiones/hora',
                                    'Total registros período (con filtro día)',
                                    'Días analizados',
                                    'Máximo gestiones/hora',
                                    'Mínimo gestiones/hora',
                                    'Estándar',
                                    'Registros sin usuario (excluidos)',
                                    'Total registros análisis motivos'
                                ],
                                'Valor': [
                                    f"{promedio_general:.2f}",
                                    f"{total_registros_periodo:,}",
                                    f"{dias_trabajados}",
                                    f"{max_registros_hora:.2f} (Usuario: {usuario_max}, Hora: {hora_max})",
                                    f"{min_registros_hora:.2f} (Usuario: {usuario_min}, Hora: {hora_min})" if min_registros_hora else "N/A",
                                    f"{ESTANDAR_GESTIONES} gestiones/hora",
                                    f"{registros_sin_usuario:,}",
                                    f"{total_registros_motivos:,}"
                                ]
                            })
                            stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
                            
                            # Hoja de configuración
                            config_df = pd.DataFrame({
                                'Parámetro': ['Rango', 'Día', 'Usuarios', 'Sedes', 'Registros totales', 'Registros con usuario', 'Registros sin usuario'],
                                'Valor': [
                                    f"{fecha_inicio_tab3} a {fecha_fin_tab3}",
                                    dia_seleccionado_tab3,
                                    'Todos' if not usuario_sel_tab3 else ', '.join(usuario_sel_tab3),
                                    'Todas' if not sede_sel_tab3 else ', '.join(sede_sel_tab3),
                                    len(df_base_filtrado),
                                    len(df_con_usuario),
                                    registros_sin_usuario
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
                    st.warning("No hay datos con los filtros de usuario seleccionados")
            
            else:
                st.warning("No hay datos con los filtros de fecha y sede seleccionados")
        
        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.info("Verifica las columnas del archivo (debe contener: fechaRegistro, nombre, sede y motivo)")
    elif uploaded_file_tab3 is not None:
        st.warning("⚠️ Corrige los errores en los filtros para continuar")
    else:
        st.info("👆 Configura los parámetros y sube un archivo Excel para comenzar el análisis de auditoría")
