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
    
    # Obtener usuarios únicos
    usuarios_disponibles_filtrados = sorted(df_filtro_base["USUARIO CREA INGRESO"].dropna().unique())
    
# ============================================================================
# PESTAÑA 2: ANÁLISIS DE TURNOS ATENDIDOS (VERSIÓN FINAL CORREGIDA)
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
                
                # Buscar columnas - ESPECÍFICAMENTE "User Atención"
                col_hora = encontrar_columna(df_temp, ['hora llegada', 'hora_llegada', 'hora'])
                col_servicio = encontrar_columna(df_temp, ['servicio'])
                # Buscar específicamente "User Atención" (con espacio) y variantes
                col_usuario = encontrar_columna(df_temp, ['user atención', 'user_atencion', 'usuario atención', 'usuario_atencion', 'usuario', 'user'])
                col_tipo = encontrar_columna(df_temp, ['tipo'])
                
                # Verificar si encontramos las columnas necesarias
                if not all([col_hora, col_servicio]):
                    st.error(f"No se encontraron las columnas de hora y servicio. Hora: {col_hora}, Servicio: {col_servicio}")
                    st.stop()
                
                if not col_usuario:
                    st.error("No se encontró la columna de usuario. Buscamos: 'User Atención', 'usuario atención', etc.")
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
                    usuarios_disponibles_filtrados = sorted(df_filtro_base["USUARIO_ATENCION"].dropna().unique())
                    
                    # Mostrar información de cuántos usuarios están disponibles
                    st.caption(f"📊 {len(usuarios_disponibles_filtrados)} usuarios disponibles para los filtros seleccionados")
                    
                    if usuarios_disponibles_filtrados:
                        usuario_sel = st.multiselect(
                            "Seleccionar usuarios:", 
                            options=usuarios_disponibles_filtrados,
                            help=f"Usuarios con registros en el rango de fechas y servicios seleccionados",
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
            col_hora = encontrar_columna(df_tab2, ['hora llegada', 'hora_llegada', 'hora'])
            col_servicio = encontrar_columna(df_tab2, ['servicio'])
            col_usuario = encontrar_columna(df_tab2, ['user atención', 'user_atencion', 'usuario atención', 'usuario_atencion', 'usuario', 'user'])
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
            - **Usuarios disponibles en filtros:** {len(usuarios_disponibles_filtrados) if 'usuarios_disponibles_filtrados' in locals() else 0}
            - **Usuarios seleccionados:** {len(usuario_sel) if usuario_sel else 0}
            - **Registros analizados (con filtro usuarios):** {len(df_filtrado):,}
            """)
            
            # ============================================================
            # GRÁFICO DE LÍNEA DE TIEMPO: MANUALES VS AUTOMÁTICOS
            # ============================================================
            if 'TIPO' in df_grafico.columns:
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
                
                st.caption(f"📊 Evolución diaria de llamados del {fecha_ini} al {fecha_fin}")
                
                # ============================================================
                # TABLA: Usuarios seleccionados con conteo de llamados
                # ============================================================
                st.divider()
                st.subheader("👥 Detalle de Llamados por Usuario Seleccionado")
                
                # Usar los usuarios seleccionados en el filtro (usuario_sel)
                if usuario_sel:  # Solo mostrar si hay usuarios seleccionados
                    # Crear DataFrame con los usuarios seleccionados
                    usuarios_seleccionados_df = pd.DataFrame({
                        'Usuario': usuario_sel
                    })
                    
                    # Calcular conteos para cada usuario usando df_filtrado (que ya tiene aplicados los filtros de usuarios)
                    conteos_manuales = []
                    conteos_automaticos = []
                    
                    for usuario in usuario_sel:
                        # Filtrar datos para este usuario específico
                        df_usuario = df_filtrado[df_filtrado['USUARIO_ATENCION'] == usuario].copy()
                        
                        # Clasificar llamados para este usuario
                        if not df_usuario.empty and 'TIPO' in df_usuario.columns:
                            df_usuario['CLASIF'] = df_usuario['TIPO'].apply(clasificar_llamado)
                            
                            # Contar manuales
                            manuales = len(df_usuario[df_usuario['CLASIF'] == 'MANUAL'])
                            conteos_manuales.append(manuales)
                            
                            # Contar automáticos
                            automaticos = len(df_usuario[df_usuario['CLASIF'] == 'AUTOMÁTICO'])
                            conteos_automaticos.append(automaticos)
                        else:
                            conteos_manuales.append(0)
                            conteos_automaticos.append(0)
                    
                    # Agregar columnas al DataFrame
                    usuarios_seleccionados_df['Llamados Manuales'] = conteos_manuales
                    usuarios_seleccionados_df['Llamados Automáticos'] = conteos_automaticos
                    
                    # Mostrar la tabla
                    st.dataframe(
                        usuarios_seleccionados_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Usuario": "👤 Usuario Atención",
                            "Llamados Manuales": st.column_config.NumberColumn("📞 Manuales", format="%d"),
                            "Llamados Automáticos": st.column_config.NumberColumn("🤖 Automáticos", format="%d")
                        }
                    )
                    
                    # Mostrar totales
                    col_total1, col_total2, col_total3 = st.columns(3)
                    with col_total1:
                        st.metric("Total Usuarios Seleccionados", len(usuario_sel))
                    with col_total2:
                        st.metric("Total Llamados Manuales", sum(conteos_manuales))
                    with col_total3:
                        st.metric("Total Llamados Automáticos", sum(conteos_automaticos))
                    
                    # Mostrar información adicional sobre los servicios
                    st.caption(f"📊 Basado en {len(servicio_sel)} servicio(s) seleccionado(s): {', '.join(servicio_sel) if servicio_sel else 'Todos'}")
                
                else:
                    st.info("👆 Selecciona usuarios en el filtro para ver el detalle de llamados")
            
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
            
            # Crear DataFrame para el gráfico
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
                    
                    # Agregar la tabla de usuarios seleccionados si existe
                    if 'usuarios_seleccionados_df' in locals() and not usuarios_seleccionados_df.empty:
                        usuarios_seleccionados_df.to_excel(w, sheet_name='Usuarios Seleccionados', index=False)
                    
                    config = pd.DataFrame({
                        'Parámetro': ['Rango', 'Día', 'Servicios', 'Usuarios', 'Registros'],
                        'Valor': [
                            f"{fecha_ini} a {fecha_fin}",
                            dia_sel,
                            ', '.join(servicio_sel) if servicio_sel else 'Todos',
                            ', '.join(usuario_sel) if usuario_sel else 'Ninguno',
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
