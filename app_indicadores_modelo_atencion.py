import streamlit as st
import pandas aspd
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
                df_proceso['DIA_SEMANA'] = df_proceso['FECHA CREACION'].dt.day_name()
                df_proceso['DIA_SEMANA_NUM'] = df_proceso['FECHA CREACION'].dt.dayofweek
                
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
                    
                    if df_proceso.empty:
                        st.warning("No hay registros para el rango seleccionado (Lunes a Viernes).")
                        st.stop()
                else:
                    dia_ingles = mapa_dias[dia_seleccionado]
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_ingles]
                    
                    if df_proceso.empty:
                        st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado}) en el rango filtrado.")
                        st.stop()
                    
                    dias_unicos = df_proceso['FECHA'].nunique()
                    st.caption(f"📊 Promediando {dias_unicos} día(s) de {dia_seleccionado}")
                
                # Identificar horas con registros
                horas_con_registros = sorted(df_proceso['HORA'].unique())
                horas_formateadas = [f"{h}:00" for h in horas_con_registros]
                
                # Obtener lista de usuarios únicos
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
                
                # Crear DataFrame
                tabla_resultados = pd.DataFrame(data, index=usuarios_proceso, columns=horas_formateadas)
                
                # Calcular estadísticas por usuario (excluyendo valores 0 para mínimo)
                tabla_resultados['TOTAL'] = tabla_resultados[horas_formateadas].sum(axis=1).round(2)
                
                # Para MÍNIMO: solo considerar valores > 0
                minimos = []
                for idx in tabla_resultados.index:
                    valores_fila = tabla_resultados.loc[idx, horas_formateadas]
                    valores_positivos = valores_fila[valores_fila > 0]
                    if len(valores_positivos) > 0:
                        minimos.append(valores_positivos.min())
                    else:
                        minimos.append(0)
                tabla_resultados['MÍNIMO'] = [round(x, 2) for x in minimos]
                
                # Para MÁXIMO: considerar todos los valores
                tabla_resultados['MÁXIMO'] = tabla_resultados[horas_formateadas].max(axis=1).round(2)
                
                # Ordenar por total
                tabla_resultados = tabla_resultados.sort_values('TOTAL', ascending=False)
                
                # Calcular totales por hora
                totales_por_hora = tabla_resultados[horas_formateadas].sum(axis=0).round(2)
                
                # Crear fila de totales
                datos_fila_total = {'TOTAL': totales_por_hora.sum()}
                for hora in horas_formateadas:
                    datos_fila_total[hora] = totales_por_hora[hora]
                datos_fila_total['MÍNIMO'] = ''
                datos_fila_total['MÁXIMO'] = ''
                
                fila_total = pd.DataFrame([datos_fila_total], index=['TOTAL'])
                
                # Combinar tabla con totales
                tabla_resultados_con_total = pd.concat([tabla_resultados, fila_total])
                
                # --- TABLA 1: PROMEDIOS DE REGISTROS ---
                st.subheader("Ingresos promedio abiertos por Admisionista")
                st.markdown("*Cantidad de ingresos que realizan por hora*")

                # Aplicar formato diferenciado
                styler = tabla_resultados_con_total.style
                
                # Formato para filas de usuarios (índices que no son 'TOTAL')
                mascara_usuarios = tabla_resultados_con_total.index != 'TOTAL'
                styler = styler.format("{:.2f}", subset=pd.IndexSlice[tabla_resultados_con_total.index[mascara_usuarios], horas_formateadas + ['TOTAL', 'MÍNIMO', 'MÁXIMO']])
                
                # Formato para fila TOTAL (solo horas y TOTAL, no MÍNIMO/MÁXIMO)
                styler = styler.format("{:.2f}", subset=pd.IndexSlice[['TOTAL'], horas_formateadas + ['TOTAL']])
                
                # Gradiente de colores
                styler = styler.background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[tabla_resultados.index, horas_formateadas])
                
                # Alineación centrada
                styler = styler.set_properties(**{'text-align': 'center'})
                
                st.dataframe(
                    styler,
                    use_container_width=True,
                    height=min(400, 50 + (len(usuarios_proceso) * 35))
                )
                
                # --- TABLA 2: TIEMPOS PROMEDIOS DE ADMISIÓN ---
                st.subheader("Tiempos Promedios de Admisión")
                st.markdown("*Tiempo promedio (minutos) que tardan en hacer un ingreso cada hora*")
                
                # Crear tabla de tiempos
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
                    # Para MÍNIMO: excluir 0
                    tiempos_usuario_min = [tabla_tiempos.loc[usuario, hora] for hora in horas_formateadas 
                                          if tabla_tiempos.loc[usuario, hora] > 0]
                    
                    # Para MÁXIMO: excluir 60 (1 registro por hora)
                    tiempos_usuario_max = [tabla_tiempos.loc[usuario, hora] for hora in horas_formateadas 
                                          if tabla_tiempos.loc[usuario, hora] > 0 and tabla_tiempos.loc[usuario, hora] != 60]
                    
                    # Para PROMEDIO: usar todos los tiempos > 0
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
                
                # Mostrar tabla de tiempos
                styler_tiempos = tabla_tiempos.style
                styler_tiempos = styler_tiempos.format("{:.1f}", na_rep="-")
                styler_tiempos = styler_tiempos.background_gradient(cmap='YlOrRd_r', axis=1, 
                                                                   subset=pd.IndexSlice[usuarios_proceso, horas_formateadas])
                styler_tiempos = styler_tiempos.set_properties(**{'text-align': 'center'})
                
                st.dataframe(
                    styler_tiempos,
                    use_container_width=True,
                    height=min(400, 50 + (len(usuarios_proceso) * 35))
                )
                
                # --- ESTADÍSTICAS RESUMEN ---
                st.subheader("Estadísticas Resumen vs Estándares")
                
                # Calcular promedios generales
                valores_validos = []
                for col in horas_formateadas:
                    for usuario in usuarios_proceso:
                        valor = tabla_resultados.loc[usuario, col]
                        if valor > 0:
                            valores_validos.append(valor)
                
                promedio_general = np.mean(valores_validos) if valores_validos else 0
                
                # Calcular tiempo promedio general (excluyendo 60)
                tiempos_todos = []
                for usuario in usuarios_proceso:
                    for hora in horas_formateadas:
                        valor = tabla_tiempos.loc[usuario, hora]
                        if valor > 0 and valor != 60:
                            tiempos_todos.append(valor)
                
                # Encontrar máximo registros/hora
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
                
                # Encontrar mínimo tiempo de admisión (excluyendo 0)
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
                
                # Diferencias
                diff_registros = promedio_general - ESTANDAR_REGISTROS
                diff_registros_pct = (diff_registros / ESTANDAR_REGISTROS) * 100 if ESTANDAR_REGISTROS > 0 else 0
                
                tiempo_promedio_general = np.mean(tiempos_todos) if tiempos_todos else None
                
                if tiempo_promedio_general:
                    diff_tiempo = tiempo_promedio_general - ESTANDAR_TIEMPO
                    diff_tiempo_pct = (diff_tiempo / ESTANDAR_TIEMPO) * 100 if ESTANDAR_TIEMPO > 0 else 0
                
                # Mostrar métricas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📈 Promedio General vs Estándar")
                    delta_reg = f"{diff_registros:+.2f} vs estándar ({diff_registros_pct:+.1f}%)"
                    st.metric("Promedio registros/hora", f"{promedio_general:.2f}", 
                             delta=delta_reg, delta_color="inverse" if diff_registros > 0 else "normal")
                    st.markdown(f"**Estándar:** {ESTANDAR_REGISTROS}")
                    
                    st.markdown("### 📈 Máximo Registros/Hora")
                    st.metric("Máximo alcanzado", f"{max_registros:.2f}")
                    st.markdown(f"**Usuario:** {usuario_max}")
                    st.markdown(f"**Hora:** {hora_max}")
                
                with col2:
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
                
                chart_data = pd.DataFrame({
                    'Usuario': top_usuarios.index,
                    'Promedio Diario': top_usuarios['TOTAL'].values
                }).set_index('Usuario')
                
                st.bar_chart(chart_data, height=400)
                st.caption("📊 Ordenado de mayor a menor")
                
                # --- EXPORTACIÓN A EXCEL ---
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
    else:
        st.info("👆 Sube un archivo Excel")

# ============================================================================
# PESTAÑA 2: ANÁLISIS DE LLAMADOS (CORREGIDA)
# ============================================================================
with tab2:
    st.header("📞 Análisis de Llamados")
    
    with st.sidebar:
        st.header("⚙️ Configuración Pestaña 2")
        uploaded_file_tab2 = st.file_uploader("Sube tu archivo Excel (.xlsx)", 
                                            type=["xlsx"], 
                                            help="Archivo con información de llamados",
                                            key="tab2_file")

    if uploaded_file_tab2 is not None:
        try:
            # Leer archivo
            df_tab2 = pd.read_excel(uploaded_file_tab2)
            
            # Mostrar vista previa de columnas para ayudar al usuario
            st.sidebar.divider()
            st.sidebar.subheader("📋 Columnas encontradas:")
            columnas_encontradas = df_tab2.columns.tolist()
            for i, col in enumerate(columnas_encontradas):
                st.sidebar.text(f"{i+1}. {col}")
            
            # Limpiar nombres de columnas
            df_tab2.columns = df_tab2.columns.astype(str).str.strip()
            
            # Función mejorada para encontrar columna
            def encontrar_columna(df, posibles_nombres):
                """
                Busca una columna que coincida con alguno de los nombres posibles
                """
                columnas_lower = {col: col.lower() for col in df.columns}
                
                for posible in posibles_nombres:
                    posible_lower = posible.lower()
                    
                    # Búsqueda exacta (sin importar mayúsculas)
                    for col_original, col_lower in columnas_lower.items():
                        if col_lower == posible_lower:
                            return col_original
                    
                    # Búsqueda por contener la palabra
                    for col_original, col_lower in columnas_lower.items():
                        if posible_lower in col_lower:
                            return col_original
                    
                    # Búsqueda por palabras clave
                    palabras_clave = posible_lower.split()
                    for col_original, col_lower in columnas_lower.items():
                        if all(palabra in col_lower for palabra in palabras_clave):
                            return col_original
                
                return None
            
            # Buscar columnas necesarias con múltiples variantes
            col_hora = encontrar_columna(df_tab2, [
                'hora llegada', 'hora_llegada', 'hora de llegada', 
                'horallegada', 'fecha hora llegada', 'fecha llegada',
                'hora', 'llegada', 'fecha'
            ])
            
            col_servicio = encontrar_columna(df_tab2, [
                'servicio', 'servicios', 'nombre servicio',
                'serv', 'area', 'especialidad'
            ])
            
            col_usuario = encontrar_columna(df_tab2, [
                'usuario atención', 'usuario_atencion', 'usuario atencion',
                'usuario', 'usuario que atiende', 'atendio', 'atendió',
                'nombre usuario', 'operador', 'agente'
            ])
            
            col_tipo = encontrar_columna(df_tab2, [
                'tipo', 'tipo llamado', 'tipo llamada',
                'tipollamado', 'clase', 'categoria', 'categoría'
            ])
            
            # Mostrar qué columnas se encontraron
            st.sidebar.divider()
            st.sidebar.subheader("✅ Columnas identificadas:")
            st.sidebar.write(f"**Hora llegada:** {col_hora if col_hora else '❌ No encontrada'}")
            st.sidebar.write(f"**Servicio:** {col_servicio if col_servicio else '❌ No encontrada'}")
            st.sidebar.write(f"**Usuario:** {col_usuario if col_usuario else '❌ No encontrada'}")
            if col_tipo:
                st.sidebar.write(f"**Tipo:** {col_tipo}")
            
            # Verificar columnas necesarias
            if not all([col_hora, col_servicio, col_usuario]):
                st.error("""
                ❌ **No se encontraron las columnas necesarias.**
                
                El archivo debe tener columnas que contengan:
                - Hora de llegada (ej: 'Hora Llegada', 'HORA_LLEGADA', 'fecha')
                - Servicio (ej: 'Servicio', 'SERVICIO', 'area')
                - Usuario que atiende (ej: 'Usuario Atención', 'USUARIO', 'agente')
                
                **Columnas encontradas en tu archivo:**
                """ + "\n".join([f"- {col}" for col in columnas_encontradas]))
                st.stop()
            
            # Renombrar columnas para uso interno
            rename_dict = {
                col_hora: 'HORA_LLEGADA',
                col_servicio: 'SERVICIO',
                col_usuario: 'USUARIO_ATENCION'
            }
            
            if col_tipo:
                rename_dict[col_tipo] = 'TIPO'
            
            df_tab2 = df_tab2.rename(columns=rename_dict)
            
            # --- PROCESAMIENTO DE FECHAS ---
            # Intentar diferentes formatos de fecha
            df_tab2["HORA_LLEGADA"] = pd.to_datetime(df_tab2["HORA_LLEGADA"], errors='coerce')
            
            # Si hay muchos errores, intentar con formato de Excel
            if df_tab2["HORA_LLEGADA"].isna().sum() > len(df_tab2) * 0.5:
                try:
                    # Intentar convertir como número de Excel
                    df_tab2["HORA_LLEGADA"] = pd.to_datetime(df_tab2["HORA_LLEGADA"].astype(float), 
                                                             origin='1899-12-30', unit='D', errors='coerce')
                except:
                    pass
            
            df_tab2_limpio = df_tab2.dropna(subset=["HORA_LLEGADA"])
            
            if df_tab2_limpio.empty:
                st.warning("No hay registros con fechas válidas en la columna de hora de llegada.")
                st.stop()
            
            # Identificar límites de fechas
            fecha_min = df_tab2_limpio["HORA_LLEGADA"].min().date()
            fecha_max = df_tab2_limpio["HORA_LLEGADA"].max().date()
            
            # --- FILTROS EN SIDEBAR ---
            with st.sidebar:
                st.divider()
                st.subheader("📅 Rango de Fechas")
                
                col1_tab2, col2_tab2 = st.columns(2)
                with col1_tab2:
                    fecha_ini = st.date_input("Inicio", fecha_min, min_value=fecha_min, max_value=fecha_max, key="tab2_fecha_ini")
                with col2_tab2:
                    fecha_fin = st.date_input("Fin", fecha_max, min_value=fecha_min, max_value=fecha_max, key="tab2_fecha_fin")
                
                if fecha_ini > fecha_fin:
                    st.error("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin")
                    st.stop()
                
                # Filtro de servicios
                servicios = sorted(df_tab2_limpio["SERVICIO"].dropna().unique())
                if servicios:
                    servicio_sel = st.multiselect("📋 Servicios", servicios, key="tab2_servicios")
                else:
                    servicio_sel = []
                    st.warning("No hay servicios en los datos")
                
                # Filtro de usuarios
                usuarios = sorted(df_tab2_limpio["USUARIO_ATENCION"].dropna().unique())
                if usuarios:
                    usuario_sel = st.multiselect("👤 Usuarios", usuarios, key="tab2_usuarios")
                else:
                    usuario_sel = []
                    st.warning("No hay usuarios en los datos")
                
                # Selector de día
                st.subheader("⚙️ Configuración")
                dias_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos (L-V)"]
                dia_sel = st.selectbox("Día a analizar", dias_opciones, index=7, key="tab2_dia")
            
            # --- APLICAR FILTROS ---
            df_filtrado = df_tab2_limpio[
                (df_tab2_limpio["HORA_LLEGADA"].dt.date >= fecha_ini) & 
                (df_tab2_limpio["HORA_LLEGADA"].dt.date <= fecha_fin)
            ]
            
            if servicio_sel:
                df_filtrado = df_filtrado[df_filtrado["SERVICIO"].isin(servicio_sel)]
            
            if usuario_sel:
                df_filtrado = df_filtrado[df_filtrado["USUARIO_ATENCION"].isin(usuario_sel)]
            
            if df_filtrado.empty:
                st.warning("No hay datos con los filtros seleccionados")
                st.stop()
            
            # --- PROCESAMIENTO ---
            st.divider()
            st.info(f"""
            **Configuración de análisis:**
            - **Rango:** {fecha_ini} a {fecha_fin}
            - **Día analizado:** {dia_sel}
            - **Servicios:** {len(servicio_sel)} seleccionados
            - **Usuarios:** {len(usuario_sel)} seleccionados
            - **Registros analizados:** {len(df_filtrado):,}
            """)
            
            # Preparar datos
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
            
            # Obtener horas y usuarios
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
            
            # MÍNIMO: solo valores > 0
            minimos = []
            for idx in tabla_llamados.index:
                valores_fila = tabla_llamados.loc[idx, horas_fmt]
                valores_positivos = valores_fila[valores_fila > 0]
                if len(valores_positivos) > 0:
                    minimos.append(valores_positivos.min())
                else:
                    minimos.append(0)
            tabla_llamados['MÍNIMO'] = [round(x, 2) for x in minimos]
            
            # MÁXIMO: todos los valores
            tabla_llamados['MÁXIMO'] = tabla_llamados[horas_fmt].max(axis=1).round(2)
            
            # Ordenar por total
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
            
            # Mostrar tabla
            st.subheader("📞 Promedio de Llamados por Agente")
            st.markdown("*Cantidad promedio de llamados por hora*")
            
            styler = tabla_llamados_con_total.style
            mascara_usuarios = tabla_llamados_con_total.index != 'TOTAL'
            styler = styler.format("{:.2f}", subset=pd.IndexSlice[tabla_llamados_con_total.index[mascara_usuarios], horas_fmt + ['TOTAL', 'MÍNIMO', 'MÁXIMO']])
            styler = styler.format("{:.2f}", subset=pd.IndexSlice[['TOTAL'], horas_fmt + ['TOTAL']])
            styler = styler.background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[tabla_llamados.index, horas_fmt])
            styler = styler.set_properties(**{'text-align': 'center'})
            
            st.dataframe(styler, use_container_width=True, height=min(400, 50 + (len(usuarios_proc) * 35)))
            
            # --- TABLA DE TIPOS (si existe) ---
            if 'TIPO' in df_proceso.columns:
                st.divider()
                st.subheader("🔄 Llamados Manuales vs Automáticos")
                
                def clasificar_llamado(valor):
                    if pd.isna(valor):
                        return 'NO CLASIFICADO'
                    v = str(valor).lower().strip()
                    if any(p in v for p in ['manual', 'm', 'man']):
                        return 'MANUAL'
                    elif any(p in v for p in ['auto', 'a', 'aut', 'autom']):
                        return 'AUTOMÁTICO'
                    return 'OTRO'
                
                df_proceso['CLASIFICACION'] = df_proceso['TIPO'].apply(clasificar_llamado)
                
                # Crear tabla resumen
                resumen_tipos = pd.crosstab(
                    df_proceso['USUARIO_ATENCION'], 
                    df_proceso['CLASIFICACION'],
                    margins=True,
                    margins_name='TOTAL'
                )
                
                st.dataframe(resumen_tipos, use_container_width=True)
            
            # --- GRÁFICO TOP USUARIOS ---
            st.divider()
            st.subheader("🏆 Top 10 Usuarios por Actividad")
            
            top_n = min(10, len(tabla_llamados))
            top_usuarios = tabla_llamados.head(top_n)
            
            chart_data = pd.DataFrame({
                'Usuario': top_usuarios.index,
                'Promedio Diario': top_usuarios['TOTAL'].values
            }).set_index('Usuario')
            
            st.bar_chart(chart_data, height=400)
            st.caption("📊 Ordenado de mayor a menor promedio de llamados")
            
            # --- EXPORTAR A EXCEL ---
            st.divider()
            st.subheader("📤 Exportar Resultados")
            
            def crear_excel_tab2():
                out = BytesIO()
                with pd.ExcelWriter(out, engine='openpyxl') as w:
                    tabla_llamados_con_total.to_excel(w, sheet_name='Llamados Promedio')
                    
                    if 'resumen_tipos' in locals():
                        resumen_tipos.to_excel(w, sheet_name='Clasificación Llamados')
                    
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
        st.info("👆 Sube un archivo Excel con datos de llamados")
