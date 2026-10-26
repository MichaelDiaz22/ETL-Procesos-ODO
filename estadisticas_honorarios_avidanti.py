import streamlit as st
import pandas as pd
import hashlib
import re
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="ANÁLISIS DE HONORARIOS MÉDICOS", page_icon="📊", layout="wide")

st.title("📊 ANÁLISIS DE GESTIÓN DE HONORARIOS MÉDICOS POR INTERFAZ")
st.markdown(
    "Carga múltiples archivos Excel. Se clasificarán automáticamente en "
    "**Ventas**, **Atenciones del especialista**, **Totales** o **Histórico**."
)

# ============================================================
# CONSTANTES GLOBALES
# ============================================================
ESTRUCTURAS = {
    "Ventas": [
        "Sede", "Ingreso No.", "Fecha Ingreso", "Número de autorización",
        "Fecha Egreso", "Nombre Contrato", "Nombre Plan", "Tipo Documento",
        "Documento No.", "Primer Apellido", "Segundo Apellido", "Primer Nombre",
        "Segundo Nombre", "Edad", "Sexo", "Clase de ingreso", "NIT",
        "Aseguradora", "Contrato", "Ubicación Consumo", "Servicio de ingreso",
        "Centro de costo", "Ubicación despacho", "Venta No.", "Fecha Venta",
        "Fecha registro venta factura", "Usuario que vende", "Origen del proceso",
        "Tipo de producto", "Categoria de producto", "Código Producto",
        "Nombre del Producto", "Cantidad", "Valor Unitario", "Valor Total",
        "Valor Unitario Recalculado", "Valor Total Recalculado", "Valor facturado",
        "Cantidades Eliminadas/Devueltas", "Manual Tarifario",
        "Manual Tarifario Recalculado", "Proceso Eliminada/Devuelta",
        "Proceso de unificación", "Ingreso de origen", "Estado",
        "Grupo de Presupuesto", "Número Factura", "Aseguradora Factura",
        "Plan Factura", "Fecha Factura", "Tipo Factura",
        "Número recibo de caja", "Valor cruzado", "Venta no cobrable",
        "Código", "Nombre", "Número de identificación del profesional",
        "Nombre del profesional"
    ],
    "Atenciones del especialista": [
        "Sede", "Periodo", "CC / Id Especialista", "Especialista Médico",
        "Nit / Beneficiario", "Nombre Beneficiario", "Medico de la venta",
        "Id de la interfaz / ID Transacción", "Id / No. Verificación",
        "Numero Venta", "Fecha de la venta", "Ubicación de la venta",
        "Tipo de producto", "Categoría", "Codigo de producto",
        "Nombre del producto Venta", "Ingreso", "Nombre Paciente", "Cantidad",
        "Estado de la venta", "Valor liquidado", "CC Usuario que verifica",
        "Nombre de Usuario que Verifica", "Fecha y hora registro",
        "ID/No de autorización",
        "CC (Usuario que autoriza “Subgerente medico”)",
        "Usuario / Sub Medico",
        "Fecha y Hora de registro de la Autorizaión"
    ],
    "Totales": [
        "periodo", "Numero de identificaciÃ³n del Gremio", "Gremio", "documento",
        "profesional", "Concepto", "No. de venta", "Fecha de venta", "Ingreso",
        "Paciente", "Centro De Costo", "Area De Negocio", "Tipo De Producto",
        "producto", "cantidad ventas", "valor tarifa ventas", "valor recargo ventas",
        "inicio visita", "fin visita", "valor tarifa visita", "valor recargo visita",
        "ingreso visita", "Forma de calculo tarifa", "Valor Configurado tarifa",
        "Forma de calculo Recargo/descuento", "Valor Configurado Recargo/descuento",
        "Total tarifas y recargos/descuentos", "Total impuestos", "Total cargos",
        "Total pagos", "Total", "liquidacion", "tarifas (reliquidado)",
        "recargos/descuentos (reliquidado)", "neto", "Usuario que elimino",
        "Fecha de eliminaciÃ³n", "DescripciÃ³n de eliminaciÃ³n"
    ],
}

UMBRAL_COINCIDENCIA = 0.60

MAPA_FASES = [
    ("ADC", "VILL-Oncología", "Fase 1"), ("ADC", "VILL-Rehabilitación Cardiaca", "Fase 1"),
    ("ADC", "VILL-Consulta Externa", "Fase 1"), ("ADC", "VILL-Hospitalización 2 Piso", "Fase 2"),
    ("ADC", "VILL-Hemodinamia", "Fase 3"), ("ADC", "VILL-Laboratorio Clínico", "Fase 1"),
    ("ADC", "VILL-UCINT 6 Piso", "Fase 2"), ("ADC", "VILL-UCI 5 Piso", "Fase 2"),
    ("ADC", "VILL-Imagenología", "Fase 1"), ("ADC", "VILL-Sala de Cirugía 1 Cardiovascular", "Fase 3"),
    ("ADC", "VILL-Hospitalización 6 Piso", "Fase 2"), ("ADC", "VILL-Sala de Cirugía 2", "Fase 3"),
    ("ADC", "VILL-Electrofisiologia", "Fase 1"), ("ADC", "VILL-Gestión Pre-transfusional", "Fase 1"),
    ("ADC", "SAN-Consulta Externa", "Fase 1"), ("ADC", "uci adultos vill", "Fase 2"),
    ("ADC", "estancia vill", "Fase 2"), ("ADC", "uci intermedia vill", "Fase 2"),
    ("ADC", "salas de cirugia vill", "Fase 3"), ("ADC", "sala de cirugia cardiovascular vill", "Fase 3"),
    ("CAA", "CAA-Hospitalización 5 Piso", "Fase 2"), ("CAA", "CAA-Urgencias", "Fase 2"),
    ("CAA", "CAA-Consulta Externa", "Fase 1"), ("CAA", "CAA-Sala de Cirugía 3", "Fase 3"),
    ("CAA", "CAA-Sala de Cirugía 4", "Fase 3"), ("CAA", "CAA-Hemodinamia", "Fase 3"),
    ("CAA", "CAC-UCINT Adulto", "Fase 2"), ("CAA", "CAA-UCI Adulto", "Fase 2"),
    ("CAA", "CAA-Imagenología", "Fase 1"), ("CAA", "CAA-Cardiología No Invasiva", "Fase 1"),
    ("CAA", "CAA-Laboratorio Clínico", "Fase 1"), ("CAA", "caa estancia piso 5", "Fase 2"),
    ("CAA", "caa uci adultos", "Fase 2"), ("CAA", "caa cons ext", "Fase 1"),
    ("CAA", "caa salas de cirugia", "Fase 3"),
    ("CAI", "CAI-Consulta Externa Nueva", "Fase 1"), ("CAI", "CAI-Sala de Cirugía 2", "Fase 3"),
    ("CAI", "CAI-Urgencias Nueva", "Fase 2"), ("CAI", "CAI-Hospitalización 6 Piso Norte Nueva", "Fase 2"),
    ("CAI", "CAI-Hospitalización 5 Piso Norte Nueva", "Fase 2"), ("CAI", "CAI-UCI 2 Piso 2 Nueva", "Fase 2"),
    ("CAI", "CAI-Hospitalización 5 Piso Sur Nueva", "Fase 2"), ("CAI", "CAI-Hospitalización 4 Piso Sur Nueva", "Fase 2"),
    ("CAI", "CAI-Sala de Cirugía 4 (Urgencias)", "Fase 2"), ("CAI", "CAI-Hospitalización 6 Piso Sur Nueva", "Fase 2"),
    ("CAI", "CAI-UCINT Piso 2 Nueva", "Fase 2"), ("CAI", "CAI-UCI 1 Piso 2 Nueva", "Fase 2"),
    ("CAI", "CAI-Electrofisiología", "Fase 1"), ("CAI", "CAI-Imagenologia", "Fase 1"),
    ("CAI", "CAI-Sala de Cirugía 1 (Cardiovascular)", "Fase 3"), ("CAI", "CAI-Cardiología No Invasiva Nueva", "Fase 1"),
    ("CAI", "CAI-Sala de Cirugía 3", "Fase 3"), ("CAI", "CAI-Hemodinamia", "Fase 3"),
    ("CAI", "CAI-Laboratorio Clínico", "Fase 1"), ("CAI", "CAI-TeleConsulta", "Fase 1"),
    ("CAI", "CAI-Gestion pre transfusional", "Fase 1"), ("CAI", "CAI-Terapias", "Fase 1"),
    ("CAI", "urgencias cai", "Fase 2"), ("CAI", "uci adultos 1 cai", "Fase 2"),
    ("CAI", "estancia piso 6 cai", "Fase 2"), ("CAI", "estancia piso 5 cai", "Fase 2"),
    ("CAI", "estancia piso 4 cai", "Fase 2"), ("CAI", "uci intermedio adultos cai", "Fase 2"),
    ("CAI", "salas de cirugia cai", "Fase 3"), ("CAI", "sala de cirugia cardiovascular cai", "Fase 3"),
    ("CAI", "trasplante renal cai", "Fase 3"),
    ("CAM", "CAM-Consulta Externa", "Fase 1"), ("CAM", "CAM-Urgencias", "Fase 2"),
    ("CAM", "CAM-Hospitalización 7 Piso Sur", "Fase 2"), ("CAM", "CAM-Hospitalización 6 Piso Norte", "Fase 2"),
    ("CAM", "CAM-Hospitalización 4 Piso Sur", "Fase 2"), ("CAM", "CAM-UCI 7 Piso", "Fase 2"),
    ("CAM", "CAM-Hospitalización 6 Piso Sur", "Fase 2"), ("CAM", "CAM-Sala de Cirugía 1 (Urgencias)", "Fase 2"),
    ("CAM", "CAM-Sala de Cirugía 4", "Fase 3"), ("CAM", "CAM-Sala de Cirugía 3", "Fase 3"),
    ("CAM", "CAM-Sala de Cirugía 2", "Fase 3"), ("CAM", "CAM-Sala de Cirugía 5", "Fase 3"),
    ("CAM", "CAM-Hospitalización 3 Piso Sur", "Fase 2"), ("CAM", "CAM-Hospitalización 3 Piso Norte", "Fase 2"),
    ("CAM", "CAM-Hospitalización 5 Piso Sur", "Fase 2"), ("CAM", "CAM-UCINT 3 Piso", "Fase 2"),
    ("CAM", "CAM-UCI 3 Piso", "Fase 2"), ("CAM", "CAM-TeleConsulta", "Fase 1"),
    ("CAM", "CAM- Sala de Cirugía 7", "Fase 3"), ("CAM", "CAM-UCINT 5 Piso", "Fase 2"),
    ("CAM", "CAM-Cardiología No Invasiva", "Fase 1"), ("CAM", "CAM-Hemodinamia Piso 5", "Fase 3"),
    ("CAM", "CAM-Electrofisiología Piso 5", "Fase 1"), ("CAM", "CAM-Resonancia Magnética", "Fase 1"),
    ("CAM", "CAM-Imagenología", "Fase 1"), ("CAM", "CAM-Sala de Cirugía 6 Cardiovascular", "Fase 3"),
    ("CAM", "CAM-Laboratorio Clínico", "Fase 1"), ("CAM", "CAM - Sala de Cirugía 8", "Fase 3"),
    ("CAM", "CAM - Terapias", "Fase 1"), ("CAM", "CAM - Hospitalizacion 4 piso norte", "Fase 2"),
    ("CAM", "estancia piso 6 cam", "Fase 2"), ("CAM", "estancia piso 3 cam", "Fase 2"),
    ("CAM", "estancia piso 7 cam", "Fase 2"), ("CAM", "estancia piso 4 cam", "Fase 2"),
    ("CAM", "estancia piso 5 cam", "Fase 2"), ("CAM", "uci intermedio adultos cam", "Fase 2"),
    ("CAM", "salas de cirugia cam", "Fase 3"), ("CAM", "sala de cirugia cardiovascular cam", "Fase 3"),
    ("CASM", "CASM- Consulta Externa", "Fase 1"), ("CASM", "CASM-Hospitalización VIP 2", "Fase 2"),
    ("CASM", "CASM-Hospitalización 2 Piso Norte", "Fase 2"), ("CASM", "CASM-Hospitalización 2 Piso Sur", "Fase 2"),
    ("CASM", "CASM-Urgencias", "Fase 2"), ("CASM", "CASM-Hospitalización VIP 1", "Fase 2"),
    ("CASM", "CASM-Hospitalización 1 piso Norte", "Fase 2"), ("CASM", "CASM-Hospitalización 1 piso", "Fase 2"),
    ("CASM", "CASM-UCI Adulto 1", "Fase 2"), ("CASM", "CASM-Sala de Cirugía 2", "Fase 3"),
    ("CASM", "CASM-UCINT", "Fase 2"), ("CASM", "CASM-UCI Adulto 2", "Fase 2"),
    ("CASM", "CASM-Hospitalización 2 Piso Centro", "Fase 2"), ("CASM", "CASM-Cardiología No Invasiva", "Fase 1"),
    ("CASM", "CASM-Sala de Cirugía 4", "Fase 3"), ("CASM", "CASM-Sala de Preparacion Cirugia", "Fase 3"),
    ("CASM", "CASM-Sala de Cirugía 3 (Urgencias)", "Fase 2"), ("CASM", "CASM- Hemodinamia", "Fase 3"),
    ("CASM", "CASM-Imagenología", "Fase 1"), ("CASM", "CASM-Sala de Cirugía 1 Cardiovascular", "Fase 3"),
    ("CASM", "CASM-Recuperación Cirugía", "Fase 3"), ("CASM", "CASM-Laboratorio Clínico", "Fase 1"),
    ("CASM", "CASM-Electrofisiología", "Fase 1"), ("CASM", "CASM-Gestion pre transfusional", "Fase 1"),
    ("CASM", "CASM-Hemodialisis", "Fase 3"), ("CASM", "CASM-Tomografia", "Fase 1"),
    ("CASM", "estancia piso 1 casm", "Fase 2"), ("CASM", "uci adultos 1 casm", "Fase 2"),
    ("CASM", "estancia piso 2 casm", "Fase 2"), ("CASM", "uci adultos 2 casm", "Fase 2"),
    ("CASM", "uci intermedia adulto casm", "Fase 2"), ("CASM", "salas de cirugia casm", "Fase 3"),
    ("CASM", "sala de cirugia cardiovascular casm", "Fase 3"),
    ("CACV", "CACV-Hospitalización 5 Piso Norte", "Fase 2"), ("CACV", "CACV-Hospitalización 5 Piso Sur", "Fase 2"),
    ("CACV", "CACV-Laboratorio Clínico", "Fase 1"), ("CACV", "CACV-Urgencias", "Fase 2"),
    ("CACV", "CACV-Imagenología", "Fase 1"), ("CACV", "CACV-Sala de Cirugía 3", "Fase 3"),
    ("CACV", "CACV-Sala de Cirugía 4", "Fase 3"), ("CACV", "CACV-Unidad Basico Neonatal", "Fase 2"),
    ("CACV", "CACV-Terapias", "Fase 1"), ("CACV", "CACV-Gestión Pre-transfusional", "Fase 1"),
    ("CACV", "CACV-Sala de Cirugía 5", "Fase 3"), ("CACV", "CACV-Hospitalización 6 Piso Norte", "Fase 2"),
    ("CACV", "CACV-Hospitalización 6 Piso Sur", "Fase 2"), ("CACV", "CACV- Hemodinamia 1", "Fase 3"),
    ("CACV", "CACV-UCI Adulto", "Fase 2"), ("CACV", "CACV-UCINT Adulto", "Fase 2"),
    ("CACV", "CACV-UCI Neonatal", "Fase 2"), ("CACV", "CACV-Sala de Partos 1", "Fase 3"),
    ("CACV", "CACV-Sala Trabajo de Parto", "Fase 3"), ("CACV", "CACV- Consulta Externa", "Fase 1"),
    ("CACV", "CACV-UCINT Neonatal", "Fase 2"), ("CACV", "CACV-Sala Postparto", "Fase 3"),
    ("CACV", "CACV-Sala de Cesaria", "Fase 3"), ("CACV", "CACV-Sala de Partos 2", "Fase 3"),
    ("CACV", "CACV-Ecografía", "Fase 1"), ("CACV", "CACV-UCINT Alto Riesgo", "Fase 2"),
    ("CACV", "CACV-Sala de Procedimientos", "Fase 3"), ("CACV", "CACV-Tomografía", "Fase 1"),
    ("CACV", "CACV-Resonancia Magnética", "Fase 1"), ("CACV", "CACV-Recuperación Cirugía", "Fase 3"),
    ("CACV", "CACV-Cardiología No Invasiva", "Fase 1"), ("CACV", "estancia piso 5 cacv", "Fase 2"),
    ("CACV", "estancia piso 6 cacv", "Fase 2"), ("CACV", "uci adultos cacv", "Fase 2"),
    ("CACV", "sala de partos cacv", "Fase 3"), ("CACV", "uci alto riesgo obstetrico uaro", "Fase 2"),
    ("CACV", "salas de cirugia cacv", "Fase 3"), ("CACV", "sala de cesarea cacv", "Fase 3"),
]

COLUMNAS_RESUMEN = [
    "Angiografía Villavicencio", "Clínica Avidanti Ibagué", "Clínica Avidanti Manizales",
    "Clínica Avidanti Santa Marta", "Clínica Avidanti Ciudad Verde", "Clínica Avidanti Armenia",
]

CODIGOS_SEDE = ["ADC", "CAI", "CAM", "CASM", "CACV", "CAA"]
MAPA_CODIGO_A_COLUMNA = dict(zip(CODIGOS_SEDE, COLUMNAS_RESUMEN))
FASES = ["Fase 1", "Fase 2", "Fase 3"]
TITULOS_FASES = {"Fase 1": "FASE 1 - AMBULATORIO", "Fase 2": "FASE 2 - HOSPITALARIO", "Fase 3": "FASE 3 - QUIRÚRGICO"}
NOMBRES_FASES_LARGOS = {"Fase 1": "Fase 1 - Ambulatorio", "Fase 2": "Fase 2 - Hospitalario", "Fase 3": "Fase 3 - Quirúrgico"}
ESTADOS_ACTIVA_FACTURADA = {"activa", "facturada"}
ESTADO_FACTURADA = {"facturada"}
MESES_ES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
SUFIJOS_POR_TABLA = {"Fase 1": "consulta externa", "Fase 2": "hospitalario", "Fase 3": "quirúrgico", "Consolidado": "consolidado"}
PREFIJOS_POR_TABLA = {"Fase 1": "ambulatorio", "Fase 2": "hospitalario", "Fase 3": "quirúrgico", "Consolidado": "consolidado"}

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def normalizar(s):
    if pd.isna(s): return ""
    txt = str(s).strip().lower()
    txt = (txt.replace("Ã³", "o").replace("Ã¡", "a").replace("Ã©", "e").replace("Ã", "i").replace("Ãº", "u"))
    txt = (txt.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    txt = re.sub(r"[_\-\.,/()]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

ESTRUCTURAS_NORM = {nombre: {normalizar(c) for c in cols} for nombre, cols in ESTRUCTURAS.items()}

def clasificar_estructura(columnas_df):
    cols_df_norm = {normalizar(c) for c in columnas_df}
    mejor = (None, 0.0)
    for nombre, esperadas in ESTRUCTURAS_NORM.items():
        if not esperadas: continue
        coincidencias = len(esperadas & cols_df_norm)
        score = coincidencias / len(esperadas)
        if score > mejor[1]: mejor = (nombre, score)
    return mejor

def obtener_columna(df, nombre_esperado):
    objetivo = normalizar(nombre_esperado)
    for c in df.columns:
        if normalizar(c) == objetivo: return c
    return None

def hash_df(df):
    return hashlib.md5(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()

def es_vacio(serie):
    s = serie.astype(str).str.strip()
    return ~s.isin(["", "nan", "None", "NaN", "null", "NULL"])

def normalizar_llave_venta(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except: pass
    s = str(v).strip()
    if s.endswith(".0"): s = s[:-2]
    if s.isdigit(): s = s.lstrip("0") or "0"
    return s

def convertir_a_numero(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace(" ", "", regex=False).str.strip(),
        errors="coerce"
    ).fillna(0)

MAPA_UBICACION = {normalizar(ubicacion): (sede_cod, str(fase).strip()) for sede_cod, ubicacion, fase in MAPA_FASES}

def _palabras_clave(texto):
    palabras = normalizar(texto).split()
    return frozenset(p for p in palabras if p != "vill")

MAPA_UBICACION_TOKENS = {ubi_norm: (sede, fase, _palabras_clave(ubi_norm)) for ubi_norm, (sede, fase) in MAPA_UBICACION.items()}

def detectar_ubicacion_robusta(valor):
    if pd.isna(valor): 
        return (None, None)
    txt_norm = normalizar(valor)
    if txt_norm in MAPA_UBICACION: 
        return MAPA_UBICACION[txt_norm]
        
    tokens_valor = _palabras_clave(txt_norm)
    mejor_match, mejor_score = None, 0
    sedes_mencionadas = [cod for cod in CODIGOS_SEDE if cod.lower() in tokens_valor]
    
    # 1. Match estricto (todos los tokens del mapa están en el valor)
    for ubi_norm, (sede, fase, tokens_ubi) in MAPA_UBICACION_TOKENS.items():
        if sedes_mencionadas and sede not in sedes_mencionadas:
            continue
        if tokens_ubi and tokens_ubi.issubset(tokens_valor):
            score = len(tokens_ubi)
            if score > mejor_score:
                mejor_score, mejor_match = score, (sede, fase)
    
    # 2. Si no hubo match estricto, intentar match por intersección significativa
    if not mejor_match:
        for ubi_norm, (sede, fase, tokens_ubi) in MAPA_UBICACION_TOKENS.items():
            if sedes_mencionadas and sede not in sedes_mencionadas:
                continue
            if not tokens_ubi:
                continue
            interseccion = tokens_ubi & tokens_valor
            # Ignorar tokens genéricos que no aportan (como números de centro de costo)
            interseccion_sig = {t for t in interseccion if not t.isdigit()}
            if len(interseccion_sig) >= 2:
                cobertura = len(interseccion_sig) / len(tokens_ubi)
                if cobertura >= 0.5:
                    score = len(interseccion_sig)
                    if score > mejor_score:
                        mejor_score, mejor_match = score, (sede, fase)
                
    if not mejor_match and sedes_mencionadas:
        return (sedes_mencionadas[0], "Fase 2")

    return mejor_match if mejor_match else (None, None)

def extraer_periodo_desde_nombre(nombre_archivo):
    base = str(nombre_archivo).rsplit(".", 1)[0]
    base_norm = base.lower()
    m = re.search(r"(20\d{2})[-_/]?(0?[1-9]|1[0-2])(?:[-_/]|$|\D)", base_norm)
    if m: return int(m.group(1)), int(m.group(2))
    m = re.search(r"(?<!\d)(0?[1-9]|1[0-2])[-_/](20\d{2})(?!\d)", base_norm)
    if m: return int(m.group(2)), int(m.group(1))
    meses_norm = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
    for nombre_mes, num_mes in meses_norm.items():
        if nombre_mes in base_norm:
            m_anio = re.search(r"(20\d{2})", base_norm)
            if m_anio: return int(m_anio.group(1)), num_mes
            return datetime.now().year, num_mes
    abrev = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
    for nombre_mes, num_mes in abrev.items():
        if re.search(rf"\b{nombre_mes}\b", base_norm):
            m_anio = re.search(r"(20\d{2})", base_norm)
            if m_anio: return int(m_anio.group(1)), num_mes
    return (None, None)

def formatear_periodo(anio, mes):
    if anio is None or mes is None: return ("—", None, None)
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = fecha_inicio + relativedelta(months=1) - relativedelta(days=1)
    etiqueta = f"{MESES_ES[mes]} {anio}"
    return (etiqueta, fecha_inicio.date(), fecha_fin.date())

def es_hoja_de_resultados(df):
    if df is None or df.empty: return False
    primera_col = df.iloc[:, 0].astype(str).tolist()
    textos_norm = [normalizar(v) for v in primera_col]
    titulos_clave = ["fase 1 ambulatorio", "fase 2 hospitalario", "fase 3 quirurgico", "consolidado todas las fases"]
    coincidencias = sum(1 for t in titulos_clave if t in textos_norm)
    return coincidencias >= 2

def parsear_hoja_resultados(df, nombre_hoja):
    resultado = {}
    fases_map = {"fase 1 ambulatorio": "Fase 1", "fase 2 hospitalario": "Fase 2", "fase 3 quirurgico": "Fase 3", "consolidado todas las fases": "Consolidado"}
    sedes_por_columna = None
    fase_actual = None

    for idx_fila, row in df.iterrows():
        valores = row.tolist()
        primera_celda = str(valores[0]).strip() if valores else ""
        primera_norm = normalizar(primera_celda)
        fase_detectada = None
        for patron, nombre_fase in fases_map.items():
            if patron in primera_norm:
                fase_detectada = nombre_fase
                break
        if fase_detectada:
            fase_actual = fase_detectada
            sedes_por_columna = None
            continue
        if primera_norm == "concepto" and fase_actual:
            sedes_por_columna = {}
            for j, celda in enumerate(valores[1:], start=1):
                celda_norm = normalizar(celda)
                for col_canon in COLUMNAS_RESUMEN:
                    if normalizar(col_canon) == celda_norm:
                        sedes_por_columna[j] = col_canon
                        break
            continue
        if fase_actual and sedes_por_columna and primera_celda and primera_norm not in ("nan", ""):
            concepto_key = f"{fase_actual} - {primera_celda}"
            resultado[concepto_key] = {}
            for j, sede_canon in sedes_por_columna.items():
                if j < len(valores):
                    resultado[concepto_key][sede_canon] = valores[j]
    return resultado

def filas_resumen(tipo_tabla):
    sufijo = SUFIJOS_POR_TABLA.get(tipo_tabla, "consulta externa")
    prefijo = PREFIJOS_POR_TABLA.get(tipo_tabla, "ambulatorio")
    return [
        "Revisadas por analistas", "Avaladas subgerencia médica", "Dinero enviado por interfaz",
        f"Total ventas {sufijo} (ACTIVO Y FACTURADO)", f"Dinero ventas {prefijo}",
        "Porcentual faltante (META 30%)", "Ventas relacionadas en factura (FACTURADO)",
        "Dinero ventas (Facturado)", "Porcentual impactado (META 0%)",
    ]

def construir_tabla_resumen(tipo_tabla="Fase 1"):
    filas = filas_resumen(tipo_tabla)
    df = pd.DataFrame("", index=filas, columns=COLUMNAS_RESUMEN)
    df.index.name = "Concepto"
    return df

def formatear_dinero_interfaz(total, cant_err, suma_err, pct_err):
    if cant_err > 0: return f"${total:,.0f} (Errores: ${suma_err:,.0f} en {cant_err} registros — {pct_err:.2f}%)"
    return f"${total:,.0f}"

def formatear_conteo_con_error(total, cant_err, suma_err, pct_err):
    if cant_err > 0: return f"{total:,} (Errores: ${suma_err:,.0f} en {cant_err} registros — {pct_err:.2f}%)"
    return f"{total:,}"

def formatear_dinero_con_error(total, cant_err, suma_err, pct_err):
    if cant_err > 0: return f"${total:,.0f} (Errores: ${suma_err:,.0f} en {cant_err} registros — {pct_err:.2f}%)"
    return f"${total:,.0f}"

def parsear_valor_generico(v):
    if pd.isna(v): return None
    s = str(v).strip()
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = s.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        return float(s) if s else None
    except Exception:
        return None

def normalizar_etiqueta_hist(concepto):
    c = str(concepto).strip()
    if c.startswith("Total ventas ") and "(ACTIVO Y FACTURADO)" in c: return "Total ventas (ACTIVO Y FACTURADO)"
    if c.startswith("Dinero ventas ") and "Facturado" not in c: return "Dinero ventas"
    return c

# ============================================================
# NUEVAS FUNCIONES DE AGRUPACIÓN
# ============================================================
def agrupar_consolidados(consolidados_por_periodo, agrupacion):
    if agrupacion == "Mes":
        return consolidados_por_periodo

    agrupado = {}
    for periodo_etiqueta, data_sedes in consolidados_por_periodo.items():
        anio, mes = extraer_periodo_desde_nombre(periodo_etiqueta)
        
        if anio is None or mes is None:
            llave = periodo_etiqueta
        else:
            if agrupacion == "Bimestre":
                bimestre = (mes - 1) // 2 + 1
                llave = f"Bimestre {bimestre} {anio}"
            elif agrupacion == "Trimestre":
                trimestre = (mes - 1) // 3 + 1
                llave = f"Trimestre {trimestre} {anio}"
            elif agrupacion == "Semestre":
                semestre = (mes - 1) // 6 + 1
                llave = f"Semestre {semestre} {anio}"
            elif agrupacion == "Año":
                llave = f"Año {anio}"
            else:
                llave = periodo_etiqueta

        if llave not in agrupado:
            agrupado[llave] = {
                sede: {
                    "revisadas": 0, "avaladas": 0, "total_ventas": 0,
                    "dinero_interfaz": 0.0, "dinero_ventas": 0.0,
                    "ventas_relacionadas": 0, "dinero_facturado": 0.0,
                    "dinero_interfaz_fase_1": 0.0, "dinero_interfaz_fase_2": 0.0, "dinero_interfaz_fase_3": 0.0
                }
                for sede in COLUMNAS_RESUMEN
            }

        for sede, vals in data_sedes.items():
            for k, v in vals.items():
                agrupado[llave][sede][k] += v

    return agrupado

def _ordenar_llaves_cronologicamente(diccionario):
    def clave_orden(llave):
        llave_lower = normalizar(llave)
        m_anio = re.search(r"(20\d{2})", llave_lower)
        anio = int(m_anio.group(1)) if m_anio else 0
        
        if "bimestre" in llave_lower:
            m_num = re.search(r"bimestre\s*(\d)", llave_lower)
            num = int(m_num.group(1)) if m_num else 0
            return (anio, 0, num)
        elif "trimestre" in llave_lower:
            m_num = re.search(r"trimestre\s*(\d)", llave_lower)
            num = int(m_num.group(1)) if m_num else 0
            return (anio, 1, num)
        elif "semestre" in llave_lower:
            m_num = re.search(r"semestre\s*(\d)", llave_lower)
            num = int(m_num.group(1)) if m_num else 0
            return (anio, 2, num)
        elif "año" in llave_lower:
            return (anio, 3, 0)
        else:
            for num_mes, nombre_mes in MESES_ES.items():
                if normalizar(nombre_mes) in llave_lower:
                    return (anio, 4, num_mes)
            return (anio, 5, 0)

    return dict(sorted(diccionario.items(), key=lambda item: clave_orden(item[0])))

# ============================================================
# PROCESAMIENTO CACHEADO OPTIMIZADO
# ============================================================
@st.cache_data(show_spinner="Procesando archivos y calculando indicadores...")
def procesar_todo(files_data):
    bases = {nombre: [] for nombre in ESTRUCTURAS}
    no_clasificados = []
    errores = []
    archivos_duplicados = []
    hojas_duplicadas = []
    periodos_detectados = []
    historicos_detectados = {}

    hashes_archivos_vistos = {}
    hashes_hojas_vistos = {}

    for f_name, f_bytes in files_data:
        hash_archivo = hashlib.md5(f_bytes).hexdigest()
        if hash_archivo in hashes_archivos_vistos:
            archivos_duplicados.append({"Archivo": f_name, "Ya cargado como": hashes_archivos_vistos[hash_archivo]})
            continue
        hashes_archivos_vistos[hash_archivo] = f_name

        anio, mes = extraer_periodo_desde_nombre(f_name)
        periodos_detectados.append((f_name, (anio, mes)))

        try:
            sheets = pd.read_excel(io.BytesIO(f_bytes), sheet_name=None, header=None)
            hojas = {name: df for name, df in sheets.items() if not df.empty}
        except Exception as e:
            errores.append((f_name, str(e)))
            continue

        for hoja, df in hojas.items():
            if es_hoja_de_resultados(df):
                a_h, m_h = extraer_periodo_desde_nombre(hoja)
                if a_h is None: a_h, m_h = anio, mes
                etiqueta, _, _ = formatear_periodo(a_h, m_h)
                if etiqueta == "—": etiqueta = hoja
                historicos_detectados[etiqueta] = parsear_hoja_resultados(df, hoja)
                continue

            try:
                df_con_header = pd.read_excel(io.BytesIO(f_bytes), sheet_name=hoja, header=0)
            except Exception:
                continue

            estructura, score = clasificar_estructura(df_con_header.columns)
            if estructura is None or score < UMBRAL_COINCIDENCIA:
                no_clasificados.append({
                    "Archivo": f_name, "Hoja": hoja, "Mejor candidato": estructura or "—",
                    "Coincidencia": f"{score:.0%}", "Columnas": len(df_con_header.columns), "Filas": len(df_con_header),
                })
                continue

            if estructura == "Totales":
                col_tot_tarifas = obtener_columna(df_con_header, "Total tarifas y recargos/descuentos")
                if col_tot_tarifas is not None:
                    valores_tot = pd.to_numeric(
                        df_con_header[col_tot_tarifas].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace(" ", "", regex=False).str.strip(),
                        errors="coerce"
                    )
                    df_con_header = df_con_header[valores_tot >= 1000].copy()

            h = hash_df(df_con_header)
            if h in hashes_hojas_vistos:
                hojas_duplicadas.append({"Archivo": f_name, "Hoja": hoja, "Estructura": estructura, "Duplicado de": hashes_hojas_vistos[h]})
                continue
            hashes_hojas_vistos[h] = f"{f_name}::{hoja}"
            bases[estructura].append((f_name, hoja, df_con_header.copy()))

    periodos_validos = [(n, p) for n, p in periodos_detectados if p[0] is not None and p[1] is not None]
    if periodos_validos:
        from collections import Counter
        conteo = Counter(p for _, p in periodos_validos)
        periodo_actual_tupla = conteo.most_common(1)[0][0]
    else:
        periodo_actual_tupla = (None, None)
    periodo_etiqueta, periodo_inicio, periodo_fin = formatear_periodo(*periodo_actual_tupla)

    if bases["Atenciones del especialista"]:
        partes = []
        for arch, hoja, df in bases["Atenciones del especialista"]:
            df_aux = df.copy()
            df_aux["_archivo"] = arch
            df_aux["_hoja"] = hoja
            partes.append(df_aux)
        atenciones_df = pd.concat(partes, ignore_index=True)
    else:
        atenciones_df = pd.DataFrame()

    conteos = {fase: {cod: {"revisadas": 0, "avaladas": 0} for cod in CODIGOS_SEDE} for fase in FASES}
    errores_revisadas = {fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE} for fase in FASES}
    errores_avaladas = {fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE} for fase in FASES}
    dinero_interfaz = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    errores_valor_bajo = {fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE} for fase in FASES}
    
    df_filtrado_revisadas = pd.DataFrame()
    ubicaciones_no_mapeadas = pd.Series(dtype=int)

    if not atenciones_df.empty:
        col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
        col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")
        col_submedico = obtener_columna(atenciones_df, "Usuario / Sub Medico")
        col_valor_liquidado = obtener_columna(atenciones_df, "Valor liquidado")

        if col_ubicacion is not None and col_verifica is not None:
            # Optimización: map vectorizado en lugar de loops iterativos
            ubicacion_norm_serie = atenciones_df[col_ubicacion].astype(str).map(normalizar)
            
            # Creamos las series de sede y fase mapeando con la función robusta
            mapeo_ubicaciones = ubicacion_norm_serie.map(detectar_ubicacion_robusta)
            sede_serie = mapeo_ubicaciones.map(lambda x: x[0])
            fase_serie = mapeo_ubicaciones.map(lambda x: x[1])

            mask_verifica = es_vacio(atenciones_df[col_verifica])
            mask_submedico = (es_vacio(atenciones_df[col_submedico]) if col_submedico is not None else pd.Series(False, index=atenciones_df.index))

            sin_match = ubicacion_norm_serie[sede_serie.isna()]
            if not sin_match.empty:
                ubicaciones_no_mapeadas = (sin_match.value_counts().rename_axis("Ubicación (normalizada)").reset_index(name="Registros"))

            valor_liquidado_num = convertir_a_numero(atenciones_df[col_valor_liquidado]) if col_valor_liquidado is not None else pd.Series(0.0, index=atenciones_df.index)
            mask_valor_mayor_1000 = valor_liquidado_num > 1000

            for fase in FASES:
                for cod in CODIGOS_SEDE:
                    mask_sede_fase = (sede_serie == cod) & (fase_serie == fase)
                    mask_rev_total = mask_sede_fase & mask_verifica
                    mask_rev = mask_rev_total & mask_valor_mayor_1000
                    mask_ava_total = mask_rev_total & mask_submedico
                    mask_ava = mask_ava_total & mask_valor_mayor_1000

                    conteos[fase][cod]["revisadas"] = int(mask_rev.sum())
                    conteos[fase][cod]["avaladas"] = int(mask_ava.sum())

                    # Errores
                    mask_rev_error = mask_rev_total & ~mask_valor_mayor_1000
                    if mask_rev_error.any():
                        errores_revisadas[fase][cod]["cantidad"] = int(mask_rev_error.sum())
                        errores_revisadas[fase][cod]["suma"] = float(valor_liquidado_num[mask_rev_error].sum())

                    mask_ava_error = mask_ava_total & ~mask_valor_mayor_1000
                    if mask_ava_error.any():
                        errores_avaladas[fase][cod]["cantidad"] = int(mask_ava_error.sum())
                        errores_avaladas[fase][cod]["suma"] = float(valor_liquidado_num[mask_ava_error].sum())

                    # Dinero interfaz
                    mask_dinero_base = mask_sede_fase & mask_verifica
                    mask_dinero_val = mask_dinero_base & mask_valor_mayor_1000
                    mask_dinero_err = mask_dinero_base & ~mask_valor_mayor_1000

                    if mask_dinero_val.any():
                        dinero_interfaz[fase][cod] = float(valor_liquidado_num[mask_dinero_val].sum())
                    if mask_dinero_err.any():
                        errores_valor_bajo[fase][cod]["cantidad"] = int(mask_dinero_err.sum())
                        errores_valor_bajo[fase][cod]["suma"] = float(valor_liquidado_num[mask_dinero_err].sum())

            df_filtrado_revisadas = atenciones_df.loc[mask_verifica].copy()

    # -------- TOTALES --------
    total_ventas_ce = {fase: {cod: 0 for cod in CODIGOS_SEDE} for fase in FASES}
    dinero_ambulatorio = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    errores_totales = {fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE} for fase in FASES}
    ubicaciones_totales_no_mapeadas = pd.Series(dtype=int)
    totales_sin_match_atenciones_df = pd.DataFrame()

    if bases["Totales"]:
        totales_df = pd.concat([df for _, _, df in bases["Totales"]], ignore_index=True)
        col_totales_venta_no = obtener_columna(totales_df, "No. de venta")
        col_totales_centro_costo = obtener_columna(totales_df, "Centro De Costo")
        col_totales_tarifa_reliq = obtener_columna(totales_df, "tarifas (reliquidado)")

        if col_totales_venta_no is not None and col_totales_centro_costo is not None:
            totales_df["_venta_no_norm"] = totales_df[col_totales_venta_no].map(normalizar_llave_venta)
            
            totales_ubic = totales_df[col_totales_centro_costo].astype(str).map(detectar_ubicacion_robusta)
            totales_df["_sede"] = totales_ubic.map(lambda x: x[0])
            totales_df["_fase"] = totales_ubic.map(lambda x: x[1])

            sin_match_totales = totales_df.loc[totales_df["_sede"].isna(), col_totales_centro_costo].astype(str).map(normalizar)
            if not sin_match_totales.empty:
                ubicaciones_totales_no_mapeadas = (sin_match_totales.value_counts().rename_axis("Centro De Costo (normalizado)").reset_index(name="Registros"))

            if col_totales_tarifa_reliq is not None:
                totales_tarifa_num = convertir_a_numero(totales_df[col_totales_tarifa_reliq])
            else:
                totales_tarifa_num = pd.Series(0.0, index=totales_df.index)

            ventas_nos_existentes = set()
            if bases["Ventas"]:
                ventas_para_cruce = pd.concat([df for _, _, df in bases["Ventas"]], ignore_index=True)
                col_venta_no_v = obtener_columna(ventas_para_cruce, "Venta No.")
                if col_venta_no_v is not None:
                    ventas_nos_existentes = set(ventas_para_cruce[col_venta_no_v].map(normalizar_llave_venta).dropna().unique())

            mask_venta_en_ventas = totales_df["_venta_no_norm"].isin(ventas_nos_existentes)

            for fase in FASES:
                for cod in CODIGOS_SEDE:
                    mask_sede_fase = (totales_df["_sede"] == cod) & (totales_df["_fase"] == fase)
                    mask_base = mask_sede_fase & mask_venta_en_ventas
                    if mask_base.any():
                        tarifas_filtro = totales_tarifa_num[mask_base]
                        indices = tarifas_filtro.index
                        mask_valida = totales_tarifa_num.loc[indices] >= 1000
                        mask_error = ~mask_valida
                        
                        total_ventas_ce[fase][cod] = int(mask_valida.sum())
                        dinero_ambulatorio[fase][cod] = float(totales_tarifa_num.loc[indices][mask_valida].sum())
                        
                        if mask_error.any():
                            errores_totales[fase][cod]["cantidad"] = int(mask_error.sum())
                            errores_totales[fase][cod]["suma"] = float(totales_tarifa_num.loc[indices][mask_error].sum())

            atenciones_nos_existentes = set()
            if not atenciones_df.empty:
                col_num_venta_at = obtener_columna(atenciones_df, "Numero Venta")
                if col_num_venta_at is not None:
                    atenciones_nos_existentes = set(atenciones_df[col_num_venta_at].map(normalizar_llave_venta).dropna().unique())

            mask_sin_match_atenciones = ~totales_df["_venta_no_norm"].isin(atenciones_nos_existentes)

            if mask_sin_match_atenciones.any():
                cols_mostrar = []
                for nombre_col in ["No. de venta", "profesional", "producto", "Centro De Costo", "tarifas (reliquidado)"]:
                    col_real = obtener_columna(totales_df, nombre_col)
                    if col_real is not None: cols_mostrar.append(col_real)
                if cols_mostrar:
                    totales_sin_match_atenciones_df = totales_df.loc[mask_sin_match_atenciones, cols_mostrar].copy()
                    totales_sin_match_atenciones_df = totales_sin_match_atenciones_df.rename(columns={"Centro De Costo": "Centro de costos"})

    # -------- VENTAS --------
    ventas_relacionadas_factura = {fase: {cod: 0 for cod in CODIGOS_SEDE} for fase in FASES}
    dinero_ventas_facturado = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    errores_ventas = {fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE} for fase in FASES}
    ubicaciones_ventas_no_mapeadas = pd.Series(dtype=int)
    estados_no_incluidos = pd.Series(dtype=int)

    totales_ventas_nos = set()
    if bases["Totales"]:
        totales_para_cruce = pd.concat([df for _, _, df in bases["Totales"]], ignore_index=True)
        col_totales_vno = obtener_columna(totales_para_cruce, "No. de venta")
        if col_totales_vno is not None:
            totales_ventas_nos = set(totales_para_cruce[col_totales_vno].map(normalizar_llave_venta).dropna().unique())

    if bases["Ventas"]:
        ventas_df = pd.concat([df for _, _, df in bases["Ventas"]], ignore_index=True)
        col_ventas_centro_costo = obtener_columna(ventas_df, "Centro de costo")
        col_ventas_estado = obtener_columna(ventas_df, "Estado")
        col_ventas_valor_facturado = obtener_columna(ventas_df, "Valor facturado")
        col_ventas_venta_no = obtener_columna(ventas_df, "Venta No.")

        if col_ventas_centro_costo is not None:
            ventas_ubic = ventas_df[col_ventas_centro_costo].astype(str).map(detectar_ubicacion_robusta)
            ventas_df["_sede"] = ventas_ubic.map(lambda x: x[0])
            ventas_df["_fase"] = ventas_ubic.map(lambda x: x[1])

            sin_match_ventas = ventas_df.loc[ventas_df["_sede"].isna(), col_ventas_centro_costo].astype(str).map(normalizar)
            if not sin_match_ventas.empty:
                ubicaciones_ventas_no_mapeadas = (sin_match_ventas.value_counts().rename_axis("Centro de costo (normalizado)").reset_index(name="Registros"))

            if col_ventas_estado is not None:
                estado_norm = ventas_df[col_ventas_estado].astype(str).str.strip().str.lower()
                mask_estado_facturada = estado_norm.isin(ESTADO_FACTURADA)
                estados_excluidos = estado_norm[~estado_norm.isin(ESTADOS_ACTIVA_FACTURADA)]
                if not estados_excluidos.empty:
                    estados_no_incluidos = (estados_excluidos.value_counts().rename_axis("Estado (normalizado)").reset_index(name="Registros"))
            else:
                mask_estado_facturada = pd.Series(False, index=ventas_df.index)

            if col_ventas_valor_facturado is not None:
                valor_facturado_num = convertir_a_numero(ventas_df[col_ventas_valor_facturado])
            else:
                valor_facturado_num = pd.Series(0.0, index=ventas_df.index)

            if col_ventas_venta_no is not None:
                venta_no_norm_serie = ventas_df[col_ventas_venta_no].map(normalizar_llave_venta)
                mask_venta_en_totales = venta_no_norm_serie.isin(totales_ventas_nos)
            else:
                mask_venta_en_totales = pd.Series(False, index=ventas_df.index)

            for fase in FASES:
                for cod in CODIGOS_SEDE:
                    mask_sede_fase = (ventas_df["_sede"] == cod) & (ventas_df["_fase"] == fase)
                    mask_base = mask_sede_fase & mask_estado_facturada & mask_venta_en_totales
                    if mask_base.any():
                        valores = valor_facturado_num[mask_base]
                        indices = valores.index
                        mask_valida = valor_facturado_num.loc[indices] >= 1000
                        mask_error = ~mask_valida
                        
                        ventas_relacionadas_factura[fase][cod] = int(mask_valida.sum())
                        dinero_ventas_facturado[fase][cod] = float(valor_facturado_num.loc[indices][mask_valida].sum())
                        
                        if mask_error.any():
                            errores_ventas[fase][cod]["cantidad"] = int(mask_error.sum())
                            errores_ventas[fase][cod]["suma"] = float(valor_facturado_num.loc[indices][mask_error].sum())

    # -------- PORCENTUALES --------
    porcentual_faltante = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    porcentual_impactado = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    porcentaje_errores_valor = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    porcentaje_errores_totales = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    porcentaje_errores_ventas = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    porcentaje_errores_revisadas = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
    porcentaje_errores_avaladas = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}

    for fase in FASES:
        for cod in CODIGOS_SEDE:
            avaladas = conteos[fase][cod]["avaladas"]
            revisadas = conteos[fase][cod]["revisadas"]
            total_ventas = total_ventas_ce[fase][cod]
            relacionadas = ventas_relacionadas_factura[fase][cod]
            cant_err_v = errores_valor_bajo[fase][cod]["cantidad"]
            cant_err_t = errores_totales[fase][cod]["cantidad"]
            cant_err_vtas = errores_ventas[fase][cod]["cantidad"]
            cant_err_rev = errores_revisadas[fase][cod]["cantidad"]
            cant_err_ava = errores_avaladas[fase][cod]["cantidad"]

            if total_ventas > 0:
                faltante_calc = ((total_ventas - avaladas) / total_ventas) * 100.0
                porcentual_faltante[fase][cod] = max(faltante_calc, 0.0) 
                impactado_calc = ((total_ventas - relacionadas) / total_ventas) * 100.0
                porcentual_impactado[fase][cod] = max(impactado_calc, 0.0)

            if revisadas > 0:
                porcentaje_errores_revisadas[fase][cod] = (cant_err_rev / revisadas) * 100.0
            if avaladas > 0:
                porcentaje_errores_valor[fase][cod] = (cant_err_v / avaladas) * 100.0
                porcentaje_errores_totales[fase][cod] = (cant_err_t / avaladas) * 100.0
                porcentaje_errores_ventas[fase][cod] = (cant_err_vtas / avaladas) * 100.0
                porcentaje_errores_avaladas[fase][cod] = (cant_err_ava / avaladas) * 100.0

    # -------- CONSOLIDADO --------
    conteos_consolidado = {cod: {"revisadas": 0, "avaladas": 0} for cod in CODIGOS_SEDE}
    errores_revisadas_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
    errores_avaladas_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
    dinero_interfaz_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    errores_valor_bajo_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
    total_ventas_ce_consolidado = {cod: 0 for cod in CODIGOS_SEDE}
    dinero_ambulatorio_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    errores_totales_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
    ventas_relacionadas_factura_consolidado = {cod: 0 for cod in CODIGOS_SEDE}
    dinero_ventas_facturado_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    errores_ventas_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}

    for cod in CODIGOS_SEDE:
        for fase in FASES:
            conteos_consolidado[cod]["revisadas"] += conteos[fase][cod]["revisadas"]
            conteos_consolidado[cod]["avaladas"] += conteos[fase][cod]["avaladas"]
            errores_revisadas_consolidado[cod]["cantidad"] += errores_revisadas[fase][cod]["cantidad"]
            errores_revisadas_consolidado[cod]["suma"] += errores_revisadas[fase][cod]["suma"]
            errores_avaladas_consolidado[cod]["cantidad"] += errores_avaladas[fase][cod]["cantidad"]
            errores_avaladas_consolidado[cod]["suma"] += errores_avaladas[fase][cod]["suma"]
            dinero_interfaz_consolidado[cod] += dinero_interfaz[fase][cod]
            errores_valor_bajo_consolidado[cod]["cantidad"] += errores_valor_bajo[fase][cod]["cantidad"]
            errores_valor_bajo_consolidado[cod]["suma"] += errores_valor_bajo[fase][cod]["suma"]
            total_ventas_ce_consolidado[cod] += total_ventas_ce[fase][cod]
            dinero_ambulatorio_consolidado[cod] += dinero_ambulatorio[fase][cod]
            errores_totales_consolidado[cod]["cantidad"] += errores_totales[fase][cod]["cantidad"]
            errores_totales_consolidado[cod]["suma"] += errores_totales[fase][cod]["suma"]
            ventas_relacionadas_factura_consolidado[cod] += ventas_relacionadas_factura[fase][cod]
            dinero_ventas_facturado_consolidado[cod] += dinero_ventas_facturado[fase][cod]
            errores_ventas_consolidado[cod]["cantidad"] += errores_ventas[fase][cod]["cantidad"]
            errores_ventas_consolidado[cod]["suma"] += errores_ventas[fase][cod]["suma"]

    porcentual_faltante_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    porcentual_impactado_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    porcentaje_errores_valor_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    porcentaje_errores_totales_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    porcentaje_errores_ventas_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    porcentaje_errores_revisadas_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
    porcentaje_errores_avaladas_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}

    for cod in CODIGOS_SEDE:
        avaladas = conteos_consolidado[cod]["avaladas"]
        revisadas = conteos_consolidado[cod]["revisadas"]
        total_ventas = total_ventas_ce_consolidado[cod]
        relacionadas = ventas_relacionadas_factura_consolidado[cod]
        cant_err_v = errores_valor_bajo_consolidado[cod]["cantidad"]
        cant_err_t = errores_totales_consolidado[cod]["cantidad"]
        cant_err_vtas = errores_ventas_consolidado[cod]["cantidad"]
        cant_err_rev = errores_revisadas_consolidado[cod]["cantidad"]
        cant_err_ava = errores_avaladas_consolidado[cod]["cantidad"]

        if total_ventas > 0:
            faltante_calc = ((total_ventas - avaladas) / total_ventas) * 100.0
            porcentual_faltante_consolidado[cod] = max(faltante_calc, 0.0)
            impactado_calc = ((total_ventas - relacionadas) / total_ventas) * 100.0
            porcentual_impactado_consolidado[cod] = max(impactado_calc, 0.0)
        if revisadas > 0:
            porcentaje_errores_revisadas_consolidado[cod] = (cant_err_rev / revisadas) * 100.0
        if avaladas > 0:
            porcentaje_errores_valor_consolidado[cod] = (cant_err_v / avaladas) * 100.0
            porcentaje_errores_totales_consolidado[cod] = (cant_err_t / avaladas) * 100.0
            porcentaje_errores_ventas_consolidado[cod] = (cant_err_vtas / avaladas) * 100.0
            porcentaje_errores_avaladas_consolidado[cod] = (cant_err_ava / avaladas) * 100.0

    # -------- TABLAS --------
    tablas_por_fase = {}
    for fase in FASES:
        tabla = construir_tabla_resumen(fase)
        filas = filas_resumen(fase)
        for cod in CODIGOS_SEDE:
            columna = MAPA_CODIGO_A_COLUMNA[cod]
            tabla.loc["Revisadas por analistas", columna] = formatear_conteo_con_error(
                conteos[fase][cod]['revisadas'],
                errores_revisadas[fase][cod]["cantidad"],
                errores_revisadas[fase][cod]["suma"],
                porcentaje_errores_revisadas[fase][cod]
            )
            tabla.loc["Avaladas subgerencia médica", columna] = formatear_conteo_con_error(
                conteos[fase][cod]['avaladas'],
                errores_avaladas[fase][cod]["cantidad"],
                errores_avaladas[fase][cod]["suma"],
                porcentaje_errores_avaladas[fase][cod]
            )
            tabla.loc["Dinero enviado por interfaz", columna] = formatear_dinero_interfaz(dinero_interfaz[fase][cod], errores_valor_bajo[fase][cod]["cantidad"], errores_valor_bajo[fase][cod]["suma"], porcentaje_errores_valor[fase][cod])
            tabla.loc[filas[3], columna] = formatear_conteo_con_error(total_ventas_ce[fase][cod], errores_totales[fase][cod]["cantidad"], errores_totales[fase][cod]["suma"], porcentaje_errores_totales[fase][cod])
            tabla.loc[filas[4], columna] = formatear_dinero_con_error(dinero_ambulatorio[fase][cod], errores_totales[fase][cod]["cantidad"], errores_totales[fase][cod]["suma"], porcentaje_errores_totales[fase][cod])
            tabla.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante[fase][cod]:,.2f}%"
            tabla.loc["Ventas relacionadas en factura (FACTURADO)", columna] = formatear_conteo_con_error(ventas_relacionadas_factura[fase][cod], errores_ventas[fase][cod]["cantidad"], errores_ventas[fase][cod]["suma"], porcentaje_errores_ventas[fase][cod])
            tabla.loc["Dinero ventas (Facturado)", columna] = formatear_dinero_con_error(dinero_ventas_facturado[fase][cod], errores_ventas[fase][cod]["cantidad"], errores_ventas[fase][cod]["suma"], porcentaje_errores_ventas[fase][cod])
            tabla.loc["Porcentual impactado (META 0%)", columna] = f"{porcentual_impactado[fase][cod]:,.2f}%"
        tablas_por_fase[fase] = tabla

    tabla_consolidada = construir_tabla_resumen("Consolidado")
    filas_cons = filas_resumen("Consolidado")
    for cod in CODIGOS_SEDE:
        columna = MAPA_CODIGO_A_COLUMNA[cod]
        tabla_consolidada.loc["Revisadas por analistas", columna] = formatear_conteo_con_error(
            conteos_consolidado[cod]['revisadas'],
            errores_revisadas_consolidado[cod]["cantidad"],
            errores_revisadas_consolidado[cod]["suma"],
            porcentaje_errores_revisadas_consolidado[cod]
        )
        tabla_consolidada.loc["Avaladas subgerencia médica", columna] = formatear_conteo_con_error(
            conteos_consolidado[cod]['avaladas'],
            errores_avaladas_consolidado[cod]["cantidad"],
            errores_avaladas_consolidado[cod]["suma"],
            porcentaje_errores_avaladas_consolidado[cod]
        )
        tabla_consolidada.loc["Dinero enviado por interfaz", columna] = formatear_dinero_interfaz(dinero_interfaz_consolidado[cod], errores_valor_bajo_consolidado[cod]["cantidad"], errores_valor_bajo_consolidado[cod]["suma"], porcentaje_errores_valor_consolidado[cod])
        tabla_consolidada.loc[filas_cons[3], columna] = formatear_conteo_con_error(total_ventas_ce_consolidado[cod], errores_totales_consolidado[cod]["cantidad"], errores_totales_consolidado[cod]["suma"], porcentaje_errores_totales_consolidado[cod])
        tabla_consolidada.loc[filas_cons[4], columna] = formatear_dinero_con_error(dinero_ambulatorio_consolidado[cod], errores_totales_consolidado[cod]["cantidad"], errores_totales_consolidado[cod]["suma"], porcentaje_errores_totales_consolidado[cod])
        tabla_consolidada.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante_consolidado[cod]:,.2f}%"
        tabla_consolidada.loc["Ventas relacionadas en factura (FACTURADO)", columna] = formatear_conteo_con_error(ventas_relacionadas_factura_consolidado[cod], errores_ventas_consolidado[cod]["cantidad"], errores_ventas_consolidado[cod]["suma"], porcentaje_errores_ventas_consolidado[cod])
        tabla_consolidada.loc["Dinero ventas (Facturado)", columna] = formatear_dinero_con_error(dinero_ventas_facturado_consolidado[cod], errores_ventas_consolidado[cod]["cantidad"], errores_ventas_consolidado[cod]["suma"], porcentaje_errores_ventas_consolidado[cod])
        tabla_consolidada.loc["Porcentual impactado (META 0%)", columna] = f"{porcentual_impactado_consolidado[cod]:,.2f}%"

    # -------- NOVEDADES --------
    resumen_verifica = pd.DataFrame()
    if not df_filtrado_revisadas.empty:
        col_verifica = obtener_columna(df_filtrado_revisadas, "Nombre de Usuario que Verifica")
        col_submedico = obtener_columna(df_filtrado_revisadas, "Usuario / Sub Medico")
        col_valor_liq = obtener_columna(df_filtrado_revisadas, "Valor liquidado")
        verificadores_limpios = df_filtrado_revisadas[col_verifica].astype(str).str.strip().replace({"nan": "", "None": "", "NaN": ""})
        df_filtrado_revisadas = df_filtrado_revisadas.assign(_verifica_limpio=verificadores_limpios)
        resumen_verifica = (df_filtrado_revisadas.groupby("_verifica_limpio", dropna=False).size().reset_index(name="Registros").rename(columns={"_verifica_limpio": "Nombre de Usuario que Verifica"}))

        def comparar_con_submedico(nombre_verifica):
            if not col_submedico: return "Sin datos de Sub Médico"
            valores_sub = df_filtrado_revisadas[col_submedico].dropna().astype(str).str.strip()
            valores_sub = valores_sub[~valores_sub.isin(["", "nan", "None", "NaN"])]
            if valores_sub.empty: return "Sin datos de Sub Médico"
            norm_verifica = normalizar(nombre_verifica)
            set_sub_norm = {normalizar(v) for v in valores_sub.unique()}
            return "Misma persona" if norm_verifica in set_sub_norm else "Diferente persona"

        resumen_verifica["¿Coincide con Usuario / Sub Médico?"] = resumen_verifica["Nombre de Usuario que Verifica"].apply(comparar_con_submedico)
        resumen_verifica = resumen_verifica.sort_values("Registros", ascending=False).reset_index(drop=True)

    # -------- CONSOLIDADOS POR PERIODO --------
    consolidados_por_periodo = {}

    if periodo_etiqueta != "—" and len(bases["Atenciones del especialista"]) > 0:
        consolidados_por_periodo[periodo_etiqueta] = {
            sede: {
                "revisadas": conteos_consolidado[cod]["revisadas"], "avaladas": conteos_consolidado[cod]["avaladas"],
                "total_ventas": total_ventas_ce_consolidado[cod], "dinero_interfaz": dinero_interfaz_consolidado[cod],
                "dinero_ventas": dinero_ambulatorio_consolidado[cod], "ventas_relacionadas": ventas_relacionadas_factura_consolidado[cod],
                "dinero_facturado": dinero_ventas_facturado_consolidado[cod],
                "dinero_interfaz_fase_1": dinero_interfaz["Fase 1"][cod], "dinero_interfaz_fase_2": dinero_interfaz["Fase 2"][cod], "dinero_interfaz_fase_3": dinero_interfaz["Fase 3"][cod],
            } for cod, sede in zip(CODIGOS_SEDE, COLUMNAS_RESUMEN)
        }

    for etiqueta_periodo, conceptos in historicos_detectados.items():
        data_periodo = {}
        for sede in COLUMNAS_RESUMEN:
            revisadas_p = 0; avaladas_p = 0; total_ventas_p = 0
            dinero_interfaz_p = 0.0; dinero_ventas_p = 0.0
            ventas_relacionadas_p = 0; dinero_facturado_p = 0.0
            dinero_interfaz_fase_1_p = 0.0; dinero_interfaz_fase_2_p = 0.0; dinero_interfaz_fase_3_p = 0.0

            for concepto, valores in conceptos.items():
                valor = valores.get(sede)
                if valor is None: continue
                num = parsear_valor_generico(valor)
                if num is None: continue
                concepto_lower = normalizar(concepto)
                es_fase_1 = concepto_lower.startswith("fase 1")
                es_fase_2 = concepto_lower.startswith("fase 2")
                es_fase_3 = concepto_lower.startswith("fase 3")
                es_consolidado = concepto_lower.startswith("consolidado")
                if es_fase_1 or es_fase_2 or es_fase_3 or es_consolidado:
                    concepto_sin_prefijo = " - ".join(concepto.split(" - ")[1:])
                else:
                    concepto_sin_prefijo = concepto
                concepto_norm = normalizar_etiqueta_hist(concepto_sin_prefijo)

                if concepto_norm == "Revisadas por analistas": revisadas_p += num
                elif concepto_norm == "Avaladas subgerencia médica": avaladas_p += num
                elif concepto_norm == "Total ventas (ACTIVO Y FACTURADO)": total_ventas_p += num
                elif concepto_norm == "Dinero enviado por interfaz":
                    dinero_interfaz_p += num
                    if es_fase_1: dinero_interfaz_fase_1_p += num
                    elif es_fase_2: dinero_interfaz_fase_2_p += num
                    elif es_fase_3: dinero_interfaz_fase_3_p += num
                elif concepto_norm == "Dinero ventas": dinero_ventas_p += num
                elif concepto_norm == "Ventas relacionadas en factura (FACTURADO)": ventas_relacionadas_p += num
                elif concepto_norm == "Dinero ventas (Facturado)": dinero_facturado_p += num

            data_periodo[sede] = {
                "revisadas": revisadas_p, "avaladas": avaladas_p, "total_ventas": total_ventas_p,
                "dinero_interfaz": dinero_interfaz_p, "dinero_ventas": dinero_ventas_p,
                "ventas_relacionadas": ventas_relacionadas_p, "dinero_facturado": dinero_facturado_p,
                "dinero_interfaz_fase_1": dinero_interfaz_fase_1_p, "dinero_interfaz_fase_2": dinero_interfaz_fase_2_p, "dinero_interfaz_fase_3": dinero_interfaz_fase_3_p,
            }
        consolidados_por_periodo[etiqueta_periodo] = data_periodo

    return {
        "tablas_por_fase": tablas_por_fase, "tabla_consolidada": tabla_consolidada, "resumen_verifica": resumen_verifica,
        "historicos_detectados": historicos_detectados, "consolidados_por_periodo": consolidados_por_periodo,
        "periodo_etiqueta": periodo_etiqueta, "periodo_inicio": str(periodo_inicio) if periodo_inicio else "—",
        "periodo_fin": str(periodo_fin) if periodo_fin else "—", "no_clasificados": no_clasificados, "errores": errores,
        "archivos_duplicados": archivos_duplicados, "hojas_duplicadas": hojas_duplicadas,
        "ubicaciones_no_mapeadas": ubicaciones_no_mapeadas, "ubicaciones_totales_no_mapeadas": ubicaciones_totales_no_mapeadas,
        "ubicaciones_ventas_no_mapeadas": ubicaciones_ventas_no_mapeadas, "estados_no_incluidos": estados_no_incluidos,
        "totales_sin_match_atenciones_df": totales_sin_match_atenciones_df,
    }

def _firma_consolidados(consolidados_por_periodo):
    partes = []
    for periodo in sorted(consolidados_por_periodo.keys()):
        sedes = consolidados_por_periodo[periodo]
        for sede in sorted(sedes.keys()):
            v = sedes[sede]
            partes.append(
                f"{periodo}|{sede}|{v['revisadas']}|{v['avaladas']}|"
                f"{v['total_ventas']}|{v['dinero_interfaz']}|{v['dinero_ventas']}|"
                f"{v['ventas_relacionadas']}|{v['dinero_facturado']}|"
                f"{v.get('dinero_interfaz_fase_1', 0)}|{v.get('dinero_interfaz_fase_2', 0)}|{v.get('dinero_interfaz_fase_3', 0)}"
            )
    return hashlib.md5(";".join(partes).encode()).hexdigest()

# ============================================================
# GRÁFICAS POR SEDE
# ============================================================
@st.cache_data(show_spinner=False)
def generar_grafica_dinero(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            datos.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
    df = pd.DataFrame(datos)
    if df.empty or df["Valor"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.barplot(data=df, x="Periodo", y="Valor", hue="Sede", ax=ax)
    def _fmt_corto(v):
        if v <= 0: return ""
        if v >= 1_000_000: return f"${v/1_000_000:,.1f}M"
        elif v >= 1_000: return f"${v/1_000:,.0f}K"
        return f"${v:,.0f}"
    for container in ax.containers:
        ax.bar_label(container, labels=[_fmt_corto(v) for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_ylim(0, df["Valor"].max() * 1.05)
    ax.set_title("Dinero enviado por interfaz por periodo y sede (Consolidado)", pad=15)
    ax.set_ylabel("Valor (COP)")
    ax.set_xlabel("Periodo")
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def generar_grafica_cobertura(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            avaladas = vals["avaladas"]
            total_ventas = vals["total_ventas"]
            cobertura = (avaladas / total_ventas * 100.0) if total_ventas > 0 else 0.0
            datos.append({"Periodo": periodo, "Sede": sede, "Cobertura": cobertura})
    df = pd.DataFrame(datos)
    if df.empty or df["Cobertura"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.barplot(data=df, x="Periodo", y="Cobertura", hue="Sede", ax=ax)
    for container in ax.containers:
        ax.bar_label(container, labels=[f"{v:.1f}%" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
    ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
    ax.set_ylim(0, 105)
    ax.set_title("Cobertura general de honorarios médicos (Avaladas / Total ventas)", pad=15)
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Periodo")
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def generar_grafica_participacion_fase(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            datos.append({
                "Periodo": periodo, "Sede": sede,
                "Fase 1 - Ambulatorio": vals.get("dinero_interfaz_fase_1", 0),
                "Fase 2 - Hospitalario": vals.get("dinero_interfaz_fase_2", 0),
                "Fase 3 - Quirúrgico": vals.get("dinero_interfaz_fase_3", 0),
            })
    df = pd.DataFrame(datos)
    if df.empty: return None
    df = df.set_index(["Periodo", "Sede"])
    total_por_fila = df.sum(axis=1)
    df_pct = df.div(total_por_fila.replace(0, pd.NA), axis=0).fillna(0) * 100
    df_pct = df_pct.reset_index()
    df_pct["Etiqueta"] = df_pct["Periodo"] + "\n" + df_pct["Sede"]
    df_pct = df_pct.set_index("Etiqueta")[["Fase 1 - Ambulatorio", "Fase 2 - Hospitalario", "Fase 3 - Quirúrgico"]]
    fig, ax = plt.subplots(figsize=(14, 7))
    df_pct.plot(kind="bar", stacked=True, ax=ax, color=["#305496", "#D1615D", "#85C17E"], width=0.6)
    for container in ax.containers:
        vals = [v.get_height() for v in container]
        labels = [f"{v:.1f}%" if v > 3 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=9, color="white", weight="bold")
    ax.set_title("Participación por fase de cada sede y periodo", pad=15)
    ax.set_ylabel("Participación (%)")
    ax.set_xlabel("")
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.legend(title="Fase", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.subplots_adjust(top=0.90)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def generar_grafica_participacion_sede(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            datos.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
    df = pd.DataFrame(datos)
    if df.empty: return None
    df["Total_Periodo"] = df.groupby("Periodo")["Valor"].transform("sum")
    df["Porcentaje"] = df.apply(lambda r: (r["Valor"] / r["Total_Periodo"] * 100) if r["Total_Periodo"] > 0 else 0, axis=1)
    df["Etiqueta"] = df["Periodo"] + "\n" + df["Sede"]
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.barplot(data=df, x="Etiqueta", y="Porcentaje", hue="Sede", ax=ax)
    for container in ax.containers:
        ax.bar_label(container, labels=[f"{v:.1f}%" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=3, label_type="center")
    ax.set_title("Participación de cada sede respecto al total general por periodo", pad=15)
    ax.set_ylabel("Participación (%)")
    ax.set_xlabel("")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.ylim(0, 105)
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


# ============================================================
# GRÁFICAS CONSOLIDADAS TOTALES
# ============================================================
@st.cache_data(show_spinner=False)
def generar_grafica_dinero_total(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        total_periodo = sum(vals["dinero_interfaz"] for vals in data_sedes.values())
        datos.append({"Periodo": periodo, "Valor": total_periodo})
    df = pd.DataFrame(datos)
    if df.empty or df["Valor"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=df, x="Periodo", y="Valor", ax=ax, color="#305496")
    def _fmt_corto(v):
        if v <= 0: return ""
        if v >= 1_000_000: return f"${v/1_000_000:,.1f}M"
        elif v >= 1_000: return f"${v/1_000:,.0f}K"
        return f"${v:,.0f}"
    for container in ax.containers:
        ax.bar_label(container, labels=[_fmt_corto(v) for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_ylim(0, df["Valor"].max() * 1.05)
    ax.set_title("Dinero enviado por interfaz por periodo (Todas las sedes consolidadas)", pad=15)
    ax.set_ylabel("Valor (COP)")
    ax.set_xlabel("Periodo")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def generar_grafica_cobertura_total(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        avaladas_total = sum(vals["avaladas"] for vals in data_sedes.values())
        total_ventas_total = sum(vals["total_ventas"] for vals in data_sedes.values())
        cobertura = (avaladas_total / total_ventas_total * 100.0) if total_ventas_total > 0 else 0.0
        datos.append({"Periodo": periodo, "Cobertura": cobertura})
    df = pd.DataFrame(datos)
    if df.empty or df["Cobertura"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=df, x="Periodo", y="Cobertura", ax=ax, color="#305496")
    for container in ax.containers:
        ax.bar_label(container, labels=[f"{v:.1f}%" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
    ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
    ax.set_ylim(0, 105)
    ax.set_title("Cobertura general de honorarios médicos por periodo (Todas las sedes consolidadas)", pad=15)
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Periodo")
    plt.xticks(rotation=30, ha="right")
    ax.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def generar_grafica_participacion_fase_total(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        f1 = sum(vals.get("dinero_interfaz_fase_1", 0) for vals in data_sedes.values())
        f2 = sum(vals.get("dinero_interfaz_fase_2", 0) for vals in data_sedes.values())
        f3 = sum(vals.get("dinero_interfaz_fase_3", 0) for vals in data_sedes.values())
        datos.append({"Periodo": periodo, "Fase 1 - Ambulatorio": f1, "Fase 2 - Hospitalario": f2, "Fase 3 - Quirúrgico": f3})
    df = pd.DataFrame(datos).set_index("Periodo")
    if df.empty: return None
    total_por_fila = df.sum(axis=1)
    df_pct = df.div(total_por_fila.replace(0, pd.NA), axis=0).fillna(0) * 100
    fig, ax = plt.subplots(figsize=(12, 6))
    df_pct.plot(kind="bar", stacked=True, ax=ax, color=["#305496", "#D1615D", "#85C17E"], width=0.5)
    for container in ax.containers:
        vals = [v.get_height() for v in container]
        labels = [f"{v:.1f}%" if v > 3 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=10, color="white", weight="bold")
    ax.set_title("Participación por fase — Todas las sedes consolidadas", pad=15)
    ax.set_ylabel("Participación (%)")
    ax.set_xlabel("Periodo")
    plt.xticks(rotation=30, ha="right", fontsize=9)
    plt.legend(title="Fase", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def generar_grafica_participacion_sede_total(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            datos.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
    df = pd.DataFrame(datos)
    if df.empty: return None
    df["Total_Periodo"] = df.groupby("Periodo")["Valor"].transform("sum")
    df["Porcentaje"] = df.apply(lambda r: (r["Valor"] / r["Total_Periodo"] * 100) if r["Total_Periodo"] > 0 else 0, axis=1)
    df_melt = df.pivot_table(index="Periodo", columns="Sede", values="Porcentaje", fill_value=0)
    fig, ax = plt.subplots(figsize=(12, 6))
    df_melt.plot(kind="bar", stacked=True, ax=ax, width=0.5, colormap="tab10")
    for container in ax.containers:
        vals = [v.get_height() for v in container]
        labels = [f"{v:.1f}%" if v > 3 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=8, color="white", weight="bold")
    ax.set_title("Participación de cada sede en el total general por periodo", pad=15)
    ax.set_ylabel("Participación (%)")
    ax.set_xlabel("Periodo")
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return buf.getvalue()


# ============================================================
# EXCEL CACHEADO
# ============================================================
@st.cache_data(show_spinner="Generando Excel de resultados...")
def generar_excel_bytes(resultados, periodo_etiqueta, periodo_inicio, periodo_fin):
    tablas_por_fase = resultados["tablas_por_fase"]
    tabla_consolidada = resultados["tabla_consolidada"]
    resumen_verifica = resultados["resumen_verifica"]
    totales_sin_match_atenciones_df = resultados["totales_sin_match_atenciones_df"]
    consolidados_por_periodo = resultados["consolidados_por_periodo"]

    wb = Workbook()
    bold_white = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="305496")
    title_fill = PatternFill("solid", fgColor="1F4E78")
    info_fill = PatternFill("solid", fgColor="D9E1F2")

    def escribir_tabla(ws, tabla_df, titulo, fila_inicio):
        fila = fila_inicio
        ws.cell(row=fila, column=1, value=titulo).font = Font(bold=True, size=13, color="FFFFFF")
        for col_idx in range(1, len(tabla_df.columns) + 2):
            ws.cell(row=fila, column=col_idx).fill = title_fill
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=len(tabla_df.columns) + 1)
        fila += 1

        ws.cell(row=fila, column=1, value="Concepto").font = bold_white
        ws.cell(row=fila, column=1).fill = header_fill
        for j, col in enumerate(tabla_df.columns, start=2):
            c = ws.cell(row=fila, column=j, value=col)
            c.font = bold_white
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", wrap_text=True)
        fila += 1

        for idx, row in tabla_df.iterrows():
            ws.cell(row=fila, column=1, value=str(idx)).font = Font(bold=True)
            for j, col in enumerate(tabla_df.columns, start=2):
                ws.cell(row=fila, column=j, value=row[col])
            fila += 1
        return fila + 2

    ws1 = wb.active
    ws1.title = "Resultados"

    periodo_info = None
    if periodo_etiqueta != "—":
        periodo_info = f"Periodo: {periodo_etiqueta} | Inicio: {periodo_inicio} | Fin: {periodo_fin}"

    fila = 1
    if periodo_info:
        ws1.cell(row=fila, column=1, value=periodo_info).font = Font(bold=True, size=12, color="FFFFFF")
        for c in range(1, len(COLUMNAS_RESUMEN) + 2):
            ws1.cell(row=fila, column=c).fill = title_fill
        ws1.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=len(COLUMNAS_RESUMEN) + 1)
        fila += 2

    for fase in FASES:
        fila = escribir_tabla(ws1, tablas_por_fase[fase], TITULOS_FASES[fase], fila)
    fila = escribir_tabla(ws1, tabla_consolidada, "CONSOLIDADO - TODAS LAS FASES", fila)

    for col_idx in range(1, len(COLUMNAS_RESUMEN) + 2):
        ws1.column_dimensions[get_column_letter(col_idx)].width = 28 if col_idx == 1 else 22

    ws2 = wb.create_sheet("Totales sin match")
    if totales_sin_match_atenciones_df is None or totales_sin_match_atenciones_df.empty:
        ws2.cell(row=1, column=1, value="No hay registros de Totales sin coincidencia en Atenciones.")
    else:
        for j, col in enumerate(totales_sin_match_atenciones_df.columns, start=1):
            c = ws2.cell(row=1, column=j, value=col)
            c.font = bold_white
            c.fill = header_fill
        for i, (_, row) in enumerate(totales_sin_match_atenciones_df.iterrows(), start=2):
            for j, col in enumerate(totales_sin_match_atenciones_df.columns, start=1):
                ws2.cell(row=i, column=j, value=row[col])
        for j in range(1, len(totales_sin_match_atenciones_df.columns) + 1):
            ws2.column_dimensions[get_column_letter(j)].width = 30

    ws3 = wb.create_sheet("Novedades")
    if resumen_verifica is None or resumen_verifica.empty:
        ws3.cell(row=1, column=1, value="No hay registros en Novedades.")
    else:
        for j, col in enumerate(resumen_verifica.columns, start=1):
            c = ws3.cell(row=1, column=j, value=col)
            c.font = bold_white
            c.fill = header_fill
        for i, (_, row) in enumerate(resumen_verifica.iterrows(), start=2):
            for j, col in enumerate(resumen_verifica.columns, start=1):
                ws3.cell(row=i, column=j, value=row[col])
        ws3.column_dimensions["A"].width = 40
        ws3.column_dimensions["B"].width = 15
        ws3.column_dimensions["C"].width = 30

    ws4 = wb.create_sheet("Reglas")
    reglas = [
        ("Carga de archivos", ""), ("", "Se aceptan múltiples Excel (.xlsx, .xls)."),
        ("", "Cada hoja se clasifica: Ventas, Atenciones del especialista, Totales o Histórico."),
        ("", "Hojas/archivos duplicados se descartan por hash."),
        ("Periodo", ""), ("", "Se extrae del nombre del archivo (YYYY-MM, MM-YYYY, nombre de mes + año)."),
        ("Filtros previos", ""), ("", "En Totales: 'Total tarifas y recargos/descuentos' >= 1000."),
        ("Mapeo de (sede, fase)", ""), ("", "Match flexible contra el mapa Sede + Ubicación → Fase."),
        ("Cálculos por (sede, fase)", ""),
        ("1. Revisadas por analistas", "Ubicación mapea + 'Nombre de Usuario que Verifica' NO vacío + 'Valor liquidado' > 1000."),
        ("2. Avaladas subgerencia médica", "Revisadas + 'Usuario / Sub Medico' NO vacío + 'Valor liquidado' > 1000."),
        ("3. Dinero enviado por interfaz", "Σ 'Valor liquidado' válido (>= 1000), errores reportados aparte."),
        ("4. Total ventas", "count(Totales ∩ Ventas con 'tarifas' >= 1000). Errores reportados aparte."),
        ("5. Dinero ventas", "Σ 'tarifas (reliquidado)' válidas (>= 1000). Errores reportados aparte."),
        ("6. Porcentual faltante (META 30%)", "(Total ventas − Avaladas) / Total ventas × 100."),
        ("7. Ventas relacionadas en factura", "count(Ventas con Estado=Facturada, 'Valor facturado' >= 1000 y 'Venta No.' ∈ Totales)."),
        ("8. Dinero ventas (Facturado)", "Σ 'Valor facturado' válido (>= 1000) con Estado=Facturada y 'Venta No.' ∈ Totales."),
        ("9. Porcentual impactado (META 0%)", "(Total ventas − Ventas relacionadas) / Total ventas × 100."),
        ("Consolidado", "Suma de las 3 fases. Porcentajes recalculados."),
        ("Agrupación", "Las gráficas permiten agrupar por Mes, Bimestre, Trimestre, Semestre o Año."),
    ]
    for i, (c1, c2) in enumerate(reglas, start=1):
        celda1 = ws4.cell(row=i, column=1, value=c1)
        celda2 = ws4.cell(row=i, column=2, value=c2)
        if c1 and not c2:
            celda1.font = Font(bold=True, size=12, color="305496")
            celda1.fill = info_fill
        celda2.alignment = Alignment(wrap_text=True, vertical="top")
    ws4.column_dimensions["A"].width = 40
    ws4.column_dimensions["B"].width = 100

    ws_analisis = wb.create_sheet("Análisis")
    ws_analisis.cell(row=1, column=1, value="Análisis histórico comparativo entre periodos (Consolidado por sede)").font = Font(bold=True, size=14, color="305496")

    if len(consolidados_por_periodo) == 0:
        ws_analisis.cell(row=3, column=1, value="No hay datos suficientes para generar el análisis.")
    else:
        sns.set_theme(style="whitegrid")
        fila_actual = 3

        def insertar_grafico(ws, fig, fila, ancho=900, alto=420, titulo=None):
            if titulo:
                ws.cell(row=fila, column=1, value=titulo).font = Font(bold=True, size=12, color="1F4E78")
                fila += 1
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", dpi=110, bbox_inches="tight")
            img_buffer.seek(0)
            xl_img = XLImage(img_buffer)
            xl_img.width = ancho
            xl_img.height = alto
            ws.add_image(xl_img, f"A{fila}")
            return fila + int(alto / 20) + 3

        datos_g1 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            for sede, vals in data_sedes.items():
                datos_g1.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
        df_g1 = pd.DataFrame(datos_g1)

        if not df_g1.empty and df_g1["Valor"].sum() > 0:
            fig, ax = plt.subplots(figsize=(14, 6))
            sns.barplot(data=df_g1, x="Periodo", y="Valor", hue="Sede", ax=ax)
            for container in ax.containers:
                ax.bar_label(container, labels=[f"${v/1e6:,.1f}M" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
            ax.set_ylim(0, df_g1["Valor"].max() * 1.05)
            ax.set_title("Dinero enviado por interfaz por periodo y sede (Consolidado)", pad=15)
            ax.set_ylabel("Valor (COP)")
            ax.set_xlabel("Periodo")
            plt.xticks(rotation=30, ha="right")
            plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
            plt.tight_layout()
            plt.subplots_adjust(top=0.88)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 1 — Dinero enviado por interfaz (COP)")
            plt.close(fig)

        datos_g2 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            for sede, vals in data_sedes.items():
                avaladas = vals["avaladas"]
                total_ventas = vals["total_ventas"]
                cobertura = (avaladas / total_ventas * 100.0) if total_ventas > 0 else 0.0
                datos_g2.append({"Periodo": periodo, "Sede": sede, "Cobertura": cobertura})
        df_g2 = pd.DataFrame(datos_g2)

        if not df_g2.empty and df_g2["Cobertura"].sum() > 0:
            fig, ax = plt.subplots(figsize=(14, 6))
            sns.barplot(data=df_g2, x="Periodo", y="Cobertura", hue="Sede", ax=ax)
            for container in ax.containers:
                ax.bar_label(container, labels=[f"{v:.1f}%" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
            ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
            ax.set_ylim(0, 105)
            ax.set_title("Cobertura general de honorarios médicos (Avaladas / Total ventas)", pad=15)
            ax.set_ylabel("Cobertura (%)")
            ax.set_xlabel("Periodo")
            plt.xticks(rotation=30, ha="right")
            plt.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
            plt.tight_layout()
            plt.subplots_adjust(top=0.88)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 2 — Cobertura general de honorarios médicos (meta 70%)")
            plt.close(fig)

        datos_g3 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            for sede, vals in data_sedes.items():
                datos_g3.append({
                    "Periodo": periodo, "Sede": sede,
                    "Fase 1 - Ambulatorio": vals.get("dinero_interfaz_fase_1", 0),
                    "Fase 2 - Hospitalario": vals.get("dinero_interfaz_fase_2", 0),
                    "Fase 3 - Quirúrgico": vals.get("dinero_interfaz_fase_3", 0),
                })
        df_g3 = pd.DataFrame(datos_g3)
        if not df_g3.empty:
            df_g3 = df_g3.set_index(["Periodo", "Sede"])
            total_fila = df_g3.sum(axis=1)
            df_g3_pct = df_g3.div(total_fila.replace(0, pd.NA), axis=0).fillna(0) * 100
            df_g3_pct = df_g3_pct.reset_index()
            df_g3_pct["Etiqueta"] = df_g3_pct["Periodo"] + "\n" + df_g3_pct["Sede"]
            df_g3_pct = df_g3_pct.set_index("Etiqueta")[["Fase 1 - Ambulatorio", "Fase 2 - Hospitalario", "Fase 3 - Quirúrgico"]]

            fig, ax = plt.subplots(figsize=(14, 7))
            df_g3_pct.plot(kind="bar", stacked=True, ax=ax, color=["#305496", "#D1615D", "#85C17E"], width=0.6)
            for container in ax.containers:
                vals = [v.get_height() for v in container]
                labels = [f"{v:.1f}%" if v > 3 else "" for v in vals]
                ax.bar_label(container, labels=labels, label_type="center", fontsize=9, color="white", weight="bold")
            ax.set_title("Participación por fase de cada sede y periodo", pad=15)
            ax.set_ylabel("Participación (%)")
            plt.xticks(rotation=45, ha="right", fontsize=9)
            plt.ylim(0, 100)
            plt.tight_layout()
            plt.subplots_adjust(top=0.90)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 3 — Participación por fase (por sede)")
            plt.close(fig)

        if not df_g1.empty:
            df_g1["Total_Periodo"] = df_g1.groupby("Periodo")["Valor"].transform("sum")
            df_g1["Porcentaje"] = df_g1.apply(lambda r: (r["Valor"] / r["Total_Periodo"] * 100) if r["Total_Periodo"] > 0 else 0, axis=1)
            df_g1["Etiqueta"] = df_g1["Periodo"] + "\n" + df_g1["Sede"]

            fig, ax = plt.subplots(figsize=(14, 7))
            sns.barplot(data=df_g1, x="Etiqueta", y="Porcentaje", hue="Sede", ax=ax)
            for container in ax.containers:
                ax.bar_label(container, labels=[f"{v:.1f}%" if v > 0 else "" for v in container.datavalues], label_type="center", fontsize=9, padding=3)
            ax.set_title("Participación de cada sede respecto al total general por periodo", pad=15)
            ax.set_ylabel("Participación (%)")
            plt.xticks(rotation=45, ha="right", fontsize=8)
            plt.ylim(0, 105)
            plt.tight_layout()
            plt.subplots_adjust(top=0.88)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 4 — Participación de cada sede en el total")
            plt.close(fig)

        sedes_con_datos = set()
        for periodo, data_sedes in consolidados_por_periodo.items():
            for sede, vals in data_sedes.items():
                if vals["dinero_interfaz"] > 0 or vals["total_ventas"] > 0 or vals["avaladas"] > 0:
                    sedes_con_datos.add(sede)

        if len(sedes_con_datos) > 1:
            datos_g5 = []
            for periodo, data_sedes in consolidados_por_periodo.items():
                total_p = sum(vals["dinero_interfaz"] for vals in data_sedes.values())
                datos_g5.append({"Periodo": periodo, "Valor": total_p})
            df_g5 = pd.DataFrame(datos_g5)

            if not df_g5.empty and df_g5["Valor"].sum() > 0:
                fig, ax = plt.subplots(figsize=(12, 6))
                sns.barplot(data=df_g5, x="Periodo", y="Valor", ax=ax, color="#305496")
                for container in ax.containers:
                    ax.bar_label(container, labels=[f"${v/1e6:,.1f}M" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
                ax.set_ylim(0, df_g5["Valor"].max() * 1.05)
                ax.set_title("Dinero enviado por interfaz por periodo (Todas las sedes consolidadas)", pad=15)
                ax.set_ylabel("Valor (COP)")
                ax.set_xlabel("Periodo")
                plt.xticks(rotation=30, ha="right")
                plt.tight_layout()
                plt.subplots_adjust(top=0.88)
                fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 5 — Dinero enviado por interfaz (TODAS LAS SEDES)")
                plt.close(fig)

            datos_g6 = []
            for periodo, data_sedes in consolidados_por_periodo.items():
                avaladas_t = sum(vals["avaladas"] for vals in data_sedes.values())
                total_ventas_t = sum(vals["total_ventas"] for vals in data_sedes.values())
                cobertura = (avaladas_t / total_ventas_t * 100.0) if total_ventas_t > 0 else 0.0
                datos_g6.append({"Periodo": periodo, "Cobertura": cobertura})
            df_g6 = pd.DataFrame(datos_g6)

            if not df_g6.empty and df_g6["Cobertura"].sum() > 0:
                fig, ax = plt.subplots(figsize=(12, 6))
                sns.barplot(data=df_g6, x="Periodo", y="Cobertura", ax=ax, color="#305496")
                for container in ax.containers:
                    ax.bar_label(container, labels=[f"{v:.1f}%" if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=0, padding=2, label_type="center")
                ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
                ax.set_ylim(0, 105)
                ax.set_title("Cobertura general de honorarios médicos por periodo (Todas las sedes consolidadas)", pad=15)
                ax.set_ylabel("Cobertura (%)")
                ax.set_xlabel("Periodo")
                plt.xticks(rotation=30, ha="right")
                ax.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
                plt.tight_layout()
                plt.subplots_adjust(top=0.88)
                fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 6 — Cobertura general de honorarios médicos (TODAS LAS SEDES)")
                plt.close(fig)

            datos_g7 = []
            for periodo, data_sedes in consolidados_por_periodo.items():
                f1 = sum(vals.get("dinero_interfaz_fase_1", 0) for vals in data_sedes.values())
                f2 = sum(vals.get("dinero_interfaz_fase_2", 0) for vals in data_sedes.values())
                f3 = sum(vals.get("dinero_interfaz_fase_3", 0) for vals in data_sedes.values())
                datos_g7.append({"Periodo": periodo, "Fase 1 - Ambulatorio": f1, "Fase 2 - Hospitalario": f2, "Fase 3 - Quirúrgico": f3})
            df_g7 = pd.DataFrame(datos_g7).set_index("Periodo")

            if not df_g7.empty:
                total_fila = df_g7.sum(axis=1)
                df_g7_pct = df_g7.div(total_fila.replace(0, pd.NA), axis=0).fillna(0) * 100

                fig, ax = plt.subplots(figsize=(12, 6))
                df_g7_pct.plot(kind="bar", stacked=True, ax=ax, color=["#305496", "#D1615D", "#85C17E"], width=0.5)
                for container in ax.containers:
                    vals = [v.get_height() for v in container]
                    labels = [f"{v:.1f}%" if v > 3 else "" for v in vals]
                    ax.bar_label(container, labels=labels, label_type="center", fontsize=10, color="white", weight="bold")
                ax.set_title("Participación por fase — Todas las sedes consolidadas", pad=15)
                ax.set_ylabel("Participación (%)")
                plt.xticks(rotation=30, ha="right", fontsize=9)
                plt.ylim(0, 100)
                plt.tight_layout()
                plt.subplots_adjust(top=0.88)
                fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 7 — Participación por fase (Todas las sedes)")
                plt.close(fig)

            datos_g8 = []
            for periodo, data_sedes in consolidados_por_periodo.items():
                for sede, vals in data_sedes.items():
                    datos_g8.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
            df_g8 = pd.DataFrame(datos_g8)

            if not df_g8.empty:
                df_g8["Total_Periodo"] = df_g8.groupby("Periodo")["Valor"].transform("sum")
                df_g8["Porcentaje"] = df_g8.apply(lambda r: (r["Valor"] / r["Total_Periodo"] * 100) if r["Total_Periodo"] > 0 else 0, axis=1)
                df_g8_melt = df_g8.pivot_table(index="Periodo", columns="Sede", values="Porcentaje", fill_value=0)

                fig, ax = plt.subplots(figsize=(12, 6))
                df_g8_melt.plot(kind="bar", stacked=True, ax=ax, width=0.5, colormap="tab10")
                for container in ax.containers:
                    vals = [v.get_height() for v in container]
                    labels = [f"{v:.1f}%" if v > 3 else "" for v in vals]
                    ax.bar_label(container, labels=labels, label_type="center", fontsize=8, color="white", weight="bold")
                ax.set_title("Participación de cada sede en el total general por periodo", pad=15)
                ax.set_ylabel("Participación (%)")
                plt.xticks(rotation=30, ha="right")
                plt.ylim(0, 100)
                plt.tight_layout()
                plt.subplots_adjust(top=0.88)
                fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, titulo="Gráfico 8 — Participación de cada sede (Todas las sedes)")
                plt.close(fig)

        ws_analisis.column_dimensions["A"].width = 130

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("📚 Reglas de procesamiento")
    st.markdown("""
**Carga de archivos**
- Se aceptan múltiples Excel (`.xlsx`, `.xls`).
- Se clasifican: **Ventas**, **Atenciones del especialista**, **Totales** o **Histórico**.
- Se descartan hojas/archivos duplicados por hash.

**Periodo**
- Se extrae del nombre del archivo (`YYYY-MM`, `MM-YYYY`, mes + año, etc.).

**Filtros previos**
- En **Totales**: `Total tarifas y recargos/descuentos >= 1000`.

**Mapeo de (sede, fase)**
- Match flexible contra el mapa `Sede + Ubicación → Fase`.

**Cálculos por (sede, fase)**

1. **Revisadas**: Ubicación mapea + `Usuario que Verifica` NO vacío + `Valor liquidado > 1000`.
2. **Avaladas**: Revisadas + `Usuario / Sub Medico` NO vacío + `Valor liquidado > 1000`.
3. **Dinero interfaz**: Σ `Valor liquidado` válido (>= 1000), errores reportados aparte.
4. **Total ventas**: count(Totales ∩ Ventas con `tarifas` >= 1000). Errores reportados aparte.
5. **Dinero ventas**: Σ `tarifas (reliquidado)` válidas (>= 1000). Errores reportados aparte.
6. **Porcentual faltante**: `(Total ventas − Avaladas) / Total ventas × 100`.
7. **Ventas relacionadas**: count(Ventas con Estado=Facturada y `Valor facturado` >= 1000)
   **que además existan en Totales** (`Venta No.` ∈ `No. de venta`).
8. **Dinero ventas (Facturado)**: Σ `Valor facturado` válido (>= 1000) con Estado=Facturada
   y que además existan en Totales.
9. **Porcentual impactado**: `(Total ventas − Ventas relacionadas) / Total ventas × 100`.

**Consolidado**
- Suma de las 3 fases. Porcentajes recalculados.

**Agrupación**
- Las gráficas permiten agrupar por Mes, Bimestre, Trimestre, Semestre o Año.
""")

# ============================================================
# CARGA
# ============================================================
uploaded_files = st.file_uploader(
    "Selecciona los archivos Excel (.xlsx, .xls)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("👆 Carga al menos un archivo Excel para comenzar.")
    st.stop()

files_data = tuple((f.name, f.getvalue()) for f in uploaded_files)

# ============================================================
# PROCESAR
# ============================================================
resultados = procesar_todo(files_data)

tablas_por_fase = resultados["tablas_por_fase"]
tabla_consolidada = resultados["tabla_consolidada"]
resumen_verifica = resultados["resumen_verifica"]
consolidados_por_periodo = resultados["consolidados_por_periodo"]
periodo_etiqueta = resultados["periodo_etiqueta"]
periodo_inicio = resultados["periodo_inicio"]
periodo_fin = resultados["periodo_fin"]

# ============================================================
# PERIODO
# ============================================================
if periodo_etiqueta != "—":
    st.markdown(
        f"<div style='background-color:#D9E1F2; padding:10px 15px; border-radius:8px; "
        f"border-left:5px solid #305496; margin-bottom:15px;'>"
        f"<b>📅 Periodo analizado:</b> {periodo_etiqueta} "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; <b>Inicio:</b> {periodo_inicio} "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; <b>Fin:</b> {periodo_fin}"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    if len(consolidados_por_periodo) > 0:
        st.info("ℹ️ No se detectó un periodo actual (archivos crudos), pero se cargó el histórico correctamente.")
    else:
        st.warning("⚠️ No se pudo detectar el periodo desde el nombre de los archivos.")

# ============================================================
# DIAGNÓSTICOS
# ============================================================
if resultados["errores"]:
    with st.expander("❌ Errores al leer archivos", expanded=False):
        for nombre, err in resultados["errores"]:
            st.write(f"- **{nombre}**: {err}")

if resultados["no_clasificados"]:
    with st.expander("⚠️ Archivos/hojas NO clasificados", expanded=False):
        st.dataframe(pd.DataFrame(resultados["no_clasificados"]), use_container_width=True)

if not resultados["ubicaciones_no_mapeadas"].empty:
    with st.expander("⚠️ Ubicaciones de la venta (Atenciones) sin coincidencia", expanded=False):
        st.dataframe(resultados["ubicaciones_no_mapeadas"], use_container_width=True)

if not resultados["ubicaciones_totales_no_mapeadas"].empty:
    with st.expander("⚠️ Centros de Costo (Totales) sin coincidencia", expanded=False):
        st.dataframe(resultados["ubicaciones_totales_no_mapeadas"], use_container_width=True)

if not resultados["ubicaciones_ventas_no_mapeadas"].empty:
    with st.expander("⚠️ Centros de costo (Ventas) sin coincidencia", expanded=False):
        st.dataframe(resultados["ubicaciones_ventas_no_mapeadas"], use_container_width=True)

if not resultados["estados_no_incluidos"].empty:
    with st.expander("ℹ️ Estados en Ventas NO incluidos (solo 'Facturada')", expanded=False):
        st.dataframe(resultados["estados_no_incluidos"], use_container_width=True)

# ============================================================
# TABLAS
# ============================================================
for fase in FASES:
    st.subheader(f"📋 {TITULOS_FASES[fase]}")
    st.dataframe(tablas_por_fase[fase], use_container_width=True, height=420)
    st.divider()

st.subheader("📋 CONSOLIDADO - TODAS LAS FASES")
st.dataframe(tabla_consolidada, use_container_width=True, height=420)
st.divider()

# ============================================================
# NOVEDADES
# ============================================================
st.subheader("🔎 Novedades")
if resumen_verifica.empty:
    st.info("No hay registros que cumplan los filtros de 'Revisadas por analistas'.")
else:
    st.dataframe(resumen_verifica, use_container_width=True)
st.divider()

# ============================================================
# ANÁLISIS HISTÓRICO Y RESUMEN
# ============================================================
if len(consolidados_por_periodo) > 0:
    with st.expander("📈 Análisis histórico comparativo y Resumen Ejecutivo", expanded=True):
        
        # 1. Selector de agrupación
        agrupacion = st.radio(
            "Agrupar resultados por:",
            options=["Mes", "Bimestre", "Trimestre", "Semestre", "Año"],
            horizontal=True,
            key="selector_agrupacion"
        )

        # 2. Aplicar agrupación y ordenar
        consolidados_agrupados = agrupar_consolidados(consolidados_por_periodo, agrupacion)
        consolidados_agrupados = _ordenar_llaves_cronologicamente(consolidados_agrupados)
        
        # 3. Generar la firma basada en los datos agrupados
        firma = _firma_consolidados(consolidados_agrupados)

        # 4. Narrativa del Resumen Ejecutivo
        st.markdown("### 📝 Resumen Ejecutivo")
        periodos_ordenados = list(consolidados_agrupados.keys())
        ultimo_periodo = periodos_ordenados[-1]

        total_revisadas = sum(vals["revisadas"] for vals in consolidados_agrupados[ultimo_periodo].values())
        total_avaladas = sum(vals["avaladas"] for vals in consolidados_agrupados[ultimo_periodo].values())
        total_ventas = sum(vals["total_ventas"] for vals in consolidados_agrupados[ultimo_periodo].values())
        total_dinero = sum(vals["dinero_interfaz"] for vals in consolidados_agrupados[ultimo_periodo].values())

        cobertura = (total_avaladas / total_ventas * 100) if total_ventas > 0 else 0
        sede_top = max(consolidados_agrupados[ultimo_periodo].items(), key=lambda x: x[1]["dinero_interfaz"])

        narrativa = f"""
En el periodo **{ultimo_periodo}**, se procesaron un total de **{total_revisadas:,}** registros, de los cuales **{total_avaladas:,}** fueron avalados por la subgerencia médica.
El dinero total enviado por interfaz ascendió a **${total_dinero:,.0f}**.
La cobertura general de honorarios médicos (Avaladas / Total Ventas) se situó en **{cobertura:.1f}%** frente a la meta del 70%.
La sede con mayor participación en el envío de dinero por interfaz fue **{sede_top[0]}** con un monto de **${sede_top[1]['dinero_interfaz']:,.0f}**.
"""
        if len(periodos_ordenados) > 1:
            primer_periodo = periodos_ordenados[0]
            total_dinero_primero = sum(vals["dinero_interfaz"] for vals in consolidados_agrupados[primer_periodo].values())

            if total_dinero_primero > 0:
                variacion = ((total_dinero - total_dinero_primero) / total_dinero_primero) * 100
                tendencia = "un incremento" if variacion >= 0 else "una disminución"
                narrativa += f"\n\nEn cuanto al histórico, al comparar **{ultimo_periodo}** con **{primer_periodo}**, se observa {tendencia} del **{abs(variacion):.1f}%** en el dinero total enviado por interfaz."
            else:
                narrativa += f"\n\nEn cuanto al histórico, el primer periodo registrado ({primer_periodo}) no presentó datos base para calcular variaciones."

        st.info(narrativa)

        st.divider()
        st.markdown("### 📈 Gráficas Comparativas")

        sns.set_theme(style="whitegrid")

        sedes_con_datos = set()
        for periodo, data_sedes in consolidados_agrupados.items():
            for sede, vals in data_sedes.items():
                if (vals["dinero_interfaz"] > 0 or vals["total_ventas"] > 0 or vals["avaladas"] > 0):
                    sedes_con_datos.add(sede)

        mostrar_consolidado_total = len(sedes_con_datos) > 1

        if mostrar_consolidado_total:
            st.markdown(f"#### Gráficas por sede (se detectaron {len(sedes_con_datos)} sedes con datos)")
        else:
            st.markdown(f"#### Gráficas por sede (solo se detectó **{len(sedes_con_datos)}** sede con datos — las gráficas consolidadas totales se muestran cuando hay más de 1 sede)")

        st.markdown("##### 💰 Dinero enviado por interfaz por periodo (por sede)")
        img_dinero = generar_grafica_dinero(consolidados_agrupados, firma)
        if img_dinero: st.image(img_dinero, use_container_width=True)

        st.markdown("##### 📈 Cobertura general de honorarios médicos (por sede)")
        img_cobertura = generar_grafica_cobertura(consolidados_agrupados, firma)
        if img_cobertura: st.image(img_cobertura, use_container_width=True)

        st.markdown("##### 🥧 Participación por fase de cada sede y periodo")
        img_part_fase = generar_grafica_participacion_fase(consolidados_agrupados, firma)
        if img_part_fase: st.image(img_part_fase, use_container_width=True)

        st.markdown("##### 🥧 Participación de cada sede en el total general")
        img_part_sede = generar_grafica_participacion_sede(consolidados_agrupados, firma)
        if img_part_sede: st.image(img_part_sede, use_container_width=True)

        if mostrar_consolidado_total:
            st.markdown("---")
            st.markdown("#### 📊 Vista consolidada — Todas las sedes sumadas")

            st.markdown("##### 💰 Dinero enviado por interfaz (Total por periodo)")
            img_dinero_total = generar_grafica_dinero_total(consolidados_agrupados, firma)
            if img_dinero_total: st.image(img_dinero_total, use_container_width=True)

            st.markdown("##### 📈 Cobertura general de honorarios médicos (Total por periodo)")
            img_cobertura_total = generar_grafica_cobertura_total(consolidados_agrupados, firma)
            if img_cobertura_total: st.image(img_cobertura_total, use_container_width=True)

            st.markdown("##### 🥧 Participación por fase (Todas las sedes consolidadas)")
            img_part_fase_total = generar_grafica_participacion_fase_total(consolidados_agrupados, firma)
            if img_part_fase_total: st.image(img_part_fase_total, use_container_width=True)

            st.markdown("##### 🥧 Participación de cada sede (Todas las sedes consolidadas)")
            img_part_sede_total = generar_grafica_participacion_sede_total(consolidados_agrupados, firma)
            if img_part_sede_total: st.image(img_part_sede_total, use_container_width=True)

# ============================================================
# EXPORTABLE EXCEL
# ============================================================
st.subheader("📥 Descarga de Resultados")
col1, col2 = st.columns(2)

with col1:
    try:
        excel_bytes = generar_excel_bytes(resultados, periodo_etiqueta, periodo_inicio, periodo_fin)
        st.download_button(
            label="📊 Descargar Resumen y Análisis (Excel)",
            data=excel_bytes,
            file_name=f"Resultados_Resumen_{periodo_etiqueta.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_excel_resumen",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"❌ Error generando el Excel: {e}")
