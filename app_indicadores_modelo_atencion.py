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
            nombres_tipo = ['Tipo', 'TIPO', 'tipo']  # Para identificar llamados manuales/auto
            
            # Encontrar las columnas reales
            col_hora_llegada = encontrar_columna(df_tab2, nombres_hora_llegada)
            col_servicio = encontrar_columna(df_tab2, nombres_servicio)
            col_usuario_atencion = encontrar_columna(df_tab2, nombres_usuario_atencion)
            col_tipo = encontrar_columna(df_tab2, nombres_tipo)  # Columna para tipo de llamado
            
            # Verificar columnas necesarias
            if not all([col_hora_llegada, col_servicio, col_usuario_atencion]):
                st.error("No se encontraron las columnas necesarias. Verifica que el archivo tenga: Hora Llegada, Servicio, Usuario Atención")
                st.stop()
            
            # Renombrar columnas para uso interno
            df_tab2 = df_tab2.rename(columns={
                col_hora_llegada: 'HORA_LLEGADA',
                col_servicio: 'SERVICIO',
                col_usuario_atencion: 'USUARIO_ATENCION'
            })
            
            # Renombrar columna Tipo si existe
            if col_tipo:
                df_tab2 = df_tab2.rename(columns={col_tipo: 'TIPO_LLAMADO'})
            
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

                # LISTA DESPLEGABLE DE SERVICIOS (como solicitaste)
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
                    index=7,
                    help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes",
                    key="tab2_dia"
                )

                # Botón para procesar
                procesar_tab2 = st.button("🚀 Procesar", type="primary", use_container_width=True, key="tab2_procesar")

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

            # --- PROCESAMIENTO AVANZADO ---
            if procesar_tab2 and not df_filtrado_tab2.empty and fecha_inicio_tab2 <= fecha_fin_tab2:
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
                df_proceso_tab2['DIA_SEMANA'] = df_proceso_tab2['HORA_LLEGADA'].dt.day_name()
                df_proceso_tab2['DIA_SEMANA_NUM'] = df_proceso_tab2['HORA_LLEGADA'].dt.dayofweek
                
                # Filtrar por día de la semana según la selección
                if dia_seleccionado_tab2 == "Todos los días (L-V)":
                    df_proceso_tab2 = df_proceso_tab2[df_proceso_tab2['DIA_SEMANA_NUM'] < 5]
                    dias_analizados_tab2 = "Lunes a Viernes"
                    dia_label_tab2 = "L-V"
                else:
                    df_proceso_tab2 = df_proceso_tab2[df_proceso_tab2['DIA_SEMANA'] == dia_seleccionado_tab2]
                    dias_analizados_tab2 = dia_seleccionado_tab2
                    dia_label_tab2 = dia_seleccionado_tab2[:3]
                
                if df_proceso_tab2.empty:
                    st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado_tab2}) en el rango filtrado.")
                else:
                    # ============================================================
                    # 1. TABLA DE PROMEDIO DE LLAMADOS POR AGENTE POR HORA Y DÍA
                    # ============================================================
                    st.subheader("📊 Tabla 1: Promedio de Llamados por Agente, Hora y Día")
                    
                    # Obtener usuarios únicos
                    usuarios_proceso_tab2 = sorted(df_proceso_tab2["USUARIO_ATENCION"].dropna().unique())
                    horas_con_registros_tab2 = sorted(df_proceso_tab2['HORA'].unique())
                    
                    if not usuarios_proceso_tab2:
                        st.warning("No hay usuarios en los datos filtrados.")
                    else:
                        # Crear tabla de promedios
                        tabla_promedios = pd.DataFrame(index=usuarios_proceso_tab2, columns=horas_con_registros_tab2)
                        
                        for usuario in usuarios_proceso_tab2:
                            df_usuario = df_proceso_tab2[df_proceso_tab2["USUARIO_ATENCION"] == usuario]
                            
                            for hora in horas_con_registros_tab2:
                                df_hora = df_usuario[df_usuario['HORA'] == hora]
                                
                                if not df_hora.empty:
                                    conteo_por_dia = df_hora.groupby('FECHA').size()
                                    promedio = conteo_por_dia.mean()
                                    tabla_promedios.at[usuario, hora] = round(promedio, 2)
                                else:
                                    tabla_promedios.at[usuario, hora] = 0.0
                        
                        # Formatear horas
                        horas_formateadas_tab2 = [f"{h}:00" for h in horas_con_registros_tab2]
                        tabla_promedios.columns = horas_formateadas_tab2
                        tabla_promedios = tabla_promedios.astype(float)
                        
                        # Agregar totales
                        tabla_promedios['TOTAL_PROMEDIO'] = tabla_promedios.sum(axis=1)
                        tabla_promedios['TOTAL_DIAS'] = df_proceso_tab2.groupby('USUARIO_ATENCION')['FECHA'].nunique()
                        tabla_promedios['PROMEDIO_DIARIO'] = tabla_promedios['TOTAL_PROMEDIO'] / tabla_promedios['TOTAL_DIAS']
                        
                        # Ordenar
                        tabla_promedios = tabla_promedios.sort_values('TOTAL_PROMEDIO', ascending=False)
                        
                        # Mostrar tabla
                        st.dataframe(
                            tabla_promedios.style
                            .background_gradient(cmap='YlOrRd', axis=1, subset=pd.IndexSlice[:, horas_formateadas_tab2])
                            .format("{:.2f}")
                            .set_properties(**{'text-align': 'center'}),
                            use_container_width=True,
                            height=min(400, 50 + (len(usuarios_proceso_tab2) * 35))
                        )
                        
                        # ============================================================
                        # 2. TABLA DE LLAMADOS MANUALES VS AUTO
                        # ============================================================
                        st.subheader("📊 Tabla 2: Llamados Manuales vs Automáticos por Usuario")
                        
                        # Verificar si existe columna de tipo
                        if 'TIPO_LLAMADO' in df_proceso_tab2.columns:
                            # Normalizar valores de tipo
                            df_proceso_tab2['TIPO_NORMALIZADO'] = df_proceso_tab2['TIPO_LLAMADO'].astype(str).str.lower().str.strip()
                            
                            # Identificar manuales y auto
                            manual_keywords = ['manual', 'm', 'man', 'manuales']
                            auto_keywords = ['auto', 'a', 'aut', 'automático', 'automatico', 'automáticos']
                            
                            df_proceso_tab2['ES_MANUAL'] = df_proceso_tab2['TIPO_NORMALIZADO'].apply(
                                lambda x: any(kw in x for kw in manual_keywords) if pd.notna(x) else False
                            )
                            df_proceso_tab2['ES_AUTO'] = df_proceso_tab2['TIPO_NORMALIZADO'].apply(
                                lambda x: any(kw in x for kw in auto_keywords) if pd.notna(x) else False
                            )
                            
                            # Crear tabla de conteo
                            tabla_tipos = pd.DataFrame(index=usuarios_proceso_tab2)
                            
                            for usuario in usuarios_proceso_tab2:
                                df_usuario = df_proceso_tab2[df_proceso_tab2["USUARIO_ATENCION"] == usuario]
                                tabla_tipos.at[usuario, 'TOTAL_LLAMADOS'] = len(df_usuario)
                                tabla_tipos.at[usuario, 'MANUALES'] = df_usuario['ES_MANUAL'].sum()
                                tabla_tipos.at[usuario, 'AUTOMATICOS'] = df_usuario['ES_AUTO'].sum()
                                tabla_tipos.at[usuario, 'NO_CLASIFICADO'] = len(df_usuario) - (df_usuario['ES_MANUAL'].sum() + df_usuario['ES_AUTO'].sum())
                            
                            # Calcular porcentajes
                            tabla_tipos['% MANUAL'] = (tabla_tipos['MANUALES'] / tabla_tipos['TOTAL_LLAMADOS'] * 100).round(1)
                            tabla_tipos['% AUTO'] = (tabla_tipos['AUTOMATICOS'] / tabla_tipos['TOTAL_LLAMADOS'] * 100).round(1)
                            tabla_tipos['% NO CLASIF'] = (tabla_tipos['NO_CLASIFICADO'] / tabla_tipos['TOTAL_LLAMADOS'] * 100).round(1)
                            
                            # Ordenar por total
                            tabla_tipos = tabla_tipos.sort_values('TOTAL_LLAMADOS', ascending=False)
                            
                            # Mostrar tabla
                            st.dataframe(
                                tabla_tipos.style
                                .background_gradient(cmap='Blues', subset=['TOTAL_LLAMADOS', 'MANUALES', 'AUTOMATICOS'])
                                .format("{:.0f}", subset=['TOTAL_LLAMADOS', 'MANUALES', 'AUTOMATICOS', 'NO_CLASIFICADO'])
                                .format("{:.1f}%", subset=['% MANUAL', '% AUTO', '% NO CLASIF'])
                                .set_properties(**{'text-align': 'center'}),
                                use_container_width=True
                            )
                            
                            # ============================================================
                            # 3. GRÁFICA DE LÍNEA DE TIEMPO - LLAMADOS MANUALES VS AUTO
                            # ============================================================
                            st.subheader("📈 Gráfica 3: Evolución Temporal de Llamados Manuales vs Automáticos")
                            
                            # Preparar datos para la gráfica
                            df_temporal = df_proceso_tab2.copy()
                            df_temporal['FECHA_DT'] = pd.to_datetime(df_temporal['FECHA'])
                            
                            # Agrupar por fecha
                            df_agrupado = df_temporal.groupby('FECHA_DT').agg({
                                'ES_MANUAL': 'sum',
                                'ES_AUTO': 'sum'
                            }).reset_index()
                            
                            df_agrupado['TOTAL'] = df_agrupado['ES_MANUAL'] + df_agrupado['ES_AUTO']
                            
                            # Crear gráfico
                            fig_temporal, ax_temporal = plt.subplots(figsize=(14, 6))
                            
                            # Líneas
                            ax_temporal.plot(df_agrupado['FECHA_DT'], df_agrupado['ES_MANUAL'], 
                                           label='Llamados Manuales', color='red', linewidth=2, marker='o')
                            ax_temporal.plot(df_agrupado['FECHA_DT'], df_agrupado['ES_AUTO'], 
                                           label='Llamados Automáticos', color='green', linewidth=2, marker='s')
                            ax_temporal.plot(df_agrupado['FECHA_DT'], df_agrupado['TOTAL'], 
                                           label='Total Llamados', color='blue', linewidth=2, linestyle='--', alpha=0.5)
                            
                            # Configurar gráfico
                            ax_temporal.set_xlabel('Fecha', fontsize=12)
                            ax_temporal.set_ylabel('Cantidad de Llamados', fontsize=12)
                            ax_temporal.set_title(f'Evolución de Llamados por Tipo ({fecha_inicio_tab2} a {fecha_fin_tab2})', fontsize=14, fontweight='bold')
                            ax_temporal.legend()
                            ax_temporal.grid(True, alpha=0.3)
                            
                            # Rotar etiquetas de fecha
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            
                            # Mostrar gráfico
                            st.pyplot(fig_temporal)
                            plt.close(fig_temporal)
                            
                            # Resumen estadístico
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Manuales", f"{int(df_agrupado['ES_MANUAL'].sum()):,}")
                            with col2:
                                st.metric("Total Automáticos", f"{int(df_agrupado['ES_AUTO'].sum()):,}")
                            with col3:
                                st.metric("Total General", f"{int(df_agrupado['TOTAL'].sum()):,}")
                            
                        else:
                            st.warning("⚠️ No se encontró la columna 'Tipo' para clasificar llamados manuales/automáticos")
                            st.info("""
                            **Para activar esta funcionalidad, asegúrate de que tu archivo tenga una columna llamada 'Tipo' 
                            que indique si el llamado fue manual o automático.**
                            
                            Ejemplos de valores:
                            - Manual, M, Manuales
                            - Auto, A, Automático, Automáticos
                            """)
                        
                        # ============================================================
                        # TABLAS ORIGINALES (MANTENIDAS)
                        # ============================================================
                        st.divider()
                        st.subheader("📋 Tabla Original: Promedios por Hora")
                        
                        # Mostrar tabla original de promedios por hora
                        st.dataframe(
                            tabla_promedios[horas_formateadas_tab2 + ['TOTAL_PROMEDIO']]
                            .style
                            .background_gradient(cmap='YlOrRd', axis=1)
                            .format("{:.2f}")
                            .set_properties(**{'text-align': 'center'}),
                            use_container_width=True
                        )
                        
                        # Tabla de tiempos
                        st.subheader("⏱️ Tabla Original: Tiempos Promedios de Atención")
                        
                        tabla_tiempos_tab2 = pd.DataFrame(index=usuarios_proceso_tab2, columns=horas_formateadas_tab2)
                        
                        for usuario in usuarios_proceso_tab2:
                            for hora_idx, hora_col in enumerate(horas_formateadas_tab2):
                                promedio_registros = tabla_promedios.at[usuario, hora_col]
                                if promedio_registros > 0:
                                    tiempo_promedio = 60 / promedio_registros
                                    tabla_tiempos_tab2.at[usuario, hora_col] = round(tiempo_promedio, 1)
                                else:
                                    tabla_tiempos_tab2.at[usuario, hora_col] = np.nan
                        
                        # Calcular tiempo promedio total
                        for usuario in usuarios_proceso_tab2:
                            tiempos_usuario = tabla_tiempos_tab2.loc[usuario, horas_formateadas_tab2].dropna().values
                            if len(tiempos_usuario) > 0:
                                tiempo_promedio_total = np.mean(tiempos_usuario)
                                tabla_tiempos_tab2.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = round(tiempo_promedio_total, 1)
                            else:
                                tabla_tiempos_tab2.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = np.nan
                        
                        st.dataframe(
                            tabla_tiempos_tab2.style
                            .background_gradient(cmap='YlOrRd_r', axis=1, subset=pd.IndexSlice[:, horas_formateadas_tab2])
                            .format("{:.1f}", na_rep="-")
                            .set_properties(**{'text-align': 'center'}),
                            use_container_width=True
                        )
                        
                        # ============================================================
                        # ESTADÍSTICAS RESUMEN
                        # ============================================================
                        st.divider()
                        st.subheader("📊 Estadísticas Resumen")
                        
                        # Calcular estadísticas
                        promedio_general_tab2 = tabla_promedios[horas_formateadas_tab2].values.mean()
                        tiempos_todos_tab2 = tabla_tiempos_tab2[horas_formateadas_tab2].values.flatten()
                        tiempos_todos_tab2 = tiempos_todos_tab2[~np.isnan(tiempos_todos_tab2)]
                        
                        if len(tiempos_todos_tab2) > 0:
                            tiempo_promedio_general_tab2 = np.mean(tiempos_todos_tab2)
                        else:
                            tiempo_promedio_general_tab2 = None
                        
                        # Mostrar métricas
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Usuarios Analizados", len(usuarios_proceso_tab2))
                        with col2:
                            st.metric("Horas con Registros", len(horas_con_registros_tab2))
                        with col3:
                            st.metric("Promedio Llamados/Hora", f"{promedio_general_tab2:.2f}")
                        with col4:
                            if tiempo_promedio_general_tab2:
                                st.metric("Tiempo Promedio Atención", f"{tiempo_promedio_general_tab2:.1f} min")
                            else:
                                st.metric("Tiempo Promedio Atención", "-")
                        
                        # ============================================================
                        # GRÁFICO DE BARRAS TOP USUARIOS
                        # ============================================================
                        st.subheader("🏆 Top 10 Usuarios por Actividad")
                        
                        top_n_tab2 = min(10, len(tabla_promedios))
                        top_usuarios_tab2 = tabla_promedios.head(top_n_tab2)
                        
                        fig_top, ax_top = plt.subplots(figsize=(12, 6))
                        usuarios_nombres_tab2 = top_usuarios_tab2.index.tolist()
                        promedios_totales_tab2 = top_usuarios_tab2['TOTAL_PROMEDIO'].values
                        
                        bars_top = ax_top.bar(usuarios_nombres_tab2, promedios_totales_tab2, color='lightcoral', alpha=0.8)
                        ax_top.set_xlabel('Usuario')
                        ax_top.set_ylabel('Promedio de Llamados por Día')
                        ax_top.set_title(f'Top {top_n_tab2} Usuarios - Promedio Diario ({dia_label_tab2})')
                        plt.xticks(rotation=45, ha='right')
                        
                        for bar in bars_top:
                            height = bar.get_height()
                            ax_top.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                       f'{height:.1f}', ha='center', va='bottom', fontsize=9)
                        
                        plt.tight_layout()
                        st.pyplot(fig_top)
                        plt.close(fig_top)
                        
                        # ============================================================
                        # EXPORTAR RESULTADOS
                        # ============================================================
                        st.divider()
                        st.subheader("📥 Exportar Resultados")
                        
                        col_exp1, col_exp2, col_exp3 = st.columns(3)
                        
                        with col_exp1:
                            csv_promedios = tabla_promedios.to_csv().encode('utf-8')
                            st.download_button(
                                label="📊 Descargar promedios (CSV)",
                                data=csv_promedios,
                                file_name=f"promedios_llamados_{fecha_inicio_tab2}_{fecha_fin_tab2}.csv",
                                mime="text/csv",
                                key="tab2_csv_promedios"
                            )
                        
                        with col_exp2:
                            if 'TIPO_LLAMADO' in df_proceso_tab2.columns:
                                csv_tipos = tabla_tipos.to_csv().encode('utf-8')
                                st.download_button(
                                    label="📋 Descargar tipos (CSV)",
                                    data=csv_tipos,
                                    file_name=f"tipos_llamados_{fecha_inicio_tab2}_{fecha_fin_tab2}.csv",
                                    mime="text/csv",
                                    key="tab2_csv_tipos"
                                )
                        
                        with col_exp3:
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                tabla_promedios.to_excel(writer, sheet_name='Promedios_Hora')
                                tabla_tiempos_tab2.to_excel(writer, sheet_name='Tiempos_Atencion')
                                
                                if 'TIPO_LLAMADO' in df_proceso_tab2.columns:
                                    tabla_tipos.to_excel(writer, sheet_name='Tipos_Llamados')
                                
                                # Hoja de resumen
                                resumen_df = pd.DataFrame({
                                    'Métrica': [
                                        'Fecha Inicio', 'Fecha Fin', 'Día Analizado',
                                        'Servicios', 'Usuarios', 'Registros Totales',
                                        'Promedio Llamados/Hora', 'Tiempo Promedio Atención',
                                        'Fecha Generación'
                                    ],
                                    'Valor': [
                                        str(fecha_inicio_tab2), str(fecha_fin_tab2), dia_seleccionado_tab2,
                                        ', '.join(servicio_sel) if servicio_sel else 'Todos',
                                        ', '.join(usuario_sel_tab2[:5]) + ('...' if len(usuario_sel_tab2) > 5 else '') if usuario_sel_tab2 else 'Todos',
                                        len(df_filtrado_tab2),
                                        f"{promedio_general_tab2:.2f}",
                                        f"{tiempo_promedio_general_tab2:.1f} min" if tiempo_promedio_general_tab2 else "-",
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    ]
                                })
                                resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
                            
                            excel_data = output.getvalue()
                            st.download_button(
                                label="📁 Descargar todo (Excel)",
                                data=excel_data,
                                file_name=f"analisis_completo_{fecha_inicio_tab2}_{fecha_fin_tab2}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="tab2_excel"
                            )

        except Exception as e:
            st.error(f"Error técnico: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("👆 Usa la barra lateral para subir un archivo Excel y activar los filtros.")
        st.caption("El archivo debe contener columnas relacionadas con llamados: Hora de Llegada, Servicio, Usuario que Atiende")
