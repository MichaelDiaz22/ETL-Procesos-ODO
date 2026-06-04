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

# Unidades funcionales por defecto
UNIDADES_POR_DEFECTO = [
    "CONSULTA ESPECIALIZADA SAN MARCEL",
    "CONSULTA ESPECIALIZADA CENTENARIO",
    "CONSULTA ESPECIALIZADA MARAYA",
    "LABORATORIO CLINICO MARAYA",
    "PROCEDIMIENTOS MENORES CONSULTA CENTENARIO",
    "PROCEDIMIENTOS MENORES CONSULTA SAN MARCEL",
    "RADIOTERAPIA CENTENARIO"
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
        "fecha_inicio": datetime(2026, 4, 15),
        "centro_atencion": None,
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
        unidades_filtro_sede = [u for u in unidades_filtro if any(clave in u for clave in config['unidades_clave'])]
        if unidades_filtro_sede:
            mask_unidades = valores_funcionales.isin(unidades_filtro_sede)
        else:
            return pd.DataFrame()
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
            return pd.DataFrame()
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
    """Procesa hojas EVENTO y PGP para facturación"""
    col_fecha_ingreso = None
    col_fecha_factura = None
    col_unidad_funcional = None
    col_unidad_operativa = None
    
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
    
    # Filtrar por unidades funcionales seleccionadas
    if unidades_filtro and len(unidades_filtro) > 0:
        unidades_filtro_sede = [u for u in unidades_filtro if any(clave in u for clave in config['unidades_clave'])]
        if unidades_filtro_sede:
            mask_unidades = valores_funcionales.isin(unidades_filtro_sede)
        else:
            return pd.DataFrame()
    else:
        mask_unidades = valores_funcionales.str.contains('|'.join(config['unidades_clave']), na=False, regex=False)
    
    df_temp = pd.DataFrame({
        '_fecha_ingreso': fechas_ingreso,
        '_fecha_factura': fechas_factura,
        '_valor_funcional': valores_funcionales
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
        
        dfs_resultado['NOVEDADES'] = df_novedades
        
        # Procesar novedades completas para cada sede
        for sede, config in SEDES.items():
            if config['centro_atencion']:
                df_novedades_sede = procesar_novedades_completo(df_novedades, config['centro_atencion'])
                dfs_resultado[f'NOVEDADES_DETALLE_{sede}'] = df_novedades_sede
            else:
                dfs_resultado[f'NOVEDADES_DETALLE_{sede}'] = pd.DataFrame()
        
        # Mostrar resumen
        st.write("---")
        st.write("### 📊 RESUMEN DE INGRESOS")
        for sede in SEDES.keys():
            total = len(dfs_resultado[f'INGRESOS_{sede}'])
            st.write(f"**{sede}:** {total:,} registros")
        
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

def graficar_pareto_novedades(df_novedades_sede):
    """Gráfica de Pareto de motivos de novedades usando matplotlib"""
    if df_novedades_sede.empty or '_motivo' not in df_novedades_sede.columns:
        return None
    
    # Contar motivos
    conteo_motivos = df_novedades_sede['_motivo'].value_counts().reset_index()
    conteo_motivos.columns = ['Motivo', 'Frecuencia']
    
    # Limitar a top 15 para mejor visualización
    if len(conteo_motivos) > 15:
        otros = pd.DataFrame({
            'Motivo': ['OTROS'],
            'Frecuencia': [conteo_motivos.iloc[15:]['Frecuencia'].sum()]
        })
        conteo_motivos = pd.concat([conteo_motivos.iloc[:15], otros], ignore_index=True)
    
    # Calcular porcentaje acumulado
    total = conteo_motivos['Frecuencia'].sum()
    conteo_motivos['Porcentaje'] = (conteo_motivos['Frecuencia'] / total * 100).round(2)
    conteo_motivos['Porcentaje Acumulado'] = conteo_motivos['Porcentaje'].cumsum()
    
    # Crear gráfica con dos ejes
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # Barras para frecuencias
    x = range(len(conteo_motivos))
    bars = ax1.bar(x, conteo_motivos['Frecuencia'], color='#FF6B6B', alpha=0.7, label='Frecuencia')
    ax1.set_xlabel('Motivos', fontsize=12)
    ax1.set_ylabel('Frecuencia', fontsize=12, color='#FF6B6B')
    ax1.tick_params(axis='y', labelcolor='#FF6B6B')
    
    # Línea para porcentaje acumulado
    ax2 = ax1.twinx()
    line = ax2.plot(x, conteo_motivos['Porcentaje Acumulado'], color='#2C3E50', 
                   marker='o', linewidth=2, markersize=8, label='% Acumulado')
    ax2.set_ylabel('Porcentaje Acumulado (%)', fontsize=12, color='#2C3E50')
    ax2.tick_params(axis='y', labelcolor='#2C3E50')
    
    # Configurar etiquetas del eje X
    ax1.set_xticks(x)
    ax1.set_xticklabels(conteo_motivos['Motivo'], rotation=45, ha='right', fontsize=10)
    
    # Agregar línea del 80%
    ax2.axhline(y=80, color='red', linestyle='--', alpha=0.5, linewidth=2, label='80%')
    
    # Agregar valores en las barras
    for bar, valor in zip(bars, conteo_motivos['Frecuencia']):
        if valor > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    str(valor), ha='center', va='bottom', fontsize=8)
    
    # Agregar título y leyenda
    plt.title('Pareto de Motivos de Novedades', fontsize=14, fontweight='bold')
    
    # Combinar leyendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    
    ax1.grid(True, alpha=0.3, axis='y')
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
        bars = ax.bar(range(len(top_motivos.columns)), valores, bottom=bottom, 
                      label=motivo, color=colores[i], alpha=0.8)
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

# Sidebar
with st.sidebar:
    st.header("📋 Información de Sedes")
    for sede, config in SEDES.items():
        fecha_str = config['fecha_inicio'].strftime('%d/%m/%Y')
        st.markdown(f"**{sede}:** Inicio {fecha_str}")

# Interfaz principal
st.header("📁 Cargar Archivo")

st.markdown("### ⚙️ Configuración del Reporte")

fecha_actual = datetime.now()

fecha_hasta = st.date_input(
    "📅 Seleccionar fecha final del reporte:",
    value=fecha_actual.date(),
    min_value=datetime(2025, 1, 1).date(),
    max_value=fecha_actual.date()
)

st.markdown("---")

archivo = st.file_uploader("Selecciona el archivo Excel", type=['xlsx', 'xls'])

if archivo:
    st.markdown("### 🔍 Filtro por Unidad Funcional")
    
    if st.button("📋 Cargar unidades funcionales disponibles"):
        with st.spinner("Cargando..."):
            unidades = obtener_unidades_funcionales(archivo)
            st.session_state.unidades_funcionales = unidades
            st.success(f"✅ {len(unidades)} unidades funcionales encontradas")
    
    if st.session_state.unidades_funcionales:
        unidades_seleccionadas = st.multiselect(
            "Selecciona unidades funcionales a incluir:",
            options=st.session_state.unidades_funcionales,
            default=[u for u in st.session_state.unidades_funcionales if u in UNIDADES_POR_DEFECTO]
        )
        st.session_state.unidades_seleccionadas = unidades_seleccionadas
        
        if unidades_seleccionadas:
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
                    
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col1.metric("📥 Total Ingresos", f"{total_ingresos:,}")
                    col2.metric("✅ Facturado Modelo", f"{total_facturado_modelo:,}", f"{pct_modelo:.1f}%")
                    col3.metric("❌ Facturado Fuera", f"{total_facturado_fuera:,}", f"{pct_fuera:.1f}%")
                    col4.metric("💰 Facturado Total", f"{total_facturado:,}", f"{pct_total:.1f}%")
                    col5.metric("⚠️ Novedades", f"{total_novedades:,}", f"{pct_novedades:.1f}%")
                    col6.metric("🔒 Novedades Bloqueantes", f"{total_novedades_bloqueantes:,}", f"{pct_bloqueantes:.1f}%")
                    
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
