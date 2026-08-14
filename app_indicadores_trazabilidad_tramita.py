import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
from io import BytesIO

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Portafolio",
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
    </style>
""", unsafe_allow_html=True)

# Configurar estilo de seaborn
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['legend.fontsize'] = 11

# Datos estáticos del portafolio base
PORTAFOLIO_BASE = [
    ("221401", "221401", "NASOSINUSCOPIA", "209_CIRUGÍA OTORRINOLARINGOLOGÍA", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("311401", "311401", "PUNCIÓN (ASPIRACIÓN) TRANSTRÁQUEAL VÍA PERCUTÁNEA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("311402", "311402", "PUNCIÓN (ASPIRACIÓN) TRANSTRÁQUEAL VÍA ENDOSCÓPICA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332201", "332201", "BRONCOSCOPIA CON LAVADO BRONQUIAL", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332202", "332202", "BRONCOSCOPIA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332203", "332203", "BRONCOSCOPIA CON LAVADO BRONCOALVEOLAR", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332204", "332204", "BRONCOSCOPIA CON CEPILLADO", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("332601", "332601", "BIOPSIA CERRADA DE PULMÓN VÍA PERCUTÁNEA", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("441302", "441302", "ESOFAGOGASTRODUODENOSCOPIA [EGD] CON O SIN BIOPSIA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("452301", "452301", "COLONOSCOPIA TOTAL", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("452305", "452305", "COLONOSCOPIA TOTAL CON O SIN BIOPSIA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("452401", "452401", "SIGMOIDOSCOPIA FLEXIBLE O RIGIDA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("7DS004", "7DS004", "DERECHOS DE SALA DE PROCEDIMIENTOS ENDOSCOPICOS", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882112", "882112", "ECOGRAFÍA DOPPLER DE VASOS DEL CUELLO", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882132", "882132", "ECOGRAFÍA DOPPLER DE OTROS VASOS PERIFÉRICOS DEL CUELLO", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882308", "882308", "ECOGRAFÍA DOPPLER DE VASOS ARTERIALES DE MIEMBROS INFERIORES", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882309", "882309", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBROS SUPERIORES", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882316", "882316", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBRO SUPERIOR", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882317", "882317", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBROS INFERIORES", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("882318", "882318", "ECOGRAFÍA DOPPLER DE VASOS VENOSOS DE MIEMBRO INFERIOR", "744_IMÁGENES DIAGNOSTICAS - IONIZANTES", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("895003", "895003", "PRUEBA DE MESA BASCULANTE", "742_DIAGNÓSTICO VASCULAR", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("895004", "895004", "MONITOREO AMBULATORIO DE PRESIÓN ARTERIAL SISTÉMICA", "742_DIAGNÓSTICO VASCULAR", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("463201", "463201", "YEYUNOSTOMÍA PERCUTÁNEA (ENDOSCÓPICA)", "203_CIRUGÍA GENERAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("422003", "422003", "ESOFAGOSCOPIA VÍA ORAL EXPLORATORIA O DIAGNÓSTICA SIN BIOPSIA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("422602", "422602", "BIOPSIA DE ESÓFAGO VÍA ENDOSCÓPICA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("423302", "423302", "CONTROL DE HEMORRAGIA DE ESÓFAGO VÍA ENDOSCÓPICA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("423304", "423304", "INYECCIÓN (ESCLEROSIS) DE VÁRICES ESOFÁGICAS VÍA ENDOSCÓPICA", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("434101", "434101", "LIGADURA ENDOSCÓPICA DE VÁRICES GÁSTRICAS", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("441201", "441201", "GASTROSCOPIA A TRAVÉS DE ESTOMA ARTIFICIAL", "235_CIRUGÍA GASTROINTESTINAL", True, "CARDIOLOGIA NO INVASIVA", "39"),
    ("010201", "010201", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR A TRAVÉS DE CATÉTER PREVIAMENTE IMPLANTADO", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010202", "010202", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR POR TREPANACIÓN (SIN CATÉTER)", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010203", "010203", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR A TRAVÉS DE UN RESERVORIO", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010204", "010204", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR, VÍA TRANSFONTANELAR", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010205", "010205", "PUNCIÓN (ASPIRACIÓN DE LÍQUIDO) VENTRICULAR", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010901", "010901", "PUNCIÓN SUBDURAL", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
    ("010902", "010902", "OTRA PUNCIÓN CRANEAL", "245_NEUROCIRUGÍA", True, "CIRUGIA", "36"),
]

# Crear DataFrame del portafolio base
df_portafolio_base = pd.DataFrame(PORTAFOLIO_BASE, columns=['CUPS', 'codIPS', 'descrCodIPS', 'codREPS', 'A', 'UNIDAD EJECUTORA', 'Codigo unidad'])

# Inicializar estado
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_filtrado' not in st.session_state:
    st.session_state.df_filtrado = None
if 'filtros_aplicados' not in st.session_state:
    st.session_state.filtros_aplicados = False

# Título principal
st.title("📊 Dashboard de Gestión de Portafolio")

# ======================== SECCIÓN DE CARGA (COLAPSABLE) ========================
with st.expander("📂 Cargar Archivo de Solicitudes", expanded=False):
    archivo = st.file_uploader(
        "Selecciona un archivo Excel",
        type=['xlsx', 'xls'],
        help="El archivo debe contener los campos: Tag, Solicitado, Auditado, Sede, Doc., Paciente, Edad, Genero, Diag., Entidad, Grupo Atención, Servicio, Cups, Radicación, Radicado, Autorizado, Autorización, Vence, Entregado, Servicio, Programado, Responsable, Estado, Observación, Prioridad, idOrden, idIndigo"
    )
    
    if archivo is not None:
        try:
            df = pd.read_excel(archivo, header=1)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            cols = df.columns.tolist()
            servicio_count = 0
            for i, col in enumerate(cols):
                if col == 'Servicio':
                    servicio_count += 1
                    if servicio_count == 2:
                        cols[i] = 'Servicio proceso tramita'
            df.columns = cols
            
            columnas_requeridas = ['Tag', 'Solicitado', 'Auditado', 'Sede', 'Doc.', 'Paciente', 
                                   'Edad', 'Genero', 'Diag.', 'Entidad', 'Grupo Atención', 
                                   'Servicio', 'Cups', 'Radicación', 'Radicado', 'Autorizado', 
                                   'Autorización', 'Vence', 'Entregado', 'Servicio proceso tramita', 
                                   'Programado', 'Responsable', 'Estado', 'Observación', 'Prioridad', 
                                   'idOrden', 'idIndigo']
            
            columnas_df = [col.strip() for col in df.columns]
            columnas_requeridas_norm = [col.strip() for col in columnas_requeridas]
            
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
                st.error(f"⚠️ El archivo no contiene las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
                st.info(f"📋 Columnas encontradas: {', '.join(df.columns.tolist())}")
                st.session_state.df = None
            else:
                df = df.dropna(how='all')
                df['Solicitado'] = pd.to_datetime(df['Solicitado'])
                if 'Entregado' in df.columns:
                    df['Entregado'] = pd.to_datetime(df['Entregado'])
                
                st.session_state.df = df
                st.session_state.filtros_aplicados = False
                st.session_state.df_filtrado = None
                
                if len(df) > 0:
                    st.session_state.fecha_inicio = df['Solicitado'].min().date()
                    st.session_state.fecha_fin = df['Solicitado'].max().date()
                
                st.success(f"✅ Archivo cargado correctamente. {len(df)} registros encontrados.")
                st.info(f"📊 Rango de fechas: {df['Solicitado'].min().strftime('%Y-%m-%d')} - {df['Solicitado'].max().strftime('%Y-%m-%d')}")
                    
        except Exception as e:
            st.error(f"⚠️ Error al leer el archivo: {e}")
            st.session_state.df = None
    else:
        st.info("📌 Carga un archivo Excel para comenzar a trabajar")

# ======================== CONTENIDO PRINCIPAL ========================
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    # Verificar columnas datetime
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
    
    # Crear columna de Área cruzando Cups con el portafolio
    df['Cups_str'] = df['Cups'].astype(str).str[:6]
    df_portafolio_base['CUPS_str'] = df_portafolio_base['CUPS'].astype(str).str[:6]
    dict_cups_area = dict(zip(df_portafolio_base['CUPS_str'], df_portafolio_base['UNIDAD EJECUTORA']))
    df['Area'] = df['Cups_str'].map(dict_cups_area)
    df['Area'] = df['Area'].fillna('Sin Área')
    
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
        
        st.session_state.df_filtrado = df_filtrado
        st.session_state.filtros_aplicados = True
        
        if len(df_filtrado) > 0:
            st.success(f"✅ Filtros aplicados: {len(df_filtrado)} registros encontrados")
        else:
            st.warning("⚠️ No hay datos con los filtros seleccionados")
    
    df_filtrado = st.session_state.df_filtrado.copy()
    
    # ======================== KPI CARDS ========================
    st.markdown("### 📊 Indicadores Clave")
    
    total_registros = len(df_filtrado)
    total_entidades = df_filtrado['Entidad'].nunique() if len(df_filtrado) > 0 else 0
    total_pacientes = df_filtrado['Paciente'].nunique() if len(df_filtrado) > 0 else 0
    
    if 'Entregado' in df_filtrado.columns and len(df_filtrado) > 0:
        df_filtrado['dias_entrega'] = (df_filtrado['Entregado'] - df_filtrado['Solicitado']).dt.total_seconds() / (24 * 3600)
        dias_entrega_validos = df_filtrado['dias_entrega'].dropna()
        dias_entrega_validos = dias_entrega_validos[dias_entrega_validos >= 0]
        promedio_dias_entrega = f"{dias_entrega_validos.mean():.1f}" if len(dias_entrega_validos) > 0 else "N/A"
    else:
        promedio_dias_entrega = "N/A"
    
    if len(df_filtrado) > 0 and 'Sede' in df_filtrado.columns:
        ordenamientos_por_dia_sede = df_filtrado.groupby([df_filtrado['Solicitado'].dt.date, 'Sede']).size()
        promedio_dia_sede = f"{ordenamientos_por_dia_sede.mean():.1f}" if len(ordenamientos_por_dia_sede) > 0 else "N/A"
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
        
        # Segunda fila de KPI
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
                    <p class="metric-label">📅 Ordenamientos/día por sede</p>
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
    
    # ======================== GRÁFICOS ========================
    if len(df_filtrado) > 0:
        st.markdown("### 📈 Análisis Visual")
        
        def clasificar_estado_gestion(estado):
            if estado == "PROGRAMAR":
                return "Pendiente gestión desde programación"
            elif estado == "RADICAR":
                return "Pendiente gestión desde Autorizaciones"
            elif estado in ["PROGRAMADO", "PENDIENTE PROGRAMAR"]:
                return "Gestionado desde programación"
            else:
                return "Gestionado / En seguimiento desde Autorizaciones"
        
        df_filtrado['Estado_Gestion'] = df_filtrado['Estado'].apply(clasificar_estado_gestion)
        
        # Paleta de colores morados
        purple_palette = ['#6d28d9', '#7c3aed', '#8b5cf6', '#a78bfa', '#c4b5fd', '#5b21b6', '#4c1d95', '#9b59b6']
        
        # ======================== GRÁFICO 1: Órdenes generadas vs gestionadas ========================
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
        
        df_gestionadas = df_temp[df_temp['Estado'] != "RADICAR"]
        ordenes_gestionadas = df_gestionadas.groupby('Fecha_Agrupada').size().reset_index()
        ordenes_gestionadas.columns = ['Fecha', 'Gestionadas']
        
        df_graf1 = pd.merge(ordenes_generadas, ordenes_gestionadas, on='Fecha', how='outer').fillna(0)
        df_graf1 = df_graf1.sort_values('Fecha')
        
        # Crear gráfico con matplotlib
        fig1, ax1 = plt.subplots(figsize=(12, 5))
        x = np.arange(len(df_graf1['Fecha']))
        width = 0.35
        
        ax1.bar(x - width/2, df_graf1['Generadas'], width, label='Generadas', color='#6d28d9')
        ax1.bar(x + width/2, df_graf1['Gestionadas'], width, label='Gestionadas', color='#a78bfa')
        
        ax1.set_xlabel('Fecha')
        ax1.set_ylabel('Cantidad')
        ax1.set_title('Órdenes Generadas vs Gestionadas')
        ax1.set_xticks(x)
        ax1.set_xticklabels(df_graf1['Fecha'], rotation=45, ha='right', fontsize=9)
        ax1.legend()
        
        # Agregar etiquetas de datos
        for i, v in enumerate(df_graf1['Generadas']):
            ax1.text(i - width/2, v + 0.5, str(int(v)), ha='center', va='bottom', fontsize=10, fontweight='bold', color='black')
        for i, v in enumerate(df_graf1['Gestionadas']):
            ax1.text(i + width/2, v + 0.5, str(int(v)), ha='center', va='bottom', fontsize=10, fontweight='bold', color='black')
        
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 2: Gestión de autorizaciones (ANILLO) ========================
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Gestión de autorizaciones y ordenes disponibles para programación")
            
            estado_gestion_counts = df_filtrado['Estado_Gestion'].value_counts().reset_index()
            estado_gestion_counts.columns = ['Estado', 'Cantidad']
            
            fig2, ax2 = plt.subplots(figsize=(10, 7))
            colors = ['#6d28d9', '#7c3aed', '#a78bfa', '#c4b5fd']
            
            # Gráfico de anillo
            wedges, texts, autotexts = ax2.pie(
                estado_gestion_counts['Cantidad'],
                labels=estado_gestion_counts['Estado'],
                autopct=lambda pct: f'{pct:.1f}%',
                colors=colors[:len(estado_gestion_counts)],
                startangle=90,
                wedgeprops={'width': 0.4, 'edgecolor': 'white', 'linewidth': 2},
                textprops={'fontsize': 11, 'fontweight': 'bold', 'color': 'black'}
            )
            
            # Ajustar etiquetas de porcentaje a color negro
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontsize(12)
                autotext.set_fontweight('bold')
            
            # Agregar cantidades fuera del gráfico en color negro
            for i, wedge in enumerate(wedges):
                ang = (wedge.theta2 + wedge.theta1) / 2
                x = 1.15 * np.cos(np.radians(ang))
                y = 1.15 * np.sin(np.radians(ang))
                ax2.text(x, y, f"{estado_gestion_counts['Cantidad'].iloc[i]}", 
                        fontsize=11, fontweight='bold', ha='center', va='center', color='black')
            
            ax2.set_title('Gestión de autorizaciones y ordenes disponibles para programación', fontsize=13, fontweight='bold')
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 3: Ordenamientos pendientes de gestión (ANILLO) ========================
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Pendientes de Gestión por Área")
            
            df_pendientes = df_filtrado[df_filtrado['Estado_Gestion'] == "Pendiente gestión desde programación"]
            if len(df_pendientes) > 0:
                pendientes_por_area = df_pendientes['Area'].value_counts().reset_index()
                pendientes_por_area.columns = ['Área', 'Cantidad']
                
                fig3, ax3 = plt.subplots(figsize=(10, 7))
                colors_area = purple_palette[:len(pendientes_por_area)]
                
                wedges, texts, autotexts = ax3.pie(
                    pendientes_por_area['Cantidad'],
                    labels=pendientes_por_area['Área'],
                    autopct=lambda pct: f'{pct:.1f}%',
                    colors=colors_area,
                    startangle=90,
                    wedgeprops={'width': 0.4, 'edgecolor': 'white', 'linewidth': 2},
                    textprops={'fontsize': 10, 'fontweight': 'bold', 'color': 'black'}
                )
                
                # Ajustar etiquetas de porcentaje a color negro
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontsize(11)
                    autotext.set_fontweight('bold')
                
                # Agregar cantidades fuera del gráfico en color negro
                for i, wedge in enumerate(wedges):
                    ang = (wedge.theta2 + wedge.theta1) / 2
                    x = 1.15 * np.cos(np.radians(ang))
                    y = 1.15 * np.sin(np.radians(ang))
                    ax3.text(x, y, f"{pendientes_por_area['Cantidad'].iloc[i]}", 
                            fontsize=10, fontweight='bold', ha='center', va='center', color='black')
                
                ax3.set_title('Pendientes de Gestión por Área', fontsize=13, fontweight='bold')
                plt.tight_layout()
                st.pyplot(fig3)
                plt.close()
            else:
                st.info("No hay ordenamientos pendientes de gestión desde programación")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICOS EN DOS COLUMNAS ========================
        col_g3, col_g4 = st.columns(2)
        
        # ======================== GRÁFICO 4: Ordenes generadas por servicio ========================
        with col_g3:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Órdenes Generadas por Área")
            
            ordenes_por_area = df_filtrado['Area'].value_counts().reset_index()
            ordenes_por_area.columns = ['Área', 'Cantidad']
            ordenes_por_area = ordenes_por_area.sort_values('Cantidad', ascending=False)
            
            fig4, ax4 = plt.subplots(figsize=(10, 5))
            bars4 = ax4.bar(ordenes_por_area['Área'], ordenes_por_area['Cantidad'], color='#7c3aed')
            
            ax4.set_xlabel('Área')
            ax4.set_ylabel('Cantidad')
            ax4.set_title('Órdenes Generadas por Área')
            ax4.set_xticklabels(ordenes_por_area['Área'], rotation=30, ha='right', fontsize=9)
            
            # Agregar etiquetas de datos
            for bar in bars4:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='black')
            
            plt.tight_layout()
            st.pyplot(fig4)
            plt.close()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 5: Estados de servicios ========================
        with col_g4:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Estados de Servicios")
            
            estados_counts = df_filtrado['Estado'].value_counts().reset_index()
            estados_counts.columns = ['Estado', 'Cantidad']
            estados_counts = estados_counts.sort_values('Cantidad', ascending=False)
            
            fig5, ax5 = plt.subplots(figsize=(10, 5))
            bars5 = ax5.bar(estados_counts['Estado'], estados_counts['Cantidad'], color='#8b5cf6')
            
            ax5.set_xlabel('Estado')
            ax5.set_ylabel('Cantidad')
            ax5.set_title('Estados de Servicios')
            ax5.set_xticklabels(estados_counts['Estado'], rotation=30, ha='right', fontsize=9)
            
            for bar in bars5:
                height = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='black')
            
            plt.tight_layout()
            st.pyplot(fig5)
            plt.close()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== GRÁFICO 6: Distribución por entidad ========================
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📊 Ordenamientos Distribuidos por Entidad")
        
        entidad_counts = df_filtrado['Entidad'].value_counts().reset_index()
        entidad_counts.columns = ['Entidad', 'Cantidad']
        entidad_counts = entidad_counts.sort_values('Cantidad', ascending=False)
        
        fig6, ax6 = plt.subplots(figsize=(12, 6))
        bars6 = ax6.bar(entidad_counts['Entidad'], entidad_counts['Cantidad'], color='#6d28d9')
        
        ax6.set_xlabel('Entidad')
        ax6.set_ylabel('Cantidad')
        ax6.set_title('Ordenamientos Distribuidos por Entidad')
        ax6.set_xticklabels(entidad_counts['Entidad'], rotation=30, ha='right', fontsize=9)
        
        for bar in bars6:
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='black')
        
        plt.tight_layout()
        st.pyplot(fig6)
        plt.close()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ======================== INFORMACIÓN DE FILTROS ========================
        st.divider()
        st.caption(f"🔍 Filtros aplicados: {len(estados_seleccionados)} estados, {len(entidades_seleccionadas)} entidades, {len(areas_seleccionadas)} áreas, {len(sedes_seleccionadas)} sedes")
        st.caption(f"📅 Rango de fechas: {fecha_inicio} - {fecha_fin}")
        
else:
    # Mensaje cuando no hay archivo cargado
    st.info("👈 Carga un archivo Excel para comenzar a visualizar el dashboard")
    
    with st.expander("📚 Ver Portafolio Base", expanded=False):
        st.dataframe(
            df_portafolio_base,
            use_container_width=True,
            height=300,
            column_config={
                "CUPS": st.column_config.TextColumn("CUPS", width="small"),
                "codIPS": st.column_config.TextColumn("Código IPS", width="small"),
                "descrCodIPS": st.column_config.TextColumn("Descripción", width="large"),
                "codREPS": st.column_config.TextColumn("Código REPS", width="medium"),
                "A": st.column_config.CheckboxColumn("Activo", width="small"),
                "UNIDAD EJECUTORA": st.column_config.TextColumn("Unidad Ejecutora", width="medium"),
                "Codigo unidad": st.column_config.TextColumn("Código Unidad", width="small"),
            }
        )

# Mensaje de pie de página
st.divider()
st.caption("💡 Dashboard de Gestión de Portafolio - Datos actualizados en tiempo real")
