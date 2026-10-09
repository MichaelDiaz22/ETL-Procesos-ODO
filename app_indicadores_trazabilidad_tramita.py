import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
from io import BytesIO
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from matplotlib.patches import Patch
import unicodedata

# Configuración de la página
st.set_page_config(
    page_title="Tablero resumen de gestión de Autorizaciones y Programación en Tramita",
    page_icon="📊",
    layout="wide"
)

# Estilos CSS personalizados para dashboard
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #7c3aed, #6d28d9);
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card .metric-value {
        font-size: 32px !important;
        font-weight: bold;
        margin: 5px 0 0 0;
    }
    .metric-card .metric-label {
        font-size: 14px;
        opacity: 0.9;
        margin: 0;
    }
    .metric-card-small {
        background: linear-gradient(135deg, #8b5cf6, #7c3aed);
        padding: 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card-small .metric-value {
        font-size: 26px !important;
        font-weight: bold;
        margin: 5px 0 0 0;
    }
    .metric-card-small .metric-label {
        font-size: 12px;
        opacity: 0.9;
        margin: 0;
    }
    .chart-container {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid #f0f0f0;
    }
    .interpretation-box {
        background: #f8f4ff;
        padding: 15px 20px;
        border-radius: 8px;
        border-left: 4px solid #7c3aed;
        margin-top: 10px;
        color: #2d2d2d;
        font-size: 14px;
        line-height: 1.6;
    }
    .interpretation-box strong {
        color: #5b21b6;
    }
    .executive-summary {
        background: linear-gradient(135deg, #f8f4ff, #ede9fe);
        padding: 25px 30px;
        border-radius: 12px;
        border: 2px solid #7c3aed;
        margin: 20px 0 30px 0;
        color: #2d2d2d;
        font-size: 15px;
        line-height: 1.8;
    }
    .executive-summary h3 {
        color: #5b21b6;
        margin-top: 0;
        font-size: 20px;
    }
    .executive-summary .highlight {
        background: #7c3aed;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .executive-summary .stat {
        font-weight: bold;
        color: #5b21b6;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# Configurar estilo de seaborn
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['legend.fontsize'] = 11

# Inicializar estado
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_portafolio' not in st.session_state:
    st.session_state.df_portafolio = None
if 'df_externas' not in st.session_state:
    st.session_state.df_externas = None
if 'df_filtrado' not in st.session_state:
    st.session_state.df_filtrado = None
if 'df_externas_filtrado' not in st.session_state:
    st.session_state.df_externas_filtrado = None
if 'filtros_aplicados' not in st.session_state:
    st.session_state.filtros_aplicados = False
if 'archivo_cargado' not in st.session_state:
    st.session_state.archivo_cargado = False

# Título principal
st.title("📊 Tablero resumen de gestión de Autorizaciones y Programación en Tramita")

# ======================== SECCIÓN DE CARGA (COLAPSABLE) ========================
with st.expander("📂 Cargar Archivo de Solicitudes", expanded=False):
    archivo = st.file_uploader(
        "Selecciona un archivo Excel que contenga las hojas: 'Datos', 'Portafolio' y 'Solicitudes Externas'",
        type=['xlsx', 'xls'],
        help="El archivo debe contener: Hoja 'Datos' con los campos: Tag, Solicitado, Auditado, Sede, Doc., Paciente, Edad, Genero, Diag., Entidad, Grupo Atención, Servicio, Cups, Radicación, Radicado, Autorizado, Autorización, Vence, Entregado, Servicio, Programado, Responsable, Estado, Observación, Prioridad, idOrden, idIndigo. Hoja 'Portafolio' con los campos: CUPS, codIPS, descrCodIPS, codREPS, A, UNIDAD EJECUTORA, Codigo unidad, Sede_Portafolio. Hoja 'Solicitudes Externas' con los campos: fechaRegistroFormulario, ciudad, proceso, idPaciente, nombrePaciente, entidad, servicio, cups, estado, fechaEntregaProceso, motivoCancelacion"
    )
    
    if archivo is not None:
        try:
            excel_file = pd.ExcelFile(archivo)
            
            if 'Datos' not in excel_file.sheet_names:
                st.error("⚠️ El archivo no contiene una hoja llamada 'Datos'")
                st.info(f"📋 Hojas disponibles: {', '.join(excel_file.sheet_names)}")
                st.session_state.df = None
                st.session_state.df_portafolio = None
                st.session_state.df_externas = None
                st.session_state.archivo_cargado = False
            else:
                df = pd.read_excel(archivo, sheet_name='Datos', header=1)
                
                unnamed_cols = [col for col in df.columns if 'Unnamed' in str(col)]
                if unnamed_cols:
                    df = df.drop(columns=unnamed_cols)
                
                cols = df.columns.tolist()
                servicio_count = 0
                for i, col in enumerate(cols):
                    if col == 'Servicio':
                        servicio_count += 1
                        if servicio_count == 2:
                            cols[i] = 'Servicio proceso tramita'
                df.columns = cols
                
                st.session_state.header_row = df.columns.tolist()
                
                columnas_requeridas = ['Tag', 'Solicitado', 'Auditado', 'Sede', 'Doc.', 'Paciente', 
                                       'Edad', 'Genero', 'Diag.', 'Entidad', 'Grupo Atención', 
                                       'Servicio', 'Cups', 'Radicación', 'Radicado', 'Autorizado', 
                                       'Autorización', 'Vence', 'Entregado', 'Servicio proceso tramita', 
                                       'Programado', 'Responsable', 'Estado', 'Observación', 'Prioridad', 
                                       'idOrden', 'idIndigo']
                
                columnas_df = [str(col).strip() for col in df.columns]
                columnas_requeridas_norm = [str(col).strip() for col in columnas_requeridas]
                
                columnas_faltantes = []
                for i, col in enumerate(columnas_requeridas_norm):
                    if col not in columnas_df:
                        if col == 'Servicio proceso tramita':
                            continue
                        columnas_faltantes.append(columnas_requeridas[i])
                
                if 'Servicio proceso tramita' in columnas_requeridas_norm:
                    servicio_count_df = sum(1 for col in columnas_df if col == 'Servicio')
                    if servicio_count_df == 1 and 'Servicio proceso tramita' in columnas_faltantes:
                        columnas_faltantes.remove('Servicio proceso tramita')
                
                if columnas_faltantes:
                    st.error(f"⚠️ La hoja 'Datos' no contiene las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
                    st.info(f"📋 Columnas encontradas: {', '.join(df.columns.tolist())}")
                    st.session_state.df = None
                    st.session_state.df_portafolio = None
                    st.session_state.df_externas = None
                    st.session_state.archivo_cargado = False
                else:
                    df = df.dropna(how='all')
                    df['Solicitado'] = pd.to_datetime(df['Solicitado'])
                    
                    if 'Entregado' in df.columns:
                        df['Entregado'] = pd.to_datetime(df['Entregado'])
                    
                    st.session_state.df = df
                    
                    if 'Portafolio' not in excel_file.sheet_names:
                        st.error("⚠️ El archivo no contiene una hoja llamada 'Portafolio'")
                        st.info(f"📋 Hojas disponibles: {', '.join(excel_file.sheet_names)}")
                        st.session_state.df_portafolio = None
                        st.session_state.df_externas = None
                        st.session_state.archivo_cargado = False
                    else:
                        df_portafolio = pd.read_excel(archivo, sheet_name='Portafolio')
                        
                        columnas_portafolio = ['CUPS', 'UNIDAD EJECUTORA', 'Sede_Portafolio']
                        columnas_portafolio_faltantes = [col for col in columnas_portafolio if col not in df_portafolio.columns]
                        
                        if columnas_portafolio_faltantes:
                            st.error(f"⚠️ La hoja 'Portafolio' no contiene las siguientes columnas requeridas: {', '.join(columnas_portafolio_faltantes)}")
                            st.info(f"📋 Columnas encontradas: {', '.join(df_portafolio.columns.tolist())}")
                            st.session_state.df_portafolio = None
                            st.session_state.df_externas = None
                            st.session_state.archivo_cargado = False
                        else:
                            df_portafolio = df_portafolio.dropna(how='all')
                            st.session_state.df_portafolio = df_portafolio
                            
                            if 'Solicitudes Externas' not in excel_file.sheet_names:
                                st.warning("⚠️ El archivo no contiene una hoja llamada 'Solicitudes Externas'. Esta hoja es opcional.")
                                st.session_state.df_externas = None
                                st.session_state.archivo_cargado = True
                            else:
                                df_externas = pd.read_excel(archivo, sheet_name='Solicitudes Externas')
                                
                                columnas_externas = ['fechaRegistroFormulario', 'ciudad', 'proceso', 'idPaciente', 
                                                    'nombrePaciente', 'entidad', 'servicio', 'cups', 'estado', 
                                                    'fechaEntregaProceso', 'motivoCancelacion']
                                columnas_externas_faltantes = [col for col in columnas_externas if col not in df_externas.columns]
                                
                                if columnas_externas_faltantes:
                                    st.warning(f"⚠️ La hoja 'Solicitudes Externas' no contiene las columnas requeridas. Se omitirá.")
                                    st.info(f"📋 Columnas faltantes: {', '.join(columnas_externas_faltantes)}")
                                    st.session_state.df_externas = None
                                else:
                                    df_externas = df_externas.dropna(how='all')
                                    
                                    df_externas['fechaRegistroFormulario'] = pd.to_datetime(df_externas['fechaRegistroFormulario'], errors='coerce')
                                    df_externas['fechaEntregaProceso'] = pd.to_datetime(df_externas['fechaEntregaProceso'], errors='coerce')
                                    
                                    df_externas['ciudad_norm'] = df_externas['ciudad'].astype(str).str.strip().str.upper()
                                    df_externas['ciudad_norm'] = df_externas['ciudad_norm'].str.replace('.', '').str.replace(',', '')
                                    
                                    df_externas['estado_norm'] = df_externas['estado'].astype(str).str.strip().str.upper()
                                    
                                    st.session_state.df_externas = df_externas
                                
                                st.session_state.archivo_cargado = True
                            
                            st.session_state.filtros_aplicados = False
                            st.session_state.df_filtrado = None
                            st.session_state.df_externas_filtrado = None
                            
                            if len(df) > 0:
                                st.session_state.fecha_inicio = df['Solicitado'].min().date()
                                st.session_state.fecha_fin = df['Solicitado'].max().date()
                            
                            st.success(f"✅ Archivo cargado correctamente.")
                            st.info(f"📊 Datos: {len(df)} registros encontrados.")
                            st.info(f"📊 Portafolio: {len(df_portafolio)} registros encontrados.")
                            if st.session_state.df_externas is not None:
                                st.info(f"📊 Solicitudes Externas: {len(df_externas)} registros encontrados.")
                            st.info(f"📅 Rango de fechas: {df['Solicitado'].min().strftime('%Y-%m-%d')} - {df['Solicitado'].max().strftime('%Y-%m-%d')}")
                    
        except Exception as e:
            st.error(f"⚠️ Error al leer el archivo: {e}")
            import traceback
            st.error(f"Detalles del error: {traceback.format_exc()}")
            st.session_state.df = None
            st.session_state.df_portafolio = None
            st.session_state.df_externas = None
            st.session_state.archivo_cargado = False
    else:
        st.info("📌 Carga un archivo Excel para comenzar a trabajar")

# ======================== FUNCIÓN PARA ASIGNAR ÁREA ========================
def asignar_area_mejorada(df_data, df_portafolio):
    df_data_copy = df_data.copy()
    df_portafolio_copy = df_portafolio.copy()
    
    df_data_copy['Cups_clean'] = df_data_copy['Cups'].astype(str).str.strip().str[:6]
    df_portafolio_copy['CUPS_clean'] = df_portafolio_copy['CUPS'].astype(str).str.strip().str[:6]
    
    df_data_copy['Sede_clean'] = df_data_copy['Sede'].astype(str).str.strip().str.upper()
    df_portafolio_copy['Sede_Portafolio_clean'] = df_portafolio_copy['Sede_Portafolio'].astype(str).str.strip().str.upper()
    
    dict_cups_sede_area = {}
    for idx, row in df_portafolio_copy.iterrows():
        key = (row['CUPS_clean'], row['Sede_Portafolio_clean'])
        dict_cups_sede_area[key] = row['UNIDAD EJECUTORA']
    
    dict_cups_area_fallback = {}
    for idx, row in df_portafolio_copy.iterrows():
        key = row['CUPS_clean']
        if key not in dict_cups_area_fallback:
            dict_cups_area_fallback[key] = row['UNIDAD EJECUTORA']
    
    def get_area(row):
        key = (row['Cups_clean'], row['Sede_clean'])
        if key in dict_cups_sede_area:
            return dict_cups_sede_area[key]
        else:
            if row['Cups_clean'] in dict_cups_area_fallback:
                return dict_cups_area_fallback[row['Cups_clean']]
            else:
                return 'Sin Área'
    
    df_data_copy['Area'] = df_data_copy.apply(get_area, axis=1)
    df_data_copy = df_data_copy.drop(['Cups_clean', 'Sede_clean'], axis=1)
    
    return df_data_copy

# ======================== FUNCIÓN PARA CLASIFICAR GESTIÓN DE EXTERNAS ========================
def clasificar_gestion_externa(estado):
    estado_norm = str(estado).strip().upper()
    if estado_norm == "PENDIENTE":
        return "Pendiente"
    else:
        return "Gestionado"

# ======================== FUNCIÓN PARA OBTENER SUFIJO DE SEDE ========================
def obtener_sufijo_sede(sedes_seleccionadas, df_filtrado):
    if sedes_seleccionadas and len(sedes_seleccionadas) > 0:
        if len(sedes_seleccionadas) == 1:
            return f"Sede: {sedes_seleccionadas[0]}"
        elif len(sedes_seleccionadas) <= 3:
            return f"Sedes: {', '.join(sedes_seleccionadas)}"
        else:
            return f"Sedes: {', '.join(sedes_seleccionadas[:3])} (+{len(sedes_seleccionadas)-3} más)"
    else:
        if df_filtrado is not None and 'Sede' in df_filtrado.columns:
            sedes_unicas = sorted(df_filtrado['Sede'].dropna().unique().tolist())
            if len(sedes_unicas) == 1:
                return f"Sede: {sedes_unicas[0]}"
            elif len(sedes_unicas) <= 3:
                return f"Sedes: {', '.join(sedes_unicas)}"
            else:
                return f"Todas las sedes ({len(sedes_unicas)})"
        return "Todas las sedes"

# ======================== FUNCIÓN PARA GENERAR RESUMEN EJECUTIVO GENERAL ========================
def generar_resumen_ejecutivo(df):
    total_ordenes = len(df)
    total_entidades = df['Entidad'].nunique()
    total_pacientes = df['Paciente'].nunique()
    
    estados_gestion = df['Estado_Gestion'].value_counts()
    pendientes_prog = estados_gestion.get('Pendiente gestión desde programación', 0)
    pendientes_aut = estados_gestion.get('Pendiente gestión desde Autorizaciones', 0)
    gestionados_prog = estados_gestion.get('Gestionado desde programación', 0)
    gestionados_aut = estados_gestion.get('Gestionado / En seguimiento desde Autorizaciones', 0)
    
    total_gestionados = gestionados_prog + gestionados_aut
    total_pendientes = pendientes_prog + pendientes_aut
    
    top_area = df['Area'].value_counts()
    area_top = top_area.index[0] if len(top_area) > 0 else "N/A"
    area_top_count = top_area.iloc[0] if len(top_area) > 0 else 0
    
    top_entidad = df['Entidad'].value_counts()
    entidad_top = top_entidad.index[0] if len(top_entidad) > 0 else "N/A"
    entidad_top_count = top_entidad.iloc[0] if len(top_entidad) > 0 else 0
    
    if 'dias_entrega' in df.columns:
        dias_entrega_validos = df['dias_entrega'].dropna()
        dias_entrega_validos = dias_entrega_validos[dias_entrega_validos >= 0]
        promedio_dias = dias_entrega_validos.mean() if len(dias_entrega_validos) > 0 else 0
    else:
        promedio_dias = 0
    
    if 'Sede' in df.columns and 'Solicitado' in df.columns:
        df_laboral = df[df['Solicitado'].dt.weekday < 5].copy()
        if len(df_laboral) > 0:
            ordenamientos_por_dia_sede = df_laboral.groupby([df_laboral['Solicitado'].dt.date, 'Sede']).size()
            promedio_dia_sede = ordenamientos_por_dia_sede.mean() if len(ordenamientos_por_dia_sede) > 0 else 0
        else:
            promedio_dia_sede = 0
    else:
        promedio_dia_sede = 0
    
    if 'Doc.' in df.columns and 'Solicitado' in df.columns:
        ordenamientos_por_paciente_dia = df.groupby(['Doc.', df['Solicitado'].dt.date]).size()
        promedio_paciente_dia = ordenamientos_por_paciente_dia.mean() if len(ordenamientos_por_paciente_dia) > 0 else 0
    else:
        promedio_paciente_dia = 0
    
    resumen = '<div class="executive-summary">'
    resumen += '<h3>📋 Resumen Ejecutivo</h3>'
    resumen += f'<p><strong>Visión General:</strong> Se identificaron <span class="stat">{total_ordenes:,}</span> órdenes correspondientes a <span class="stat">{total_pacientes:,}</span> pacientes y <span class="stat">{total_entidades}</span> entidades diferentes.</p>'
    resumen += f'<p><strong>Gestión de Órdenes:</strong> Del total de órdenes, <span class="stat">{total_gestionados:,} ({total_gestionados/total_ordenes*100:.1f}%)</span> ya han sido gestionadas, mientras que <span class="stat">{total_pendientes:,} ({total_pendientes/total_ordenes*100:.1f}%)</span> se encuentran pendientes de gestión.</p>'
    
    if total_pendientes > 0:
        resumen += f'<p><strong>Cuellos de Botella:</strong> De las órdenes pendientes, <span class="stat">{pendientes_prog:,} ({pendientes_prog/total_pendientes*100:.1f}%)</span> están pendientes desde programación y <span class="stat">{pendientes_aut:,} ({pendientes_aut/total_pendientes*100:.1f}%)</span> desde autorizaciones.</p>'
    
    if area_top != "N/A":
        resumen += f'<p><strong>Concentración por Área:</strong> El área con mayor volumen de órdenes es <span class="stat">"{area_top}"</span> con <span class="stat">{area_top_count:,}</span> órdenes (<span class="stat">{area_top_count/total_ordenes*100:.1f}%</span> del total).</p>'
    
    resumen += f'<p><strong>Concentración por Entidad:</strong> La entidad con mayor participación es <span class="stat">"{entidad_top}"</span> con <span class="stat">{entidad_top_count:,}</span> órdenes (<span class="stat">{entidad_top_count/total_ordenes*100:.1f}%</span> del total).</p>'
    
    if promedio_dias > 0:
        resumen += f'<p><strong>Tiempos de Gestión:</strong> El tiempo promedio de entrega de Autorizaciones a Programación es de <span class="stat">{promedio_dias:.1f}</span> días.</p>'
    
    if promedio_dia_sede > 0:
        resumen += f'<p><strong>Productividad por Sede:</strong> En promedio se generan <span class="stat">{promedio_dia_sede:.1f}</span> órdenes por día hábil en la sede.</p>'
    
    if promedio_paciente_dia > 0:
        resumen += f'<p><strong>Productividad por Paciente:</strong> En promedio cada paciente genera <span class="stat">{promedio_paciente_dia:.1f}</span> órdenes por día.</p>'
    
    resumen += '</div>'
    
    return resumen

# ======================== FUNCIÓN PARA GENERAR RESUMEN EJECUTIVO DE EXTERNAS (AMPLIADO) ========================
def generar_resumen_ejecutivo_externas(df_externas_filtrado, sufijo_sede):
    """Genera un resumen ejecutivo específico para solicitudes externas con narrativa ampliada"""
    if df_externas_filtrado is None or len(df_externas_filtrado) == 0:
        return '<div class="executive-summary"><h3>📋 Resumen Ejecutivo - Solicitudes Externas</h3><p>No se encontraron solicitudes externas para las ciudades seleccionadas.</p></div>'
    
    total_externas = len(df_externas_filtrado)
    
    df_ext_temp = df_externas_filtrado.copy()
    df_ext_temp['gestion_clasificacion'] = df_ext_temp['estado'].apply(clasificar_gestion_externa)
    
    total_gestionados_ext = (df_ext_temp['gestion_clasificacion'] == 'Gestionado').sum()
    total_no_gestionados_ext = (df_ext_temp['gestion_clasificacion'] == 'Pendiente').sum()
    pct_gestionados = (total_gestionados_ext / total_externas * 100) if total_externas > 0 else 0
    pct_pendientes = (total_no_gestionados_ext / total_externas * 100) if total_externas > 0 else 0
    
    # MÉTRICAS DE TIEMPO
    entregados = df_ext_temp[df_ext_temp['estado_norm'] == 'ENTREGADA'].copy()
    promedio_dias_entrega_ext = None
    num_entregados_validos = 0
    mediana_dias_entrega_ext = None
    min_dias_entrega_ext = None
    max_dias_entrega_ext = None
    pct_entregados_a_tiempo = 0
    num_entregados_a_tiempo = 0
    
    if len(entregados) > 0:
        entregados['dias_entrega_ext'] = (entregados['fechaEntregaProceso'] - entregados['fechaRegistroFormulario']).dt.total_seconds() / (24 * 3600)
        entregados_validos = entregados[entregados['dias_entrega_ext'].notna() & (entregados['dias_entrega_ext'] >= 0)]
        num_entregados_validos = len(entregados_validos)
        if num_entregados_validos > 0:
            promedio_dias_entrega_ext = entregados_validos['dias_entrega_ext'].mean()
            mediana_dias_entrega_ext = entregados_validos['dias_entrega_ext'].median()
            min_dias_entrega_ext = entregados_validos['dias_entrega_ext'].min()
            max_dias_entrega_ext = entregados_validos['dias_entrega_ext'].max()
            num_entregados_a_tiempo = (entregados_validos['dias_entrega_ext'] <= 5).sum()
            pct_entregados_a_tiempo = (num_entregados_a_tiempo / num_entregados_validos * 100)
    
    # TOP PROCESO
    top_proceso_txt = ""
    if 'proceso' in df_externas_filtrado.columns:
        top_procesos = df_externas_filtrado['proceso'].value_counts()
        if len(top_procesos) > 0:
            top_proceso = top_procesos.index[0]
            top_proceso_count = top_procesos.iloc[0]
            top_proceso_pct = top_proceso_count/total_externas*100
            top_proceso_txt = f'El proceso más frecuente es <span class="stat">"{str(top_proceso)[:60]}"</span> con <span class="stat">{top_proceso_count:,}</span> solicitudes (<span class="stat">{top_proceso_pct:.1f}%</span> del total)'
            
            if len(top_procesos) >= 3:
                top3_count = top_procesos.head(3).sum()
                pct_top3 = top3_count/total_externas*100
                top_proceso_txt += f'. Los 3 procesos principales concentran el <span class="stat">{pct_top3:.1f}%</span> de las solicitudes'
            
            top_proceso_txt += '.'
    
    # TOP SERVICIO
    top_servicio_txt = ""
    if 'servicio' in df_externas_filtrado.columns:
        top_servicios = df_externas_filtrado['servicio'].value_counts()
        if len(top_servicios) > 0:
            top_servicio = top_servicios.index[0]
            top_servicio_count = top_servicios.iloc[0]
            top_servicio_pct = top_servicio_count/total_externas*100
            top_servicio_txt = f'El servicio más solicitado es <span class="stat">"{str(top_servicio)[:60]}"</span> con <span class="stat">{top_servicio_count:,}</span> solicitudes (<span class="stat">{top_servicio_pct:.1f}%</span> del total)'
            
            if len(top_servicios) >= 10:
                top10_count = top_servicios.head(10).sum()
                pct_top10 = top10_count/total_externas*100
                top_servicio_txt += f'. Los 10 servicios principales concentran el <span class="stat">{pct_top10:.1f}%</span> de las solicitudes'
            
            top_servicio_txt += '.'
    
    # TOP ESTADO
    top_estado_txt = ""
    if 'estado' in df_externas_filtrado.columns:
        top_estados = df_externas_filtrado['estado'].value_counts()
        if len(top_estados) > 0:
            top_estado = top_estados.index[0]
            top_estado_count = top_estados.iloc[0]
            top_estado_pct = top_estado_count/total_externas*100
            top_estado_txt = f'El estado más frecuente es <span class="stat">"{top_estado}"</span> con <span class="stat">{top_estado_count:,}</span> solicitudes (<span class="stat">{top_estado_pct:.1f}%</span> del total)'
            
            if len(top_estados) > 1:
                segundo_estado = top_estados.index[1]
                segundo_estado_count = top_estados.iloc[1]
                segundo_estado_pct = segundo_estado_count/total_externas*100
                top_estado_txt += f'. El segundo estado más frecuente es <span class="stat">"{segundo_estado}"</span> con <span class="stat">{segundo_estado_count:,}</span> solicitudes (<span class="stat">{segundo_estado_pct:.1f}%</span>)'
            
            top_estado_txt += '.'
    
    # DISTRIBUCIÓN MENSUAL
    distribucion_mensual_txt = ""
    mes_pico_txt = ""
    if 'fechaRegistroFormulario' in df_externas_filtrado.columns:
        df_mes = df_externas_filtrado.dropna(subset=['fechaRegistroFormulario']).copy()
        if len(df_mes) > 0:
            df_mes['mes'] = df_mes['fechaRegistroFormulario'].dt.to_period('M')
            por_mes = df_mes.groupby('mes').size()
            if len(por_mes) > 0:
                mes_pico = por_mes.idxmax()
                mes_pico_count = por_mes.max()
                mes_bajo = por_mes.idxmin()
                mes_bajo_count = por_mes.min()
                promedio_mes = por_mes.mean()
                
                distribucion_mensual_txt = f'La distribución mensual muestra un promedio de <span class="stat">{promedio_mes:.1f}</span> solicitudes por mes, con un máximo de <span class="stat">{mes_pico_count}</span> en <span class="stat">{mes_pico.strftime("%Y-%m")}</span> y un mínimo de <span class="stat">{mes_bajo_count}</span> en <span class="stat">{mes_bajo.strftime("%Y-%m")}</span>.'
                
                if len(por_mes) >= 2:
                    primer_mes = por_mes.index[0]
                    ultimo_mes = por_mes.index[-1]
                    primer_val = por_mes.iloc[0]
                    ultimo_val = por_mes.iloc[-1]
                    if primer_val > 0:
                        cambio_pct = ((ultimo_val - primer_val) / primer_val) * 100
                        if cambio_pct > 20:
                            tendencia = f"tendencia al alza (+{cambio_pct:.1f}%)"
                        elif cambio_pct < -20:
                            tendencia = f"tendencia a la baja ({cambio_pct:.1f}%)"
                        else:
                            tendencia = f"tendencia estable ({cambio_pct:+.1f}%)"
                        mes_pico_txt = f'Comparando el primer mes ({primer_mes.strftime("%Y-%m")}) con el último ({ultimo_mes.strftime("%Y-%m")}), se observa una <strong>{tendencia}</strong> en el volumen de solicitudes.'
    
    # ENTIDADES
    entidades_txt = ""
    if 'entidad' in df_externas_filtrado.columns:
        top_entidades = df_externas_filtrado['entidad'].value_counts()
        if len(top_entidades) > 0:
            num_entidades = len(top_entidades)
            entidades_txt = f'Las solicitudes están asociadas a <strong>{num_entidades}</strong> entidad(es). '
            entidad_top = top_entidades.index[0]
            entidad_top_count = top_entidades.iloc[0]
            entidad_top_pct = entidad_top_count/total_externas*100
            entidades_txt += f'La entidad con mayor volumen es <span class="stat">"{str(entidad_top)[:50]}"</span> con <strong>{entidad_top_count}</strong> solicitudes (<span class="stat">{entidad_top_pct:.1f}%</span>).'
    
    # CONSTRUIR RESUMEN EJECUTIVO AMPLIADO
    resumen = '<div class="executive-summary">'
    resumen += '<h3>📋 Resumen Ejecutivo - Solicitudes Externas</h3>'
    
    # Sección 1: Visión General (sin ciudades ni pacientes únicos)
    resumen += f'<p><strong>🔹 Visión General ({sufijo_sede}):</strong> Se identificaron <span class="stat">{total_externas:,}</span> solicitudes externas en total.'
    if entidades_txt:
        resumen += f' {entidades_txt}'
    resumen += '</p>'
    
    # Sección 2: Estado de Gestión (sin el mensaje de "Buen desempeño")
    resumen += f'<p><strong>🔹 Estado de Gestión:</strong> Del total, <span class="stat">{total_gestionados_ext:,} ({pct_gestionados:.1f}%)</span> ya han sido gestionadas y <span class="stat">{total_no_gestionados_ext:,} ({pct_pendientes:.1f}%)</span> se encuentran pendientes de gestión.'
    if pct_pendientes >= 50:
        resumen += f' <strong style="color: #dc2626;">⚠️ Atención:</strong> Más de la mitad de las solicitudes están pendientes, lo que representa un <strong>riesgo operativo alto</strong> que requiere priorización inmediata.'
    elif pct_pendientes >= 25:
        resumen += f' <strong style="color: #ea580c;">⚠️ Nota:</strong> La proporción de pendientes es significativa ({pct_pendientes:.1f}%), se recomienda monitorear de cerca la gestión.'
    resumen += '</p>'
    
    # Sección 3: Tiempos de Entrega (sin el mensaje de "satisfactorio")
    if promedio_dias_entrega_ext is not None and num_entregados_validos > 0:
        resumen += f'<p><strong>🔹 Tiempos de Entrega a Proceso:</strong> El tiempo promedio de entrega es de <span class="stat">{promedio_dias_entrega_ext:.1f}</span> días (mediana: <span class="stat">{mediana_dias_entrega_ext:.1f}</span> días), calculado sobre <strong>{num_entregados_validos}</strong> registros con fechas válidas. El rango oscila entre <strong>{min_dias_entrega_ext:.1f}</strong> y <strong>{max_dias_entrega_ext:.1f}</strong> días.'
        
        if mediana_dias_entrega_ext is not None and promedio_dias_entrega_ext > 0:
            diferencia = promedio_dias_entrega_ext - mediana_dias_entrega_ext
            if diferencia > 2:
                resumen += f' La diferencia entre promedio y mediana (<strong>+{diferencia:.1f} días</strong>) sugiere la presencia de <strong>casos atípicos con tiempos muy largos</strong> que elevan el promedio.'
            elif diferencia < -2:
                resumen += f' La mediana supera al promedio, indicando una <strong>distribución con valores bajos frecuentes</strong>.'
        
        resumen += f' De los entregados, <span class="stat">{num_entregados_a_tiempo:,} ({pct_entregados_a_tiempo:.1f}%)</span> fueron entregados en <strong>5 días o menos</strong>.'
        if pct_entregados_a_tiempo >= 40 and pct_entregados_a_tiempo < 70:
            resumen += ' Hay margen de mejora en los tiempos de entrega.'
        elif pct_entregados_a_tiempo < 40:
            resumen += ' <strong style="color: #dc2626;">Se requiere revisar los procesos</strong> para reducir los tiempos de entrega.'
        resumen += '</p>'
    elif len(entregados) > 0:
        resumen += f'<p><strong>🔹 Tiempos de Entrega a Proceso:</strong> Existen <strong>{len(entregados)}</strong> registros con estado "ENTREGADA", pero no se encontraron fechas válidas para calcular el tiempo promedio de entrega.</p>'
    else:
        resumen += f'<p><strong>🔹 Tiempos de Entrega a Proceso:</strong> No hay registros con estado "ENTREGADA" en el período filtrado, por lo que no es posible calcular tiempos de entrega.</p>'
    
    # Sección 4: Distribución Mensual
    if distribucion_mensual_txt:
        resumen += f'<p><strong>🔹 Distribución Mensual:</strong> {distribucion_mensual_txt}'
        if mes_pico_txt:
            resumen += f' {mes_pico_txt}'
        resumen += '</p>'
    
    # Sección 5: Hallazgos Principales
    if top_proceso_txt or top_servicio_txt or top_estado_txt:
        resumen += f'<p><strong>🔹 Hallazgos Principales:</strong></p>'
        resumen += '<ul style="margin-top: 5px; line-height: 1.8;">'
        if top_proceso_txt:
            resumen += f'<li><strong>Procesos:</strong> {top_proceso_txt}</li>'
        if top_servicio_txt:
            resumen += f'<li><strong>Servicios:</strong> {top_servicio_txt}</li>'
        if top_estado_txt:
            resumen += f'<li><strong>Estados:</strong> {top_estado_txt}</li>'
        resumen += '</ul>'
    
    # Sección 6: Recomendaciones Automáticas (sin "Mantener el ritmo actual")
    resumen += '<p><strong>🔹 Recomendaciones Sugeridas:</strong></p>'
    resumen += '<ul style="margin-top: 5px; line-height: 1.8;">'
    
    recomendaciones = []
    if pct_pendientes >= 50:
        recomendaciones.append('Priorizar la gestión de solicitudes pendientes, ya que superan el 50% del total.')
    elif pct_pendientes >= 25:
        recomendaciones.append('Establecer un plan de seguimiento para reducir el volumen de pendientes.')
    
    if promedio_dias_entrega_ext is not None and promedio_dias_entrega_ext > 5:
        recomendaciones.append(f'Revisar los procesos de entrega, ya que el tiempo promedio ({promedio_dias_entrega_ext:.1f} días) supera los 5 días.')
    
    if len(top_procesos) >= 1 and top_procesos.iloc[0]/total_externas > 0.4:
        recomendaciones.append(f'El proceso "{str(top_procesos.index[0])[:40]}" concentra más del 40% de las solicitudes; considerar optimización específica.')
    
    if not recomendaciones:
        recomendaciones.append('Continuar con el monitoreo regular de las solicitudes externas.')
    
    for rec in recomendaciones:
        resumen += f'<li>{rec}</li>'
    resumen += '</ul>'
    
    resumen += '</div>'
    
    return resumen

# ======================== FUNCIÓN PARA GENERAR INTERPRETACIONES ========================
def generar_interpretacion(titulo, texto):
    return f'<div class="interpretation-box"><strong>📝 {titulo}:</strong> {texto}</div>'

# ======================== CONTENIDO PRINCIPAL ========================
if st.session_state.archivo_cargado and st.session_state.df is not None and st.session_state.df_portafolio is not None:
    df = st.session_state.df.copy()
    df_portafolio = st.session_state.df_portafolio.copy()
    df_externas = st.session_state.df_externas.copy() if st.session_state.df_externas is not None else None
    
    if not pd.api.types.is_datetime64_any_dtype(df['Solicitado']):
        try:
            df['Solicitado'] = pd.to_datetime(df['Solicitado'])
        except:
            st.error("⚠️ No se pudo convertir la columna 'Solicitado' a formato de fecha")
            st.stop()
    
    if 'Entregado' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Entregado']):
        try:
            df['Entregado'] = pd.to_datetime(df['Entregado'])
        except:
            pass
    
    if len(df) == 0:
        st.warning("⚠️ El archivo no contiene datos después de la fila de título")
        st.stop()
    
    df = asignar_area_mejorada(df, df_portafolio)
    
    def clasificar_estado_gestion(estado):
        if estado == "PROGRAMAR":
            return "Pendiente gestión desde programación"
        elif estado == "RADICAR":
            return "Pendiente gestión desde Autorizaciones"
        elif estado in ["PROGRAMADO", "PENDIENTE PROGRAMAR"]:
            return "Gestionado desde programación"
        else:
            return "Gestionado / En seguimiento desde Autorizaciones"
    
    df['Estado_Gestion'] = df['Estado'].apply(clasificar_estado_gestion)
    
    if 'Entregado' in df.columns:
        df['dias_entrega'] = (df['Entregado'] - df['Solicitado']).dt.total_seconds() / (24 * 3600)
    
    with st.expander("📊 Estadísticas de Asignación de Áreas", expanded=False):
        conteo_areas = df['Area'].value_counts()
        total_sin_area = (df['Area'] == 'Sin Área').sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de registros", len(df))
            st.metric("Registros sin área", total_sin_area)
            st.metric("Porcentaje sin área", f"{(total_sin_area/len(df)*100):.1f}%" if len(df) > 0 else "0%")
        
        with col2:
            st.write("Distribución de áreas:")
            st.dataframe(conteo_areas.reset_index().rename(columns={'index': 'Área', 'Area': 'Cantidad'}))
        
        if total_sin_area > 0:
            st.warning("⚠️ Algunos registros no pudieron ser asignados a un área. Verifica que los CUPS y Sedes coincidan con el portafolio base.")
            ejemplos_sin_area = df[df['Area'] == 'Sin Área'][['Cups', 'Sede']].head(10)
            st.dataframe(ejemplos_sin_area)
    
    # ======================== BARRA DE FILTROS ========================
    st.markdown("### 🔍 Panel de Filtros")
    
    with st.form(key="filtros_form"):
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
        
        with col_f1:
            fecha_min = df['Solicitado'].min().date()
            fecha_max = df['Solicitado'].max().date()
            fecha_inicio = st.date_input(
                "📅 Desde",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_inicio_dashboard"
            )
        
        with col_f2:
            fecha_fin = st.date_input(
                "📅 Hasta",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_fin_dashboard"
            )
        
        with col_f3:
            estados_disponibles = sorted(df['Estado'].dropna().unique().tolist())
            estados_seleccionados = st.multiselect(
                "📌 Estado",
                options=estados_disponibles,
                default=estados_disponibles,
                key="estados_dashboard"
            )
        
        with col_f4:
            st.write("")
            st.write("")
            aplicar_filtros = st.form_submit_button("🔍 Aplicar Filtros", use_container_width=True)
        
        col_f5, col_f6, col_f7 = st.columns([2, 2, 2])
        
        with col_f5:
            entidades_disponibles = sorted(df['Entidad'].dropna().unique().tolist())
            entidades_seleccionadas = st.multiselect(
                "🏥 Entidad",
                options=entidades_disponibles,
                default=entidades_disponibles,
                key="entidades_dashboard"
            )
        
        with col_f6:
            areas_disponibles = sorted(df['Area'].dropna().unique().tolist())
            areas_seleccionadas = st.multiselect(
                "📂 Área",
                options=areas_disponibles,
                default=areas_disponibles,
                key="areas_dashboard"
            )
        
        with col_f7:
            sedes_disponibles = sorted(df['Sede'].dropna().unique().tolist())
            sedes_seleccionadas = st.multiselect(
                "📍 Sede",
                options=sedes_disponibles,
                default=sedes_disponibles,
                key="sedes_dashboard"
            )
    
    col_reset1, col_reset2 = st.columns([1, 5])
    with col_reset1:
        if st.button("🔄 Restablecer Filtros", key="reset_filters_dashboard"):
            st.session_state.df_filtrado = None
            st.session_state.df_externas_filtrado = None
            st.session_state.filtros_aplicados = False
            st.rerun()
    
    # ======================== APLICAR FILTROS ========================
    if st.session_state.df_filtrado is None or aplicar_filtros:
        df_filtrado = df.copy()
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio <= fecha_fin:
                fecha_inicio_dt = pd.Timestamp(fecha_inicio)
                fecha_fin_dt = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                df_filtrado = df_filtrado[(df_filtrado['Solicitado'] >= fecha_inicio_dt) & (df_filtrado['Solicitado'] <= fecha_fin_dt)]
            else:
                st.warning("⚠️ La fecha de inicio debe ser menor o igual a la fecha de fin")
        
        if estados_seleccionados:
            df_filtrado = df_filtrado[df_filtrado['Estado'].isin(estados_seleccionados)]
        if entidades_seleccionadas:
            df_filtrado = df_filtrado[df_filtrado['Entidad'].isin(entidades_seleccionadas)]
        if areas_seleccionadas:
            df_filtrado = df_filtrado[df_filtrado['Area'].isin(areas_seleccionadas)]
        if sedes_seleccionadas:
            df_filtrado = df_filtrado[df_filtrado['Sede'].isin(sedes_seleccionadas)]
        
        if sedes_seleccionadas:
            df_portafolio_filtrado = df_portafolio[df_portafolio['Sede_Portafolio'].isin(sedes_seleccionadas)]
        else:
            df_portafolio_filtrado = df_portafolio.copy()
        
        df_filtrado = asignar_area_mejorada(df_filtrado, df_portafolio_filtrado)
        df_filtrado['Estado_Gestion'] = df_filtrado['Estado'].apply(clasificar_estado_gestion)
        
        if 'Entregado' in df_filtrado.columns:
            df_filtrado['dias_entrega'] = (df_filtrado['Entregado'] - df_filtrado['Solicitado']).dt.total_seconds() / (24 * 3600)
        
        df_externas_filtrado = None
        if df_externas is not None and len(df_externas) > 0:
            df_externas_filtrado = df_externas.copy()
            
            if sedes_seleccionadas:
                palabras_clave = []
                for sede in sedes_seleccionadas:
                    sede_clean = str(sede).strip().upper()
                    sede_clean = sede_clean.replace('.', '').replace(',', '')
                    
                    partes = sede_clean.split()
                    if len(partes) > 1:
                        palabra_clave = ' '.join(partes[1:])
                        if len(palabra_clave) > 0:
                            palabras_clave.append(palabra_clave)
                    else:
                        palabras_clave.append(sede_clean)
                    
                    palabras_clave.append(sede_clean)
                    
                    if len(partes) > 0:
                        palabras_clave.append(partes[0])
                
                palabras_clave = list(set([p for p in palabras_clave if len(p) > 1]))
                
                def ciudad_coincide(ciudad_norm):
                    if pd.isna(ciudad_norm):
                        return False
                    ciudad_str = str(ciudad_norm).strip().upper()
                    ciudad_str = ciudad_str.replace('.', '').replace(',', '')
                    
                    for palabra in palabras_clave:
                        if palabra in ciudad_str:
                            return True
                        if len(palabra) > 3 and ciudad_str in palabra:
                            return True
                    return False
                
                mask = df_externas_filtrado['ciudad_norm'].apply(ciudad_coincide)
                df_externas_filtrado = df_externas_filtrado[mask]
                
                if len(df_externas_filtrado) == 0 and len(palabras_clave) > 0:
                    for palabra in palabras_clave:
                        if len(palabra) > 2:
                            partes_palabra = palabra.split()
                            for parte in partes_palabra:
                                if len(parte) > 2:
                                    mask = df_externas_filtrado['ciudad_norm'].str.contains(parte, na=False)
                                    if mask.any():
                                        df_externas_filtrado = df_externas_filtrado[mask]
                                        break
                            if len(df_externas_filtrado) > 0:
                                break
            
            if fecha_inicio and fecha_fin and 'fechaRegistroFormulario' in df_externas_filtrado.columns:
                fecha_inicio_dt = pd.Timestamp(fecha_inicio)
                fecha_fin_dt = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                df_externas_filtrado = df_externas_filtrado[
                    (df_externas_filtrado['fechaRegistroFormulario'] >= fecha_inicio_dt) & 
                    (df_externas_filtrado['fechaRegistroFormulario'] <= fecha_fin_dt)
                ]
            
            if df_externas_filtrado is not None:
                df_externas_filtrado = df_externas_filtrado.dropna(how='all')
        
        st.session_state.df_filtrado = df_filtrado
        st.session_state.df_externas_filtrado = df_externas_filtrado
        st.session_state.filtros_aplicados = True
        
        if len(df_filtrado) > 0:
            st.success(f"✅ Filtros aplicados: {len(df_filtrado)} registros encontrados")
            if df_externas_filtrado is not None and len(df_externas_filtrado) > 0:
                st.info(f"📊 Solicitudes externas filtradas: {len(df_externas_filtrado)} registros encontrados para las ciudades seleccionadas")
            elif df_externas_filtrado is not None:
                st.info("📊 Solicitudes externas filtradas: No se encontraron registros para las ciudades seleccionadas")
        else:
            st.warning("⚠️ No hay datos con los filtros seleccionados")
    
    df_filtrado = st.session_state.df_filtrado.copy()
    df_externas_filtrado = st.session_state.df_externas_filtrado.copy() if st.session_state.df_externas_filtrado is not None else None
    
    # ======================== RESUMEN EJECUTIVO GENERAL ========================
    if len(df_filtrado) > 0:
        st.markdown("### 📋 Resumen Ejecutivo")
        resumen_html = generar_resumen_ejecutivo(df_filtrado)
        st.markdown(resumen_html, unsafe_allow_html=True)
    else:
        st.warning("⚠️ No hay datos para mostrar el resumen ejecutivo")
    
    # ======================== KPI CARDS GENERALES ========================
    st.markdown("### 📊 Indicadores Clave")
    
    total_registros = len(df_filtrado)
    total_entidades = df_filtrado['Entidad'].nunique() if len(df_filtrado) > 0 else 0
    total_pacientes = df_filtrado['Paciente'].nunique() if len(df_filtrado) > 0 else 0
    
    if 'Entregado' in df_filtrado.columns and len(df_filtrado) > 0:
        dias_entrega_validos = df_filtrado['dias_entrega'].dropna()
        dias_entrega_validos = dias_entrega_validos[dias_entrega_validos >= 0]
        promedio_dias_entrega = f"{dias_entrega_validos.mean():.1f}" if len(dias_entrega_validos) > 0 else "N/A"
    else:
        promedio_dias_entrega = "N/A"
    
    if len(df_filtrado) > 0 and 'Sede' in df_filtrado.columns and 'Solicitado' in df_filtrado.columns:
        df_laboral = df_filtrado[df_filtrado['Solicitado'].dt.weekday < 5].copy()
        
        if len(df_laboral) > 0:
            ordenamientos_por_dia_sede = df_laboral.groupby([df_laboral['Solicitado'].dt.date, 'Sede']).size()
            promedio_dia_sede = f"{ordenamientos_por_dia_sede.mean():.1f}" if len(ordenamientos_por_dia_sede) > 0 else "N/A"
        else:
            promedio_dia_sede = "N/A"
    else:
        promedio_dia_sede = "N/A"
    
    if len(df_filtrado) > 0 and 'Doc.' in df_filtrado.columns:
        ordenamientos_por_paciente_dia = df_filtrado.groupby(['Doc.', df_filtrado['Solicitado'].dt.date]).size()
        promedio_paciente_dia = f"{ordenamientos_por_paciente_dia.mean():.1f}" if len(ordenamientos_por_paciente_dia) > 0 else "N/A"
    else:
        promedio_paciente_dia = "N/A"
    
    if len(df_filtrado) > 0:
        col_k1, col_k2, col_k3 = st.columns(3)
        
        with col_k1:
            st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-label">📊 Total Registros</p>
                    <p class="metric-value">{total_registros:,}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_k2:
            st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-label">🏥 Entidades</p>
                    <p class="metric-value">{total_entidades:,}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_k3:
            st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-label">👥 Pacientes</p>
                    <p class="metric-value">{total_pacientes:,}</p>
                </div>
            """, unsafe_allow_html=True)
        
        col_k4, col_k5, col_k6 = st.columns(3)
        
        with col_k4:
            st.markdown(f"""
                <div class="metric-card-small">
                    <p class="metric-label">⏱️ Días promedio entrega</p>
                    <p class="metric-value">{promedio_dias_entrega}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_k5:
            st.markdown(f"""
                <div class="metric-card-small">
                    <p class="metric-label">📅 Ordenamientos/día por sede (Lun-Vie)</p>
                    <p class="metric-value">{promedio_dia_sede}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_k6:
            st.markdown(f"""
                <div class="metric-card-small">
                    <p class="metric-label">👤 Ordenamientos/día por paciente</p>
                    <p class="metric-value">{promedio_paciente_dia}</p>
                </div>
            """, unsafe_allow_html=True)
    
    # ======================== TABLA DE RESULTADOS ========================
    with st.expander("📋 Ver Detalle de Resultados (Datos Filtrados)", expanded=False):
        st.markdown("#### Detalle de órdenes con filtros aplicados")
        
        columnas_tabla = ['Estado', 'Estado_Gestion', 'Solicitado', 'Doc.', 'Paciente', 'Entidad', 'Area', 'Cups', 'Servicio', 'Observación']
        columnas_existentes = [col for col in columnas_tabla if col in df_filtrado.columns]
        
        if columnas_existentes:
            df_tabla = df_filtrado[columnas_existentes].copy()
            
            if 'Solicitado' in df_tabla.columns:
                df_tabla['Solicitado'] = df_tabla['Solicitado'].dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(
                df_tabla,
                use_container_width=True,
                height=400,
                column_config={
                    "Estado": st.column_config.TextColumn("Estado", width="medium"),
                    "Estado_Gestion": st.column_config.TextColumn("Estado de Gestión", width="large"),
                    "Solicitado": st.column_config.TextColumn("Solicitado", width="medium"),
                    "Doc.": st.column_config.TextColumn("Documento", width="small"),
                    "Paciente": st.column_config.TextColumn("Paciente", width="large"),
                    "Entidad": st.column_config.TextColumn("Entidad", width="large"),
                    "Area": st.column_config.TextColumn("Área", width="large"),
                    "Cups": st.column_config.TextColumn("Cups", width="small"),
                    "Servicio": st.column_config.TextColumn("Servicio", width="medium"),
                    "Observación": st.column_config.TextColumn("Observación", width="large"),
                }
            )
            st.caption(f"📊 Mostrando {len(df_tabla)} registros")
        else:
            st.warning("No se encontraron las columnas necesarias para mostrar la tabla")
    
    # ======================== GRÁFICOS GENERALES ========================
    if len(df_filtrado) > 0:
        st.markdown("### 📈 Análisis Visual")
        
        colores_diferenciados = [
            '#FF6B6B',  # Rojo
            '#4ECDC4',  # Verde azulado
            '#45B7D1',  # Azul
            '#96CEB4',  # Verde claro
            '#FFEAA7',  # Amarillo
            '#DDA0DD',  # Ciruela claro
            '#FF8C94',  # Rosa
            '#A8E6CF',  # Menta
            '#D4A5A5',  # Rosa viejo
            '#9B59B6',  # Morado
            '#F39C12',  # Naranja
            '#1ABC9C',  # Turquesa
            '#E74C3C',  # Rojo oscuro
            '#3498DB',  # Azul claro
            '#7D3C98'   # Púrpura oscuro
        ]
        
        sufijo_sede = obtener_sufijo_sede(sedes_seleccionadas, df_filtrado)
        
        # ======================== GRÁFICO 1 ========================
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📊 Ordenes Generadas vs Gestionadas")
        
        agrupacion = st.radio(
            "Agrupar por:",
            options=["Día", "Semana", "Quincena", "Mes"],
            horizontal=True,
            key="agrupacion_grafico1_dashboard"
        )
        
        df_temp = df_filtrado.copy()
        
        if agrupacion == "Día":
            df_temp['Fecha_Agrupada'] = df_temp['Solicitado'].dt.date
        elif agrupacion == "Semana":
            df_temp['Fecha_Agrupada'] = df_temp['Solicitado'].dt.to_period('W').dt.start_time
        elif agrupacion == "Quincena":
            df_temp['Dia'] = df_temp['Solicitado'].dt.day
            df_temp['Quincena'] = df_temp['Dia'].apply(lambda x: 1 if x <= 15 else 2)
            df_temp['Fecha_Agrupada'] = df_temp['Solicitado'].dt.to_period('M').dt.start_time
            df_temp['Fecha_Agrupada'] = df_temp.apply(
                lambda row: row['Fecha_Agrupada'] + pd.Timedelta(days=(row['Quincena']-1)*15), 
                axis=1
            )
        elif agrupacion == "Mes":
            df_temp['Fecha_Agrupada'] = df_temp['Solicitado'].dt.to_period('M').dt.start_time
        
        ordenes_generadas = df_temp.groupby('Fecha_Agrupada').size().reset_index()
        ordenes_generadas.columns = ['Fecha', 'Generadas']
        
        df_gestionadas = df_temp[df_temp['Estado_Gestion'].isin([
            "Gestionado desde programación",
            "Gestionado / En seguimiento desde Autorizaciones"
        ])]
        ordenes_gestionadas = df_gestionadas.groupby('Fecha_Agrupada').size().reset_index()
        ordenes_gestionadas.columns = ['Fecha', 'Gestionadas']
        
        df_graf1 = pd.merge(ordenes_generadas, ordenes_gestionadas, on='Fecha', how='outer').fillna(0)
        df_graf1 = df_graf1.sort_values('Fecha')
        
        fig1, ax1 = plt.subplots(figsize=(12, 5))
        x = np.arange(len(df_graf1['Fecha']))
        width = 0.35
        
        ax1.bar(x - width/2, df_graf1['Generadas'], width, label='Generadas', color='#6d28d9')
        ax1.bar(x + width/2, df_graf1['Gestionadas'], width, label='Gestionadas', color='#a78bfa')
        
        ax1.set_xlabel('Fecha')
        ax1.set_ylabel('Cantidad')
        ax1.set_title(f'Órdenes Generadas vs Gestionadas - {sufijo_sede}')
        ax1.set_xticks(x)
        ax1.set_xticklabels(df_graf1['Fecha'], rotation=45, ha='right', fontsize=9)
        ax1.legend()
        
        for i, v in enumerate(df_graf1['Generadas']):
            ax1.text(i - width/2, v + 0.5, str(int(v)), ha='center', va='bottom', fontsize=10, fontweight='bold', color='black')
        for i, v in enumerate(df_graf1['Gestionadas']):
            ax1.text(i + width/2, v + 0.5, str(int(v)), ha='center', va='bottom', fontsize=10, fontweight='bold', color='black')
        
        plt.tight_layout()
        st.pyplot(fig1)
        
        total_generadas = df_graf1['Generadas'].sum()
        total_gestionadas = df_graf1['Gestionadas'].sum()
        pct_gestionadas = (total_gestionadas / total_generadas * 100) if total_generadas > 0 else 0
        pct_pendientes = 100 - pct_gestionadas
        dia_pico = df_graf1.loc[df_graf1['Generadas'].idxmax(), 'Fecha'] if len(df_graf1) > 0 else "N/A"
        max_generadas = int(df_graf1['Generadas'].max()) if len(df_graf1) > 0 else 0
        
        texto_interpretacion1 = f'Se generaron <strong>{int(total_generadas)}</strong> órdenes en total, de las cuales <strong>{int(total_gestionadas)} (<span class="stat">{pct_gestionadas:.1f}%</span>)</strong> ya fueron gestionadas y <strong>{int(total_generadas - total_gestionadas)} (<span class="stat">{pct_pendientes:.1f}%</span>)</strong> aún se encuentran pendientes de gestión. El día con mayor actividad fue <strong>{dia_pico}</strong> con <strong>{max_generadas}</strong> órdenes generadas.'
        
        st.markdown(generar_interpretacion("Interpretación", texto_interpretacion1), unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 2 ========================
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Gestión de autorizaciones y ordenes disponibles para programación")
            
            estado_gestion_counts = df_filtrado['Estado_Gestion'].value_counts().reset_index()
            estado_gestion_counts.columns = ['Estado', 'Cantidad']
            
            colores_estados = {
                'Pendiente gestión desde programación': '#FF6B6B',
                'Pendiente gestión desde Autorizaciones': '#4ECDC4',
                'Gestionado desde programación': '#45B7D1',
                'Gestionado / En seguimiento desde Autorizaciones': '#96CEB4'
            }
            
            colors = [colores_estados.get(estado, '#CCCCCC') for estado in estado_gestion_counts['Estado']]
            
            fig2, ax2 = plt.subplots(figsize=(14, 8))
            
            wedges, texts, autotexts = ax2.pie(
                estado_gestion_counts['Cantidad'],
                labels=None,
                autopct=lambda pct: f'{pct:.1f}%',
                colors=colors,
                startangle=90,
                wedgeprops={'width': 0.4, 'edgecolor': 'white', 'linewidth': 2},
                pctdistance=0.75,
                textprops={'fontsize': 12, 'fontweight': 'bold', 'color': 'black'}
            )
            
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontsize(13)
                autotext.set_fontweight('bold')
                autotext.set_bbox(dict(
                    boxstyle="round,pad=0.3", 
                    facecolor='white', 
                    edgecolor='gray', 
                    alpha=0.85,
                    linewidth=1
                ))
            
            for i, wedge in enumerate(wedges):
                ang = (wedge.theta2 + wedge.theta1) / 2
                x = 1.35 * np.cos(np.radians(ang))
                y = 1.35 * np.sin(np.radians(ang))
                
                x_mid = 1.05 * np.cos(np.radians(ang))
                y_mid = 1.05 * np.sin(np.radians(ang))
                
                ax2.plot([x_mid, x], [y_mid, y], color='gray', linewidth=1.5, linestyle='-', alpha=0.7)
                
                cantidad = estado_gestion_counts['Cantidad'].iloc[i]
                ax2.text(x, y, f"{cantidad}", 
                        fontsize=14, fontweight='bold', ha='center', va='center', 
                        color='black',
                        bbox=dict(
                            boxstyle="round,pad=0.3", 
                            facecolor='white', 
                            edgecolor='gray', 
                            alpha=0.9,
                            linewidth=1
                        ))
            
            legend_elements = []
            for i, estado in enumerate(estado_gestion_counts['Estado']):
                legend_elements.append(
                    Patch(facecolor=colors[i], edgecolor='white', linewidth=2, 
                          label=f"{estado} ({estado_gestion_counts['Cantidad'].iloc[i]})")
                )
            
            ax2.legend(
                handles=legend_elements,
                loc='center left',
                bbox_to_anchor=(1.05, 0.5),
                fontsize=11,
                title="Estados de Gestión",
                title_fontsize=13,
                framealpha=0.95,
                edgecolor='#7c3aed',
                facecolor='white',
                shadow=True,
                borderpad=1
            )
            
            ax2.set_title(f'Gestión de autorizaciones y ordenes disponibles para programación - {sufijo_sede}', 
                          fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            st.pyplot(fig2)
            
            total_estados = estado_gestion_counts['Cantidad'].sum()
            estado_pendientes_prog = estado_gestion_counts[estado_gestion_counts['Estado'] == 'Pendiente gestión desde programación']['Cantidad'].sum() if 'Pendiente gestión desde programación' in estado_gestion_counts['Estado'].values else 0
            estado_pendientes_aut = estado_gestion_counts[estado_gestion_counts['Estado'] == 'Pendiente gestión desde Autorizaciones']['Cantidad'].sum() if 'Pendiente gestión desde Autorizaciones' in estado_gestion_counts['Estado'].values else 0
            estado_gestionados_prog = estado_gestion_counts[estado_gestion_counts['Estado'] == 'Gestionado desde programación']['Cantidad'].sum() if 'Gestionado desde programación' in estado_gestion_counts['Estado'].values else 0
            estado_gestionados_aut = estado_gestion_counts[estado_gestion_counts['Estado'] == 'Gestionado / En seguimiento desde Autorizaciones']['Cantidad'].sum() if 'Gestionado / En seguimiento desde Autorizaciones' in estado_gestion_counts['Estado'].values else 0
            
            mayor_carga = "Pendiente gestión desde programación" if estado_pendientes_prog == max([estado_pendientes_prog, estado_pendientes_aut, estado_gestionados_prog, estado_gestionados_aut]) else "Pendiente gestión desde Autorizaciones"
            
            texto_interpretacion2 = f'Del total de <strong>{total_estados}</strong> órdenes, <strong>{estado_pendientes_prog} (<span class="stat">{estado_pendientes_prog/total_estados*100:.1f}%</span>)</strong> se encuentran pendientes de gestión desde programación, <strong>{estado_pendientes_aut} (<span class="stat">{estado_pendientes_aut/total_estados*100:.1f}%</span>)</strong> pendientes desde autorizaciones, <strong>{estado_gestionados_prog} (<span class="stat">{estado_gestionados_prog/total_estados*100:.1f}%</span>)</strong> ya gestionadas desde programación, y <strong>{estado_gestionados_aut} (<span class="stat">{estado_gestionados_aut/total_estados*100:.1f}%</span>)</strong> gestionadas o en seguimiento desde autorizaciones. La mayor carga de trabajo se concentra en <strong>{mayor_carga}</strong>.'
            
            st.markdown(generar_interpretacion("Interpretación", texto_interpretacion2), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 3 ========================
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Pendientes de Gestión por Área")
            
            df_pendientes = df_filtrado[df_filtrado['Estado_Gestion'] == "Pendiente gestión desde programación"]
            pendientes_por_area = None
            
            if len(df_pendientes) > 0:
                pendientes_por_area = df_pendientes['Area'].value_counts().reset_index()
                pendientes_por_area.columns = ['Área', 'Cantidad']
                
                num_areas = len(pendientes_por_area)
                colors_area = colores_diferenciados[:num_areas]
                while len(colors_area) < num_areas:
                    colors_area = colors_area + colores_diferenciados
                colors_area = colors_area[:num_areas]
                
                fig3, ax3 = plt.subplots(figsize=(14, 8))
                
                wedges, texts, autotexts = ax3.pie(
                    pendientes_por_area['Cantidad'],
                    labels=None,
                    autopct=lambda pct: f'{pct:.1f}%',
                    colors=colors_area,
                    startangle=90,
                    wedgeprops={'width': 0.4, 'edgecolor': 'white', 'linewidth': 2},
                    pctdistance=0.75,
                    textprops={'fontsize': 12, 'fontweight': 'bold', 'color': 'black'}
                )
                
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontsize(12)
                    autotext.set_fontweight('bold')
                    autotext.set_bbox(dict(
                        boxstyle="round,pad=0.3", 
                        facecolor='white', 
                        edgecolor='gray', 
                        alpha=0.85,
                        linewidth=1
                    ))
                
                for i, wedge in enumerate(wedges):
                    ang = (wedge.theta2 + wedge.theta1) / 2
                    x = 1.35 * np.cos(np.radians(ang))
                    y = 1.35 * np.sin(np.radians(ang))
                    
                    x_mid = 1.05 * np.cos(np.radians(ang))
                    y_mid = 1.05 * np.sin(np.radians(ang))
                    
                    ax3.plot([x_mid, x], [y_mid, y], color='gray', linewidth=1.5, linestyle='-', alpha=0.7)
                    
                    cantidad = pendientes_por_area['Cantidad'].iloc[i]
                    ax3.text(x, y, f"{cantidad}", 
                            fontsize=13, fontweight='bold', ha='center', va='center', 
                            color='black',
                            bbox=dict(
                                boxstyle="round,pad=0.3", 
                                facecolor='white', 
                                edgecolor='gray', 
                                alpha=0.9,
                                linewidth=1
                            ))
                
                legend_elements_area = []
                for i, area in enumerate(pendientes_por_area['Área']):
                    legend_elements_area.append(
                        Patch(facecolor=colors_area[i], edgecolor='white', linewidth=2, 
                              label=f"{area} ({pendientes_por_area['Cantidad'].iloc[i]})")
                    )
                
                ax3.legend(
                    handles=legend_elements_area,
                    loc='center left',
                    bbox_to_anchor=(1.05, 0.5),
                    fontsize=11,
                    title="Áreas",
                    title_fontsize=13,
                    framealpha=0.95,
                    edgecolor='#7c3aed',
                    facecolor='white',
                    shadow=True,
                    borderpad=1
                )
                
                ax3.set_title(f'Pendientes de Gestión por Área - {sufijo_sede}', fontsize=14, fontweight='bold', pad=20)
                plt.tight_layout()
                st.pyplot(fig3)
                
                total_pendientes = pendientes_por_area['Cantidad'].sum()
                
                if len(pendientes_por_area) > 0:
                    max_area = pendientes_por_area.iloc[0]['Área']
                    max_cantidad = pendientes_por_area.iloc[0]['Cantidad']
                    
                    texto_interpretacion3 = f'Hay <strong>{total_pendientes}</strong> órdenes pendientes de gestión desde programación, distribuidas en <strong>{len(pendientes_por_area)}</strong> áreas. El área con mayor volumen de pendientes es <span class="stat">"{max_area}"</span> con <strong>{max_cantidad}</strong> órdenes (<span class="stat">{max_cantidad/total_pendientes*100:.1f}%</span> del total).'
                    
                    if len(pendientes_por_area) > 1:
                        segunda_area = pendientes_por_area.iloc[1]['Área']
                        segunda_cantidad = pendientes_por_area.iloc[1]['Cantidad']
                        texto_interpretacion3 += f' {segunda_area} es la segunda área con <strong>{segunda_cantidad}</strong> órdenes pendientes (<span class="stat">{segunda_cantidad/total_pendientes*100:.1f}%</span> del total).'
                    
                    st.markdown(generar_interpretacion("Interpretación", texto_interpretacion3), unsafe_allow_html=True)
            else:
                st.info("No hay ordenamientos pendientes de gestión desde programación")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICOS EN DOS COLUMNAS ========================
        col_g3, col_g4 = st.columns(2)
        
        # ======================== GRÁFICO 6: ÓRDENES GENERADAS POR ÁREA ========================
        with col_g3:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Órdenes Generadas por Área")
            
            ordenes_por_area = df_filtrado['Area'].value_counts().reset_index()
            ordenes_por_area.columns = ['Área', 'Cantidad']
            ordenes_por_area = ordenes_por_area.sort_values('Cantidad', ascending=False)
            
            fig6, ax6 = plt.subplots(figsize=(10, 5))
            bars6 = ax6.bar(ordenes_por_area['Área'], ordenes_por_area['Cantidad'], color='#7c3aed')
            
            ax6.set_xlabel('Área')
            ax6.set_ylabel('Cantidad')
            ax6.set_title(f'Órdenes Generadas por Área - {sufijo_sede}')
            ax6.set_xticklabels(ordenes_por_area['Área'], rotation=30, ha='right', fontsize=9)
            
            for bar in bars6:
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='black')
            
            plt.tight_layout()
            st.pyplot(fig6)
            
            if len(ordenes_por_area) > 0:
                total_ordenes = ordenes_por_area['Cantidad'].sum()
                top_area = ordenes_por_area.iloc[0]['Área']
                top_cantidad = ordenes_por_area.iloc[0]['Cantidad']
                
                texto_interpretacion6 = f'Se generaron <strong>{total_ordenes}</strong> órdenes distribuidas en <strong>{len(ordenes_por_area)}</strong> áreas. El área con mayor generación de órdenes es <span class="stat">"{top_area}"</span> con <strong>{top_cantidad}</strong> órdenes (<span class="stat">{top_cantidad/total_ordenes*100:.1f}%</span> del total).'
                
                if len(ordenes_por_area) > 1:
                    segunda_area = ordenes_por_area.iloc[1]['Área']
                    segunda_cantidad = ordenes_por_area.iloc[1]['Cantidad']
                    texto_interpretacion6 += f' {segunda_area} generó <strong>{segunda_cantidad}</strong> órdenes, representando el <span class="stat">{segunda_cantidad/total_ordenes*100:.1f}%</span> del total.'
                
                st.markdown(generar_interpretacion("Interpretación", texto_interpretacion6), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 7: ESTADOS DE SERVICIOS ========================
        with col_g4:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Estados de Servicios")
            
            estados_counts = df_filtrado['Estado'].value_counts().reset_index()
            estados_counts.columns = ['Estado', 'Cantidad']
            estados_counts = estados_counts.sort_values('Cantidad', ascending=False)
            
            fig7, ax7 = plt.subplots(figsize=(10, 5))
            bars7 = ax7.bar(estados_counts['Estado'], estados_counts['Cantidad'], color='#8b5cf6')
            
            ax7.set_xlabel('Estado')
            ax7.set_ylabel('Cantidad')
            ax7.set_title(f'Estados de Servicios - {sufijo_sede}')
            ax7.set_xticklabels(estados_counts['Estado'], rotation=30, ha='right', fontsize=9)
            
            for bar in bars7:
                height = bar.get_height()
                ax7.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='black')
            
            plt.tight_layout()
            st.pyplot(fig7)
            
            total_estados_serv = estados_counts['Cantidad'].sum()
            top_estado = estados_counts.iloc[0]['Estado']
            top_estado_cant = estados_counts.iloc[0]['Cantidad']
            
            texto_interpretacion7 = f'El estado más frecuente es <span class="stat">"{top_estado}"</span> con <strong>{top_estado_cant}</strong> órdenes (<span class="stat">{top_estado_cant/total_estados_serv*100:.1f}%</span> del total).'
            
            if len(estados_counts) > 1:
                segundo_estado = estados_counts.iloc[1]['Estado']
                segundo_cantidad = estados_counts.iloc[1]['Cantidad']
                texto_interpretacion7 += f' {segundo_estado} es el segundo estado con <strong>{segundo_cantidad}</strong> órdenes (<span class="stat">{segundo_cantidad/total_estados_serv*100:.1f}%</span> del total).'
            
            texto_interpretacion7 += f' Esto indica que la mayoría de las órdenes se encuentran en estado <span class="stat">"{top_estado}"</span>.'
            
            st.markdown(generar_interpretacion("Interpretación", texto_interpretacion7), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 8: ORDENAMIENTOS POR ENTIDAD ========================
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📊 Ordenamientos Distribuidos por Entidad")
        
        entidad_counts = df_filtrado['Entidad'].value_counts().reset_index()
        entidad_counts.columns = ['Entidad', 'Cantidad']
        entidad_counts = entidad_counts.sort_values('Cantidad', ascending=False)
        
        fig8, ax8 = plt.subplots(figsize=(14, 7))
        bars8 = ax8.bar(entidad_counts['Entidad'], entidad_counts['Cantidad'], color='#6d28d9')
        
        ax8.set_xlabel('Entidad', fontsize=12)
        ax8.set_ylabel('Cantidad', fontsize=12)
        ax8.set_title(f'Ordenamientos Distribuidos por Entidad - {sufijo_sede}', fontsize=14, fontweight='bold')
        ax8.set_xticklabels(entidad_counts['Entidad'], rotation=45, ha='right', fontsize=9)
        
        for bar in bars8:
            height = bar.get_height()
            ax8.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold', color='black')
        
        plt.tight_layout()
        st.pyplot(fig8)
        
        if len(entidad_counts) > 0:
            total_entidad = entidad_counts['Cantidad'].sum()
            top_entidad = entidad_counts.iloc[0]['Entidad']
            top_entidad_cant = entidad_counts.iloc[0]['Cantidad']
            
            texto_interpretacion8 = f'<strong>{total_entidad}</strong> órdenes están distribuidas entre <strong>{len(entidad_counts)}</strong> entidades. La entidad con mayor volumen es <span class="stat">"{top_entidad}"</span> con <strong>{top_entidad_cant}</strong> órdenes (<span class="stat">{top_entidad_cant/total_entidad*100:.1f}%</span> del total).'
            
            if len(entidad_counts) > 1:
                segunda_entidad = entidad_counts.iloc[1]['Entidad']
                segunda_cantidad = entidad_counts.iloc[1]['Cantidad']
                texto_interpretacion8 += f' {segunda_entidad} es la segunda entidad con <strong>{segunda_cantidad}</strong> órdenes (<span class="stat">{segunda_cantidad/total_entidad*100:.1f}%</span> del total).'
            
            st.markdown(generar_interpretacion("Interpretación", texto_interpretacion8), unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ======================== SECCIÓN COMPRIMIBLE: SOLICITUDES EXTERNAS ========================
    st.divider()
    
    with st.expander("📂 Solicitudes Externas - Análisis Completo", expanded=False):
        # ======================== CÁLCULO DE MÉTRICAS DE EXTERNAS ========================
        total_externas = 0
        total_gestionados_ext = 0
        pct_gestionados_ext = 0
        total_pendientes_ext = 0
        pct_pendientes_ext = 0
        promedio_dias_entrega_ext = None
        num_entregados_validos = 0
        pct_entregados_a_tiempo = 0
        total_procesos = 0
        total_servicios = 0
        
        if df_externas_filtrado is not None and len(df_externas_filtrado) > 0:
            total_externas = len(df_externas_filtrado)
            df_ext_temp = df_externas_filtrado.copy()
            df_ext_temp['gestion_clasificacion'] = df_ext_temp['estado'].apply(clasificar_gestion_externa)
            total_gestionados_ext = (df_ext_temp['gestion_clasificacion'] == 'Gestionado').sum()
            total_pendientes_ext = (df_ext_temp['gestion_clasificacion'] == 'Pendiente').sum()
            pct_gestionados_ext = (total_gestionados_ext / total_externas * 100) if total_externas > 0 else 0
            pct_pendientes_ext = (total_pendientes_ext / total_externas * 100) if total_externas > 0 else 0
            
            entregados = df_ext_temp[df_ext_temp['estado_norm'] == 'ENTREGADA'].copy()
            if len(entregados) > 0:
                entregados['dias_entrega_ext'] = (entregados['fechaEntregaProceso'] - entregados['fechaRegistroFormulario']).dt.total_seconds() / (24 * 3600)
                entregados_validos = entregados[entregados['dias_entrega_ext'].notna() & (entregados['dias_entrega_ext'] >= 0)]
                num_entregados_validos = len(entregados_validos)
                if num_entregados_validos > 0:
                    promedio_dias_entrega_ext = entregados_validos['dias_entrega_ext'].mean()
                    pct_entregados_a_tiempo = (entregados_validos['dias_entrega_ext'] <= 5).sum() / num_entregados_validos * 100
            
            if 'proceso' in df_externas_filtrado.columns:
                total_procesos = df_externas_filtrado['proceso'].nunique()
            if 'servicio' in df_externas_filtrado.columns:
                total_servicios = df_externas_filtrado['servicio'].nunique()
        
        sufijo_sede_ext = obtener_sufijo_sede(sedes_seleccionadas, df_filtrado)
        
        # ======================== INDICADORES CLAVE DE SOLICITUDES EXTERNAS (6 TARJETAS) ========================
        st.markdown("#### 📊 Indicadores clave de solicitudes externas")
        
        # Primera fila: 3 tarjetas principales
        col_ext_k1, col_ext_k2, col_ext_k3 = st.columns(3)
        
        with col_ext_k1:
            st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-label">📋 Solicitudes Externas</p>
                    <p class="metric-value">{total_externas:,}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_ext_k2:
            if total_externas > 0:
                st.markdown(f"""
                    <div class="metric-card">
                        <p class="metric-label">✅ % Gestionado (Externas)</p>
                        <p class="metric-value">{pct_gestionados_ext:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="metric-card">
                        <p class="metric-label">✅ % Gestionado (Externas)</p>
                        <p class="metric-value">N/A</p>
                    </div>
                """, unsafe_allow_html=True)
        
        with col_ext_k3:
            if promedio_dias_entrega_ext is not None and num_entregados_validos > 0:
                st.markdown(f"""
                    <div class="metric-card">
                        <p class="metric-label">⏱️ Días entrega (Externas)</p>
                        <p class="metric-value">{promedio_dias_entrega_ext:.1f}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="metric-card">
                        <p class="metric-label">⏱️ Días entrega (Externas)</p>
                        <p class="metric-value">N/A</p>
                    </div>
                """, unsafe_allow_html=True)
        
        # Segunda fila: 3 tarjetas adicionales
        col_ext_k4, col_ext_k5, col_ext_k6 = st.columns(3)
        
        with col_ext_k4:
            st.markdown(f"""
                <div class="metric-card-small">
                    <p class="metric-label">⚠️ Pendientes (Externas)</p>
                    <p class="metric-value">{total_pendientes_ext:,} ({pct_pendientes_ext:.1f}%)</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_ext_k5:
            if num_entregados_validos > 0:
                st.markdown(f"""
                    <div class="metric-card-small">
                        <p class="metric-label">⚡ % Entregados ≤ 5 días</p>
                        <p class="metric-value">{pct_entregados_a_tiempo:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="metric-card-small">
                        <p class="metric-label">⚡ % Entregados ≤ 5 días</p>
                        <p class="metric-value">N/A</p>
                    </div>
                """, unsafe_allow_html=True)

        
        # ======================== RESUMEN EJECUTIVO DE SOLICITUDES EXTERNAS ========================
        st.markdown("#### 📋 Resumen Ejecutivo - Solicitudes Externas")
        resumen_ext_html = generar_resumen_ejecutivo_externas(df_externas_filtrado, sufijo_sede_ext)
        st.markdown(resumen_ext_html, unsafe_allow_html=True)
        
        # ======================== TABLA DE SOLICITUDES EXTERNAS ========================
        with st.expander("📋 Ver Detalle de Solicitudes Externas", expanded=False):
            if df_externas_filtrado is not None and len(df_externas_filtrado) > 0:
                columnas_ext = ['fechaRegistroFormulario', 'ciudad', 'proceso', 'idPaciente', 'nombrePaciente', 'entidad', 'servicio', 'estado']
                columnas_ext_existentes = [col for col in columnas_ext if col in df_externas_filtrado.columns]
                
                if columnas_ext_existentes:
                    df_ext_tabla = df_externas_filtrado[columnas_ext_existentes].copy()
                    
                    if 'fechaRegistroFormulario' in df_ext_tabla.columns:
                        df_ext_tabla['fechaRegistroFormulario'] = pd.to_datetime(df_ext_tabla['fechaRegistroFormulario']).dt.strftime('%Y-%m-%d')
                    
                    df_ext_tabla['Clasificación'] = df_ext_tabla['estado'].apply(clasificar_gestion_externa)
                    
                    st.dataframe(
                        df_ext_tabla,
                        use_container_width=True,
                        height=300,
                        column_config={
                            "fechaRegistroFormulario": st.column_config.TextColumn("Fecha Registro", width="medium"),
                            "ciudad": st.column_config.TextColumn("Ciudad", width="medium"),
                            "proceso": st.column_config.TextColumn("Proceso", width="large"),
                            "idPaciente": st.column_config.TextColumn("ID Paciente", width="small"),
                            "nombrePaciente": st.column_config.TextColumn("Paciente", width="large"),
                            "entidad": st.column_config.TextColumn("Entidad", width="large"),
                            "servicio": st.column_config.TextColumn("Servicio", width="large"),
                            "estado": st.column_config.TextColumn("Estado", width="medium"),
                            "Clasificación": st.column_config.TextColumn("Clasificación", width="medium"),
                        }
                    )
                    st.caption(f"📊 Mostrando {len(df_ext_tabla)} registros de solicitudes externas")
            else:
                st.info("No hay datos de solicitudes externas para mostrar")
        
        # ======================== GRÁFICOS DE SOLICITUDES EXTERNAS ========================
        if df_externas_filtrado is not None and len(df_externas_filtrado) > 0:
            st.markdown("#### 📈 Análisis Visual - Solicitudes Externas")
            
            # ======================== GRÁFICO 5B: PROCESOS POR MES ========================
            if 'proceso' in df_externas_filtrado.columns:
                with st.container():
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📊 Solicitudes Externas: Procesos por Mes")
                    
                    df_ext_mes = df_externas_filtrado.copy()
                    df_ext_mes['mes'] = df_ext_mes['fechaRegistroFormulario'].dt.to_period('M').dt.start_time
                    
                    procesos_por_mes = df_ext_mes.groupby(['mes', 'proceso']).size().reset_index(name='Cantidad')
                    procesos_por_mes = procesos_por_mes.sort_values('mes')
                    
                    if len(procesos_por_mes) > 0:
                        fig5b, ax5b = plt.subplots(figsize=(14, 7))
                        
                        meses_unicos = sorted(procesos_por_mes['mes'].unique())
                        procesos_unicos = sorted(procesos_por_mes['proceso'].unique())
                        
                        datos_pivot = procesos_por_mes.pivot(index='mes', columns='proceso', values='Cantidad').fillna(0)
                        
                        colores_procesos = colores_diferenciados[:len(procesos_unicos)]
                        while len(colores_procesos) < len(procesos_unicos):
                            colores_procesos = colores_procesos + colores_diferenciados
                        colores_procesos = colores_procesos[:len(procesos_unicos)]
                        
                        bottom = np.zeros(len(datos_pivot))
                        for i, proceso in enumerate(procesos_unicos):
                            if proceso in datos_pivot.columns:
                                valores = datos_pivot[proceso].values
                                bars = ax5b.bar(range(len(datos_pivot)), valores, bottom=bottom, 
                                               label=str(proceso)[:40], color=colores_procesos[i], 
                                               edgecolor='white', linewidth=1.5)
                                for j, v in enumerate(valores):
                                    if v > 0:
                                        text_color = 'white' if v > 5 else 'black'
                                        ax5b.text(j, bottom[j] + v/2, f'{int(v)}', 
                                                 ha='center', va='center', 
                                                 fontsize=9, fontweight='bold', color=text_color)
                                bottom += valores
                        
                        ax5b.set_xlabel('Mes', fontsize=12)
                        ax5b.set_ylabel('Cantidad de Solicitudes', fontsize=12)
                        ax5b.set_title(f"Solicitudes Externas: Procesos por Mes - {sufijo_sede}", 
                                      fontsize=14, fontweight='bold')
                        
                        ax5b.set_xticks(range(len(datos_pivot.index)))
                        ax5b.set_xticklabels([m.strftime('%Y-%m') for m in datos_pivot.index], rotation=45, ha='right')
                        
                        for i, total in enumerate(bottom):
                            if total > 0:
                                ax5b.text(i, total + 0.3, f'{int(total)}', ha='center', va='bottom', 
                                         fontsize=11, fontweight='bold', color='black')
                        
                        ax5b.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=10, 
                                   title='Procesos', title_fontsize=11)
                        
                        plt.tight_layout()
                        st.pyplot(fig5b)
                        
                        # Interpretación ampliada
                        total_solicitudes = procesos_por_mes['Cantidad'].sum()
                        mes_pico = procesos_por_mes.groupby('mes')['Cantidad'].sum().idxmax()
                        cantidad_pico = procesos_por_mes.groupby('mes')['Cantidad'].sum().max()
                        mes_bajo = procesos_por_mes.groupby('mes')['Cantidad'].sum().idxmin()
                        cantidad_baja = procesos_por_mes.groupby('mes')['Cantidad'].sum().min()
                        promedio_mes = procesos_por_mes.groupby('mes')['Cantidad'].sum().mean()
                        
                        proceso_top = procesos_por_mes.groupby('proceso')['Cantidad'].sum().idxmax()
                        cantidad_top = procesos_por_mes.groupby('proceso')['Cantidad'].sum().max()
                        pct_top = cantidad_top / total_solicitudes * 100
                        
                        top3_procesos = procesos_por_mes.groupby('proceso')['Cantidad'].sum().nlargest(3)
                        pct_top3 = top3_procesos.sum() / total_solicitudes * 100
                        
                        serie_mensual = procesos_por_mes.groupby('mes')['Cantidad'].sum()
                        cv_mensual = (serie_mensual.std() / serie_mensual.mean() * 100) if serie_mensual.mean() > 0 else 0
                        
                        tendencia_txt = ""
                        if len(serie_mensual) >= 2:
                            primer_val = serie_mensual.iloc[0]
                            ultimo_val = serie_mensual.iloc[-1]
                            if primer_val > 0:
                                cambio_pct = ((ultimo_val - primer_val) / primer_val) * 100
                                if cambio_pct > 20:
                                    tendencia_txt = f'La tendencia del período muestra un <strong>crecimiento del {cambio_pct:.1f}%</strong> comparando el primer mes con el último, lo que sugiere un aumento sostenido en la demanda.'
                                elif cambio_pct < -20:
                                    tendencia_txt = f'La tendencia del período muestra una <strong>reducción del {abs(cambio_pct):.1f}%</strong> comparando el primer mes con el último, lo que podría indicar una mejora en la canalización interna o menor demanda externa.'
                                else:
                                    tendencia_txt = f'La tendencia del período es <strong>estable ({cambio_pct:+.1f}%)</strong>, sin cambios significativos entre el primer y último mes.'
                        
                        if cv_mensual > 50:
                            variabilidad_txt = f'La <strong>alta variabilidad mensual (CV: {cv_mensual:.1f}%)</strong> indica que el volumen de solicitudes fluctúa considerablemente, lo que puede dificultar la planificación de recursos.'
                        elif cv_mensual > 25:
                            variabilidad_txt = f'La <strong>variabilidad mensual moderada (CV: {cv_mensual:.1f}%)</strong> sugiere fluctuaciones normales en la demanda.'
                        else:
                            variabilidad_txt = f'La <strong>baja variabilidad mensual (CV: {cv_mensual:.1f}%)</strong> indica una demanda relativamente estable y predecible.'
                        
                        texto_interpretacion5b = (
                            f'Se registraron <strong>{int(total_solicitudes)}</strong> solicitudes externas en <strong>{len(meses_unicos)}</strong> meses. '
                            f'El mes de mayor actividad fue <span class="stat">{mes_pico.strftime("%Y-%m")}</span> con <strong>{int(cantidad_pico)}</strong> solicitudes, mientras que el mes más bajo fue <span class="stat">{mes_bajo.strftime("%Y-%m")}</span> con <strong>{int(cantidad_baja)}</strong>. '
                            f'El promedio mensual es de <strong>{promedio_mes:.1f}</strong> solicitudes. {variabilidad_txt} {tendencia_txt}<br>'
                            f'<strong>Concentración por proceso:</strong> El proceso más frecuente es <span class="stat">"{proceso_top}"</span> con <strong>{int(cantidad_top)}</strong> solicitudes (<span class="stat">{pct_top:.1f}%</span> del total). '
                            f'Los 3 procesos principales concentran el <span class="stat">{pct_top3:.1f}%</span> de todas las solicitudes, lo que refleja una '
                            f'{"<strong>alta dependencia</strong> de pocos procesos" if pct_top3 > 70 else "<strong>distribución moderada</strong> entre varios procesos" if pct_top3 > 40 else "<strong>buena diversificación</strong> entre múltiples procesos"}.'
                        )
                        
                        st.markdown(generar_interpretacion("Interpretación", texto_interpretacion5b), unsafe_allow_html=True)
                    else:
                        st.info("No hay datos de procesos para mostrar por mes")
                    st.markdown('</div>', unsafe_allow_html=True)

                        # ======================== GRÁFICO 5C: TOP 10 SERVICIOS POR MES ========================
            if 'servicio' in df_externas_filtrado.columns:
                with st.container():
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📊 Solicitudes Externas: Top 10 Servicios más Solicitados por Mes")
                    
                    df_ext_serv = df_externas_filtrado.copy()
                    df_ext_serv['mes'] = df_ext_serv['fechaRegistroFormulario'].dt.to_period('M').dt.start_time
                    df_ext_serv = df_ext_serv.dropna(subset=['mes', 'servicio'])
                    
                    meses_unicos_serv = sorted(df_ext_serv['mes'].dropna().unique())
                    
                    if len(meses_unicos_serv) > 0:
                        opciones_mes = ["Todos los meses (Top 10 global)"] + [m.strftime('%Y-%m') for m in meses_unicos_serv]
                        mes_seleccionado = st.selectbox(
                            "Selecciona un mes para ver su Top 10 de servicios:",
                            options=opciones_mes,
                            index=0,
                            key="selector_mes_top_servicios"
                        )
                        
                        if mes_seleccionado == "Todos los meses (Top 10 global)":
                            df_top10 = df_ext_serv.copy()
                            titulo_mes = "Todos los meses"
                            total_periodo = len(df_top10)
                        else:
                            mes_dt = pd.to_datetime(mes_seleccionado + "-01")
                            df_top10 = df_ext_serv[df_ext_serv['mes'] == mes_dt].copy()
                            titulo_mes = mes_seleccionado
                            total_periodo = len(df_top10)
                        
                        if len(df_top10) > 0:
                            # Agrupar por servicio Y proceso para incluir el proceso en la etiqueta
                            tiene_proceso = 'proceso' in df_top10.columns
                            
                            if tiene_proceso:
                                # Agrupar por (servicio, proceso) para contar combinaciones
                                conteo_servicios = df_top10.groupby(['servicio', 'proceso']).size().reset_index(name='Cantidad')
                                conteo_servicios = conteo_servicios.sort_values('Cantidad', ascending=False).head(10).reset_index(drop=True)
                                # Crear etiqueta combinada: "SERVICIO - PROCESO"
                                conteo_servicios['Etiqueta'] = conteo_servicios.apply(
                                    lambda row: f"{str(row['servicio']).strip()} - {str(row['proceso']).strip()}", 
                                    axis=1
                                )
                            else:
                                # Si no hay proceso, usar solo el servicio
                                conteo_servicios = df_top10['servicio'].value_counts().head(10).reset_index()
                                conteo_servicios.columns = ['servicio', 'Cantidad']
                                conteo_servicios['Etiqueta'] = conteo_servicios['servicio'].astype(str)
                            
                            conteo_servicios['Porcentaje'] = (conteo_servicios['Cantidad'] / total_periodo * 100).round(1)
                            
                            fig5c, ax5c = plt.subplots(figsize=(16, 9))
                            
                            colores_barras = plt.cm.viridis(np.linspace(0.15, 0.85, len(conteo_servicios)))
                            
                            y_pos = range(len(conteo_servicios))
                            bars = ax5c.barh(y_pos, conteo_servicios['Cantidad'], 
                                            color=colores_barras, edgecolor='white', linewidth=1.5)
                            
                            # Usar la etiqueta combinada (Servicio - Proceso), truncada a 75 caracteres
                            etiquetas_y = [f"{str(e)[:75]}{'...' if len(str(e)) > 75 else ''}" 
                                          for e in conteo_servicios['Etiqueta']]
                            ax5c.set_yticks(y_pos)
                            ax5c.set_yticklabels(etiquetas_y, fontsize=9)
                            ax5c.invert_yaxis()
                            
                            ax5c.set_xlabel('Cantidad de Solicitudes', fontsize=12)
                            ax5c.set_ylabel('Servicio - Proceso', fontsize=12)
                            ax5c.set_title(f"Solicitudes Externas: Top 10 Servicios más Solicitados - {titulo_mes} - {sufijo_sede}", 
                                          fontsize=14, fontweight='bold')
                            
                            max_cant = conteo_servicios['Cantidad'].max() if len(conteo_servicios) > 0 else 1
                            for i, (bar, row) in enumerate(zip(bars, conteo_servicios.itertuples())):
                                width = bar.get_width()
                                ax5c.text(width + max_cant * 0.01, 
                                         bar.get_y() + bar.get_height()/2,
                                         f'{int(width)} ({row.Porcentaje:.1f}%)', 
                                         ha='left', va='center', fontsize=10, fontweight='bold')
                            
                            ax5c.set_xlim(0, max_cant * 1.18)
                            
                            plt.tight_layout()
                            st.pyplot(fig5c)
                            
                            # Interpretación ampliada
                            texto_interpretacion5c = (
                                f'<strong>Análisis del Top 10 de servicios - {titulo_mes}:</strong> '
                                f'Se analizaron <strong>{total_periodo}</strong> solicitudes en el período seleccionado. '
                            )
                            
                            if len(conteo_servicios) > 0:
                                top_etiqueta = conteo_servicios.iloc[0]['Etiqueta']
                                top_cant = conteo_servicios.iloc[0]['Cantidad']
                                top_pct = conteo_servicios.iloc[0]['Porcentaje']
                                texto_interpretacion5c += (
                                    f'El servicio más solicitado es <span class="stat">"{str(top_etiqueta)[:80]}"</span> con '
                                    f'<strong>{int(top_cant)}</strong> solicitudes (<span class="stat">{top_pct:.1f}%</span> del total). '
                                )
                                
                                total_top10 = conteo_servicios['Cantidad'].sum()
                                pct_top10 = (total_top10 / total_periodo * 100) if total_periodo > 0 else 0
                                texto_interpretacion5c += (
                                    f'Los 10 servicios más solicitados concentran el <span class="stat">{pct_top10:.1f}%</span> de las solicitudes. '
                                )
                                
                                if pct_top10 > 80:
                                    texto_interpretacion5c += f'Esta <strong>alta concentración</strong> indica que la demanda se enfoca en un grupo reducido de servicios, lo que puede facilitar la especialización pero también representa un <strong>riesgo de dependencia</strong>.'
                                elif pct_top10 > 50:
                                    texto_interpretacion5c += f'Existe una <strong>concentración moderada</strong>, con margen para ampliar la diversidad de servicios ofrecidos.'
                                else:
                                    texto_interpretacion5c += f'La demanda está <strong>bastante diversificada</strong> entre múltiples servicios, reflejando una atención amplia.'
                                
                                # Distribución de los 10 servicios
                                if len(conteo_servicios) >= 5:
                                    top5_cant = conteo_servicios.head(5)['Cantidad'].sum()
                                    pct_top5 = top5_cant / total_periodo * 100
                                    texto_interpretacion5c += f'<br><strong>Distribución acumulada:</strong> El Top 5 de servicios acumula el <span class="stat">{pct_top5:.1f}%</span> de las solicitudes, mientras que los servicios 6-10 suman el <span class="stat">{pct_top10 - pct_top5:.1f}%</span> restante.'
                            
                            st.markdown(generar_interpretacion("Interpretación", texto_interpretacion5c), unsafe_allow_html=True)
                        else:
                            st.info(f"No hay datos de servicios para el mes {titulo_mes}")
                    else:
                        st.info("No hay datos de servicios para mostrar por mes")
                    st.markdown('</div>', unsafe_allow_html=True)

            # ======================== GRÁFICO 5D: DISTRIBUCIÓN DE ESTADOS POR PROCESO ========================
            if 'proceso' in df_externas_filtrado.columns and 'estado' in df_externas_filtrado.columns:
                with st.container():
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📊 Solicitudes Externas: Distribución de Estados por Proceso")
                    
                    agrupacion_ep = st.radio(
                        "Agrupar por:",
                        options=["Total", "Día", "Semana", "Mes"],
                        horizontal=True,
                        index=0,
                        key="agrupacion_estado_proceso"
                    )
                    
                    df_ext_ep = df_externas_filtrado.copy()
                    
                    top_procesos_ep = df_ext_ep['proceso'].value_counts().head(10).index.tolist()
                    df_ext_ep_top = df_ext_ep[df_ext_ep['proceso'].isin(top_procesos_ep)].copy()
                    
                    if len(df_ext_ep_top) > 0:
                        # CASO ESPECIAL: AGRUPACIÓN POR MES
                        if agrupacion_ep == "Mes":
                            df_ext_ep_top['periodo'] = df_ext_ep_top['fechaRegistroFormulario'].dt.to_period('M').dt.start_time
                            
                            meses_unicos_ep = sorted(df_ext_ep_top['periodo'].dropna().unique())
                            estados_unicos_mes = sorted(df_ext_ep_top['estado'].dropna().unique())
                            
                            totales_por_proceso = df_ext_ep_top.groupby('proceso').size().sort_values(ascending=True)
                            procesos_ordenados = totales_por_proceso.index.tolist()
                            
                            n_procesos = len(procesos_ordenados)
                            n_meses = len(meses_unicos_ep)
                            
                            altura_total_disponible = 0.8
                            ancho_barra = altura_total_disponible / n_meses if n_meses > 0 else altura_total_disponible
                            
                            colores_estados_mes = colores_diferenciados[:len(estados_unicos_mes)]
                            while len(colores_estados_mes) < len(estados_unicos_mes):
                                colores_estados_mes = colores_estados_mes + colores_diferenciados
                            colores_estados_mes = colores_estados_mes[:len(estados_unicos_mes)]
                            dict_color_estado = {estado: colores_estados_mes[i] for i, estado in enumerate(estados_unicos_mes)}
                            
                            # Figura con espacio reservado a la derecha para las leyendas
                            fig5d, ax5d = plt.subplots(figsize=(18, max(7, n_procesos * 0.8)))
                            fig5d.subplots_adjust(right=0.72)
                            
                            y_pos = np.arange(n_procesos)
                            
                            # Calcular el máximo total para ajustar el límite del eje X
                            max_total = 0
                            for p_idx, proceso in enumerate(procesos_ordenados):
                                df_proceso = df_ext_ep_top[df_ext_ep_top['proceso'] == proceso]
                                for mes in meses_unicos_ep:
                                    total_celda = (df_proceso['periodo'] == mes).sum()
                                    if total_celda > max_total:
                                        max_total = total_celda
                            
                            # Dibujar las barras y añadir etiquetas de mes
                            for p_idx, proceso in enumerate(procesos_ordenados):
                                df_proceso = df_ext_ep_top[df_ext_ep_top['proceso'] == proceso]
                                
                                for m_idx, mes in enumerate(meses_unicos_ep):
                                    df_celda = df_proceso[df_proceso['periodo'] == mes]
                                    if len(df_celda) == 0:
                                        continue
                                    
                                    offset = (m_idx - (n_meses - 1) / 2) * ancho_barra
                                    left = 0
                                    for estado in estados_unicos_mes:
                                        valor = (df_celda['estado'] == estado).sum()
                                        if valor > 0:
                                            ax5d.barh(p_idx + offset, valor, left=left, height=ancho_barra,
                                                     color=dict_color_estado[estado], edgecolor='white', linewidth=0.8)
                                            if valor >= 2:
                                                ax5d.text(left + valor/2, p_idx + offset, f'{int(valor)}',
                                                         ha='center', va='center', fontsize=7, 
                                                         fontweight='bold', color='white')
                                            left += valor
                                    
                                    total_celda = len(df_celda)
                                    if total_celda > 0:
                                        # Etiqueta del total al final de la barra
                                        ax5d.text(total_celda + 0.3, p_idx + offset, f'{total_celda}',
                                                 ha='left', va='center', fontsize=8, 
                                                 fontweight='bold', color='black')
                                        
                                        # Etiqueta del mes a la izquierda de la barra
                                        mes_str = mes.strftime('%Y-%m')
                                        ax5d.text(-max_total * 0.02 if max_total > 0 else -0.5, 
                                                 p_idx + offset, mes_str,
                                                 ha='right', va='center', fontsize=7,
                                                 color='#5b21b6', fontweight='bold',
                                                 bbox=dict(boxstyle="round,pad=0.15", 
                                                          facecolor='#f8f4ff', 
                                                          edgecolor='#c4b5fd', 
                                                          alpha=0.9,
                                                          linewidth=0.8))
                            
                            etiquetas_proc = [f"{str(p)[:45]}{'...' if len(str(p)) > 45 else ''}" for p in procesos_ordenados]
                            ax5d.set_yticks(y_pos)
                            ax5d.set_yticklabels(etiquetas_proc, fontsize=10)
                            
                            ax5d.set_xlabel('Cantidad de Solicitudes', fontsize=12)
                            ax5d.set_ylabel('Proceso', fontsize=12)
                            ax5d.set_title(f'Solicitudes Externas: Distribución de Estados por Proceso - Agrupado por Mes - {sufijo_sede}',
                                          fontsize=14, fontweight='bold')
                            
                            # ===== LEYENDA 1: ESTADOS (colores de las barras) =====
                            legend_estados = [Patch(facecolor=dict_color_estado[estado], edgecolor='white', 
                                                    label=str(estado)[:35])
                                              for estado in estados_unicos_mes]
                            legend1 = ax5d.legend(handles=legend_estados, 
                                                 loc='upper left', 
                                                 bbox_to_anchor=(1.02, 1.0), 
                                                 fontsize=9, 
                                                 title='Estados (color de barra)', 
                                                 title_fontsize=10,
                                                 framealpha=0.95, 
                                                 edgecolor='#7c3aed',
                                                 borderpad=1)
                            ax5d.add_artist(legend1)
                            
                            # ===== LEYENDA 2: MESES (etiquetas de la izquierda) =====
                            legend_meses = [Patch(facecolor='#f8f4ff', edgecolor='#c4b5fd', 
                                                  label=m.strftime('%Y-%m'))
                                            for m in meses_unicos_ep]
                            legend2 = ax5d.legend(handles=legend_meses, 
                                                 loc='upper left', 
                                                 bbox_to_anchor=(1.02, 0.55), 
                                                 fontsize=9,
                                                 title='Meses (etiqueta izquierda)', 
                                                 title_fontsize=10,
                                                 framealpha=0.95, 
                                                 edgecolor='#7c3aed',
                                                 borderpad=1)
                            ax5d.add_artist(legend2)
                            
                            # Ajustar el límite del eje X para dejar espacio a las etiquetas de mes a la izquierda
                            limite_izq = -max_total * 0.10 if max_total > 0 else -1
                            limite_der = max_total * 1.18 if max_total > 0 else 10
                            ax5d.set_xlim(limite_izq, limite_der)
                            
                            # Nota explicativa en la esquina
                            ax5d.text(0.02, 0.98, "Cada barra representa un mes (etiqueta a la izquierda)", 
                                     transform=ax5d.transAxes, fontsize=8, style='italic',
                                     va='top', ha='left', color='#6b7280',
                                     bbox=dict(boxstyle="round,pad=0.3", facecolor='#f9fafb', 
                                              edgecolor='#e5e7eb', alpha=0.9))
                            
                            st.pyplot(fig5d, use_container_width=True)
                            
                            # Interpretación ampliada
                            total_analizado = len(df_ext_ep_top)
                            total_general = len(df_externas_filtrado)
                            pct_analizado = total_analizado/total_general*100
                            
                            estado_comun_serie = df_ext_ep_top['estado'].value_counts()
                            estado_comun = estado_comun_serie.index[0]
                            estado_comun_count = estado_comun_serie.iloc[0]
                            pct_estado_comun = estado_comun_count / total_analizado * 100
                            
                            proceso_top_serie = df_ext_ep_top['proceso'].value_counts()
                            proceso_mas_volumen = proceso_top_serie.index[0]
                            proceso_mas_count = proceso_top_serie.iloc[0]
                            
                            proceso_mas_concentrado = None
                            max_concentracion = 0
                            for proc in procesos_ordenados:
                                df_p = df_ext_ep_top[df_ext_ep_top['proceso'] == proc]
                                if len(df_p) > 0:
                                    estado_top_p = df_p['estado'].value_counts().iloc[0]
                                    concentracion = estado_top_p / len(df_p) * 100
                                    if concentracion > max_concentracion:
                                        max_concentracion = concentracion
                                        proceso_mas_concentrado = proc
                            
                            estado_menos = estado_comun_serie.index[-1]
                            estado_menos_count = estado_comun_serie.iloc[-1]
                            
                            texto_interpretacion5d = (
                                f'<strong>Cobertura del análisis:</strong> El gráfico muestra la distribución de estados en los '
                                f'<strong>{n_procesos}</strong> procesos más relevantes durante <strong>{n_meses}</strong> meses. '
                                f'Estos procesos representan <strong>{total_analizado}</strong> de <strong>{total_general}</strong> '
                                f'solicitudes externas (<span class="stat">{pct_analizado:.1f}%</span> del total).<br>'
                                f'<strong>Estado dominante:</strong> El estado más común es <span class="stat">"{estado_comun}"</span> '
                                f'con <strong>{estado_comun_count}</strong> registros (<span class="stat">{pct_estado_comun:.1f}%</span> de los procesos analizados), '
                                f'mientras que el menos frecuente es <span class="stat">"{estado_menos}"</span> con <strong>{estado_menos_count}</strong> registros.<br>'
                                f'<strong>Proceso más activo:</strong> El proceso con mayor volumen es <span class="stat">"{str(proceso_mas_volumen)[:50]}"</span> '
                                f'con <strong>{proceso_mas_count}</strong> solicitudes. '
                            )
                            
                            if proceso_mas_concentrado is not None:
                                texto_interpretacion5d += (
                                    f'El proceso con mayor concentración en un solo estado es <span class="stat">"{str(proceso_mas_concentrado)[:50]}"</span>, '
                                    f'con un <strong>{max_concentracion:.1f}%</strong> de sus registros en un único estado. '
                                )
                                if max_concentracion > 80:
                                    texto_interpretacion5d += 'Esta <strong>alta concentración</strong> sugiere un flujo muy homogéneo en este proceso, o bien un posible <strong>sesgo en el registro de estados</strong> que valdría la pena revisar.'
                            
                            st.markdown(generar_interpretacion("Interpretación", texto_interpretacion5d), unsafe_allow_html=True)
                        
                        # OTROS CASOS: TOTAL / DÍA / SEMANA
                        else:
                            if agrupacion_ep == "Total":
                                pivot_ep = df_ext_ep_top.groupby(['proceso', 'estado']).size().unstack(fill_value=0)
                                pivot_ep = pivot_ep.loc[pivot_ep.sum(axis=1).sort_values(ascending=True).index]
                                etiquetas_y = [f"{str(p)[:50]}{'...' if len(str(p)) > 50 else ''}" for p in pivot_ep.index]
                                titulo_periodo = "Total"
                            elif agrupacion_ep == "Día":
                                df_ext_ep_top['periodo'] = df_ext_ep_top['fechaRegistroFormulario'].dt.date
                                pivot_ep = df_ext_ep_top.groupby(['proceso', 'periodo', 'estado']).size().unstack(fill_value=0)
                                nuevas_etiquetas = []
                                for idx in pivot_ep.index:
                                    proceso, periodo = idx
                                    periodo_str = periodo.strftime('%Y-%m-%d') if hasattr(periodo, 'strftime') else str(periodo)
                                    nuevas_etiquetas.append(f"{str(proceso)[:35]} | {periodo_str}")
                                pivot_ep.index = nuevas_etiquetas
                                pivot_ep = pivot_ep.loc[pivot_ep.sum(axis=1).sort_values(ascending=True).index]
                                etiquetas_y = [f"{str(e)[:65]}{'...' if len(str(e)) > 65 else ''}" for e in pivot_ep.index]
                                titulo_periodo = "Agrupado por Día"
                            elif agrupacion_ep == "Semana":
                                df_ext_ep_top['periodo'] = df_ext_ep_top['fechaRegistroFormulario'].dt.to_period('W').dt.start_time
                                pivot_ep = df_ext_ep_top.groupby(['proceso', 'periodo', 'estado']).size().unstack(fill_value=0)
                                nuevas_etiquetas = []
                                for idx in pivot_ep.index:
                                    proceso, periodo = idx
                                    periodo_str = periodo.strftime('%Y-%m-%d') if hasattr(periodo, 'strftime') else str(periodo)
                                    nuevas_etiquetas.append(f"{str(proceso)[:35]} | {periodo_str}")
                                pivot_ep.index = nuevas_etiquetas
                                pivot_ep = pivot_ep.loc[pivot_ep.sum(axis=1).sort_values(ascending=True).index]
                                etiquetas_y = [f"{str(e)[:65]}{'...' if len(str(e)) > 65 else ''}" for e in pivot_ep.index]
                                titulo_periodo = "Agrupado por Semana"
                            
                            fig5d, ax5d = plt.subplots(figsize=(14, max(7, len(pivot_ep) * 0.55)))
                            
                            estados_unicos_ep = pivot_ep.columns.tolist()
                            colores_estados_ep = colores_diferenciados[:len(estados_unicos_ep)]
                            while len(colores_estados_ep) < len(estados_unicos_ep):
                                colores_estados_ep = colores_estados_ep + colores_diferenciados
                            colores_estados_ep = colores_estados_ep[:len(estados_unicos_ep)]
                            
                            left = np.zeros(len(pivot_ep))
                            y_pos = np.arange(len(pivot_ep))
                            
                            for i, estado in enumerate(estados_unicos_ep):
                                valores = pivot_ep[estado].values
                                bars = ax5d.barh(y_pos, valores, left=left, 
                                                label=str(estado)[:35], color=colores_estados_ep[i],
                                                edgecolor='white', linewidth=1.2)
                                for j, v in enumerate(valores):
                                    if v > 0:
                                        ax5d.text(left[j] + v/2, y_pos[j], f'{int(v)}', 
                                                 ha='center', va='center', fontsize=8, 
                                                 fontweight='bold', color='white')
                                left += valores
                            
                            ax5d.set_yticks(y_pos)
                            ax5d.set_yticklabels(etiquetas_y, fontsize=9)
                            
                            for j, total in enumerate(left):
                                ax5d.text(total + 0.3, y_pos[j], f'{int(total)}', 
                                         ha='left', va='center', fontsize=9, 
                                         fontweight='bold', color='black')
                            
                            ax5d.set_xlabel('Cantidad de Solicitudes', fontsize=12)
                            ax5d.set_ylabel('Proceso', fontsize=12)
                            ax5d.set_title(f'Solicitudes Externas: Distribución de Estados por Proceso - {titulo_periodo} - {sufijo_sede}', 
                                          fontsize=14, fontweight='bold')
                            
                            ax5d.legend(loc='lower right', fontsize=10, title='Estados', title_fontsize=11,
                                       framealpha=0.95, edgecolor='#7c3aed')
                            
                            max_total = left.max() if len(left) > 0 else 1
                            ax5d.set_xlim(0, max_total * 1.12)
                            
                            plt.tight_layout()
                            st.pyplot(fig5d)
                            
                            # Interpretación ampliada
                            total_analizado = int(pivot_ep.values.sum())
                            total_general = len(df_externas_filtrado)
                            pct_analizado = total_analizado/total_general*100
                            n_filas = len(pivot_ep)
                            
                            estado_comun_serie = df_ext_ep_top['estado'].value_counts()
                            estado_comun = estado_comun_serie.index[0]
                            estado_comun_count = estado_comun_serie.iloc[0]
                            pct_estado_comun = estado_comun_count / total_analizado * 100
                            
                            texto_interpretacion5d = (
                                f'<strong>Cobertura del análisis ({titulo_periodo}):</strong> Se analizaron <strong>{n_filas}</strong> registros '
                                f'(combinación proceso{" + periodo" if agrupacion_ep != "Total" else ""}) que representan '
                                f'<strong>{total_analizado}</strong> de <strong>{total_general}</strong> solicitudes externas '
                                f'(<span class="stat">{pct_analizado:.1f}%</span> del total).<br>'
                                f'<strong>Estado dominante:</strong> El estado más común es <span class="stat">"{estado_comun}"</span> '
                                f'con <strong>{estado_comun_count}</strong> registros (<span class="stat">{pct_estado_comun:.1f}%</span> del total analizado).'
                            )
                            
                            if agrupacion_ep != "Total":
                                texto_interpretacion5d += (
                                    f'<br><strong>Valor del desglose temporal:</strong> Al agrupar por {titulo_periodo.lower()}, se puede observar la '
                                    f'<strong>evolución de cada proceso a lo largo del tiempo</strong> y detectar si ciertos estados se acumulan '
                                    f'en períodos específicos, lo cual es clave para la planeación operativa.'
                                )
                            
                            st.markdown(generar_interpretacion("Interpretación", texto_interpretacion5d), unsafe_allow_html=True)
                    else:
                        st.info("No hay datos de procesos para mostrar")
                    st.markdown('</div>', unsafe_allow_html=True)

            # ======================== GRÁFICO 5E: MATRIZ DE CALOR ========================
            if 'proceso' in df_externas_filtrado.columns:
                with st.container():
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📊 Solicitudes Externas: Matriz de Calor - Procesos vs Meses")
                    
                    df_ext_hm = df_externas_filtrado.copy()
                    df_ext_hm['mes_str'] = df_ext_hm['fechaRegistroFormulario'].dt.to_period('M').dt.strftime('%Y-%m')
                    
                    top_procesos_hm = df_ext_hm['proceso'].value_counts().head(10).index.tolist()
                    df_hm = df_ext_hm[df_ext_hm['proceso'].isin(top_procesos_hm)]
                    
                    pivot_hm = df_hm.groupby(['proceso', 'mes_str']).size().unstack(fill_value=0)
                    
                    if len(pivot_hm) > 0:
                        fig5e, ax5e = plt.subplots(figsize=(14, max(6, len(pivot_hm) * 0.5)))
                        
                        im = ax5e.imshow(pivot_hm.values, cmap='YlOrRd', aspect='auto')
                        
                        ax5e.set_xticks(range(len(pivot_hm.columns)))
                        ax5e.set_xticklabels(pivot_hm.columns, rotation=45, ha='right', fontsize=9)
                        
                        ax5e.set_yticks(range(len(pivot_hm.index)))
                        etiquetas_y_hm = [f"{str(p)[:50]}{'...' if len(str(p)) > 50 else ''}" for p in pivot_hm.index]
                        ax5e.set_yticklabels(etiquetas_y_hm, fontsize=9)
                        
                        ax5e.set_xlabel('Mes', fontsize=12)
                        ax5e.set_ylabel('Proceso', fontsize=12)
                        ax5e.set_title(f"Solicitudes Externas: Matriz de Calor - Procesos vs Meses - {sufijo_sede}", 
                                      fontsize=14, fontweight='bold')
                        
                        for i in range(len(pivot_hm.index)):
                            for j in range(len(pivot_hm.columns)):
                                valor = pivot_hm.values[i, j]
                                if valor > 0:
                                    text_color = 'white' if valor > pivot_hm.values.max() * 0.6 else 'black'
                                    ax5e.text(j, i, f'{int(valor)}', ha='center', va='center', 
                                             fontsize=9, fontweight='bold', color=text_color)
                        
                        cbar = plt.colorbar(im, ax=ax5e, shrink=0.8)
                        cbar.set_label('Cantidad de Solicitudes', fontsize=10)
                        
                        plt.tight_layout()
                        st.pyplot(fig5e)
                        
                        # Interpretación ampliada
                        total_hm = int(pivot_hm.values.sum())
                        max_valor = pivot_hm.values.max()
                        idx_max = np.unravel_index(pivot_hm.values.argmax(), pivot_hm.values.shape)
                        proceso_max = pivot_hm.index[idx_max[0]]
                        mes_max = pivot_hm.columns[idx_max[1]]
                        
                        pct_max = max_valor / total_hm * 100 if total_hm > 0 else 0
                        
                        texto_interpretacion5e = (
                            f'<strong>Visión general:</strong> La matriz de calor concentra <strong>{total_hm}</strong> solicitudes externas '
                            f'en los <strong>{len(pivot_hm.index)}</strong> procesos más relevantes a lo largo de <strong>{len(pivot_hm.columns)}</strong> meses.<br>'
                            f'<strong>Punto de máxima concentración:</strong> El proceso <span class="stat">"{str(proceso_max)[:50]}"</span> durante el mes '
                            f'<span class="stat">{mes_max}</span> registró <strong>{int(max_valor)}</strong> solicitudes, lo que representa el '
                            f'<span class="stat">{pct_max:.1f}%</span> del total analizado. '
                        )
                        
                        if pct_max > 25:
                            texto_interpretacion5e += 'Esta <strong>alta concentración</strong> en un solo punto sugiere un evento puntual o una demanda estacional específica que merece análisis detallado.'
                        elif pct_max > 10:
                            texto_interpretacion5e += 'Esta concentración es <strong>moderada</strong> y podría reflejar patrones estacionales recurrentes.'
                        else:
                            texto_interpretacion5e += 'La concentración es <strong>baja</strong>, indicando una distribución relativamente uniforme de la demanda.'
                        
                        st.markdown(generar_interpretacion("Interpretación", texto_interpretacion5e), unsafe_allow_html=True)
                    else:
                        st.info("No hay datos suficientes para mostrar la matriz de calor")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay datos de solicitudes externas disponibles para las ciudades seleccionadas.")
    
    # ======================== EXPORTACIÓN A EXCEL ========================
    st.divider()
    st.markdown("### 📥 Exportar Reporte Completo")
    
    def preparar_datos_exportacion(df_export, df_graf1_data, estado_gestion_data, pendientes_data, 
                                   ordenes_area_data, estados_serv_data, entidad_data, 
                                   df_ext_proceso_mes_export, df_ext_top_serv_export, 
                                   df_ext_estado_proceso_export):
        datos_detalle = df_export[['Estado', 'Estado_Gestion', 'Solicitado', 'Doc.', 'Paciente', 'Entidad', 'Area', 'Cups', 'Servicio', 'Observación']].copy()
        datos_detalle['Solicitado'] = datos_detalle['Solicitado'].dt.strftime('%Y-%m-%d %H:%M')
        
        resumen_data = []
        
        total_generadas = df_graf1_data['Generadas'].sum()
        total_gestionadas = df_graf1_data['Gestionadas'].sum()
        pct_gestionadas = (total_gestionadas / total_generadas * 100) if total_generadas > 0 else 0
        resumen_data.append(['Gráfico 1', 'Órdenes Generadas vs Gestionadas', f'Total generadas: {int(total_generadas)}', ''])
        resumen_data.append(['', '', f'Total gestionadas: {int(total_gestionadas)} ({pct_gestionadas:.1f}%)', ''])
        resumen_data.append(['', '', f'Pendientes: {int(total_generadas - total_gestionadas)} ({100-pct_gestionadas:.1f}%)', ''])
        resumen_data.append(['', '', '', ''])
        
        if len(estado_gestion_data) > 0:
            total_estados = estado_gestion_data['Cantidad'].sum()
            for _, row in estado_gestion_data.iterrows():
                resumen_data.append(['Gráfico 2', 'Gestión de autorizaciones', f'{row["Estado"]}: {row["Cantidad"]} ({row["Cantidad"]/total_estados*100:.1f}%)', ''])
        resumen_data.append(['', '', '', ''])
        
        if pendientes_data is not None and len(pendientes_data) > 0:
            total_pend = pendientes_data['Cantidad'].sum()
            for _, row in pendientes_data.iterrows():
                resumen_data.append(['Gráfico 3', 'Pendientes por Área', f'{row["Área"]}: {row["Cantidad"]} ({row["Cantidad"]/total_pend*100:.1f}%)', ''])
        resumen_data.append(['', '', '', ''])
        
        if df_ext_proceso_mes_export is not None and len(df_ext_proceso_mes_export) > 0:
            for _, row in df_ext_proceso_mes_export.iterrows():
                resumen_data.append(['Gráfico 5B', f'Solicitudes Externas: Procesos por Mes - {row["mes_str"]}', 
                                    f'{row["proceso"]}: {row["Cantidad"]}', ''])
            resumen_data.append(['', '', '', ''])
        
        if df_ext_top_serv_export is not None and len(df_ext_top_serv_export) > 0:
            for _, row in df_ext_top_serv_export.iterrows():
                resumen_data.append(['Gráfico 5C', f'Solicitudes Externas: Top 10 Servicios - {row["mes_str"]}', 
                                    f'{row["servicio"]}: {row["cantidad"]} ({row["porcentaje"]:.1f}%)', ''])
            resumen_data.append(['', '', '', ''])
        
        if df_ext_estado_proceso_export is not None and len(df_ext_estado_proceso_export) > 0:
            for _, row in df_ext_estado_proceso_export.iterrows():
                resumen_data.append(['Gráfico 5D', f'Solicitudes Externas: Estados por Proceso - {str(row["proceso"])[:40]}', 
                                    f'{row["estado"]}: {row["Cantidad"]}', ''])
            resumen_data.append(['', '', '', ''])
        
        if len(ordenes_area_data) > 0:
            total_ord = ordenes_area_data['Cantidad'].sum()
            for _, row in ordenes_area_data.iterrows():
                resumen_data.append(['Gráfico 6', 'Órdenes por Área', f'{row["Área"]}: {row["Cantidad"]} ({row["Cantidad"]/total_ord*100:.1f}%)', ''])
        resumen_data.append(['', '', '', ''])
        
        if len(estados_serv_data) > 0:
            total_est = estados_serv_data['Cantidad'].sum()
            for _, row in estados_serv_data.iterrows():
                resumen_data.append(['Gráfico 7', 'Estados de Servicios', f'{row["Estado"]}: {row["Cantidad"]} ({row["Cantidad"]/total_est*100:.1f}%)', ''])
        resumen_data.append(['', '', '', ''])
        
        if len(entidad_data) > 0:
            total_ent = entidad_data['Cantidad'].sum()
            for _, row in entidad_data.iterrows():
                resumen_data.append(['Gráfico 8', 'Distribución por Entidad', f'{row["Entidad"]}: {row["Cantidad"]} ({row["Cantidad"]/total_ent*100:.1f}%)', ''])
        
        resumen_df = pd.DataFrame(resumen_data, columns=['Gráfico', 'Categoría', 'Detalle', 'Observación'])
        
        return datos_detalle, resumen_df
    
    if st.button("📥 Exportar Reporte a Excel", use_container_width=True, type="primary"):
        try:
            df_export = df_filtrado.copy()
            
            estado_gestion_data = estado_gestion_counts.copy()
            pendientes_data = pendientes_por_area.copy() if pendientes_por_area is not None and len(pendientes_por_area) > 0 else pd.DataFrame()
            ordenes_area_data = ordenes_por_area.copy() if len(ordenes_por_area) > 0 else pd.DataFrame()
            estados_serv_data = estados_counts.copy()
            entidad_data = entidad_counts.copy()
            
            df_ext_proceso_mes_export = None
            df_ext_top_serv_export = None
            df_ext_estado_proceso_export = None
            
            if df_externas_filtrado is not None and len(df_externas_filtrado) > 0:
                if 'proceso' in df_externas_filtrado.columns and 'fechaRegistroFormulario' in df_externas_filtrado.columns:
                    df_ext_mes_exp = df_externas_filtrado.copy()
                    df_ext_mes_exp['mes_str'] = df_ext_mes_exp['fechaRegistroFormulario'].dt.to_period('M').dt.strftime('%Y-%m')
                    df_ext_proceso_mes_export = df_ext_mes_exp.groupby(['mes_str', 'proceso']).size().reset_index(name='Cantidad')
                
                if 'servicio' in df_externas_filtrado.columns and 'fechaRegistroFormulario' in df_externas_filtrado.columns:
                    df_ext_serv_exp = df_externas_filtrado.copy()
                    df_ext_serv_exp['mes_str'] = df_ext_serv_exp['fechaRegistroFormulario'].dt.to_period('M').dt.strftime('%Y-%m')
                    top_serv_rows = []
                    for mes in sorted(df_ext_serv_exp['mes_str'].dropna().unique()):
                        df_mes_serv = df_ext_serv_exp[df_ext_serv_exp['mes_str'] == mes]
                        if len(df_mes_serv) > 0:
                            conteo = df_mes_serv['servicio'].value_counts().head(10)
                            for servicio, cantidad in conteo.items():
                                top_serv_rows.append({
                                    'mes_str': mes,
                                    'servicio': servicio,
                                    'cantidad': cantidad,
                                    'porcentaje': (cantidad / len(df_mes_serv) * 100) if len(df_mes_serv) > 0 else 0
                                })
                    if len(top_serv_rows) > 0:
                        df_ext_top_serv_export = pd.DataFrame(top_serv_rows)
                
                if 'proceso' in df_externas_filtrado.columns and 'estado' in df_externas_filtrado.columns:
                    top_procesos_exp = df_externas_filtrado['proceso'].value_counts().head(10).index.tolist()
                    df_ext_ep_exp = df_externas_filtrado[df_externas_filtrado['proceso'].isin(top_procesos_exp)]
                    df_ext_estado_proceso_export = df_ext_ep_exp.groupby(['proceso', 'estado']).size().reset_index(name='Cantidad')
            
            datos_detalle, resumen_graficos = preparar_datos_exportacion(
                df_export, df_graf1, estado_gestion_data, pendientes_data, 
                ordenes_area_data, estados_serv_data, entidad_data,
                df_ext_proceso_mes_export, df_ext_top_serv_export, df_ext_estado_proceso_export
            )
            
            output = BytesIO()
            wb = Workbook()
            
            ws1 = wb.active
            ws1.title = "Datos Detallados"
            
            header_fill = PatternFill(start_color="7c3aed", end_color="7c3aed", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for r_idx, row in enumerate(dataframe_to_rows(datos_detalle, index=False, header=True), 1):
                for c_idx, value in enumerate(row, 1):
                    cell = ws1.cell(row=r_idx, column=c_idx, value=value)
                    if r_idx == 1:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    cell.border = thin_border
            
            for column in ws1.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_length = min(max_length + 2, 50)
                ws1.column_dimensions[column_letter].width = adjusted_length
            
            ws2 = wb.create_sheet("Resumen Gráficos")
            for r_idx, row in enumerate(dataframe_to_rows(resumen_graficos, index=False, header=True), 1):
                for c_idx, value in enumerate(row, 1):
                    cell = ws2.cell(row=r_idx, column=c_idx, value=value)
                    if r_idx == 1:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    cell.border = thin_border
            
            for column in ws2.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_length = min(max_length + 2, 50)
                ws2.column_dimensions[column_letter].width = adjusted_length
            
            if df_externas_filtrado is not None and len(df_externas_filtrado) > 0:
                ws3 = wb.create_sheet("Solicitudes Externas")
                columnas_ext_export = ['fechaRegistroFormulario', 'ciudad', 'proceso', 'idPaciente', 
                                      'nombrePaciente', 'entidad', 'servicio', 'estado', 'Clasificación']
                
                cols_disponibles = [c for c in columnas_ext_export[:-1] if c in df_externas_filtrado.columns]
                if len(cols_disponibles) > 0:
                    df_ext_export_sheet = df_externas_filtrado[cols_disponibles].copy()
                    df_ext_export_sheet['Clasificación'] = df_ext_export_sheet['estado'].apply(clasificar_gestion_externa) if 'estado' in df_ext_export_sheet.columns else ''
                    
                    if 'fechaRegistroFormulario' in df_ext_export_sheet.columns:
                        df_ext_export_sheet['fechaRegistroFormulario'] = pd.to_datetime(df_ext_export_sheet['fechaRegistroFormulario']).dt.strftime('%Y-%m-%d')
                    
                    for r_idx, row in enumerate(dataframe_to_rows(df_ext_export_sheet, index=False, header=True), 1):
                        for c_idx, value in enumerate(row, 1):
                            cell = ws3.cell(row=r_idx, column=c_idx, value=value)
                            if r_idx == 1:
                                cell.fill = header_fill
                                cell.font = header_font
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                            cell.border = thin_border
                    
                    for column in ws3.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_length = min(max_length + 2, 50)
                        ws3.column_dimensions[column_letter].width = adjusted_length
            
            wb.save(output)
            output.seek(0)
            
            st.download_button(
                label="⬇️ Descargar Excel",
                data=output,
                file_name=f"Reporte_Portafolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.success("✅ Reporte generado correctamente. Haz clic en 'Descargar Excel' para guardar el archivo.")
            
        except Exception as e:
            st.error(f"❌ Error al exportar: {e}")
            import traceback
            st.error(traceback.format_exc())
    
    st.divider()
    st.caption(f"🔍 Filtros aplicados: {len(estados_seleccionados)} estados, {len(entidades_seleccionadas)} entidades, {len(areas_seleccionadas)} áreas, {len(sedes_seleccionadas)} sedes")
    st.caption(f"📅 Rango de fechas: {fecha_inicio} - {fecha_fin}")
        
else:
    st.info("👈 Carga un archivo Excel que contenga las hojas 'Datos', 'Portafolio' y 'Solicitudes Externas' para comenzar a visualizar el dashboard")
    
    with st.expander("📚 Ver Formato Esperado del Archivo", expanded=False):
        st.markdown("""
        ### El archivo Excel debe contener tres hojas:
        
        **Hoja 1: 'Datos'** - Debe contener las siguientes columnas:
        - Tag, Solicitado, Auditado, Sede, Doc., Paciente, Edad, Genero, Diag., Entidad, Grupo Atención, Servicio, Cups, Radicación, Radicado, Autorizado, Autorización, Vence, Entregado, Servicio, Programado, Responsable, Estado, Observación, Prioridad, idOrden, idIndigo
        
        **Hoja 2: 'Portafolio'** - Debe contener las siguientes columnas:
        - CUPS, codIPS, descrCodIPS, codREPS, A, UNIDAD EJECUTORA, Codigo unidad, Sede_Portafolio
        
        **Hoja 3: 'Solicitudes Externas'** - Debe contener las siguientes columnas:
        - fechaRegistroFormulario, ciudad, proceso, idPaciente, nombrePaciente, entidad, servicio, cups, estado, fechaEntregaProceso, motivoCancelacion
        """)

st.divider()
st.caption("💡 Tablero resumen de gestión de Autorizaciones y Programación en Tramita - Datos actualizados en tiempo real")
