import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Tabla Resumen por Ciudad",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Tabla Resumen por Ciudad")
st.markdown("---")

# El resto del código hasta la función graficar_novedades_temporales se mantiene igual
# ... (todo el código anterior hasta antes de las funciones de gráficas)

def graficar_novedades_temporales(df_novedades_sede, periodo):
    """Gráfica de novedades generadas por período usando matplotlib"""
    if df_novedades_sede.empty:
        return None
    
    df_novedades_sede['Fecha'] = pd.to_datetime(df_novedades_sede['_fecha'])
    
    if periodo == 'Mensual':
        df_agrupado = df_novedades_sede.groupby(df_novedades_sede['Fecha'].dt.to_period('M')).size().reset_index(name='Cantidad')
        df_agrupado['Fecha'] = df_agrupado['Fecha'].astype(str)
        titulo = "Novedades Generadas por Mes"
    elif periodo == 'Semanal':
        df_agrupado = df_novedades_sede.groupby(df_novedades_sede['Fecha'].dt.to_period('W')).size().reset_index(name='Cantidad')
        df_agrupado['Fecha'] = df_agrupado['Fecha'].astype(str)
        titulo = "Novedades Generadas por Semana"
    else:
        df_agrupado = df_novedades_sede.groupby('_fecha').size().reset_index(name='Cantidad')
        df_agrupado.columns = ['Fecha', 'Cantidad']
        titulo = "Novedades Generadas por Día"
    
    # Crear gráfica con matplotlib
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(len(df_agrupado)), df_agrupado['Cantidad'], color='#FF6B6B')
    ax.set_xlabel('Período')
    ax.set_ylabel('Número de Novedades')
    ax.set_title(titulo)
    ax.set_xticks(range(len(df_agrupado)))
    ax.set_xticklabels(df_agrupado['Fecha'], rotation=45, ha='right')
    plt.tight_layout()
    
    return fig

def graficar_pareto_novedades(df_novedades_sede):
    """Gráfica de Pareto de motivos de novedades usando matplotlib"""
    if df_novedades_sede.empty or '_motivo' not in df_novedades_sede.columns:
        return None
    
    # Contar motivos
    conteo_motivos = df_novedades_sede['_motivo'].value_counts().reset_index()
    conteo_motivos.columns = ['Motivo', 'Frecuencia']
    
    # Calcular porcentaje acumulado
    conteo_motivos['Porcentaje'] = (conteo_motivos['Frecuencia'] / conteo_motivos['Frecuencia'].sum() * 100).round(2)
    conteo_motivos['Porcentaje Acumulado'] = conteo_motivos['Porcentaje'].cumsum()
    
    # Crear gráfica con dos ejes
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Barras para frecuencias
    x = range(len(conteo_motivos))
    ax1.bar(x, conteo_motivos['Frecuencia'], color='#FF6B6B', alpha=0.7, label='Frecuencia')
    ax1.set_xlabel('Motivos')
    ax1.set_ylabel('Frecuencia', color='#FF6B6B')
    ax1.tick_params(axis='y', labelcolor='#FF6B6B')
    
    # Línea para porcentaje acumulado
    ax2 = ax1.twinx()
    ax2.plot(x, conteo_motivos['Porcentaje Acumulado'], color='#2C3E50', marker='o', linewidth=2, label='% Acumulado')
    ax2.set_ylabel('Porcentaje Acumulado (%)', color='#2C3E50')
    ax2.tick_params(axis='y', labelcolor='#2C3E50')
    
    # Configurar etiquetas del eje X
    ax1.set_xticks(x)
    ax1.set_xticklabels(conteo_motivos['Motivo'], rotation=45, ha='right')
    
    # Agregar línea del 80%
    ax2.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='80%')
    
    plt.title('Pareto de Motivos de Novedades')
    fig.tight_layout()
    
    return fig

def graficar_distribucion_motivos_meses(df_novedades_sede):
    """Gráfica de distribución de motivos por mes usando matplotlib"""
    if df_novedades_sede.empty or '_motivo' not in df_novedades_sede.columns:
        return None
    
    # Extraer mes y año
    df_novedades_sede['Mes'] = pd.to_datetime(df_novedades_sede['_fecha']).dt.strftime('%Y-%m')
    df_novedades_sede['NombreMes'] = pd.to_datetime(df_novedades_sede['_fecha']).dt.strftime('%B %Y')
    
    # Crear tabla pivote
    pivot_table = pd.crosstab(df_novedades_sede['_motivo'], df_novedades_sede['Mes'])
    
    # Ordenar por frecuencia total descendente
    pivot_table['Total'] = pivot_table.sum(axis=1)
    pivot_table = pivot_table.sort_values('Total', ascending=False)
    pivot_table = pivot_table.drop('Total', axis=1)
    
    # Obtener top 10 motivos
    top_motivos = pivot_table.head(10)
    
    # Reordenar columnas (meses) cronológicamente
    meses_ordenados = sorted(top_motivos.columns)
    top_motivos = top_motivos[meses_ordenados]
    
    # Crear gráfica de barras apiladas
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Colores para diferentes motivos
    colores = plt.cm.Set3(np.linspace(0, 1, len(top_motivos.index)))
    
    bottom = np.zeros(len(top_motivos.columns))
    for i, motivo in enumerate(top_motivos.index):
        valores = top_motivos.loc[motivo].values
        ax.bar(range(len(top_motivos.columns)), valores, bottom=bottom, 
               label=motivo, color=colores[i])
        bottom += valores
    
    ax.set_xlabel('Mes')
    ax.set_ylabel('Frecuencia')
    ax.set_title('Distribución de Motivos de Devolución por Mes')
    ax.set_xticks(range(len(top_motivos.columns)))
    ax.set_xticklabels(top_motivos.columns, rotation=45, ha='right')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=8)
    
    plt.tight_layout()
    
    return fig

# El resto del código se mantiene igual hasta la sección donde se muestran las gráficas
# ... (todo el código intermedio se mantiene igual)

# En la sección donde se muestran las gráficas, cambiamos st.plotly_chart por st.pyplot:

# En lugar de:
# st.plotly_chart(fig_novedades_temp, use_container_width=True)

# Usamos:
# st.pyplot(fig_novedades_temp)

# El código completo desde la sección de mostrar resultados sería:

# Mostrar resultados
if st.session_state.datos_cargados:
    st.markdown("---")
    st.header("📊 Tablas Resumen por Sede")
    
    df_novedades = st.session_state.dfs.get('NOVEDADES', None)
    fecha_fin = st.session_state.fecha_hasta
    
    sedes_lista = list(SEDES.keys())
    tabs = st.tabs(["📊 Resumen Ejecutivo"] + sedes_lista)
    
    with tabs[0]:
        st.subheader("📊 Comparativo entre Sedes")
        
        if st.session_state.resumen_ejecutivo is not None and not st.session_state.resumen_ejecutivo.empty:
            columnas_mostrar = ['Sede', 'Ingresos', 'Facturado total', 
                               '% facturado total / ingresos', '% novedades / ingresos',
                               '% novedades bloqueantes / ingresos']
            
            st.dataframe(st.session_state.resumen_ejecutivo[columnas_mostrar], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("**📌 Nota del corte:**")
            for _, row in st.session_state.resumen_ejecutivo.iterrows():
                fecha_inicio_str = row['fecha_inicio'].strftime('%d/%m/%Y')
                fecha_fin_str = row['fecha_fin'].strftime('%d/%m/%Y')
                st.markdown(f"- **{row['Sede']}:** {fecha_inicio_str} al {fecha_fin_str}")
        else:
            st.info("No hay datos para mostrar en el resumen ejecutivo")
    
    for i, sede in enumerate(sedes_lista):
        with tabs[i + 1]:
            config = SEDES[sede]
            fecha_inicio = config['fecha_inicio']
            
            if fecha_fin < fecha_inicio:
                st.warning(f"La fecha {fecha_fin.date()} es anterior a la fecha de inicio de {sede}")
                continue
            
            df_ingresos = st.session_state.dfs.get(f'INGRESOS_{sede}', pd.DataFrame())
            df_facturacion = st.session_state.dfs.get(f'FACTURACION_{sede}', pd.DataFrame())
            df_novedades_sede = st.session_state.dfs.get(f'NOVEDADES_DETALLE_{sede}', pd.DataFrame())
            
            periodo = st.selectbox(
                "📊 Agrupar por:",
                options=['Diario', 'Semanal', 'Mensual'],
                key=f"periodo_{sede}"
            )
            
            with st.spinner(f"Calculando {sede}..."):
                # Tabla principal
                df_tabla = construir_tabla_sede(
                    sede, config, fecha_inicio, fecha_fin, df_ingresos, df_facturacion, df_novedades, periodo
                )
                
                if len(df_tabla) > 0:
                    total_ingresos = df_tabla['ingresos'].sum()
                    total_facturado_modelo = df_tabla['facturado modelo'].sum()
                    total_facturado_fuera = df_tabla['facturado fuera modelo'].sum()
                    total_facturado = df_tabla['facturado total'].sum()
                    total_novedades = df_tabla['Novedades'].sum()
                    total_novedades_bloqueantes = df_tabla['Novedades Bloqueantes'].sum()
                    
                    pct_modelo = (total_facturado_modelo / total_ingresos * 100) if total_ingresos > 0 else 0
                    pct_fuera = (total_facturado_fuera / total_ingresos * 100) if total_ingresos > 0 else 0
                    pct_total = (total_facturado / total_ingresos * 100) if total_ingresos > 0 else 0
                    pct_novedades = (total_novedades / total_ingresos * 100) if total_ingresos > 0 else 0
                    pct_bloqueantes = (total_novedades_bloqueantes / total_ingresos * 100) if total_ingresos > 0 else 0
                    
                    cols = st.columns(6)
                    cols[0].metric("📥 Total Ingresos", f"{total_ingresos:,}")
                    cols[1].metric("✅ Facturado Modelo", f"{total_facturado_modelo:,}", f"{pct_modelo:.1f}%")
                    cols[2].metric("❌ Facturado Fuera", f"{total_facturado_fuera:,}", f"{pct_fuera:.1f}%")
                    cols[3].metric("💰 Facturado Total", f"{total_facturado:,}", f"{pct_total:.1f}%")
                    cols[4].metric("⚠️ Novedades", f"{total_novedades:,}", f"{pct_novedades:.1f}%")
                    cols[5].metric("🔒 Novedades Bloqueantes", f"{total_novedades_bloqueantes:,}", f"{pct_bloqueantes:.1f}%")
                    
                    # Gráfica 1: Novedades generadas (afectada por el período seleccionado)
                    st.markdown("---")
                    st.subheader("📈 Novedades Generadas")
                    fig_novedades_temp = graficar_novedades_temporales(df_novedades_sede, periodo)
                    if fig_novedades_temp:
                        st.pyplot(fig_novedades_temp, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos de novedades para mostrar en esta sede")
                    
                    # Gráfica 2: Pareto de novedades (NO afectada por el período)
                    st.markdown("---")
                    st.subheader("📊 Pareto de Motivos de Novedades")
                    fig_pareto = graficar_pareto_novedades(df_novedades_sede)
                    if fig_pareto:
                        st.pyplot(fig_pareto, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos suficientes para generar el Pareto de novedades")
                    
                    # Gráfica 3: Distribución por mes (NO afectada por el período)
                    st.markdown("---")
                    st.subheader("📅 Distribución de Motivos por Mes")
                    fig_distribucion = graficar_distribucion_motivos_meses(df_novedades_sede)
                    if fig_distribucion:
                        st.pyplot(fig_distribucion, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos suficientes para generar la distribución por mes")
                    
                    # Tabla de datos
                    st.markdown("---")
                    st.subheader("📋 Datos Detallados")
                    
                    columnas_mostrar = ['Fecha', 'ingresos', 'facturado modelo', 'facturado fuera modelo', 'facturado total', 'Novedades', 'Novedades Bloqueantes']
                    if periodo == 'Semanal':
                        columnas_mostrar.insert(1, 'semana')
                    elif periodo == 'Mensual':
                        columnas_mostrar.insert(1, 'mes')
                    
                    df_display = df_tabla[columnas_mostrar].copy()
                    if 'Fecha' in df_display.columns:
                        df_display['Fecha'] = df_display['Fecha'].dt.strftime('%Y-%m-%d')
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    if len(df_tabla) > 1:
                        chart_data = df_tabla[['ingresos', 'facturado total', 'Novedades', 'Novedades Bloqueantes']].copy()
                        chart_data.index = df_tabla['Fecha']
                        st.line_chart(chart_data)
                    
                    # Botón de descarga
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_tabla.to_excel(writer, sheet_name=f'Resumen_{periodo}', index=False)
                    
                    st.download_button(
                        "📥 Descargar Excel",
                        output.getvalue(),
                        f"{sede.lower().replace(' ', '_')}_{periodo.lower()}.xlsx",
                        key=f"excel_{sede}_{periodo}"
                    )
                else:
                    st.info(f"No hay datos para {sede} en el período seleccionado")
    
    if st.button("🔄 Reiniciar"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

else:
    st.info("👆 Carga un archivo Excel para comenzar")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por sede")
