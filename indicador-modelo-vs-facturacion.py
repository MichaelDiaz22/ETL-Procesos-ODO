import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
import numpy as np
import xlsxwriter
from io import BytesIO
import tempfile
import os

# Configuración de la página
st.set_page_config(
    page_title="Indicador novedades en modelo de acceso (Admisiones vs. Facturación)",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Indicador novedades en modelo de acceso (Admisiones vs. Facturación)")
st.markdown("---")

# Unidades funcionales por defecto
UNIDADES_POR_DEFECTO = [
    "CONSULTA ESPECIALIZADA SAN MARCEL",
    "CONSULTA ESPECIALIZADA CENTENARIO",
    "CONSULTA ESPECIALIZADA MARAYA",
    "LABORATORIO CLINICO MARAYA",
    "PROCEDIMIENTOS MENORES CONSULTA CENTENARIO",
    "PROCEDIMIENTOS MENORES CONSULTA SAN MARCEL",
    "RADIOTERAPIA CENTENARIO",
    "CONSULTA ESPECIALIZADA CIRCUNVALAR"
]

# Definición de sedes
SEDES = {
    "SAN MARCEL": {
        "fecha_inicio": datetime(2025, 9, 16),
        "centro_atencion": "SAN MARCEL",
        "unidades_clave": ["SAN MARCEL"],
        "unidad_operativa": "MANIZALES"
    },
    "CAT MARAYA": {
        "fecha_inicio": datetime(2026, 4, 15),
        "centro_atencion": "CLINICA DE ALTA TECNOLOGIA MARAYA",
        "unidades_clave": ["MARAYA"],
        "unidad_operativa": "PEREIRA"
    },
    "CIRCUNVALAR": {
        "fecha_inicio": datetime(2026, 7, 2),
        "centro_atencion": "CIRCUNVALAR",
        "unidades_clave": ["CIRCUNVALAR"],
        "unidad_operativa": "PEREIRA"
    },
    "CENTENARIO": {
        "fecha_inicio": datetime(2025, 11, 20),
        "centro_atencion": "CENTENARIO",
        "unidades_clave": ["CENTENARIO"],
        "unidad_operativa": "ARMENIA"
    },
    "CAT ARMENIA": {
        "fecha_inicio": datetime(2025, 11, 20),
        "centro_atencion": None,
        "unidades_clave": ["CAT ARMENIA"],
        "unidad_operativa": "ARMENIA"
    }
}

HOJAS_REQUERIDAS = ['EVENTO', 'PGP', 'PDTE EVENTO', 'PDTE PGP']
HOJA_NOVEDADES = 'NOVEDADES'

# Session state
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'dfs' not in st.session_state:
    st.session_state.dfs = {}
if 'fecha_hasta' not in st.session_state:
    st.session_state.fecha_hasta = None
if 'unidades_funcionales' not in st.session_state:
    st.session_state.unidades_funcionales = []
if 'unidades_seleccionadas' not in st.session_state:
    st.session_state.unidades_seleccionadas = UNIDADES_POR_DEFECTO.copy()
if 'resumen_ejecutivo' not in st.session_state:
    st.session_state.resumen_ejecutivo = None
if 'periodos_sedes' not in st.session_state:
    st.session_state.periodos_sedes = {}

def convertir_fecha_excel(numero):
    try:
        if pd.isna(numero):
            return None
        if isinstance(numero, (int, float)):
            if numero >= 61:
                numero -= 1
            fecha_base = datetime(1899, 12, 30)
            return fecha_base + timedelta(days=numero)
        elif isinstance(numero, datetime):
            return numero
        else:
            fecha = pd.to_datetime(numero, errors='coerce', dayfirst=True)
            if pd.notna(fecha):
                return fecha
        return None
    except:
        return None

def obtener_unidades_funcionales(archivo):
    try:
        unidades_set = set()
        for hoja in HOJAS_REQUERIDAS:
            df = pd.read_excel(archivo, sheet_name=hoja, nrows=1000)
            col_unidad_funcional = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'unidad funcional ingreso' in col_lower:
                    col_unidad_funcional = col
                    break
            if col_unidad_funcional:
                valores = df[col_unidad_funcional].dropna().unique()
                for valor in valores:
                    unidades_set.add(str(valor).strip())
        return sorted(list(unidades_set))
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto_str = str(texto).upper().strip()
    texto_str = texto_str.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    texto_str = texto_str.replace("Ñ", "N")
    texto_str = " ".join(texto_str.split())
    return texto_str

def procesar_hoja_ingresos_evento_pgp(df, nombre_hoja, unidades_filtro, config):
    """Procesa hojas EVENTO y PGP para ingresos"""
    col_fecha = None
    for col in df.columns:
        if 'fecha ingreso' in col.lower():
            col_fecha = col
            break
    
    col_unidad_funcional = None
    for col in df.columns:
        if 'unidad funcional ingreso' in col.lower():
            col_unidad_funcional = col
            break
    
    col_unidad_operativa = None
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'unidad operativa' in col_lower or 'ciudad unidad operativa' in col_lower:
            col_unidad_operativa = col
            break
    
    if not col_fecha or not col_unidad_funcional:
        return pd.DataFrame()
    
    # Convertir fechas
    fechas_convertidas = []
    for v in df[col_fecha]:
        fecha = convertir_fecha_excel(v)
        fechas_convertidas.append(fecha.date() if fecha else None)
    
    valores_funcionales = df[col_unidad_funcional].astype(str).str.upper().str.strip()
    
    # Filtrar por unidades funcionales seleccionadas
    if unidades_filtro and len(unidades_filtro) > 0:
        # Buscar unidades que coincidan con las claves de la sede
        unidades_filtro_sede = [u for u in unidades_filtro if any(clave in u for clave in config['unidades_clave'])]
        if unidades_filtro_sede:
            mask_unidades = valores_funcionales.isin(unidades_filtro_sede)
        else:
            # Si no hay unidades específicas para esta sede, intentar con las claves
            mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    else:
        mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    
    df_temp = pd.DataFrame({
        '_fecha': fechas_convertidas,
        '_valor_funcional': valores_funcionales
    })[mask_unidades]
    
    # Filtrar por unidad operativa
    if col_unidad_operativa and not df_temp.empty:
        valores_unidad_operativa = df[col_unidad_operativa].astype(str).str.upper().str.strip()
        mask_operativa = valores_unidad_operativa == config['unidad_operativa']
        df_temp = df_temp.loc[mask_operativa[mask_unidades].values]
    
    return df_temp

def procesar_hoja_ingresos_pdte(df, nombre_hoja, unidades_filtro, config):
    """Procesa hojas PDTE EVENTO y PDTE PGP para ingresos"""
    col_fecha = None
    for col in df.columns:
        if 'fecha ingreso' in col.lower():
            col_fecha = col
            break
    
    col_unidad_funcional = None
    for col in df.columns:
        if 'unidad funcional ingreso' in col.lower():
            col_unidad_funcional = col
            break
    
    col_centro = None
    for col in df.columns:
        if 'centro de atencion' in col.lower():
            col_centro = col
            break
    
    if not col_fecha or not col_unidad_funcional or not config['centro_atencion']:
        return pd.DataFrame()
    
    # Convertir fechas
    fechas_convertidas = []
    for v in df[col_fecha]:
        fecha = convertir_fecha_excel(v)
        fechas_convertidas.append(fecha.date() if fecha else None)
    
    valores_funcionales = df[col_unidad_funcional].astype(str).str.upper().str.strip()
    
    # Filtrar por unidades funcionales seleccionadas
    if unidades_filtro and len(unidades_filtro) > 0:
        unidades_filtro_sede = [u for u in unidades_filtro if any(clave in u for clave in config['unidades_clave'])]
        if unidades_filtro_sede:
            mask_unidades = valores_funcionales.isin(unidades_filtro_sede)
        else:
            mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    else:
        mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    
    # Crear DataFrame temporal
    df_temp = pd.DataFrame({
        '_fecha': fechas_convertidas,
        '_valor_funcional': valores_funcionales
    })[mask_unidades]
    
    # Filtrar por centro de atención
    if col_centro and not df_temp.empty:
        centros_normalizados = df[col_centro].astype(str).str.upper().str.strip()
        centros_normalizados = [normalizar_texto(c) for c in centros_normalizados]
        centro_upper = normalizar_texto(config['centro_atencion'])
        mask_centro = [c == centro_upper for c in centros_normalizados]
        mask_combinada = mask_unidades & pd.Series(mask_centro)
        df_temp = df_temp.loc[mask_combinada[mask_unidades].values]
    
    return df_temp

def procesar_hoja_facturacion(df, nombre_hoja, unidades_filtro, config):
    """Procesa hojas EVENTO y PGP para facturación incluyendo usuario facturador"""
    col_fecha_ingreso = None
    col_fecha_factura = None
    col_unidad_funcional = None
    col_unidad_operativa = None
    col_usuario_facturo = None
    
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'fecha ingreso' in col_lower:
            col_fecha_ingreso = col
        elif 'fecha factura' in col_lower or 'fecha_factura' in col_lower:
            col_fecha_factura = col
        elif 'unidad funcional ingreso' in col_lower:
            col_unidad_funcional = col
        elif 'unidad operativa' in col_lower or 'ciudad unidad operativa' in col_lower:
            col_unidad_operativa = col
        elif 'usuario facturo' in col_lower or 'usuario_facturo' in col_lower or 'facturador' in col_lower:
            col_usuario_facturo = col
    
    if not col_fecha_ingreso or not col_fecha_factura or not col_unidad_funcional:
        return pd.DataFrame()
    
    fechas_ingreso = []
    for v in df[col_fecha_ingreso]:
        fecha = convertir_fecha_excel(v)
        fechas_ingreso.append(fecha.date() if fecha else None)
    
    fechas_factura = []
    for v in df[col_fecha_factura]:
        fecha = convertir_fecha_excel(v)
        fechas_factura.append(fecha.date() if fecha else None)
    
    valores_funcionales = df[col_unidad_funcional].astype(str).str.upper().str.strip()
    
    # Obtener usuarios facturadores si existen
    usuarios = []
    if col_usuario_facturo:
        usuarios = df[col_usuario_facturo].astype(str).str.upper().str.strip().fillna('NO ESPECIFICADO').tolist()
    else:
        usuarios = ['NO ESPECIFICADO'] * len(df)
    
    # Filtrar por unidades funcionales seleccionadas
    if unidades_filtro and len(unidades_filtro) > 0:
        unidades_filtro_sede = [u for u in unidades_filtro if any(clave in u for clave in config['unidades_clave'])]
        if unidades_filtro_sede:
            mask_unidades = valores_funcionales.isin(unidades_filtro_sede)
        else:
            mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    else:
        mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    
    df_temp = pd.DataFrame({
        '_fecha_ingreso': fechas_ingreso,
        '_fecha_factura': fechas_factura,
        '_valor_funcional': valores_funcionales,
        '_usuario': usuarios
    })[mask_unidades]
    
    # Filtrar por unidad operativa
    if col_unidad_operativa and not df_temp.empty:
        valores_unidad_operativa = df[col_unidad_operativa].astype(str).str.upper().str.strip()
        mask_operativa = valores_unidad_operativa == config['unidad_operativa']
        df_temp = df_temp.loc[mask_operativa[mask_unidades].values]
    
    return df_temp

def procesar_novedades_completo(df, centro_atencion):
    """Procesa la hoja NOVEDADES para obtener todos los detalles"""
    if df is None or df.empty or not centro_atencion:
        return pd.DataFrame()
    
    # Buscar columnas relevantes
    col_fecha = None
    for col in df.columns:
        if 'fechadevolucion' in col.lower() or 'fecha devolucion' in col.lower():
            col_fecha = col
            break
    
    col_centro = None
    for col in df.columns:
        if 'centro de atencion' in col.lower():
            col_centro = col
            break
    
    col_motivo = None
    for col in df.columns:
        col_lower = col.lower()
        if 'motivo' in col_lower or 'causa' in col_lower or 'descripcion' in col_lower:
            col_motivo = col
            break
    
    col_bloqueante = None
    for col in df.columns:
        if 'bloqueante' in col.lower():
            col_bloqueante = col
            break
    
    if not col_fecha or not col_centro:
        return pd.DataFrame()
    
    # Convertir fechas
    fechas_convertidas = []
    for v in df[col_fecha]:
        fecha = convertir_fecha_excel(v)
        fechas_convertidas.append(fecha.date() if fecha else None)
    
    centros_normalizados = [normalizar_texto(v) for v in df[col_centro]]
    centro_upper = normalizar_texto(centro_atencion)
    
    df_procesado = pd.DataFrame({
        '_fecha': fechas_convertidas,
        '_centro': centros_normalizados
    })
    
    if col_motivo:
        df_procesado['_motivo'] = df[col_motivo].astype(str).str.upper().str.strip()
    else:
        df_procesado['_motivo'] = 'SIN ESPECIFICAR'
    
    if col_bloqueante:
        df_procesado['_bloqueante'] = df[col_bloqueante].astype(str).str.upper().str.strip()
    
    # Filtrar por centro
    df_filtrado = df_procesado[df_procesado['_centro'] == centro_upper]
    
    return df_filtrado

def procesar_hoja_novedades(df, centro_atencion, fecha_inicio, fecha_fin):
    """Procesa la hoja NOVEDADES para conteo"""
    if df is None or df.empty or not centro_atencion:
        return {}, {}
    
    df_novedades = procesar_novedades_completo(df, centro_atencion)
    if df_novedades.empty:
        return {}, {}
    
    mask_fecha = (df_novedades['_fecha'] >= fecha_inicio.date()) & (df_novedades['_fecha'] <= fecha_fin.date())
    df_filtrado = df_novedades[mask_fecha]
    
    conteo_total = {}
    conteo_bloqueantes = {}
    
    for fecha in df_filtrado['_fecha']:
        conteo_total[fecha] = conteo_total.get(fecha, 0) + 1
    
    if '_bloqueante' in df_filtrado.columns:
        for idx, row in df_filtrado.iterrows():
            if row['_bloqueante'] == 'SI':
                conteo_bloqueantes[row['_fecha']] = conteo_bloqueantes.get(row['_fecha'], 0) + 1
    
    return conteo_total, conteo_bloqueantes

def cargar_archivo(archivo, unidades_filtro):
    try:
        excel_file = pd.ExcelFile(archivo)
        hojas_disponibles = excel_file.sheet_names
        
        hojas_faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_disponibles]
        if hojas_faltantes:
            st.error(f"Faltan hojas: {', '.join(hojas_faltantes)}")
            return False, None, None
        
        dfs_ingresos = {sede: [] for sede in SEDES.keys()}
        dfs_facturacion = {sede: [] for sede in SEDES.keys()}
        dfs_facturacion_detalle = {sede: [] for sede in SEDES.keys()}
        
        # Procesar hojas EVENTO y PGP
        for hoja in ['EVENTO', 'PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            for sede, config in SEDES.items():
                df_ing = procesar_hoja_ingresos_evento_pgp(df, hoja, unidades_filtro, config)
                if not df_ing.empty:
                    dfs_ingresos[sede].append(df_ing)
                
                df_fac = procesar_hoja_facturacion(df, hoja, unidades_filtro, config)
                if not df_fac.empty:
                    dfs_facturacion[sede].append(df_fac)
                    dfs_facturacion_detalle[sede].append(df_fac)
        
        # Procesar hojas PDTE EVENTO y PDTE PGP
        for hoja in ['PDTE EVENTO', 'PDTE PGP']:
            df = pd.read_excel(archivo, sheet_name=hoja)
            
            for sede, config in SEDES.items():
                if config['centro_atencion']:
                    df_ing = procesar_hoja_ingresos_pdte(df, hoja, unidades_filtro, config)
                    if not df_ing.empty:
                        dfs_ingresos[sede].append(df_ing)
        
        # Cargar novedades
        df_novedades = None
        if HOJA_NOVEDADES in hojas_disponibles:
            df_novedades = pd.read_excel(archivo, sheet_name=HOJA_NOVEDADES)
        
        # Combinar resultados
        dfs_resultado = {}
        for sede in SEDES.keys():
            if dfs_ingresos[sede]:
                dfs_resultado[f'INGRESOS_{sede}'] = pd.concat(dfs_ingresos[sede], ignore_index=True)
            else:
                dfs_resultado[f'INGRESOS_{sede}'] = pd.DataFrame()
            
            if dfs_facturacion[sede]:
                dfs_resultado[f'FACTURACION_{sede}'] = pd.concat(dfs_facturacion[sede], ignore_index=True)
            else:
                dfs_resultado[f'FACTURACION_{sede}'] = pd.DataFrame()
            
            if dfs_facturacion_detalle[sede]:
                dfs_resultado[f'FACTURACION_DETALLE_{sede}'] = pd.concat(dfs_facturacion_detalle[sede], ignore_index=True)
            else:
                dfs_resultado[f'FACTURACION_DETALLE_{sede}'] = pd.DataFrame()
        
        dfs_resultado['NOVEDADES'] = df_novedades
        
        # Procesar novedades completas para cada sede
        for sede, config in SEDES.items():
            if config['centro_atencion']:
                df_novedades_sede = procesar_novedades_completo(df_novedades, config['centro_atencion'])
                dfs_resultado[f'NOVEDADES_DETALLE_{sede}'] = df_novedades_sede
            else:
                dfs_resultado[f'NOVEDADES_DETALLE_{sede}'] = pd.DataFrame()
        
        return True, dfs_resultado, datetime.now()
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False, None, None

def contar_ingresos_sede(df_ingresos, fecha_inicio, fecha_fin):
    if df_ingresos.empty:
        return {}
    
    mask_fecha = (df_ingresos['_fecha'] >= fecha_inicio.date()) & (df_ingresos['_fecha'] <= fecha_fin.date())
    df_filtrado = df_ingresos[mask_fecha]
    
    conteo = {}
    for fecha in df_filtrado['_fecha']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def contar_facturado_modelo_sede(df_facturacion, fecha_inicio, fecha_fin):
    if df_facturacion.empty:
        return {}
    
    mask_fechas = (df_facturacion['_fecha_ingreso'] >= fecha_inicio.date()) & (df_facturacion['_fecha_factura'] >= fecha_inicio.date())
    df_filtrado = df_facturacion[mask_fechas]
    
    mask_fecha_fin = df_filtrado['_fecha_factura'] <= fecha_fin.date()
    df_filtrado = df_filtrado[mask_fecha_fin]
    
    conteo = {}
    for fecha in df_filtrado['_fecha_factura']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def contar_facturado_fuera_modelo_sede(df_facturacion, fecha_inicio, fecha_fin):
    if df_facturacion.empty:
        return {}
    
    mask_fechas = (df_facturacion['_fecha_ingreso'] < fecha_inicio.date()) & (df_facturacion['_fecha_factura'] >= fecha_inicio.date())
    df_filtrado = df_facturacion[mask_fechas]
    
    mask_fecha_fin = df_filtrado['_fecha_factura'] <= fecha_fin.date()
    df_filtrado = df_filtrado[mask_fecha_fin]
    
    conteo = {}
    for fecha in df_filtrado['_fecha_factura']:
        conteo[fecha] = conteo.get(fecha, 0) + 1
    
    return conteo

def contar_novedades_sede(df_novedades, centro_atencion, fecha_inicio, fecha_fin):
    if df_novedades is None or df_novedades.empty or not centro_atencion:
        return {}, {}
    
    return procesar_hoja_novedades(df_novedades, centro_atencion, fecha_inicio, fecha_fin)

def calcular_resumen_ejecutivo(dfs, fecha_fin):
    resultados = []
    
    for sede, config in SEDES.items():
        fecha_inicio = config['fecha_inicio']
        
        # Si la fecha de fin es anterior a la fecha de inicio, saltar esta sede
        if fecha_fin < fecha_inicio:
            continue
        
        df_ingresos = dfs.get(f'INGRESOS_{sede}', pd.DataFrame())
        df_facturacion = dfs.get(f'FACTURACION_{sede}', pd.DataFrame())
        df_novedades = dfs.get('NOVEDADES', None)
        
        conteo_ingresos = contar_ingresos_sede(df_ingresos, fecha_inicio, fecha_fin)
        conteo_facturado_modelo = contar_facturado_modelo_sede(df_facturacion, fecha_inicio, fecha_fin)
        conteo_facturado_fuera = contar_facturado_fuera_modelo_sede(df_facturacion, fecha_inicio, fecha_fin)
        conteo_novedades, conteo_bloqueantes = contar_novedades_sede(df_novedades, config.get('centro_atencion'), fecha_inicio, fecha_fin)
        
        total_ingresos = sum(conteo_ingresos.values())
        total_facturado = sum(conteo_facturado_modelo.values()) + sum(conteo_facturado_fuera.values())
        total_novedades = sum(conteo_novedades.values())
        total_bloqueantes = sum(conteo_bloqueantes.values())
        
        pct_facturado = (total_facturado / total_ingresos * 100) if total_ingresos > 0 else 0
        pct_novedades = (total_novedades / total_ingresos * 100) if total_ingresos > 0 else 0
        pct_bloqueantes = (total_bloqueantes / total_ingresos * 100) if total_ingresos > 0 else 0
        
        resultados.append({
            'Sede': sede,
            'Ingresos': f"{total_ingresos:,}",
            'Facturado total': f"{total_facturado:,}",
            '% facturado total / ingresos': f"{pct_facturado:.1f}%",
            '% novedades / ingresos': f"{pct_novedades:.1f}%",
            '% novedades bloqueantes / ingresos': f"{pct_bloqueantes:.1f}%",
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        })
    
    return pd.DataFrame(resultados)

def formatear_rango_semana(fecha_inicio_semana, fecha_fin_semana, fecha_fin_global):
    fecha_fin_real = min(fecha_fin_semana, fecha_fin_global)
    inicio_str = fecha_inicio_semana.strftime('%d-%m')
    fin_str = fecha_fin_real.strftime('%d-%m')
    return f"{inicio_str} / {fin_str}"

def agrupar_por_periodo(df, periodo, fecha_fin_global):
    if df.empty:
        return df
    
    df_agrupado = df.copy()
    df_agrupado['Fecha'] = pd.to_datetime(df_agrupado['Fecha'])
    
    if periodo == 'Mensual':
        df_agrupado['Periodo'] = df_agrupado['Fecha'].dt.strftime('%Y-%m')
        df_agrupado['Fecha'] = df_agrupado['Fecha'].dt.to_period('M').dt.start_time
        df_agrupado['semana'] = 'Mensual'
        df_agrupado['mes'] = df_agrupado['Periodo']
    elif periodo == 'Semanal':
        df_agrupado['InicioSemana'] = df_agrupado['Fecha'] - pd.to_timedelta(df_agrupado['Fecha'].dt.dayofweek, unit='d')
        df_agrupado['FinSemana'] = df_agrupado['InicioSemana'] + timedelta(days=6)
        df_agrupado['Periodo'] = df_agrupado['InicioSemana'].dt.strftime('%Y-W%W')
        df_agrupado['Fecha'] = df_agrupado['InicioSemana']
        df_agrupado['semana'] = df_agrupado.apply(
            lambda row: formatear_rango_semana(row['InicioSemana'], row['FinSemana'], fecha_fin_global), 
            axis=1
        )
        df_agrupado['mes'] = 'Semanal'
    else:
        df_agrupado['Periodo'] = df_agrupado['Fecha'].dt.strftime('%Y-%m-%d')
        df_agrupado['semana'] = df_agrupado['Fecha'].dt.isocalendar().week
        df_agrupado['mes'] = df_agrupado['Fecha'].dt.strftime('%Y-%m')
    
    columnas_agrupar = ['ingresos', 'facturado modelo', 'facturado fuera modelo', 'facturado total', 'Novedades', 'Novedades Bloqueantes']
    df_resultado = df_agrupado.groupby(['Periodo', 'Fecha', 'semana', 'mes', 'año'])[columnas_agrupar].sum().reset_index()
    
    return df_resultado

def construir_tabla_sede(sede, config, fecha_inicio, fecha_fin, df_ingresos, df_facturacion, df_novedades, periodo):
    conteo_ingresos = contar_ingresos_sede(df_ingresos, fecha_inicio, fecha_fin)
    conteo_facturado_modelo = contar_facturado_modelo_sede(df_facturacion, fecha_inicio, fecha_fin)
    conteo_facturado_fuera = contar_facturado_fuera_modelo_sede(df_facturacion, fecha_inicio, fecha_fin)
    conteo_novedades, conteo_bloqueantes = contar_novedades_sede(df_novedades, config.get('centro_atencion'), fecha_inicio, fecha_fin)
    
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    datos = []
    for fecha in fechas:
        fecha_key = fecha.date()
        ingresos = conteo_ingresos.get(fecha_key, 0)
        facturado_modelo = conteo_facturado_modelo.get(fecha_key, 0)
        facturado_fuera = conteo_facturado_fuera.get(fecha_key, 0)
        facturado_total = facturado_modelo + facturado_fuera
        novedades = conteo_novedades.get(fecha_key, 0)
        novedades_bloqueantes = conteo_bloqueantes.get(fecha_key, 0)
        
        datos.append({
            'Fecha': fecha,
            'semana': fecha.isocalendar()[1],
            'año': fecha.year,
            'mes': calendar.month_name[fecha.month],
            'ingresos': ingresos,
            'facturado modelo': facturado_modelo,
            'facturado fuera modelo': facturado_fuera,
            'facturado total': facturado_total,
            'Novedades': novedades,
            'Novedades Bloqueantes': novedades_bloqueantes
        })
    
    df = pd.DataFrame(datos)
    df_agrupado = agrupar_por_periodo(df, periodo, fecha_fin)
    
    return df_agrupado

def obtener_matriz_usuario_unidad(df_facturacion_detalle, fecha_inicio, fecha_fin, periodo):
    """
    Genera una matriz de facturación por Usuario vs Unidad Funcional
    Muestra la cantidad de registros por usuario y por unidad funcional
    """
    if df_facturacion_detalle.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Filtrar por fechas
    mask_fecha = (df_facturacion_detalle['_fecha_factura'] >= fecha_inicio.date()) & (df_facturacion_detalle['_fecha_factura'] <= fecha_fin.date())
    df_filtrado = df_facturacion_detalle[mask_fecha].copy()
    
    if df_filtrado.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Agrupar por usuario y unidad funcional (sin período para la matriz principal)
    matriz = df_filtrado.groupby(['_usuario', '_valor_funcional']).size().reset_index(name='Cantidad')
    
    # Crear tabla pivote: Usuarios vs Unidades Funcionales
    pivot_usuario_unidad = matriz.pivot_table(
        index='_usuario', 
        columns='_valor_funcional', 
        values='Cantidad', 
        fill_value=0
    ).reset_index()
    
    # Agregar columna de total
    pivot_usuario_unidad['TOTAL'] = pivot_usuario_unidad.select_dtypes(include=['number']).sum(axis=1)
    
    # Ordenar por total descendente
    pivot_usuario_unidad = pivot_usuario_unidad.sort_values('TOTAL', ascending=False)
    
    # Reordenar columnas: usuario, luego unidades ordenadas alfabéticamente, luego total
    columnas_unidades = [col for col in pivot_usuario_unidad.columns if col not in ['_usuario', 'TOTAL']]
    columnas_unidades_ordenadas = sorted(columnas_unidades)
    pivot_usuario_unidad = pivot_usuario_unidad[['_usuario'] + columnas_unidades_ordenadas + ['TOTAL']]
    
    # Crear también la matriz transpuesta (Unidades vs Usuarios)
    pivot_unidad_usuario = matriz.pivot_table(
        index='_valor_funcional', 
        columns='_usuario', 
        values='Cantidad', 
        fill_value=0
    ).reset_index()
    
    # Agregar columna de total para unidades
    pivot_unidad_usuario['TOTAL'] = pivot_unidad_usuario.select_dtypes(include=['number']).sum(axis=1)
    
    # Ordenar por total descendente
    pivot_unidad_usuario = pivot_unidad_usuario.sort_values('TOTAL', ascending=False)
    
    # Reordenar columnas: unidad funcional, luego usuarios ordenados alfabéticamente, luego total
    columnas_usuarios = [col for col in pivot_unidad_usuario.columns if col not in ['_valor_funcional', 'TOTAL']]
    columnas_usuarios_ordenadas = sorted(columnas_usuarios)
    pivot_unidad_usuario = pivot_unidad_usuario[['_valor_funcional'] + columnas_usuarios_ordenadas + ['TOTAL']]
    
    return pivot_usuario_unidad, pivot_unidad_usuario

def graficar_matriz_calor(df_matriz, titulo):
    """Genera gráfica de calor para la matriz de facturación"""
    if df_matriz.empty or len(df_matriz.columns) < 2:
        return None
    
    # Preparar datos para la gráfica de calor
    if '_usuario' in df_matriz.columns:
        # Matriz de usuarios vs unidades
        df_heat = df_matriz.set_index('_usuario')
        # Eliminar columna TOTAL si existe
        df_heat = df_heat.drop(columns=['TOTAL'], errors='ignore')
        
        # Limitar a top 10 usuarios y top 10 unidades para mejor visualización
        if len(df_heat.index) > 10:
            usuarios_top = df_heat.sum(axis=1).nlargest(10).index
            df_heat = df_heat.loc[usuarios_top]
        
        if len(df_heat.columns) > 10:
            unidades_top = df_heat.sum(axis=0).nlargest(10).index
            df_heat = df_heat[unidades_top]
        
        if df_heat.empty:
            return None
        
        fig, ax = plt.subplots(figsize=(max(10, len(df_heat.columns) * 0.4), max(6, len(df_heat.index) * 0.4)))
        
        # Crear heatmap
        im = ax.imshow(df_heat.values, cmap='YlOrRd', aspect='auto', interpolation='nearest')
        
        # Configurar ejes
        ax.set_xticks(np.arange(len(df_heat.columns)))
        ax.set_yticks(np.arange(len(df_heat.index)))
        ax.set_xticklabels(df_heat.columns, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels(df_heat.index, fontsize=9)
        
        ax.set_xlabel('Unidades Funcionales', fontsize=11, fontweight='bold')
        ax.set_ylabel('Usuarios', fontsize=11, fontweight='bold')
        ax.set_title(titulo, fontsize=13, fontweight='bold')
        
        # Agregar valores en las celdas
        max_valor = df_heat.values.max()
        for i in range(len(df_heat.index)):
            for j in range(len(df_heat.columns)):
                valor = df_heat.iloc[i, j]
                if valor > 0:
                    text_color = 'white' if valor > max_valor * 0.6 else 'black'
                    ax.text(j, i, str(int(valor)), ha='center', va='center', fontsize=7, color=text_color)
        
        # Agregar barra de color
        plt.colorbar(im, ax=ax, label='Cantidad de Facturas')
        
        plt.tight_layout()
        return fig
    else:
        return None

def obtener_facturacion_por_usuario(df_facturacion_detalle, fecha_inicio, fecha_fin, periodo):
    """Obtiene la facturación agrupada por usuario y período"""
    if df_facturacion_detalle.empty:
        return pd.DataFrame()
    
    # Filtrar por fechas
    mask_fecha = (df_facturacion_detalle['_fecha_factura'] >= fecha_inicio.date()) & (df_facturacion_detalle['_fecha_factura'] <= fecha_fin.date())
    df_filtrado = df_facturacion_detalle[mask_fecha].copy()
    
    if df_filtrado.empty:
        return pd.DataFrame()
    
    # Crear columna de período
    df_filtrado['fecha_dt'] = pd.to_datetime(df_filtrado['_fecha_factura'])
    
    if periodo == 'Mensual':
        df_filtrado['Periodo'] = df_filtrado['fecha_dt'].dt.strftime('%Y-%m')
    elif periodo == 'Semanal':
        df_filtrado['Periodo'] = df_filtrado['fecha_dt'].dt.to_period('W').astype(str)
    else:
        df_filtrado['Periodo'] = df_filtrado['fecha_dt'].dt.strftime('%Y-%m-%d')
    
    # Agrupar por usuario y período
    resultado = df_filtrado.groupby(['_usuario', 'Periodo']).size().reset_index(name='Cantidad')
    resultado = resultado.pivot(index='_usuario', columns='Periodo', values='Cantidad').fillna(0).astype(int)
    
    # Agregar total por usuario
    resultado['TOTAL'] = resultado.sum(axis=1)
    
    # Ordenar por total descendente
    resultado = resultado.sort_values('TOTAL', ascending=False)
    
    # Reordenar columnas cronológicamente
    periodos = [col for col in resultado.columns if col != 'TOTAL']
    periodos_ordenados = sorted(periodos)
    resultado = resultado[periodos_ordenados + ['TOTAL']]
    
    return resultado

def graficar_facturacion_por_usuario_mensual(df_facturacion_detalle, fecha_inicio, fecha_fin, sede):
    """
    Gráfica de barras apiladas mostrando la facturación por usuario por mes
    NO se ve afectada por el selector de período (siempre muestra datos mensuales)
    """
    if df_facturacion_detalle.empty:
        return None
    
    # Filtrar por fechas
    mask_fecha = (df_facturacion_detalle['_fecha_factura'] >= fecha_inicio.date()) & (df_facturacion_detalle['_fecha_factura'] <= fecha_fin.date())
    df_filtrado = df_facturacion_detalle[mask_fecha].copy()
    
    if df_filtrado.empty:
        return None
    
    # Crear columna de mes
    df_filtrado['fecha_dt'] = pd.to_datetime(df_filtrado['_fecha_factura'])
    df_filtrado['Mes'] = df_filtrado['fecha_dt'].dt.strftime('%Y-%m')
    df_filtrado['NombreMes'] = df_filtrado['fecha_dt'].dt.strftime('%B %Y')
    
    # Crear tabla pivote: usuarios vs meses
    pivot_table = pd.crosstab(df_filtrado['_usuario'], df_filtrado['Mes'])
    
    # Ordenar por frecuencia total descendente (top 8 usuarios)
    pivot_table['Total'] = pivot_table.sum(axis=1)
    pivot_table = pivot_table.sort_values('Total', ascending=False)
    pivot_table = pivot_table.drop('Total', axis=1)
    
    # Obtener top 8 usuarios (si hay menos, mostrar todos)
    top_usuarios = pivot_table.head(8)
    
    # Si no hay usuarios, retornar None
    if top_usuarios.empty:
        return None
    
    # Reordenar columnas (meses) cronológicamente
    meses_ordenados = sorted(top_usuarios.columns)
    top_usuarios = top_usuarios[meses_ordenados]
    
    # Crear gráfica de barras apiladas
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Colores para diferentes usuarios
    colores = plt.cm.Set2(np.linspace(0, 1, len(top_usuarios.index)))
    
    bottom = np.zeros(len(top_usuarios.columns))
    
    for i, usuario in enumerate(top_usuarios.index):
        valores = top_usuarios.loc[usuario].values
        bars = ax.bar(range(len(top_usuarios.columns)), valores, bottom=bottom, 
                      label=usuario, color=colores[i], alpha=0.8)
        
        # Agregar valores en las barras si son significativos
        max_valor = top_usuarios.values.max()
        for j, valor in enumerate(valores):
            if valor > 0 and valor > max_valor * 0.05:
                ax.text(j, bottom[j] + valor/2, str(int(valor)), 
                       ha='center', va='center', fontsize=8, fontweight='bold')
        bottom += valores
    
    ax.set_xlabel('Mes', fontsize=12)
    ax.set_ylabel('Cantidad Facturada', fontsize=12)
    ax.set_title(f'Distribución de Facturación por Usuario - {sede}', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(top_usuarios.columns)))
    ax.set_xticklabels(top_usuarios.columns, rotation=45, ha='right', fontsize=10)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    return fig

# Funciones de gráficas con matplotlib
def graficar_novedades_temporales(df_novedades_sede, periodo):
    """Gráfica de novedades generadas por período usando matplotlib"""
    if df_novedades_sede.empty:
        return None
    
    df_novedades_sede['Fecha'] = pd.to_datetime(df_novedades_sede['_fecha'])
    
    if periodo == 'Mensual':
        df_agrupado = df_novedades_sede.groupby(df_novedades_sede['Fecha'].dt.to_period('M')).size().reset_index(name='Cantidad')
        df_agrupado['Fecha'] = df_agrupado['Fecha'].astype(str)
        titulo = "Novedades Generadas por Mes"
        xlabel = "Mes"
    elif periodo == 'Semanal':
        df_agrupado = df_novedades_sede.groupby(df_novedades_sede['Fecha'].dt.to_period('W')).size().reset_index(name='Cantidad')
        df_agrupado['Fecha'] = df_agrupado['Fecha'].astype(str)
        titulo = "Novedades Generadas por Semana"
        xlabel = "Semana"
    else:
        df_agrupado = df_novedades_sede.groupby('_fecha').size().reset_index(name='Cantidad')
        df_agrupado.columns = ['Fecha', 'Cantidad']
        df_agrupado['Fecha'] = df_agrupado['Fecha'].astype(str)
        titulo = "Novedades Generadas por Día"
        xlabel = "Día"
    
    # Crear gráfica con matplotlib
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(range(len(df_agrupado)), df_agrupado['Cantidad'], color='#FF6B6B', alpha=0.7)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Número de Novedades', fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(df_agrupado)))
    ax.set_xticklabels(df_agrupado['Fecha'], rotation=45, ha='right', fontsize=10)
    
    # Agregar valores en las barras
    for bar, valor in zip(bars, df_agrupado['Cantidad']):
        if valor > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                   str(valor), ha='center', va='bottom', fontsize=9)
    
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    return fig

def graficar_facturacion_temporal(df_tabla, periodo):
    """Gráfica de facturación por período usando matplotlib"""
    if df_tabla.empty:
        return None
    
    # Asegurar que Fecha sea datetime
    df_tabla = df_tabla.copy()
    if 'Fecha' in df_tabla.columns and not pd.api.types.is_datetime64_any_dtype(df_tabla['Fecha']):
        df_tabla['Fecha'] = pd.to_datetime(df_tabla['Fecha'])
    
    # Preparar datos según el período
    if periodo == 'Mensual':
        if 'mes' in df_tabla.columns:
            x_data = df_tabla['mes'].astype(str)
        else:
            x_data = df_tabla['Fecha'].dt.strftime('%Y-%m')
        titulo = "Facturación por Mes"
        xlabel = "Mes"
    elif periodo == 'Semanal':
        if 'semana' in df_tabla.columns:
            x_data = df_tabla['semana'].astype(str)
        else:
            x_data = df_tabla['Fecha'].dt.isocalendar().week.astype(str)
        titulo = "Facturación por Semana"
        xlabel = "Semana"
    else:
        x_data = df_tabla['Fecha'].dt.strftime('%Y-%m-%d')
        titulo = "Facturación por Día"
        xlabel = "Fecha"
    
    # Crear gráfica
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Barras para facturación total
    bars = ax.bar(range(len(df_tabla)), df_tabla['facturado total'], 
                  color='#4CAF50', alpha=0.7, label='Facturado Total', width=0.7)
    
    # Línea para tendencia
    ax.plot(range(len(df_tabla)), df_tabla['facturado total'], 
            color='#2E7D32', linewidth=2, marker='o', markersize=6, label='Tendencia')
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Cantidad Facturada', fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(df_tabla)))
    ax.set_xticklabels(x_data, rotation=45, ha='right', fontsize=9)
    
    # Agregar valores en las barras
    for bar, valor in zip(bars, df_tabla['facturado total']):
        if valor > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(1, valor*0.02), 
                   str(int(valor)), ha='center', va='bottom', fontsize=8)
    
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper left', fontsize=10)
    plt.tight_layout()
    
    return fig

def graficar_pareto_novedades(df_novedades_sede):
    """Gráfica de Pareto de motivos de novedades usando matplotlib - Versión optimizada con leyenda a la derecha"""
    if df_novedades_sede.empty or '_motivo' not in df_novedades_sede.columns:
        return None
    
    # Contar motivos
    conteo_motivos = df_novedades_sede['_motivo'].value_counts().reset_index()
    conteo_motivos.columns = ['Motivo', 'Frecuencia']
    
    # Limitar a top 10 para mejor visualización
    if len(conteo_motivos) > 10:
        otros = pd.DataFrame({
            'Motivo': ['OTROS'],
            'Frecuencia': [conteo_motivos.iloc[10:]['Frecuencia'].sum()]
        })
        conteo_motivos = pd.concat([conteo_motivos.iloc[:10], otros], ignore_index=True)
    
    # Calcular porcentaje acumulado
    total = conteo_motivos['Frecuencia'].sum()
    conteo_motivos['Porcentaje'] = (conteo_motivos['Frecuencia'] / total * 100).round(1)
    conteo_motivos['Porcentaje Acumulado'] = conteo_motivos['Porcentaje'].cumsum()
    
    # Crear gráfica con dos ejes
    fig, ax1 = plt.subplots(figsize=(14, 6.5))
    
    # Barras para frecuencias
    x = range(len(conteo_motivos))
    bars = ax1.bar(x, conteo_motivos['Frecuencia'], color='#FF6B6B', alpha=0.8, label='Frecuencia', width=0.6)
    ax1.set_xlabel('Motivos', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Frecuencia', fontsize=11, fontweight='bold', color='#FF6B6B')
    ax1.tick_params(axis='y', labelcolor='#FF6B6B', labelsize=10)
    
    # Línea para porcentaje acumulado
    ax2 = ax1.twinx()
    ax2.plot(x, conteo_motivos['Porcentaje Acumulado'], color='#2C3E50', 
            marker='o', linewidth=2.5, markersize=7, label='% Acumulado')
    ax2.set_ylabel('Porcentaje Acumulado (%)', fontsize=11, fontweight='bold', color='#2C3E50')
    ax2.tick_params(axis='y', labelcolor='#2C3E50', labelsize=10)
    
    # Configurar etiquetas del eje X
    ax1.set_xticks(x)
    ax1.set_xticklabels(conteo_motivos['Motivo'], rotation=25, ha='right', fontsize=8.5)
    
    # Agregar línea del 80%
    ax2.axhline(y=80, color='red', linestyle='--', alpha=0.6, linewidth=1.5)
    
    # Agregar valores y porcentajes en las barras
    for i, (bar, valor, pct) in enumerate(zip(bars, conteo_motivos['Frecuencia'], conteo_motivos['Porcentaje'])):
        if valor > 0:
            # Valor de frecuencia sobre la barra
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(1, valor*0.02), 
                    f'{int(valor)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
            # Porcentaje dentro de la barra (si es suficientemente alta)
            if bar.get_height() > max(conteo_motivos['Frecuencia']) * 0.05:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2, 
                        f'{pct}%', ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    
    # Agregar porcentajes acumulados en los puntos de la línea
    for i, (x_val, pct_acum) in enumerate(zip(x, conteo_motivos['Porcentaje Acumulado'])):
        ax2.annotate(f'{pct_acum:.1f}%', 
                    xy=(x_val, pct_acum), 
                    xytext=(0, 10), 
                    textcoords='offset points',
                    ha='center', 
                    fontsize=9, 
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # Agregar título
    plt.title('Pareto de Motivos de Novedades', fontsize=14, fontweight='bold', pad=15)
    
    # Leyenda al lado derecho
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9, framealpha=0.9)
    
    # Mejorar la cuadrícula
    ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
    ax1.set_axisbelow(True)
    
    # Ajustar límites para mejor visualización
    ax1.set_ylim(0, max(conteo_motivos['Frecuencia']) * 1.12)
    ax2.set_ylim(0, 105)
    
    plt.tight_layout()
    
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
    
    # Obtener top 8 motivos
    top_motivos = pivot_table.head(8)
    
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
                      label=motivo, color=colores[i], alpha=0.8)
        # Agregar valores en las barras si son significativos
        for j, valor in enumerate(valores):
            if valor > 0 and valor > max(top_motivos.values.flatten()) * 0.05:
                ax.text(j, bottom[j] + valor/2, str(valor), 
                       ha='center', va='center', fontsize=8, fontweight='bold')
        bottom += valores
    
    ax.set_xlabel('Mes', fontsize=12)
    ax.set_ylabel('Frecuencia', fontsize=12)
    ax.set_title('Distribución de Motivos de Devolución por Mes', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(top_motivos.columns)))
    ax.set_xticklabels(top_motivos.columns, rotation=45, ha='right', fontsize=10)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    return fig

def generar_narrativa_ejecutiva(df_resumen):
    """
    Genera una narrativa automática basada en los resultados del análisis
    Excluye sedes que tengan 0 en todos sus datos
    Los objetivos son: facturación > 90% y novedades < 5%
    """
    if df_resumen.empty:
        return "No hay datos suficientes para generar conclusiones."
    
    # Crear una copia y calcular ingresos numéricos
    df_temp = df_resumen.copy()
    df_temp['Ingresos_num'] = df_temp['Ingresos'].str.replace(',', '').astype(int)
    
    # Identificar sedes excluidas
    sedes_excluidas = df_temp[df_temp['Ingresos_num'] == 0]['Sede'].tolist()
    
    # Filtrar solo sedes con datos
    df_activas = df_temp[df_temp['Ingresos_num'] > 0].copy()
    
    if df_activas.empty:
        if sedes_excluidas:
            return f"No hay sedes con datos válidos para generar el análisis. Las siguientes sedes tienen 0 ingresos en el período seleccionado: {', '.join(sedes_excluidas)}"
        else:
            return "No hay sedes con datos válidos para generar el análisis. Todas las sedes tienen 0 ingresos en el período seleccionado."
    
    # Calcular métricas para sedes activas
    df_activas['%_facturado'] = df_activas['% facturado total / ingresos'].str.replace('%', '').astype(float)
    df_activas['%_novedades'] = df_activas['% novedades / ingresos'].str.replace('%', '').astype(float)
    df_activas['%_bloqueantes'] = df_activas['% novedades bloqueantes / ingresos'].str.replace('%', '').astype(float)
    
    # Definir objetivos
    OBJETIVO_FACTURACION = 90.0
    OBJETIVO_NOVEDADES = 5.0
    
    narrativa = []
    narrativa.append("## 📋 ANÁLISIS Y CONCLUSIONES EJECUTIVAS\n")
    
    # Mostrar sedes excluidas si las hay
    if sedes_excluidas:
        narrativa.append(f"**ℹ️ Nota:** Las siguientes sedes no presentan actividad en el período analizado y han sido excluidas del análisis: ")
        narrativa.append(f"{', '.join(sedes_excluidas)}.\n\n")
    
    # 1. Análisis general de volumen vs objetivos
    total_ingresos = df_activas['Ingresos_num'].sum()
    total_facturado = df_activas['Facturado total'].str.replace(',', '').astype(int).sum()
    eficiencia_total = (total_facturado/total_ingresos*100) if total_ingresos > 0 else 0
    total_novedades_pct = df_activas['%_novedades'].mean()
    
    narrativa.append("### 📊 PANORAMA GENERAL\n")
    narrativa.append(f"Durante el período analizado, se procesaron **{total_ingresos:,} ingresos** en las sedes activas, ")
    narrativa.append(f"de los cuales se han facturado **{total_facturado:,}** ({eficiencia_total:.1f}% del total). ")
    
    # Evaluar cumplimiento del objetivo de facturación
    if eficiencia_total >= OBJETIVO_FACTURACION:
        narrativa.append(f"✅ **CUMPLE el objetivo de facturación** (meta: >{OBJETIVO_FACTURACION}%). ")
    else:
        narrativa.append(f"❌ **NO CUMPLE el objetivo de facturación** (meta: >{OBJETIVO_FACTURACION}%). ")
    
    narrativa.append(f"El promedio de novedades sobre ingresos es del **{total_novedades_pct:.1f}%**, ")
    
    # Evaluar cumplimiento del objetivo de novedades
    if total_novedades_pct <= OBJETIVO_NOVEDADES:
        narrativa.append(f"✅ **CUMPLE el objetivo de novedades** (meta: <{OBJETIVO_NOVEDADES}%). ")
    else:
        narrativa.append(f"❌ **NO CUMPLE el objetivo de novedades** (meta: <{OBJETIVO_NOVEDADES}%). ")
    
    narrativa.append("\n")
    
    # 2. Evaluación por sede individual
    narrativa.append("### 🏆 EVALUACIÓN POR SEDE\n")
    narrativa.append("| Sede | Facturación | vs Objetivo | Novedades | vs Objetivo |\n")
    narrativa.append("|------|-------------|-------------|-----------|-------------|\n")
    
    for _, row in df_activas.iterrows():
        sede = row['Sede']
        pct_fact = row['%_facturado']
        pct_nov = row['%_novedades']
        
        fact_icon = "✅" if pct_fact >= OBJETIVO_FACTURACION else "❌"
        nov_icon = "✅" if pct_nov <= OBJETIVO_NOVEDADES else "❌"
        
        narrativa.append(f"| {sede} | {pct_fact:.1f}% | {fact_icon} | {pct_nov:.1f}% | {nov_icon} |\n")
    
    narrativa.append("\n")
    
    # 3. Identificar sedes que requieren atención
    sedes_facturacion_baja = df_activas[df_activas['%_facturado'] < OBJETIVO_FACTURACION]['Sede'].tolist()
    sedes_novedades_alta = df_activas[df_activas['%_novedades'] > OBJETIVO_NOVEDADES]['Sede'].tolist()
    
    if sedes_facturacion_baja or sedes_novedades_alta:
        narrativa.append("### ⚠️ SEDES QUE REQUIEREN ATENCIÓN\n")
        
        if sedes_facturacion_baja:
            narrativa.append(f"**Facturación por debajo del objetivo ({OBJETIVO_FACTURACION}%):** ")
            narrativa.append(f"{', '.join(sedes_facturacion_baja)}\n")
            narrativa.append("  - Revisar procesos de facturación en estas sedes\n")
            narrativa.append("  - Identificar cuellos de botella en el ciclo de facturación\n")
            narrativa.append("  - Implementar seguimiento diario de facturación pendiente\n\n")
        
        if sedes_novedades_alta:
            narrativa.append(f"**Novedades por encima del objetivo ({OBJETIVO_NOVEDADES}%):** ")
            narrativa.append(f"{', '.join(sedes_novedades_alta)}\n")
            narrativa.append("  - Analizar causas raíz de las devoluciones\n")
            narrativa.append("  - Revisar los motivos más frecuentes en la gráfica de Pareto\n")
            narrativa.append("  - Implementar acciones correctivas inmediatas\n\n")
    
    # 4. Análisis de novedades bloqueantes
    avg_bloqueantes = df_activas['%_bloqueantes'].mean()
    
    narrativa.append("### 🔒 NOVEDADES BLOQUEANTES\n")
    narrativa.append(f"En promedio, el **{avg_bloqueantes:.1f}%** de las novedades son bloqueantes, ")
    
    if avg_bloqueantes > 20:
        narrativa.append("lo cual es **CRÍTICO**. Las novedades bloqueantes afectan directamente el flujo de caja ")
        narrativa.append("y requieren atención prioritaria para su resolución.\n")
    elif avg_bloqueantes > 10:
        narrativa.append("lo cual es **MODERADO**. Se recomienda implementar controles preventivos para reducir este indicador.\n")
    else:
        narrativa.append("lo cual es **BAJO**, indicando que la mayoría de novedades son subsanables sin mayor impacto.\n")
    
    # 5. Resumen ejecutivo final con evaluación de objetivos
    narrativa.append("\n### 📌 CONCLUSIÓN FINAL\n")
    
    cumple_facturacion = eficiencia_total >= OBJETIVO_FACTURACION
    cumple_novedades = total_novedades_pct <= OBJETIVO_NOVEDADES
    
    if cumple_facturacion and cumple_novedades:
        narrativa.append(f"✅ **DESEMPEÑO EXCELENTE:** El sistema de facturación está operando al {eficiencia_total:.1f}% de eficiencia ")
        narrativa.append(f"y las novedades están en {total_novedades_pct:.1f}%. ")
        narrativa.append("Se cumplen ambos objetivos estratégicos. Mantener los controles actuales y realizar seguimiento preventivo.")
    elif cumple_facturacion and not cumple_novedades:
        narrativa.append(f"⚠️ **DESEMPEÑO MODERADO:** La facturación está en {eficiencia_total:.1f}% (cumple objetivo), ")
        narrativa.append(f"pero las novedades están en {total_novedades_pct:.1f}% (superan el objetivo del {OBJETIVO_NOVEDADES}%). ")
        narrativa.append("Se recomienda enfocar esfuerzos en reducir las devoluciones y ajustes.")
    elif not cumple_facturacion and cumple_novedades:
        narrativa.append(f"⚠️ **DESEMPEÑO MODERADO:** Las novedades están controladas ({total_novedades_pct:.1f}% < {OBJETIVO_NOVEDADES}%), ")
        narrativa.append(f"pero la facturación está en {eficiencia_total:.1f}% (por debajo del objetivo del {OBJETIVO_FACTURACION}%). ")
        narrativa.append("Se requiere mejorar la eficiencia en el ciclo de facturación.")
    else:
        narrativa.append(f"🔴 **DESEMPEÑO CRÍTICO:** No se cumplen los objetivos estratégicos. ")
        narrativa.append(f"Facturación: {eficiencia_total:.1f}% (meta: >{OBJETIVO_FACTURACION}%), ")
        narrativa.append(f"Novedades: {total_novedades_pct:.1f}% (meta: <{OBJETIVO_NOVEDADES}%). ")
        narrativa.append("Se requiere una intervención inmediata de la gerencia para revisar los procesos.")
    
    return "".join(narrativa)

# Sidebar
with st.sidebar:
    st.header("📋 Información de Sedes")
    for sede, config in SEDES.items():
        fecha_str = config['fecha_inicio'].strftime('%d/%m/%Y')
        st.markdown(f"**{sede}:** Inicio {fecha_str}")

# Interfaz principal
st.markdown("### ⚙️ Configuración del Reporte")

fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 1, 1).date(),
    max_value=fecha_actual.date()
)

archivo = st.file_uploader("Selecciona el archivo Excel", type=['xlsx', 'xls'])

st.markdown("---")

if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    if st.button("📋 Cargar unidades funcionales disponibles"):
        with st.spinner("Cargando..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            st.success(f"✅ {len(unidades)} unidades funcionales encontradas")
    
    if st.session_state.unidades_funcionales:
        # Incluir automáticamente las unidades de CIRCUNVALAR si existen
        default_selection = []
        for u in st.session_state.unidades_funcionales:
            if u in UNIDADES_POR_DEFECTO:
                default_selection.append(u)
            # También incluir unidades que contengan "CIRCUNVALAR"
            elif "CIRCUNVALAR" in u.upper():
                default_selection.append(u)
        
        unidades_seleccionadas = st.multiselect(
            "Selecciona unidades funcionales a incluir:",
            options=st.session_state.unidades_funcionales,
            default=[u for u in st.session_state.unidades_funcionales if u in default_selection] or st.session_state.unidades_funcionales[:10]
        )
        st.session_state.unidades_seleccionadas = unidades_seleccionadas
        
        if unidades_seleccionadas:
            # Verificar si CIRCUNVALAR está seleccionada
            tiene_circunvalar = any("CIRCUNVALAR" in u.upper() for u in unidades_seleccionadas)
            if tiene_circunvalar:
                st.info(f"📌 {len(unidades_seleccionadas)} unidades funcionales seleccionadas - Incluye CIRCUNVALAR")
            else:
                st.info(f"📌 {len(unidades_seleccionadas)} unidades funcionales seleccionadas")
    
    st.markdown("---")
    
    if st.button("📊 Procesar Archivo", type="primary"):
        with st.spinner("Procesando..."):
            exito, dfs, _ = cargar_archivo(archivo, st.session_state.unidades_seleccionadas)
            
            if exito:
                st.session_state.datos_cargados = True
                st.session_state.dfs = dfs
                st.session_state.fecha_hasta = datetime.combine(fecha_hasta, datetime.min.time())
                
                df_resumen = calcular_resumen_ejecutivo(dfs, st.session_state.fecha_hasta)
                st.session_state.resumen_ejecutivo = df_resumen
                
                st.success("✅ Archivo procesado correctamente!")

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
            # Filtrar sedes con datos (ingresos > 0)
            df_resumen_filtrado = st.session_state.resumen_ejecutivo.copy()
            df_resumen_filtrado['Ingresos_num'] = df_resumen_filtrado['Ingresos'].str.replace(',', '').astype(int)
            sedes_con_datos = df_resumen_filtrado[df_resumen_filtrado['Ingresos_num'] > 0]
            sedes_sin_datos = df_resumen_filtrado[df_resumen_filtrado['Ingresos_num'] == 0]
            
            # Mostrar sedes excluidas si las hay
            if not sedes_sin_datos.empty:
                st.warning(f"⚠️ Las siguientes sedes no presentan actividad en el período seleccionado y han sido excluidas del análisis: {', '.join(sedes_sin_datos['Sede'].tolist())}")
                st.markdown("---")
            
            if not sedes_con_datos.empty:
                columnas_mostrar = ['Sede', 'Ingresos', 'Facturado total', 
                                   '% facturado total / ingresos', '% novedades / ingresos',
                                   '% novedades bloqueantes / ingresos']
                
                st.dataframe(sedes_con_datos[columnas_mostrar], use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("**📌 Nota del corte:**")
                for _, row in sedes_con_datos.iterrows():
                    fecha_inicio_str = row['fecha_inicio'].strftime('%d/%m/%Y')
                    fecha_fin_str = row['fecha_fin'].strftime('%d/%m/%Y')
                    st.markdown(f"- **{row['Sede']}:** {fecha_inicio_str} al {fecha_fin_str}")
                
                # Mostrar objetivos
                st.markdown("---")
                st.markdown("### 🎯 OBJETIVOS ESTRATÉGICOS")
                col1, col2 = st.columns(2)
                col1.metric("🎯 Facturación Total / Ingresos", "> 90%", delta="Meta", delta_color="normal")
                col2.metric("🎯 Novedades / Ingresos", "< 5%", delta="Meta", delta_color="normal")
                
                # Generar y mostrar narrativa ejecutiva
                st.markdown("---")
                narrativa = generar_narrativa_ejecutiva(st.session_state.resumen_ejecutivo)
                st.markdown(narrativa)
                
                # Botón para descargar el análisis
                st.markdown("---")
                if st.button("📥 Descargar Análisis Ejecutivo (TXT)"):
                    output = BytesIO()
                    output.write(narrativa.encode('utf-8'))
                    st.download_button(
                        label="📄 Descargar Análisis",
                        data=output.getvalue(),
                        file_name="analisis_ejecutivo.txt",
                        mime="text/plain",
                        key="download_analisis"
                    )
            else:
                st.info("No hay sedes con datos válidos para mostrar en el período seleccionado.")
        else:
            st.info("No hay datos para mostrar en el resumen ejecutivo")
    
    for i, sede in enumerate(sedes_lista):
        with tabs[i + 1]:
            config = SEDES[sede]
            fecha_inicio = config['fecha_inicio']
            
            # Verificar si la fecha de fin es anterior a la fecha de inicio
            if fecha_fin < fecha_inicio:
                st.warning(f"⚠️ La fecha seleccionada ({fecha_fin.strftime('%d/%m/%Y')}) es anterior a la fecha de inicio de {sede} ({fecha_inicio.strftime('%d/%m/%Y')}). No hay datos disponibles.")
                continue
            
            df_ingresos = st.session_state.dfs.get(f'INGRESOS_{sede}', pd.DataFrame())
            df_facturacion = st.session_state.dfs.get(f'FACTURACION_{sede}', pd.DataFrame())
            df_facturacion_detalle = st.session_state.dfs.get(f'FACTURACION_DETALLE_{sede}', pd.DataFrame())
            df_novedades_sede = st.session_state.dfs.get(f'NOVEDADES_DETALLE_{sede}', pd.DataFrame())
            
            with st.spinner(f"Calculando {sede}..."):
                # Tabla principal (inicialmente diaria para cálculos de totales)
                df_tabla = construir_tabla_sede(
                    sede, config, fecha_inicio, fecha_fin, df_ingresos, df_facturacion, df_novedades, 'Diario'
                )
                
                if len(df_tabla) > 0 and df_tabla['ingresos'].sum() > 0:
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
                    
                    # Métricas en la parte superior
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col1.metric("📥 Total Ingresos", f"{total_ingresos:,}")
                    col2.metric("✅ Facturado Modelo", f"{total_facturado_modelo:,}", f"{pct_modelo:.1f}%")
                    col3.metric("❌ Facturado Fuera", f"{total_facturado_fuera:,}", f"{pct_fuera:.1f}%")
                    col4.metric("💰 Facturado Total", f"{total_facturado:,}", f"{pct_total:.1f}%")
                    col5.metric("⚠️ Novedades", f"{total_novedades:,}", f"{pct_novedades:.1f}%")
                    col6.metric("🔒 Novedades Bloqueantes", f"{total_novedades_bloqueantes:,}", f"{pct_bloqueantes:.1f}%")
                    
                    st.markdown("---")
                    
                    # Selector de agrupación (default: Semanal)
                    periodo_key = f"periodo_{sede}"
                    default_periodo = st.session_state.periodos_sedes.get(sede, 'Semanal')
                    periodo = st.selectbox(
                        "📊 Agrupar por:",
                        options=['Diario', 'Semanal', 'Mensual'],
                        index=['Diario', 'Semanal', 'Mensual'].index(default_periodo),
                        key=periodo_key
                    )
                    # Guardar el período seleccionado en session state
                    st.session_state.periodos_sedes[sede] = periodo
                    
                    # Recalcular tabla con el período seleccionado
                    df_tabla = construir_tabla_sede(
                        sede, config, fecha_inicio, fecha_fin, df_ingresos, df_facturacion, df_novedades, periodo
                    )
                    
                    # Tabla de datos detallados
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
                    
                    # Gráfica 1: Tendencia de Ingresos y Facturación
                    if len(df_tabla) > 1:
                        st.markdown("---")
                        st.subheader("📈 Tendencia de Ingresos y Facturación")
                        chart_data = df_tabla[['ingresos', 'facturado total', 'Novedades', 'Novedades Bloqueantes']].copy()
                        chart_data.index = df_tabla['Fecha']
                        st.line_chart(chart_data)
                    
                    # Gráfica 2: Facturación por período
                    st.markdown("---")
                    st.subheader("💰 Facturación por Período")
                    fig_facturacion = graficar_facturacion_temporal(df_tabla, periodo)
                    if fig_facturacion:
                        st.pyplot(fig_facturacion, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos de facturación para mostrar")
                    
                    # Tabla de facturación por usuario (con la agrupación seleccionada)
                    st.markdown("---")
                    st.subheader("👥 Facturación por Usuario (Facturador)")
                    
                    df_usuario = obtener_facturacion_por_usuario(df_facturacion_detalle, fecha_inicio, fecha_fin, periodo)
                    
                    if not df_usuario.empty:
                        # Mostrar tabla
                        st.dataframe(df_usuario, use_container_width=True)
                        
                        # Gráfica de facturación por usuario (estilo mensual apilado - independiente del selector)
                        st.markdown("---")
                        st.subheader("📊 Distribución de Facturación por Usuario (Mensual)")
                        fig_usuario_mensual = graficar_facturacion_por_usuario_mensual(
                            df_facturacion_detalle, fecha_inicio, fecha_fin, sede
                        )
                        if fig_usuario_mensual:
                            st.pyplot(fig_usuario_mensual, use_container_width=True)
                            plt.close()
                        else:
                            st.info("No hay datos suficientes para generar la gráfica de facturación por usuario")
                        
                        # ============ SECCIÓN: Matriz Usuario vs Unidad Funcional ============
                        with st.expander("🏢 Ver Facturación por Usuario vs Unidad Funcional", expanded=False):
                            st.markdown("*Esta tabla muestra la cantidad de registros facturados por cada usuario en cada unidad funcional, basado en los filtros de unidad funcional seleccionados.*")
                            
                            # Generar matriz de usuario vs unidad funcional
                            df_matriz_usuario, df_matriz_unidad = obtener_matriz_usuario_unidad(
                                df_facturacion_detalle, fecha_inicio, fecha_fin, periodo
                            )
                            
                            if not df_matriz_usuario.empty:
                                # Mostrar tabla de usuarios vs unidades
                                st.markdown("**📋 Matriz: Usuarios vs Unidades Funcionales**")
                                st.dataframe(df_matriz_usuario, use_container_width=True)
                                
                                st.markdown("---")
                                
                                # Mostrar tabla transpuesta (unidades vs usuarios)
                                st.markdown("**📋 Matriz: Unidades Funcionales vs Usuarios**")
                                st.dataframe(df_matriz_unidad, use_container_width=True)
                                
                                # Gráfica de calor
                                st.markdown("---")
                                st.markdown("**📊 Mapa de Calor - Facturación por Usuario y Unidad Funcional**")
                                fig_heatmap = graficar_matriz_calor(df_matriz_usuario, f'Distribución de Facturación - {sede}')
                                if fig_heatmap:
                                    st.pyplot(fig_heatmap, use_container_width=True)
                                    plt.close()
                                else:
                                    st.info("No hay suficientes datos para generar el mapa de calor")
                                
                                # Botón para descargar matrices
                                output_matrices = BytesIO()
                                with pd.ExcelWriter(output_matrices, engine='openpyxl') as writer:
                                    # Asegurarse de que los DataFrames tengan formato plano
                                    df_usuario_export = df_matriz_usuario.copy()
                                    df_unidad_export = df_matriz_unidad.copy()
                                    
                                    # Convertir nombres de columnas a string para evitar problemas
                                    df_usuario_export.columns = [str(col) for col in df_usuario_export.columns]
                                    df_unidad_export.columns = [str(col) for col in df_unidad_export.columns]
                                    
                                    df_usuario_export.to_excel(writer, sheet_name='Usuarios_vs_Unidades', index=False)
                                    df_unidad_export.to_excel(writer, sheet_name='Unidades_vs_Usuarios', index=False)
                                
                                st.download_button(
                                    label="📥 Descargar Matrices (Excel)",
                                    data=output_matrices.getvalue(),
                                    file_name=f"{sede.lower().replace(' ', '_')}_matriz_usuario_unidad.xlsx",
                                    key=f"excel_matriz_{sede}_{periodo}"
                                )
                            else:
                                st.info("No hay datos de facturación por usuario y unidad funcional para mostrar en este período")
                        # ============ FIN SECCIÓN ============
                    else:
                        st.info("No hay datos de facturación por usuario para mostrar")
                    
                    # Gráfica 3: Novedades generadas (afectada por el período seleccionado)
                    st.markdown("---")
                    st.subheader("📈 Novedades Generadas")
                    fig_novedades_temp = graficar_novedades_temporales(df_novedades_sede, periodo)
                    if fig_novedades_temp:
                        st.pyplot(fig_novedades_temp, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos de novedades para mostrar en esta sede")
                    
                    # Gráfica 4: Pareto de novedades (NO afectada por el período)
                    st.markdown("---")
                    st.subheader("📊 Pareto de Motivos de Novedades")
                    fig_pareto = graficar_pareto_novedades(df_novedades_sede)
                    if fig_pareto:
                        st.pyplot(fig_pareto, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos suficientes para generar el Pareto de novedades")
                    
                    # Gráfica 5: Distribución por mes (NO afectada por el período)
                    st.markdown("---")
                    st.subheader("📅 Distribución de Motivos por Mes")
                    fig_distribucion = graficar_distribucion_motivos_meses(df_novedades_sede)
                    if fig_distribucion:
                        st.pyplot(fig_distribucion, use_container_width=True)
                        plt.close()
                    else:
                        st.info("No hay datos suficientes para generar la distribución por mes")
                    
                    # Botón de descarga de Excel para esta sede individual (con la agrupación seleccionada)
                    st.markdown("---")
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_tabla.to_excel(writer, sheet_name=f'Resumen_{periodo}', index=False)
                        if not df_usuario.empty:
                            df_usuario.to_excel(writer, sheet_name=f'Facturadores_{periodo}', index=True)
                    
                    st.download_button(
                        "📥 Descargar Excel (Sede)",
                        output.getvalue(),
                        f"{sede.lower().replace(' ', '_')}_{periodo.lower()}.xlsx",
                        key=f"excel_{sede}_{periodo}"
                    )
                elif len(df_tabla) > 0 and df_tabla['ingresos'].sum() == 0:
                    st.info(f"📌 La sede {sede} no tiene ingresos en el período seleccionado (desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')}).")
                else:
                    st.info(f"📌 No hay datos para {sede} en el período seleccionado (desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')}).")
    
    # Botón para exportar TODO (datos + gráficas + narrativa)
    st.markdown("---")
    st.subheader("📥 Exportar Reporte Completo")
    
    if st.button("📊 Exportar todo (Datos + Gráficas + Narrativa a Excel)", type="primary"):
        with st.spinner("Generando archivo Excel con todas las gráficas insertadas..."):
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Crear el archivo Excel con xlsxwriter
                output = BytesIO()
                workbook = xlsxwriter.Workbook(output, {'constant_memory': False})
                
                # Hoja 1: Resumen Ejecutivo (datos)
                if st.session_state.resumen_ejecutivo is not None and not st.session_state.resumen_ejecutivo.empty:
                    df_resumen_export = st.session_state.resumen_ejecutivo.copy()
                    df_resumen_export['Ingresos_num'] = df_resumen_export['Ingresos'].str.replace(',', '').astype(int)
                    df_resumen_export = df_resumen_export[df_resumen_export['Ingresos_num'] > 0]
                    df_resumen_export = df_resumen_export.drop(columns=['Ingresos_num', 'fecha_inicio', 'fecha_fin'], errors='ignore')
                    
                    worksheet = workbook.add_worksheet('Resumen_Ejecutivo')
                    for col_num, value in enumerate(df_resumen_export.columns.values):
                        worksheet.write(0, col_num, value)
                    for row_num, row in enumerate(df_resumen_export.values, 1):
                        for col_num, value in enumerate(row):
                            worksheet.write(row_num, col_num, value)
                
                # Hoja 2: Narrativa Ejecutiva
                worksheet_narrativa = workbook.add_worksheet('Narrativa_Ejecutiva')
                narrativa_texto = generar_narrativa_ejecutiva(st.session_state.resumen_ejecutivo)
                
                # Escribir la narrativa línea por línea
                lineas = narrativa_texto.split('\n')
                for row_num, linea in enumerate(lineas):
                    linea_limpia = linea.replace('##', '').replace('###', '').replace('**', '').replace('📋', '').replace('📊', '').replace('🏆', '').replace('⚠️', '').replace('🔒', '').replace('💡', '').replace('📌', '').strip()
                    worksheet_narrativa.write(row_num, 0, linea_limpia)
                
                # Procesar cada sede con su período seleccionado
                for sede in SEDES.keys():
                    config = SEDES[sede]
                    fecha_inicio = config['fecha_inicio']
                    
                    if fecha_fin >= fecha_inicio:
                        df_ingresos = st.session_state.dfs.get(f'INGRESOS_{sede}', pd.DataFrame())
                        df_facturacion = st.session_state.dfs.get(f'FACTURACION_{sede}', pd.DataFrame())
                        df_facturacion_detalle = st.session_state.dfs.get(f'FACTURACION_DETALLE_{sede}', pd.DataFrame())
                        df_novedades_sede = st.session_state.dfs.get(f'NOVEDADES_DETALLE_{sede}', pd.DataFrame())
                        
                        # Obtener el período seleccionado para esta sede (default: Semanal)
                        periodo_export = st.session_state.periodos_sedes.get(sede, 'Semanal')
                        
                        # Calcular tabla resumen con el período seleccionado
                        df_sede = construir_tabla_sede(
                            sede, config, fecha_inicio, fecha_fin, 
                            df_ingresos, df_facturacion, df_novedades, periodo_export
                        )
                        
                        if not df_sede.empty and df_sede['ingresos'].sum() > 0:
                            sheet_name = sede.replace(' ', '_')[:31]
                            worksheet = workbook.add_worksheet(sheet_name)
                            
                            # Asegurar que Fecha sea string para Excel
                            df_export = df_sede.copy()
                            if 'Fecha' in df_export.columns:
                                df_export['Fecha'] = df_export['Fecha'].dt.strftime('%Y-%m-%d')
                            
                            # Escribir datos principales
                            for col_num, value in enumerate(df_export.columns.values):
                                worksheet.write(0, col_num, value)
                            for row_num, row in enumerate(df_export.values, 1):
                                for col_num, value in enumerate(row):
                                    worksheet.write(row_num, col_num, value)
                            
                            row_start = len(df_export) + 3
                            
                            # Matriz Usuario vs Unidad Funcional
                            df_matriz_usuario, df_matriz_unidad = obtener_matriz_usuario_unidad(
                                df_facturacion_detalle, fecha_inicio, fecha_fin, periodo_export
                            )
                            if not df_matriz_usuario.empty:
                                worksheet.write(row_start, 0, f"Matriz: Usuarios vs Unidades Funcionales")
                                row_start += 1
                                for col_num, value in enumerate(df_matriz_usuario.columns.values):
                                    worksheet.write(row_start, col_num, str(value))
                                for row_num, row in enumerate(df_matriz_usuario.values, row_start + 1):
                                    for col_num, value in enumerate(row):
                                        worksheet.write(row_num, col_num, value)
                                row_start += len(df_matriz_usuario) + 3
                                
                                worksheet.write(row_start, 0, f"Matriz: Unidades Funcionales vs Usuarios")
                                row_start += 1
                                for col_num, value in enumerate(df_matriz_unidad.columns.values):
                                    worksheet.write(row_start, col_num, str(value))
                                for row_num, row in enumerate(df_matriz_unidad.values, row_start + 1):
                                    for col_num, value in enumerate(row):
                                        worksheet.write(row_num, col_num, value)
                                row_start += len(df_matriz_unidad) + 3
                            
                            # Gráfica de Facturación (con el período seleccionado)
                            fig_fact = graficar_facturacion_temporal(df_sede, periodo_export)
                            if fig_fact:
                                img_path = os.path.join(temp_dir, f"{sede}_facturacion.png")
                                fig_fact.savefig(img_path, dpi=100, bbox_inches='tight')
                                worksheet.insert_image(row_start, 0, img_path, {'x_scale': 0.7, 'y_scale': 0.7})
                                plt.close(fig_fact)
                                row_start += 25
                            
                            # Tabla de facturación por usuario (con el período seleccionado)
                            df_usuario = obtener_facturacion_por_usuario(df_facturacion_detalle, fecha_inicio, fecha_fin, periodo_export)
                            if not df_usuario.empty:
                                # Resetear índice para que el nombre del usuario sea una columna
                                df_usuario_export = df_usuario.reset_index()
                                df_usuario_export.columns.name = None
                                
                                # Escribir título de la tabla
                                worksheet.write(row_start, 0, f"Facturación por Usuario ({periodo_export})")
                                row_start += 1
                                
                                # Escribir datos de la tabla (incluyendo la columna de usuario)
                                for col_num, value in enumerate(df_usuario_export.columns.values):
                                    worksheet.write(row_start, col_num, value)
                                for row_num, row in enumerate(df_usuario_export.values, row_start + 1):
                                    for col_num, value in enumerate(row):
                                        worksheet.write(row_num, col_num, value)
                                
                                row_start += len(df_usuario_export) + 3
                                
                                # Gráfica de facturación por usuario (mensual apilada - independiente)
                                fig_usuario_mensual = graficar_facturacion_por_usuario_mensual(
                                    df_facturacion_detalle, fecha_inicio, fecha_fin, sede
                                )
                                if fig_usuario_mensual:
                                    img_path = os.path.join(temp_dir, f"{sede}_usuarios_mensual.png")
                                    fig_usuario_mensual.savefig(img_path, dpi=100, bbox_inches='tight')
                                    worksheet.insert_image(row_start, 0, img_path, {'x_scale': 0.7, 'y_scale': 0.7})
                                    plt.close(fig_usuario_mensual)
                                    row_start += 25
                            
                            # Gráfica de Novedades Temporales (con el período seleccionado)
                            fig_nov_temp = graficar_novedades_temporales(df_novedades_sede, periodo_export)
                            if fig_nov_temp:
                                img_path = os.path.join(temp_dir, f"{sede}_novedades_temp.png")
                                fig_nov_temp.savefig(img_path, dpi=100, bbox_inches='tight')
                                worksheet.insert_image(row_start, 0, img_path, {'x_scale': 0.7, 'y_scale': 0.7})
                                plt.close(fig_nov_temp)
                                row_start += 25
                            
                            # Gráfica de Pareto
                            fig_pareto = graficar_pareto_novedades(df_novedades_sede)
                            if fig_pareto:
                                img_path = os.path.join(temp_dir, f"{sede}_pareto.png")
                                fig_pareto.savefig(img_path, dpi=100, bbox_inches='tight')
                                worksheet.insert_image(row_start, 0, img_path, {'x_scale': 0.7, 'y_scale': 0.7})
                                plt.close(fig_pareto)
                                row_start += 25
                            
                            # Gráfica de Distribución
                            fig_dist = graficar_distribucion_motivos_meses(df_novedades_sede)
                            if fig_dist:
                                img_path = os.path.join(temp_dir, f"{sede}_distribucion.png")
                                fig_dist.savefig(img_path, dpi=100, bbox_inches='tight')
                                worksheet.insert_image(row_start, 0, img_path, {'x_scale': 0.7, 'y_scale': 0.7})
                                plt.close(fig_dist)
                
                workbook.close()
                
                # Limpiar archivos temporales
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
                
                st.success("✅ Reporte completo generado exitosamente!")
                st.download_button(
                    label="📥 Descargar Reporte Completo (Datos + Gráficas + Narrativa)",
                    data=output.getvalue(),
                    file_name=f"reporte_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Error al generar el reporte: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
                # Limpiar archivos temporales en caso de error
                for file in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, file))
                    except:
                        pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
    
    if st.button("🔄 Reiniciar"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

else:
    st.info("👆 Carga un archivo Excel para comenzar")

st.markdown("---")
st.caption("Aplicación para análisis de facturación por sede")
