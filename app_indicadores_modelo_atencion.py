import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Gestión de Ingresos", layout="wide")

st.title("📊 Visualizador de Registros con Filtros Dinámicos")

# 1. Carga de archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

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

        # --- SECCIÓN DE FILTROS EN SIDEBAR ---
        st.sidebar.header("⚙️ Filtros de Búsqueda")

        # 1. Filtro de Fechas (Rango basado en el archivo)
        st.sidebar.subheader("Rango de Evaluación")
        
        # Crear dos selectores separados para fecha inicial y final
        col1, col2 = st.sidebar.columns(2)
        
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
            st.sidebar.error("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin")
            st.sidebar.info(f"Selecciona fechas entre: **{fecha_minima_archivo}** y **{fecha_maxima_archivo}**")
        else:
            st.sidebar.success(f"✅ Rango válido: {fecha_inicio} a {fecha_fin}")

        # 2. Filtro de Centro de Atención
        centros = sorted(df["CENTRO ATENCION"].dropna().unique())
        centro_sel = st.sidebar.multiselect(
            "Centro de Atención:", 
            options=centros,
            help="Selecciona uno o más centros de atención"
        )

        # 3. Filtro de Usuario Crea Ingreso
        usuarios = sorted(df["USUARIO CREA INGRESO"].dropna().unique())
        usuario_sel = st.sidebar.multiselect(
            "Usuario que Creó Ingreso:", 
            options=usuarios,
            help="Selecciona uno o más usuarios"
        )

        # 4. Selector de día de la semana para el procesamiento
        st.sidebar.subheader("Configuración de Procesamiento")
        dia_semana_opciones = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Todos los días (L-V)"]
        dia_seleccionado = st.sidebar.selectbox(
            "Día de la semana a analizar:",
            options=dia_semana_opciones,
            index=7,  # Por defecto selecciona "Todos los días (L-V)"
            help="Selecciona un día específico o 'Todos los días' para promediar de lunes a viernes"
        )

        # Botón para procesar
        procesar = st.sidebar.button("🚀 Procesar", type="primary", use_container_width=True)

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
            st.subheader("📈 Tabla Dinámica de Promedios por Hora y Día")
            
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
            else:
                # Filtrar por día específico
                df_proceso = df_proceso[df_proceso['DIA_SEMANA'] == dia_seleccionado]
                dias_analizados = dia_seleccionado
            
            # Verificar si hay datos después del filtro por día
            if df_proceso.empty:
                st.warning(f"No hay registros para el día seleccionado ({dia_seleccionado}) en el rango filtrado.")
            else:
                # Definir rango de horas (6 AM a 8 PM)
                horas = list(range(6, 21))  # 6, 7, 8, ..., 20 (8 PM)
                
                # Obtener lista de usuarios únicos
                usuarios_proceso = sorted(df_proceso["USUARIO CREA INGRESO"].dropna().unique())
                
                if not usuarios_proceso:
                    st.warning("No hay usuarios en los datos filtrados.")
                else:
                    # Crear estructura para la tabla dinámica
                    tabla_resultados = pd.DataFrame(index=usuarios_proceso, columns=horas)
                    
                    # Calcular promedios para cada usuario y hora
                    for usuario in usuarios_proceso:
                        df_usuario = df_proceso[df_proceso["USUARIO CREA INGRESO"] == usuario]
                        
                        for hora in horas:
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
                    horas_formateadas = [f"{h}:00" for h in horas]
                    tabla_resultados.columns = horas_formateadas
                    
                    # Agregar columna de total por usuario
                    tabla_resultados['TOTAL'] = tabla_resultados.sum(axis=1)
                    
                    # Mostrar tabla de resultados
                    st.success(f"✅ Tabla de promedios generada ({dias_analizados})")
                    
                    # Mostrar tabla con formato
                    st.dataframe(
                        tabla_resultados.style
                        .background_gradient(cmap='YlOrRd', axis=1)
                        .format("{:.2f}"),
                        use_container_width=True
                    )
                    
                    # Estadísticas resumen
                    st.subheader("📊 Estadísticas Resumen")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Usuarios analizados", len(usuarios_proceso))
                    with col2:
                        st.metric("Horas analizadas", len(horas))
                    with col3:
                        st.metric("Promedio general por hora", 
                                 round(tabla_resultados.iloc[:, :-1].values.mean(), 2))
                    with col4:
                        st.metric("Total promedio por usuario", 
                                 round(tabla_resultados['TOTAL'].mean(), 2))
                    
                    # Gráfico de calor interactivo
                    st.subheader("🔥 Mapa de Calor de Promedios")
                    
                    # Preparar datos para el heatmap
                    datos_heatmap = tabla_resultados.iloc[:, :-1].values  # Excluir columna TOTAL
                    
                    fig = go.Figure(data=go.Heatmap(
                        z=datos_heatmap,
                        x=horas_formateadas,
                        y=usuarios_proceso,
                        colorscale='YlOrRd',
                        text=np.round(datos_heatmap, 2),
                        texttemplate='%{text}',
                        textfont={"size": 10},
                        hoverinfo='x+y+z',
                        showscale=True
                    ))
                    
                    fig.update_layout(
                        title=f'Promedio de Registros por Hora ({dias_analizados})',
                        xaxis_title='Hora del día',
                        yaxis_title='Usuario',
                        height=400 + (len(usuarios_proceso) * 20)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Botón para descargar los resultados
                    st.divider()
                    st.subheader("📥 Exportar Resultados")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Exportar a CSV
                        csv_procesado = tabla_resultados.to_csv().encode('utf-8')
                        st.download_button(
                            label="💾 Descargar tabla de promedios (CSV)",
                            data=csv_procesado,
                            file_name=f"promedios_{fecha_inicio}_{fecha_fin}_{dia_seleccionado.replace(' ', '_')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        # Exportar a Excel
                        excel_buffer = pd.ExcelWriter('resultados_promedios.xlsx', engine='openpyxl')
                        tabla_resultados.to_excel(excel_buffer, sheet_name='Promedios')
                        excel_buffer.close()
                        
                        with open('resultados_promedios.xlsx', 'rb') as f:
                            excel_data = f.read()
                        
                        st.download_button(
                            label="📊 Descargar tabla de promedios (Excel)",
                            data=excel_data,
                            file_name=f"promedios_{fecha_inicio}_{fecha_fin}_{dia_seleccionado.replace(' ', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # Información adicional
                    with st.expander("📖 Información sobre el cálculo"):
                        st.markdown("""
                        **Cómo se calculan los promedios:**
                        1. Para cada usuario y cada hora (6:00 AM a 8:00 PM)
                        2. Se cuentan los registros por fecha única
                        3. Se promedia esa cantidad a lo largo de todos los días del mismo tipo en el rango seleccionado
                        4. Ejemplo: Si un usuario tuvo 2 registros a las 9:00 AM el lunes 1, 3 registros el lunes 8, y 1 registro el lunes 15,
                           el promedio sería (2+3+1)/3 = 2.0 registros por lunes a las 9:00 AM
                        
                        **Notas importantes:**
                        - Los sábados y domingos se excluyen cuando se selecciona "Todos los días (L-V)"
                        - Los valores cero indican que no hubo registros en esa hora para el usuario
                        - Los promedios se redondean a 2 decimales
                        """)

    except Exception as e:
        st.error(f"Error técnico: {e}")
        st.info("Verifica que el archivo tenga las columnas necesarias: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
else:
    st.info("👆 Sube un archivo Excel para activar los filtros.")
    st.caption("El archivo debe contener al menos las columnas: 'FECHA CREACION', 'CENTRO ATENCION', 'USUARIO CREA INGRESO'")
