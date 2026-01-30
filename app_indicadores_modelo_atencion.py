import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
import matplotlib.pyplot as plt
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos y Llamados", layout="wide")

st.title("📊 Visualizador de Registros con Filtros Dinámicos")

# Crear pestañas
tab1, tab2 = st.tabs(["📋 Análisis de Ingresos", "📞 Análisis de Llamados"])

# ============================================================================
# PESTAÑA 1: ANÁLISIS DE INGRESOS (CÓDIGO ORIGINAL)
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

                # Botón para procesar
                procesar = st.button("🚀 Procesar", type="primary", use_container_width=True, key="tab1_procesar")

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

            # --- PROCESAMIENTO AVANZADO (solo si se presiona el botón) ---
            if procesar and not df_filtrado.empty and fecha_inicio <= fecha_fin:
                st.divider()
                st.subheader("📈 Análisis de Promedios por Hora y Día")
                
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
                df_proceso['DIA_SEMANA_NUM'] = df_proceso['FECHA CREACION'].dt.dayofweek  # 0=Lunes, 6=Domingo
                
                # Filtrar por día de la semana según la selección
                if dia_seleccionado == "Todos los días (L-V)":
                    # Filtrar solo lunes a viernes
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA_NUM'] < 5]
                    dias_analizados = "Lunes a Viernes"
                    dia_label = "L-V"
                else:
                    # Filtrar por día específico
                    df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_seleccionado]
                    dias_analizados = dia_seleccionado
                    dia_label = dia_seleccionado[:3]
                
                # Verificar si hay datos después del filtro por día
                if df_proceso.empty:
                    st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado}) en el rango filtrado.")
                else:
                    # Identificar horas con registros (no usar horas fijas 6-20)
                    horas_con_registros = sorted(df_proceso['HORA'].unique())
                    
                    # Obtener lista de usuarios únicos
                    usuarios_proceso = sorted(df_proceso["USUARIO CREA INGRESO"].dropna().unique())
                    
                    if not usuarios_proceso:
                        st.warning("No hay usuarios en los datos filtrados.")
                    else:
                        # Crear estructura para la tabla dinámica
                        tabla_resultados = pd.DataFrame(index=usuarios_proceso, columns=horas_con_registros)
                        
                        # Calcular promedios para cada usuario y hora
                        for usuario in usuarios_proceso:
                            df_usuario = df_proceso[df_proceso["USUARIO CREA INGRESO"] == usuario]
                            
                            for hora in horas_con_registros:
                                # Filtrar registros para esta hora específica
                                df_hora = df_usuario[df_usuario['HORA'] == hora]
                                
                                if not df_hora.empty:
                                    # Contar registros por fecha única (para calcular promedio por día)
                                    conteo_por_dia = df_hora.groupby('FECHA').size()
                                    
                                    # Calcular promedio de registros por día en esta hora
                                    promedio = conteo_por_dia.mean()
                                    tabla_resultados.at[usuario, hora] = round(promedio, 2)
                                else:
                                    tabla_resultados.at[usuario, hora] = 0.0
                        
                        # Formatear nombres de columnas (horas)
                        horas_formateadas = [f"{h}:00" for h in horas_con_registros]
                        tabla_resultados.columns = horas_formateadas
                        
                        # Asegurar que todos los valores sean numéricos
                        tabla_resultados = tabla_resultados.astype(float)
                        
                        # Agregar columna de total por usuario
                        tabla_resultados['TOTAL'] = tabla_resultados.sum(axis=1)
                        
                        # Ordenar por total descendente
                        tabla_resultados = tabla_resultados.sort_values('TOTAL', ascending=False)
                        
                        # --- TABLA 1: PROMEDIOS DE REGISTROS ---
                        st.subheader("📋 Tabla de ingresos promedio abiertos por Admisionista")
                        st.markdown("*Cantidad de ingresos que realizan por hora*")

                        # Mostrar tabla con formato
                        st.dataframe(
                            tabla_resultados.style
                            .background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[:, horas_formateadas])
                            .format("{:.2f}")
                            .set_properties(**{'text-align': 'center'}),
                            use_container_width=True,
                            height=min(400, 50 + (len(usuarios_proceso) * 35))
                        )
                        
                        # --- TABLA 2: TIEMPOS PROMEDIOS DE ADMISIÓN ---
                        st.subheader("⏱️ Tabla de Tiempos Promedios de Admisión")
                        st.markdown("*Tiempo promedio (minutos) que tardan en hacer un ingreso cada hora*")
                        
                        # Crear tabla de tiempos promedios (usando NaN en lugar de 'N/A' para valores vacíos)
                        tabla_tiempos = pd.DataFrame(index=usuarios_proceso, columns=horas_formateadas)
                        
                        # Calcular tiempo promedio = 60 / promedio de registros
                        for usuario in usuarios_proceso:
                            for hora_idx, hora_col in enumerate(horas_formateadas):
                                promedio_registros = tabla_resultados.at[usuario, hora_col]
                                if promedio_registros > 0:
                                    tiempo_promedio = 60 / promedio_registros
                                    tabla_tiempos.at[usuario, hora_col] = round(tiempo_promedio, 1)
                                else:
                                    # Usar np.nan en lugar de 'N/A' para valores vacíos
                                    tabla_tiempos.at[usuario, hora_col] = np.nan
                        
                        # Agregar columna de tiempo promedio total (promedio de tiempos válidos)
                        for usuario in usuarios_proceso:
                            tiempos_usuario = tabla_tiempos.loc[usuario, horas_formateadas].dropna().values
                            if len(tiempos_usuario) > 0:
                                tiempo_promedio_total = np.mean(tiempos_usuario)
                                tabla_tiempos.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = round(tiempo_promedio_total, 1)
                            else:
                                tabla_tiempos.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = np.nan
                        
                        # Mostrar tabla de tiempos con gradiente invertido
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
                        st.subheader("📊 Estadísticas Resumen vs Estándares")
                        
                        # Contar horas con registros
                        horas_con_registros_count = len(horas_con_registros)
                        
                        # Calcular promedios generales
                        promedio_general = tabla_resultados[horas_formateadas].values.mean()
                        
                        # Calcular tiempo promedio general (excluyendo NaN)
                        tiempos_todos = []
                        for usuario in usuarios_proceso:
                            for hora_col in horas_formateadas:
                                valor = tabla_tiempos.at[usuario, hora_col]
                                if not pd.isna(valor):
                                    tiempos_todos.append(valor)
                        
                        # ESTÁNDARES DEFINIDOS
                        ESTANDAR_REGISTROS_HORA = 13  # 13 registros por hora estándar
                        ESTANDAR_TIEMPO_ADMISION = 4  # 4 minutos por admisión estándar
                        
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
                        
                        # Mostrar métricas con diferencias vs estándar
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Métrica de registros por hora vs estándar
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
                            # Métrica de tiempo de admisión vs estándar
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
                        st.subheader("📊 Top Usuarios por Actividad Promedio")
                        
                        top_n = min(10, len(tabla_resultados))
                        top_usuarios = tabla_resultados.head(top_n)
                        
                        # Crear gráfico de barras con matplotlib (rotado como solicitado)
                        fig, ax = plt.subplots(figsize=(12, 6))
                        
                        # Preparar datos para el gráfico
                        usuarios_nombres = top_usuarios.index.tolist()
                        promedios_totales = top_usuarios['TOTAL'].values
                        
                        # Crear barras verticales (X: usuario, Y: promedio)
                        bars = ax.bar(usuarios_nombres, promedios_totales, color='steelblue', alpha=0.8)
                        
                        # Configurar ejes
                        ax.set_xlabel('Usuario')
                        ax.set_ylabel('Promedio de Registros por Día')
                        ax.set_title(f'Top {top_n} Usuarios - Promedio Diario de Registros ({dia_label})')
                        
                        # Rotar etiquetas del eje X para mejor visualización
                        plt.xticks(rotation=45, ha='right')
                        
                        # Añadir valores en las barras
                        for bar in bars:
                            height = bar.get_height()
                            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                   f'{height:.1f}', ha='center', va='bottom', fontsize=9)
                        
                        # Ajustar márgenes
                        plt.tight_layout()
                        
                        # Mostrar el gráfico en Streamlit
                        st.pyplot(fig)
                        plt.close(fig)
                        
                        # --- EXPORTAR RESULTADOS ---
                        st.divider()
                        st.subheader("📥 Exportar Resultados")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Exportar tabla de promedios a CSV
                            csv_promedios = tabla_resultados.to_csv().encode('utf-8')
                            st.download_button(
                                label="📊 Descargar promedios (CSV)",
                                data=csv_promedios,
                                file_name=f"promedios_registros_{fecha_inicio}_{fecha_fin}_{dia_label}.csv",
                                mime="text/csv",
                                help="Tabla de promedios de registros por hora",
                                key="tab1_csv_promedios"
                            )
                        
                        with col2:
                            # Exportar tabla de tiempos a CSV (reemplazar NaN por "-")
                            tabla_tiempos_export = tabla_tiempos.copy()
                            tabla_tiempos_export = tabla_tiempos_export.fillna("-")
                            csv_tiempos = tabla_tiempos_export.to_csv().encode('utf-8')
                            st.download_button(
                                label="⏱️ Descargar tiempos (CSV)",
                                data=csv_tiempos,
                                file_name=f"tiempos_admision_{fecha_inicio}_{fecha_fin}_{dia_label}.csv",
                                mime="text/csv",
                                help="Tabla de tiempos promedios de admisión",
                                key="tab1_csv_tiempos"
                            )
                        
                        with col3:
                            # Crear archivo Excel con ambas tablas
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                tabla_resultados.to_excel(writer, sheet_name='Promedios_Registros')
                                
                                # Exportar tabla de tiempos reemplazando NaN por "-"
                                tabla_tiempos_export_excel = tabla_tiempos.copy()
                                tabla_tiempos_export_excel = tabla_tiempos_export_excel.fillna("-")
                                tabla_tiempos_export_excel.to_excel(writer, sheet_name='Tiempos_Admision')
                                
                                # Agregar hoja con estadísticas y comparación con estándar
                                estadisticas_df = pd.DataFrame({
                                    'Métrica': [
                                        'Usuarios analizados', 
                                        'Horas con registros', 
                                        'Promedio registros/hora (Real)',
                                        'Promedio registros/hora (Estándar)',
                                        'Diferencia registros/hora',
                                        'Diferencia registros/hora (%)',
                                        'Tiempo promedio admisión (Real)',
                                        'Tiempo promedio admisión (Estándar)',
                                        'Diferencia tiempo admisión',
                                        'Diferencia tiempo admisión (%)',
                                        'Rango de fechas', 
                                        'Día analizado', 
                                        'Fecha de generación'
                                    ],
                                    'Valor': [
                                        len(usuarios_proceso), 
                                        horas_con_registros_count,
                                        f"{promedio_general:.2f}",
                                        f"{ESTANDAR_REGISTROS_HORA}",
                                        f"{diferencia_registros:+.2f}",
                                        f"{diferencia_registros_porcentaje:+.1f}%",
                                        f"{tiempo_promedio_general:.1f} min" if tiempo_promedio_general else "-",
                                        f"{ESTANDAR_TIEMPO_ADMISION} min",
                                        f"{diferencia_tiempo:+.1f} min" if diferencia_tiempo else "-",
                                        f"{diferencia_tiempo_porcentaje:+.1f}%" if diferencia_tiempo_porcentaje else "-",
                                        f"{fecha_inicio} a {fecha_fin}",
                                        dia_seleccionado, 
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    ]
                                })
                                estadisticas_df.to_excel(writer, sheet_name='Estadísticas', index=False)
                            
                            excel_data = output.getvalue()
                            
                            st.download_button(
                                label="📁 Descargar todo (Excel)",
                                data=excel_data,
                                file_name=f"analisis_completo_{fecha_inicio}_{fecha_fin}_{dia_label}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="Archivo Excel con todas las tablas y estadísticas",
                                key="tab1_excel"
                            )

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
        
        # 1. Carga de archivo en la sidebar (con campos diferentes)
        uploaded_file_tab2 = st.file_uploader("Sube tu archivo Excel (.xlsx)", 
                                            type=["xlsx"], 
                                            help="Archivo debe contener columnas relacionadas con llamados: Hora Llegada, Servicio, Usuario Atención",
                                            key="tab2_file")

    if uploaded_file_tab2 is not None:
        try:
            # Leer el archivo
            df_tab2 = pd.read_excel(uploaded_file_tab2)
            
            # Mostrar información sobre las columnas disponibles
            with st.expander("📋 Ver columnas del archivo cargado"):
                st.write(f"Número de columnas: {len(df_tab2.columns)}")
                st.write("Columnas disponibles:")
                for col in df_tab2.columns:
                    st.write(f"- {col}")
            
            # --- ENCONTRAR COLUMNAS POR NOMBRES ALTERNATIVOS ---
            # Función para encontrar columnas por nombres alternativos
            def encontrar_columna(df, nombres_alternativos):
                for nombre in nombres_alternativos:
                    if nombre in df.columns:
                        return nombre
                return None
            
            # Nombres alternativos para cada columna clave
            nombres_hora_llegada = [
                'HORA LLEGADA', 'Hora Llegada', 'Hora llegada', 'HORA_LLEGADA',
                'Hora de Llegada', 'HORA DE LLEGADA', 'Hora de llegada',
                'Fecha Hora Llegada', 'FECHA HORA LLEGADA'
            ]
            
            nombres_servicio = [
                'Servicio', 'SERVICIO', 'servicio', 'Servicio Atención',
                'SERVICIO ATENCIÓN', 'Tipo Servicio'
            ]
            
            nombres_usuario_atencion = [
                'Usuario Atención', 'USUARIO ATENCIÓN', 'Usuario atención',
                'Usuario', 'USUARIO', 'Atendido Por', 'ATENDIDO POR',
                'Usuario que Atiende', 'USUARIO QUE ATIENDE'
            ]
            
            # Encontrar las columnas reales
            col_hora_llegada = encontrar_columna(df_tab2, nombres_hora_llegada)
            col_servicio = encontrar_columna(df_tab2, nombres_servicio)
            col_usuario_atencion = encontrar_columna(df_tab2, nombres_usuario_atencion)
            
            # Verificar que se encontraron las columnas necesarias
            columnas_faltantes = []
            if not col_hora_llegada:
                columnas_faltantes.append("Hora Llegada")
            if not col_servicio:
                columnas_faltantes.append("Servicio")
            if not col_usuario_atencion:
                columnas_faltantes.append("Usuario Atención")
            
            if columnas_faltantes:
                st.error(f"⚠️ No se encontraron las siguientes columnas necesarias: {', '.join(columnas_faltantes)}")
                st.info("""
                **Sugerencias:**
                1. Verifica que el archivo tenga columnas con nombres similares a:
                   - Para fecha/hora: 'HORA LLEGADA', 'Hora Llegada', 'Hora de Llegada'
                   - Para servicio: 'Servicio', 'SERVICIO'
                   - Para usuario: 'Usuario Atención', 'USUARIO ATENCIÓN'
                2. Revisa la pestaña 'Ver columnas del archivo cargado' para ver los nombres exactos
                3. Asegúrate de que no haya espacios extra al inicio o final de los nombres
                """)
            else:
                st.success(f"✅ Columnas encontradas: '{col_hora_llegada}', '{col_servicio}', '{col_usuario_atencion}'")
                
                # Renombrar columnas para uso interno
                df_tab2 = df_tab2.rename(columns={
                    col_hora_llegada: 'HORA_LLEGADA',
                    col_servicio: 'SERVICIO',
                    col_usuario_atencion: 'USUARIO_ATENCION'
                })
                
                # --- PROCESAMIENTO DE FECHAS ---
                # Convertimos la columna a datetime para poder operar
                df_tab2["HORA_LLEGADA"] = pd.to_datetime(df_tab2["HORA_LLEGADA"], errors='coerce')
                
                # Eliminamos filas con fechas nulas para evitar errores en el selector
                df_tab2_limpio = df_tab2.dropna(subset=["HORA_LLEGADA"])

                if df_tab2_limpio.empty:
                    st.warning("No hay registros con fechas válidas en la columna de hora de llegada.")
                else:
                    # Identificamos los límites reales del archivo
                    fecha_minima_archivo_tab2 = df_tab2_limpio["HORA_LLEGADA"].min().date()
                    fecha_maxima_archivo_tab2 = df_tab2_limpio["HORA_LLEGADA"].max().date()

                    # --- CONTINUACIÓN DE FILTROS EN SIDEBAR ---
                    with st.sidebar:
                        # 2. Filtro de Fechas (Rango basado en el archivo)
                        st.subheader("Rango de Evaluación")
                        
                        # Crear dos selectores separados para fecha inicial y final
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
                        
                        # Validar que la fecha de inicio sea menor o igual a la fecha de fin
                        if fecha_inicio_tab2 > fecha_fin_tab2:
                            st.error("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin")
                            st.info(f"Selecciona fechas entre: **{fecha_minima_archivo_tab2}** y **{fecha_maxima_archivo_tab2}**")
                        else:
                            st.success(f"✅ Rango válido: {fecha_inicio_tab2} a {fecha_fin_tab2}")

                        # 3. FILTRO ADICIONAL POR SERVICIO (NUEVO)
                        servicios = sorted(df_tab2_limpio["SERVICIO"].dropna().unique())
                        servicio_sel = st.multiselect(
                            "Servicio:", 
                            options=servicios,
                            help="Selecciona uno o más servicios",
                            key="tab2_servicio"
                        )

                        # 4. Filtro de Usuario Atención
                        usuarios_tab2 = sorted(df_tab2_limpio["USUARIO_ATENCION"].dropna().unique())
                        usuario_sel_tab2 = st.multiselect(
                            "Usuario Atención:", 
                            options=usuarios_tab2,
                            help="Selecciona uno o más usuarios",
                            key="tab2_usuario"
                        )

                        # 5. Selector de día de la semana para el procesamiento
                        st.subheader("Configuración de Procesamiento")
                        dia_semana_opciones_tab2 = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
                        dia_seleccionado_tab2 = st.selectbox(
                            "Día de la semana a analizar:",
                            options=dia_semana_opciones_tab2,
                            index=7,  # Por defecto selecciona "Todos los días (L-V)"
                            help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                            key="tab2_dia"
                        )

                        # Botón para procesar
                        procesar_tab2 = st.button("🚀 Procesar", type="primary", use_container_width=True, key="tab2_procesar")

                    # --- APLICACIÓN DE FILTROS ---
                    df_filtrado_tab2 = df_tab2_limpio.copy()

                    # Filtrado por Rango de Fechas (solo si las fechas son válidas)
                    if fecha_inicio_tab2 <= fecha_fin_tab2:
                        df_filtrado_tab2 = df_filtrado_tab2[
                            (df_filtrado_tab2["HORA_LLEGADA"].dt.date >= fecha_inicio_tab2) & 
                            (df_filtrado_tab2["HORA_LLEGADA"].dt.date <= fecha_fin_tab2)
                        ]
                    
                    # Filtrado por Servicio (NUEVO FILTRO)
                    if servicio_sel:
                        df_filtrado_tab2 = df_filtrado_tab2[df_filtrado_tab2["SERVICIO"].isin(servicio_sel)]
                    
                    # Filtrado por Usuario
                    if usuario_sel_tab2:
                        df_filtrado_tab2 = df_filtrado_tab2[df_filtrado_tab2["USUARIO_ATENCION"].isin(usuario_sel_tab2)]

                    # --- PROCESAMIENTO AVANZADO (solo si se presiona el botón) ---
                    if procesar_tab2 and not df_filtrado_tab2.empty and fecha_inicio_tab2 <= fecha_fin_tab2:
                        st.divider()
                        st.subheader("📈 Análisis de Promedios por Hora y Día (Llamados)")
                        
                        # Mostrar configuración seleccionada
                        st.info(f"""
                        **Configuración de análisis:**
                        - **Rango:** {fecha_inicio_tab2} a {fecha_fin_tab2}
                        - **Día analizado:** {dia_seleccionado_tab2}
                        - **Servicios:** {', '.join(servicio_sel) if servicio_sel else 'Todos'}
                        - **Usuarios:** {', '.join(usuario_sel_tab2) if usuario_sel_tab2 else 'Todos'}
                        """)
                        
                        # Preparar datos para el procesamiento
                        df_proceso_tab2 = df_filtrado_tab2.copy()
                        
                        # Extraer información de fecha y hora
                        df_proceso_tab2['FECHA'] = df_proceso_tab2['HORA_LLEGADA'].dt.date
                        df_proceso_tab2['HORA'] = df_proceso_tab2['HORA_LLEGADA'].dt.hour
                        df_proceso_tab2['DIA_SEMANA'] = df_proceso_tab2['HORA_LLEGADA'].dt.day_name()
                        df_proceso_tab2['DIA_SEMANA_NUM'] = df_proceso_tab2['HORA_LLEGADA'].dt.dayofweek  # 0=Lunes, 6=Domingo
                        
                        # Filtrar por día de la semana según la selección
                        if dia_seleccionado_tab2 == "Todos los días (L-V)":
                            # Filtrar solo lunes a viernes
                            df_proceso_tab2 = df_proceso_tab2[df_proceso_tab2['DIA_SEMANA_NUM'] < 5]
                            dias_analizados_tab2 = "Lunes a Viernes"
                            dia_label_tab2 = "L-V"
                        else:
                            # Filtrar por día específico
                            df_proceso_tab2 = df_proceso_tab2[df_proceso_tab2['DIA_SEMANA'] == dia_seleccionado_tab2]
                            dias_analizados_tab2 = dia_seleccionado_tab2
                            dia_label_tab2 = dia_seleccionado_tab2[:3]
                        
                        # Verificar si hay datos después del filtro por día
                        if df_proceso_tab2.empty:
                            st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado_tab2}) en el rango filtrado.")
                        else:
                            # Identificar horas con registros
                            horas_con_registros_tab2 = sorted(df_proceso_tab2['HORA'].unique())
                            
                            # Obtener lista de usuarios únicos
                            usuarios_proceso_tab2 = sorted(df_proceso_tab2["USUARIO_ATENCION"].dropna().unique())
                            
                            if not usuarios_proceso_tab2:
                                st.warning("No hay usuarios en los datos filtrados.")
                            else:
                                # Crear estructura para la tabla dinámica
                                tabla_resultados_tab2 = pd.DataFrame(index=usuarios_proceso_tab2, columns=horas_con_registros_tab2)
                                
                                # Calcular promedios para cada usuario y hora
                                for usuario in usuarios_proceso_tab2:
                                    df_usuario = df_proceso_tab2[df_proceso_tab2["USUARIO_ATENCION"] == usuario]
                                    
                                    for hora in horas_con_registros_tab2:
                                        # Filtrar registros para esta hora específica
                                        df_hora = df_usuario[df_usuario['HORA'] == hora]
                                        
                                        if not df_hora.empty:
                                            # Contar registros por fecha única (para calcular promedio por día)
                                            conteo_por_dia = df_hora.groupby('FECHA').size()
                                            
                                            # Calcular promedio de registros por día en esta hora
                                            promedio = conteo_por_dia.mean()
                                            tabla_resultados_tab2.at[usuario, hora] = round(promedio, 2)
                                        else:
                                            tabla_resultados_tab2.at[usuario, hora] = 0.0
                                
                                # Formatear nombres de columnas (horas)
                                horas_formateadas_tab2 = [f"{h}:00" for h in horas_con_registros_tab2]
                                tabla_resultados_tab2.columns = horas_formateadas_tab2
                                
                                # Asegurar que todos los valores sean numéricos
                                tabla_resultados_tab2 = tabla_resultados_tab2.astype(float)
                                
                                # Agregar columna de total por usuario
                                tabla_resultados_tab2['TOTAL'] = tabla_resultados_tab2.sum(axis=1)
                                
                                # Ordenar por total descendente
                                tabla_resultados_tab2 = tabla_resultados_tab2.sort_values('TOTAL', ascending=False)
                                
                                # --- TABLA 1: PROMEDIOS DE LLAMADOS ---
                                st.subheader("📋 Tabla de llamados promedio atendidos por Usuario")
                                st.markdown("*Cantidad de llamados que atienden por hora*")

                                # Mostrar tabla con formato
                                st.dataframe(
                                    tabla_resultados_tab2.style
                                    .background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[:, horas_formateadas_tab2])
                                    .format("{:.2f}")
                                    .set_properties(**{'text-align': 'center'}),
                                    use_container_width=True,
                                    height=min(400, 50 + (len(usuarios_proceso_tab2) * 35))
                                )
                                
                                # --- TABLA 2: TIEMPOS PROMEDIOS DE ATENCIÓN ---
                                st.subheader("⏱️ Tabla de Tiempos Promedios de Atención")
                                st.markdown("*Tiempo promedio (minutos) que tardan en atender un llamado cada hora*")
                                
                                # Crear tabla de tiempos promedios
                                tabla_tiempos_tab2 = pd.DataFrame(index=usuarios_proceso_tab2, columns=horas_formateadas_tab2)
                                
                                # Calcular tiempo promedio = 60 / promedio de registros
                                for usuario in usuarios_proceso_tab2:
                                    for hora_idx, hora_col in enumerate(horas_formateadas_tab2):
                                        promedio_registros = tabla_resultados_tab2.at[usuario, hora_col]
                                        if promedio_registros > 0:
                                            tiempo_promedio = 60 / promedio_registros
                                            tabla_tiempos_tab2.at[usuario, hora_col] = round(tiempo_promedio, 1)
                                        else:
                                            tabla_tiempos_tab2.at[usuario, hora_col] = np.nan
                                
                                # Agregar columna de tiempo promedio total
                                for usuario in usuarios_proceso_tab2:
                                    tiempos_usuario = tabla_tiempos_tab2.loc[usuario, horas_formateadas_tab2].dropna().values
                                    if len(tiempos_usuario) > 0:
                                        tiempo_promedio_total = np.mean(tiempos_usuario)
                                        tabla_tiempos_tab2.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = round(tiempo_promedio_total, 1)
                                    else:
                                        tabla_tiempos_tab2.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = np.nan
                                
                                # Mostrar tabla de tiempos con gradiente invertido
                                st.dataframe(
                                    tabla_tiempos_tab2.style
                                    .background_gradient(cmap='YlOrRd_r', axis=1, subset=pd.IndexSlice[:, horas_formateadas_tab2])
                                    .set_properties(**{'text-align': 'center'})
                                    .format("{:.1f}", na_rep="-")
                                    .format("{:.1f}", subset=['TIEMPO_PROMEDIO_TOTAL']),
                                    use_container_width=True,
                                    height=min(400, 50 + (len(usuarios_proceso_tab2) * 35))
                                )
                                
                                # --- ESTADÍSTICAS RESUMEN CON ESTÁNDARES ---
                                st.subheader("📊 Estadísticas Resumen vs Estándares")
                                
                                # Contar horas con registros
                                horas_con_registros_count_tab2 = len(horas_con_registros_tab2)
                                
                                # Calcular promedios generales
                                promedio_general_tab2 = tabla_resultados_tab2[horas_formateadas_tab2].values.mean()
                                
                                # Calcular tiempo promedio general (excluyendo NaN)
                                tiempos_todos_tab2 = []
                                for usuario in usuarios_proceso_tab2:
                                    for hora_col in horas_formateadas_tab2:
                                        valor = tabla_tiempos_tab2.at[usuario, hora_col]
                                        if not pd.isna(valor):
                                            tiempos_todos_tab2.append(valor)
                                
                                # ESTÁNDARES DEFINIDOS (pueden ser diferentes para llamados)
                                ESTANDAR_LLAMADOS_HORA = 15  # 15 llamados por hora estándar
                                ESTANDAR_TIEMPO_ATENCION = 3  # 3 minutos por atención estándar
                                
                                # Calcular diferencias vs estándar
                                diferencia_registros_tab2 = promedio_general_tab2 - ESTANDAR_LLAMADOS_HORA
                                diferencia_registros_porcentaje_tab2 = (diferencia_registros_tab2 / ESTANDAR_LLAMADOS_HORA) * 100 if ESTANDAR_LLAMADOS_HORA > 0 else 0
                                
                                if tiempos_todos_tab2:
                                    tiempo_promedio_general_tab2 = np.mean(tiempos_todos_tab2)
                                    diferencia_tiempo_tab2 = tiempo_promedio_general_tab2 - ESTANDAR_TIEMPO_ATENCION
                                    diferencia_tiempo_porcentaje_tab2 = (diferencia_tiempo_tab2 / ESTANDAR_TIEMPO_ATENCION) * 100 if ESTANDAR_TIEMPO_ATENCION > 0 else 0
                                else:
                                    tiempo_promedio_general_tab2 = None
                                    diferencia_tiempo_tab2 = None
                                    diferencia_tiempo_porcentaje_tab2 = None
                                
                                # Mostrar métricas con diferencias vs estándar
                                col1_tab2, col2_tab2 = st.columns(2)
                                
                                with col1_tab2:
                                    # Métrica de llamados por hora vs estándar
                                    delta_registros_tab2 = f"{diferencia_registros_tab2:+.2f} vs estándar ({diferencia_registros_porcentaje_tab2:+.1f}%)"
                                    color_delta_registros_tab2 = "inverse" if diferencia_registros_tab2 > 0 else "normal"
                                    
                                    st.metric(
                                        label="📈 Promedio llamados/hora", 
                                        value=f"{promedio_general_tab2:.2f}",
                                        delta=delta_registros_tab2,
                                        delta_color=color_delta_registros_tab2,
                                        help=f"Estándar: {ESTANDAR_LLAMADOS_HORA} llamados/hora"
                                    )
                                    
                                    st.caption(f"**Estándar:** {ESTANDAR_LLAMADOS_HORA} llamados por hora")
                                
                                with col2_tab2:
                                    # Métrica de tiempo de atención vs estándar
                                    if tiempo_promedio_general_tab2 is not None:
                                        delta_tiempo_tab2 = f"{diferencia_tiempo_tab2:+.1f} min vs estándar ({diferencia_tiempo_porcentaje_tab2:+.1f}%)"
                                        color_delta_tiempo_tab2 = "inverse" if diferencia_tiempo_tab2 > 0 else "normal"
                                        
                                        st.metric(
                                            label="⏱️ Tiempo promedio atención", 
                                            value=f"{tiempo_promedio_general_tab2:.1f} min",
                                            delta=delta_tiempo_tab2,
                                            delta_color=color_delta_tiempo_tab2,
                                            help=f"Estándar: {ESTANDAR_TIEMPO_ATENCION} minutos por atención"
                                        )
                                        
                                        st.caption(f"**Estándar:** {ESTANDAR_TIEMPO_ATENCION} minutos por atención")
                                    else:
                                        st.metric(
                                            label="⏱️ Tiempo promedio atención", 
                                            value="-",
                                            help="No hay datos suficientes para calcular el tiempo promedio"
                                        )
                                        st.caption(f"**Estándar:** {ESTANDAR_TIEMPO_ATENCION} minutos por atención")
                                
                                # --- GRÁFICO DE BARRAS: TOP USUARIOS ---
                                st.subheader("📊 Top Usuarios por Actividad Promedio (Llamados)")
                                
                                top_n_tab2 = min(10, len(tabla_resultados_tab2))
                                top_usuarios_tab2 = tabla_resultados_tab2.head(top_n_tab2)
                                
                                # Crear gráfico de barras
                                fig_tab2, ax_tab2 = plt.subplots(figsize=(12, 6))
                                
                                # Preparar datos para el gráfico
                                usuarios_nombres_tab2 = top_usuarios_tab2.index.tolist()
                                promedios_totales_tab2 = top_usuarios_tab2['TOTAL'].values
                                
                                # Crear barras verticales
                                bars_tab2 = ax_tab2.bar(usuarios_nombres_tab2, promedios_totales_tab2, color='lightcoral', alpha=0.8)
                                
                                # Configurar ejes
                                ax_tab2.set_xlabel('Usuario')
                                ax_tab2.set_ylabel('Promedio de Llamados por Día')
                                ax_tab2.set_title(f'Top {top_n_tab2} Usuarios - Promedio Diario de Llamados ({dia_label_tab2})')
                                
                                # Rotar etiquetas del eje X
                                plt.xticks(rotation=45, ha='right')
                                
                                # Añadir valores en las barras
                                for bar in bars_tab2:
                                    height = bar.get_height()
                                    ax_tab2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                               f'{height:.1f}', ha='center', va='bottom', fontsize=9)
                                
                                # Ajustar márgenes
                                plt.tight_layout()
                                
                                # Mostrar el gráfico en Streamlit
                                st.pyplot(fig_tab2)
                                plt.close(fig_tab2)
                                
                                # --- EXPORTAR RESULTADOS ---
                                st.divider()
                                st.subheader("📥 Exportar Resultados")
                                
                                col1_tab2, col2_tab2, col3_tab2 = st.columns(3)
                                
                                with col1_tab2:
                                    # Exportar tabla de promedios a CSV
                                    csv_promedios_tab2 = tabla_resultados_tab2.to_csv().encode('utf-8')
                                    st.download_button(
                                        label="📊 Descargar promedios (CSV)",
                                        data=csv_promedios_tab2,
                                        file_name=f"promedios_llamados_{fecha_inicio_tab2}_{fecha_fin_tab2}_{dia_label_tab2}.csv",
                                        mime="text/csv",
                                        help="Tabla de promedios de llamados por hora",
                                        key="tab2_csv_promedios"
                                    )
                                
                                with col2_tab2:
                                    # Exportar tabla de tiempos a CSV
                                    tabla_tiempos_export_tab2 = tabla_tiempos_tab2.copy()
                                    tabla_tiempos_export_tab2 = tabla_tiempos_export_tab2.fillna("-")
                                    csv_tiempos_tab2 = tabla_tiempos_export_tab2.to_csv().encode('utf-8')
                                    st.download_button(
                                        label="⏱️ Descargar tiempos (CSV)",
                                        data=csv_tiempos_tab2,
                                        file_name=f"tiempos_atencion_{fecha_inicio_tab2}_{fecha_fin_tab2}_{dia_label_tab2}.csv",
                                        mime="text/csv",
                                        help="Tabla de tiempos promedios de atención",
                                        key="tab2_csv_tiempos"
                                    )
                                
                                with col3_tab2:
                                    # Crear archivo Excel con ambas tablas
                                    output_tab2 = BytesIO()
                                    with pd.ExcelWriter(output_tab2, engine='openpyxl') as writer:
                                        tabla_resultados_tab2.to_excel(writer, sheet_name='Promedios_Llamados')
                                        
                                        tabla_tiempos_export_excel_tab2 = tabla_tiempos_tab2.copy()
                                        tabla_tiempos_export_excel_tab2 = tabla_tiempos_export_excel_tab2.fillna("-")
                                        tabla_tiempos_export_excel_tab2.to_excel(writer, sheet_name='Tiempos_Atencion')
                                        
                                        # Agregar hoja con estadísticas
                                        estadisticas_df_tab2 = pd.DataFrame({
                                            'Métrica': [
                                                'Usuarios analizados', 
                                                'Horas con registros', 
                                                'Promedio llamados/hora (Real)',
                                                'Promedio llamados/hora (Estándar)',
                                                'Diferencia llamados/hora',
                                                'Diferencia llamados/hora (%)',
                                                'Tiempo promedio atención (Real)',
                                                'Tiempo promedio atención (Estándar)',
                                                'Diferencia tiempo atención',
                                                'Diferencia tiempo atención (%)',
                                                'Rango de fechas', 
                                                'Día analizado', 
                                                'Servicios analizados',
                                                'Fecha de generación'
                                            ],
                                            'Valor': [
                                                len(usuarios_proceso_tab2), 
                                                horas_con_registros_count_tab2,
                                                f"{promedio_general_tab2:.2f}",
                                                f"{ESTANDAR_LLAMADOS_HORA}",
                                                f"{diferencia_registros_tab2:+.2f}",
                                                f"{diferencia_registros_porcentaje_tab2:+.1f}%",
                                                f"{tiempo_promedio_general_tab2:.1f} min" if tiempo_promedio_general_tab2 else "-",
                                                f"{ESTANDAR_TIEMPO_ATENCION} min",
                                                f"{diferencia_tiempo_tab2:+.1f} min" if diferencia_tiempo_tab2 else "-",
                                                f"{diferencia_tiempo_porcentaje_tab2:+.1f}%" if diferencia_tiempo_porcentaje_tab2 else "-",
                                                f"{fecha_inicio_tab2} a {fecha_fin_tab2}",
                                                dia_seleccionado_tab2, 
                                                ', '.join(servicio_sel) if servicio_sel else 'Todos',
                                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            ]
                                        })
                                        estadisticas_df_tab2.to_excel(writer, sheet_name='Estadísticas', index=False)
                                    
                                    excel_data_tab2 = output_tab2.getvalue()
                                    
                                    st.download_button(
                                        label="📁 Descargar todo (Excel)",
                                        data=excel_data_tab2,
                                        file_name=f"analisis_llamados_completo_{fecha_inicio_tab2}_{fecha_fin_tab2}_{dia_label_tab2}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        help="Archivo Excel con todas las tablas y estadísticas",
                                        key="tab2_excel"
                                    )

        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.info("""
            **Posibles soluciones:**
            1. Verifica que el archivo sea un Excel válido (.xlsx)
            2. Asegúrate de que el archivo no esté protegido con contraseña
            3. Revisa que tenga datos en las hojas correctas
            4. Comprueba que los nombres de las columnas no tengan caracteres especiales
            """)
    else:
        st.info("👆 Usa la barra lateral para subir un archivo Excel y activar los filtros.")
        st.caption("El archivo debe contener columnas relacionadas con llamados: Hora de Llegada, Servicio, Usuario que Atiende")
