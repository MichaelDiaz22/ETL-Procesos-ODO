import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
import matplotlib.pyplot as plt
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos", layout="wide")

st.title("📊 Visualizador de Registros con Filtros Dinámicos")

# --- SECCIÓN DE FILTROS EN SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # 1. Carga de archivo en la sidebar
    uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"], help="Archivo debe contener columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")

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
                    max_value=fecha_maxima_archivo
                )
            
            with col2:
                fecha_fin = st.date_input(
                    "Fecha de fin:",
                    value=fecha_maxima_archivo,
                    min_value=fecha_minima_archivo,
                    max_value=fecha_maxima_archivo
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
                help="Selecciona uno o más centros de atención"
            )

            # 4. Filtro de Usuario Crea Ingreso
            usuarios = sorted(df["USUARIO CREA INGRESO"].dropna().unique())
            usuario_sel = st.multiselect(
                "Usuario que Creó Ingreso:", 
                options=usuarios,
                help="Selecciona uno o más usuarios"
            )

            # 5. Selector de día de la semana para el procesamiento
            st.subheader("Configuración de Procesamiento")
            dia_semana_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
            dia_seleccionado = st.selectbox(
                "Día de la semana a analizar:",
                options=dia_semana_opciones,
                index=7,  # Por defecto selecciona "Todos los días (L-V)"
                help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes"
            )

            # Botón para procesar
            procesar = st.button("🚀 Procesar", type="primary", use_container_width=True)

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

        # --- VISUALIZACIÓN PRINCIPAL ---
        st.info(f"📅 Rango disponible en archivo: de **{fecha_minima_archivo}** hasta **{fecha_maxima_archivo}**")
        
        if fecha_inicio <= fecha_fin:
            st.success(f"🗓️ Rango seleccionado: **{fecha_inicio}** a **{fecha_fin}**")
        else:
            st.warning("⚠️ Ajusta las fechas para ver los registros filtrados")

        # Métricas de control
        col1, col2, col3 = st.columns(3)
        col1.metric("Total en Archivo", len(df))
        col2.metric("Registros Filtrados", len(df_filtrado))
        col3.metric("Columnas", len(df.columns))

        st.divider()

        # Mostrar los primeros 10 registros de la tabla filtrada
        st.subheader("🔍 Vista Previa (Primeros 10 registros filtrados)")
        if not df_filtrado.empty and fecha_inicio <= fecha_fin:
            st.dataframe(df_filtrado.head(10), use_container_width=True)
            
            # Mostrar estadísticas
            st.caption(f"Mostrando {min(10, len(df_filtrado))} de {len(df_filtrado)} registros")
            
            # Botón para descargar el resultado actual
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar estos resultados",
                data=csv,
                file_name="registros_filtrados.csv",
                mime="text/csv",
                help="Descarga todos los registros filtrados en formato CSV"
            )
        elif fecha_inicio > fecha_fin:
            st.warning("Por favor, ajusta las fechas: la fecha de inicio debe ser menor o igual a la fecha de fin.")
        else:
            st.warning("No hay registros que coincidan con los filtros seleccionados.")

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
                    st.success(f"✅ Tabla de promedios generada ({dias_analizados})")
                    
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
                    st.markdown("*Tiempo promedio (minutos) entre admisiones por hora: 60 / promedio de registros*")
                    
                    # Crear tabla de tiempos promedios
                    tabla_tiempos = pd.DataFrame(index=usuarios_proceso, columns=horas_formateadas)
                    
                    # Calcular tiempo promedio = 60 / promedio de registros
                    for usuario in usuarios_proceso:
                        for hora_idx, hora_col in enumerate(horas_formateadas):
                            promedio_registros = tabla_resultados.at[usuario, hora_col]
                            if promedio_registros > 0:
                                tiempo_promedio = 60 / promedio_registros
                                tabla_tiempos.at[usuario, hora_col] = round(tiempo_promedio, 1)
                            else:
                                tabla_tiempos.at[usuario, hora_col] = "N/A"
                    
                    # Agregar columna de tiempo promedio total
                    tiempos_validos = []
                    for usuario in usuarios_proceso:
                        tiempos_usuario = []
                        for hora_col in horas_formateadas:
                            valor = tabla_tiempos.at[usuario, hora_col]
                            if valor != "N/A":
                                tiempos_usuario.append(valor)
                        
                        if tiempos_usuario:
                            tiempo_promedio_total = np.mean(tiempos_usuario)
                            tabla_tiempos.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = round(tiempo_promedio_total, 1)
                        else:
                            tabla_tiempos.at[usuario, 'TIEMPO_PROMEDIO_TOTAL'] = "N/A"
                    
                    # Mostrar tabla de tiempos
                    st.dataframe(
                        tabla_tiempos.style
                        .background_gradient(cmap='YlGn', axis=1, subset=pd.IndexSlice[:, horas_formateadas])
                        .set_properties(**{'text-align': 'center'})
                        .format("{:.1f}"),
                        use_container_width=True,
                        height=min(400, 50 + (len(usuarios_proceso) * 35))
                    )
                    
                    # --- ESTADÍSTICAS RESUMEN ---
                    st.subheader("📊 Estadísticas Resumen")
                    
                    # Contar horas con registros
                    horas_con_registros_count = len(horas_con_registros)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Usuarios analizados", len(usuarios_proceso))
                    with col2:
                        st.metric("Horas con registros", horas_con_registros_count)
                    with col3:
                        promedio_general = tabla_resultados[horas_formateadas].values.mean()
                        st.metric("Promedio registros/hora", f"{promedio_general:.2f}")
                    with col4:
                        # Calcular tiempo promedio general (excluyendo N/A)
                        tiempos_todos = []
                        for usuario in usuarios_proceso:
                            for hora_col in horas_formateadas:
                                valor = tabla_tiempos.at[usuario, hora_col]
                                if valor != "N/A":
                                    tiempos_todos.append(valor)
                        
                        if tiempos_todos:
                            tiempo_promedio_general = np.mean(tiempos_todos)
                            st.metric("Tiempo promedio admisión", f"{tiempo_promedio_general:.1f} min")
                        else:
                            st.metric("Tiempo promedio admisión", "N/A")
                    
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
                            help="Tabla de promedios de registros por hora"
                        )
                    
                    with col2:
                        # Exportar tabla de tiempos a CSV
                        csv_tiempos = tabla_tiempos.to_csv().encode('utf-8')
                        st.download_button(
                            label="⏱️ Descargar tiempos (CSV)",
                            data=csv_tiempos,
                            file_name=f"tiempos_admision_{fecha_inicio}_{fecha_fin}_{dia_label}.csv",
                            mime="text/csv",
                            help="Tabla de tiempos promedios de admisión"
                        )
                    
                    with col3:
                        # Crear archivo Excel con ambas tablas
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            tabla_resultados.to_excel(writer, sheet_name='Promedios_Registros')
                            tabla_tiempos.to_excel(writer, sheet_name='Tiempos_Admision')
                            
                            # Agregar hoja con estadísticas
                            estadisticas_df = pd.DataFrame({
                                'Métrica': ['Usuarios analizados', 'Horas con registros', 
                                          'Promedio registros/hora', 'Rango de fechas', 
                                          'Día analizado', 'Fecha de generación'],
                                'Valor': [len(usuarios_proceso), horas_con_registros_count,
                                         f"{promedio_general:.2f}", f"{fecha_inicio} a {fecha_fin}",
                                         dia_seleccionado, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                            })
                            estadisticas_df.to_excel(writer, sheet_name='Estadísticas', index=False)
                        
                        excel_data = output.getvalue()
                        
                        st.download_button(
                            label="📁 Descargar todo (Excel)",
                            data=excel_data,
                            file_name=f"analisis_completo_{fecha_inicio}_{fecha_fin}_{dia_label}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Archivo Excel con todas las tablas y estadísticas"
                        )

    except Exception as e:
        st.error(f"Error técnico: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.info("Verifica que el archivo tenga las columnas necesarias: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
else:
    st.info("👆 Usa la barra lateral para subir un archivo Excel y activar los filtros.")
    st.caption("El archivo debe contener al menos las columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
