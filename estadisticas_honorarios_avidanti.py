import streamlit as st
import pandas as pd
import hashlib
import re
import io
import unicodedata
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
# FUNCIONES AUXILIARES DE FORMATO
# ============================================================
def formatear_numero(valor, es_dinero=False):
    if pd.isna(valor) or valor is None:
        return ""
    try:
        if es_dinero:
            prefijo = "$"
            base = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            prefijo = ""
            if float(valor).is_integer():
                base = f"{valor:,.0f}".replace(",", ".")
            else:
                base = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{prefijo}{base}"
    except:
        return str(valor)

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def limpiar_texto(s):
    """Elimina caracteres invisibles, espacios duros, BOM, etc."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\xa0", " ").replace("\u202f", " ").replace("\ufeff", "").replace("\u2007", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def normalizar(s):
    if pd.isna(s): return ""
    txt = limpiar_texto(s).lower()
    txt = (txt.replace("Ã³", "o").replace("Ã¡", "a").replace("Ã©", "e").replace("Ã", "i").replace("Ãº", "u"))
    txt = (txt.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    txt = re.sub(r"[_\-\.,/()]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def extraer_codigo_producto(valor):
    if pd.isna(valor):
        return ""
    s = limpiar_texto(valor)
    m = re.match(r"^(\d{6})", s)
    if m:
        return m.group(1)
    m = re.search(r"(\d{6})", s)
    return m.group(1) if m else ""

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
    
    for ubi_norm, (sede, fase, tokens_ubi) in MAPA_UBICACION_TOKENS.items():
        if sedes_mencionadas and sede not in sedes_mencionadas:
            continue
        if tokens_ubi and tokens_ubi.issubset(tokens_valor):
            score = len(tokens_ubi)
            if score > mejor_score:
                mejor_score, mejor_match = score, (sede, fase)
    
    if not mejor_match:
        for ubi_norm, (sede, fase, tokens_ubi) in MAPA_UBICACION_TOKENS.items():
            if sedes_mencionadas and sede not in sedes_mencionadas:
                continue
            if not tokens_ubi:
                continue
            interseccion = tokens_ubi & tokens_valor
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
    primera_col = [limpiar_texto(v) for v in df.iloc[:, 0].astype(str).tolist()]
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
        primera_celda = limpiar_texto(valores[0]) if valores else ""
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
                    v = valores[j]
                    if pd.isna(v) if not isinstance(v, str) else False:
                        v_str = ""
                    else:
                        v_str = limpiar_texto(v)
                    resultado[concepto_key][sede_canon] = v_str
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
    base = formatear_numero(total, es_dinero=True)
    if cant_err > 0: 
        err = formatear_numero(suma_err, es_dinero=True)
        pct = f"{pct_err:.2f}".replace(".", ",")
        return f"{base} (Errores: {err} en {cant_err} registros — {pct}%)"
    return base

def formatear_conteo_con_error(total, cant_err, suma_err, pct_err):
    base = formatear_numero(total)
    if cant_err > 0: 
        err = formatear_numero(suma_err, es_dinero=True)
        pct = f"{pct_err:.2f}".replace(".", ",")
        return f"{base} (Errores: {err} en {cant_err} registros — {pct}%)"
    return base

def formatear_dinero_con_error(total, cant_err, suma_err, pct_err):
    base = formatear_numero(total, es_dinero=True)
    if cant_err > 0: 
        err = formatear_numero(suma_err, es_dinero=True)
        pct = f"{pct_err:.2f}".replace(".", ",")
        return f"{base} (Errores: {err} en {cant_err} registros — {pct}%)"
    return base

# ============================================================
# PARSER DE VALORES ROBUSTO (US / CO / invisible)
# ============================================================
def parsear_valor_generico(v):
    """
    Convierte cualquier valor (str, float, int, np.float64, NaN, None) a float.
    Soporta formato US ($1,234,567.89) y CO ($1.234.567,89).
    Extrae únicamente el valor válido fuera del paréntesis de errores.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            if pd.isna(v):
                return None
            return float(v)
        except Exception:
            pass
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "null", "nat", ""):
        return None
    
    # Eliminar estrictamente cualquier contenido entre paréntesis (errores)
    if "(" in s:
        s = s.split("(")[0].strip()
    
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in ("-", ".", ","):
        return None

    tiene_coma = "," in s
    tiene_punto = "." in s

    if tiene_coma and tiene_punto:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif tiene_punto:
        partes = s.split(".")
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3 and len(partes[0]) <= 3):
            s = s.replace(".", "")
    elif tiene_coma:
        partes = s.split(",")
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3 and len(partes[0]) <= 3):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        solo_digitos = re.sub(r"[^\d]", "", s)
        if solo_digitos:
            try:
                return float(solo_digitos)
            except Exception:
                return None
        return None

def normalizar_etiqueta_hist(concepto):
    c = limpiar_texto(concepto)
    if c.startswith("Total ventas ") and "(ACTIVO Y FACTURADO)" in c: return "Total ventas (ACTIVO Y FACTURADO)"
    if c.startswith("Dinero ventas ") and "Facturado" not in c: return "Dinero ventas"
    return c

MAPA_METRICAS_HIST = {
    "Revisadas por analistas": "revisadas",
    "Avaladas subgerencia médica": "avaladas",
    "Total ventas (ACTIVO Y FACTURADO)": "total_ventas",
    "Dinero enviado por interfaz": "dinero_interfaz",
    "Dinero ventas": "dinero_ventas",
    "Ventas relacionadas en factura (FACTURADO)": "ventas_relacionadas",
    "Dinero ventas (Facturado)": "dinero_facturado",
}

def _etiqueta_periodo_corta(p):
    e = str(p)
    for l, c in [
        ("Enero","Ene"),("Febrero","Feb"),("Marzo","Mar"),("Abril","Abr"),
        ("Mayo","May"),("Junio","Jun"),("Julio","Jul"),("Agosto","Ago"),
        ("Septiembre","Sep"),("Octubre","Oct"),("Noviembre","Nov"),("Diciembre","Dic")
    ]:
        e = e.replace(l, c)
    return e.replace(" 20", "-")

# ============================================================
# AGRUPACIÓN Y ORDEN
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
# PROCESAMIENTO CACHEADO
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
            xls = pd.ExcelFile(io.BytesIO(f_bytes))
        except Exception as e:
            errores.append({"Archivo": f_name, "Error": str(e)})
            continue

        for sheet_name in xls.sheet_names:
            try:
                df_sheet = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
                df_sheet = df_sheet.dropna(how="all").dropna(axis=1, how="all")
                if df_sheet.empty:
                    continue

                if es_hoja_de_resultados(df_sheet):
                    res_pars = parsear_hoja_resultados(df_sheet, sheet_name)
                    etiqueta_periodo, _, _ = formatear_periodo(anio, mes)
                    if etiqueta_periodo == "—":
                        etiqueta_periodo = f_name.rsplit(".", 1)[0]

                    if etiqueta_periodo not in historicos_detectados:
                        historicos_detectados[etiqueta_periodo] = {
                            sede: {
                                "revisadas": 0, "avaladas": 0, "total_ventas": 0,
                                "dinero_interfaz": 0.0, "dinero_ventas": 0.0,
                                "ventas_relacionadas": 0, "dinero_facturado": 0.0,
                                "dinero_interfaz_fase_1": 0.0, "dinero_interfaz_fase_2": 0.0, "dinero_interfaz_fase_3": 0.0
                            }
                            for sede in COLUMNAS_RESUMEN
                        }

                    for concepto_fase, sedes_vals in res_pars.items():
                        partes = concepto_fase.split(" - ", 1)
                        if len(partes) != 2:
                            continue
                        fase_str, concepto_bruto = partes
                        concepto_norm = normalizar_etiqueta_hist(concepto_bruto)
                        metrica = MAPA_METRICAS_HIST.get(concepto_norm)

                        for sede, val_str in sedes_vals.items():
                            # Extrae solo el valor válido fuera del paréntesis
                            val_num = parsear_valor_generico(val_str)
                            if val_num is not None:
                                if fase_str == "Consolidado" and metrica:
                                    historicos_detectados[etiqueta_periodo][sede][metrica] += val_num
                                
                                if fase_str == "Fase 1" and concepto_norm == "Dinero enviado por interfaz":
                                    historicos_detectados[etiqueta_periodo][sede]["dinero_interfaz_fase_1"] += val_num
                                elif fase_str == "Fase 2" and concepto_norm == "Dinero enviado por interfaz":
                                    historicos_detectados[etiqueta_periodo][sede]["dinero_interfaz_fase_2"] += val_num
                                elif fase_str == "Fase 3" and concepto_norm == "Dinero enviado por interfaz":
                                    historicos_detectados[etiqueta_periodo][sede]["dinero_interfaz_fase_3"] += val_num
                    continue

                hash_hoja = hash_df(df_sheet)
                if hash_hoja in hashes_hojas_vistos:
                    hojas_duplicadas.append({"Archivo": f_name, "Hoja": sheet_name, "Duplicada de": hashes_hojas_vistos[hash_hoja]})
                    continue
                hashes_hojas_vistos[hash_hoja] = f"{f_name} -> {sheet_name}"

                tipo_est, _ = clasificar_estructura(df_sheet.columns)
                if tipo_est:
                    df_sheet["_Archivo_Origen"] = f_name
                    df_sheet["_Hoja_Origen"] = sheet_name
                    bases[tipo_est].append(df_sheet)
                else:
                    no_clasificados.append({"Archivo": f_name, "Hoja": sheet_name, "Columnas": list(df_sheet.columns)[:8]})
            except Exception as e:
                errores.append({"Archivo": f_name, "Hoja": sheet_name, "Error": str(e)})

    df_ventas = pd.concat(bases["Ventas"], ignore_index=True) if bases["Ventas"] else pd.DataFrame()
    df_atenciones = pd.concat(bases["Atenciones del especialista"], ignore_index=True) if bases["Atenciones del especialista"] else pd.DataFrame()
    df_totales = pd.concat(bases["Totales"], ignore_index=True) if bases["Totales"] else pd.DataFrame()

    return df_ventas, df_atenciones, df_totales, historicos_detectados, no_clasificados, errores, archivos_duplicados, hojas_duplicadas, periodos_detectados

# ============================================================
# INTERFAZ DE CARGA DE ARCHIVOS
# ============================================================
archivos_subidos = st.file_uploader(
    "Sube tus archivos Excel (pueden ser archivos de Ventas, Atenciones, Totales o Resúmenes Históricos)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not archivos_subidos:
    st.info("👋 Por favor, carga al menos un archivo Excel para comenzar el análisis.")
    st.stop()

files_data = [(f.name, f.read()) for f in archivos_subidos]
df_ventas, df_atenciones, df_totales, historicos_detectados, no_clasificados, errores, archivos_duplicados, hojas_duplicadas, periodos_detectados = procesar_todo(files_data)

if archivos_duplicados or hojas_duplicadas or no_clasificados or errores:
    with st.expander("⚠️ Advertencias y registros no clasificados", expanded=False):
        if archivos_duplicados:
            st.warning("Archivos idénticos detectados (ignorados):")
            st.dataframe(pd.DataFrame(archivos_duplicados))
        if hojas_duplicadas:
            st.warning("Hojas idénticas detectadas (ignorados):")
            st.dataframe(pd.DataFrame(hojas_duplicadas))
        if no_clasificados:
            st.info("Hojas con estructuras no reconocidas:")
            st.dataframe(pd.DataFrame(no_clasificados))
        if errores:
            st.error("Errores al procesar archivos/hojas:")
            st.dataframe(pd.DataFrame(errores))

# ============================================================
# SELECCIÓN DE PERIODO Y DATOS BASE
# ============================================================
st.sidebar.header("⚙️ Configuración del Análisis")

anios_meses_disponibles = set()
for f_name, (a, m) in periodos_detectados:
    if a and m:
        anios_meses_disponibles.add((a, m))

if not anios_meses_disponibles:
    anios_meses_disponibles.add((datetime.now().year, datetime.now().month))

lista_periodos_ordenada = sorted(list(anios_meses_disponibles))
opciones_periodo = [formatear_periodo(a, m)[0] for a, m in lista_periodos_ordenada]

periodo_seleccionado_str = st.sidebar.selectbox("Selecciona el Periodo a Analizar", options=opciones_periodo)
idx_sel = opciones_periodo.index(periodo_seleccionado_str)
anio_sel, mes_sel = lista_periodos_ordenada[idx_sel]
_, fecha_ini, fecha_fin = formatear_periodo(anio_sel, mes_sel)

st.sidebar.markdown(f"**Rango:** {fecha_ini} al {fecha_fin}")

if not df_atenciones.empty:
    col_per_at = obtener_columna(df_atenciones, "Periodo")
    if col_per_at:
        df_atenciones["_Periodo_Norm"] = df_atenciones[col_per_at].astype(str).str.strip()

tab_actual, tab_historico = st.tabs(["📋 Análisis del Periodo Actual", "📈 Análisis Histórico & Gráficos"])

with tab_actual:
    st.subheader(f"Análisis Consolidado — {periodo_seleccionado_str}")
    st.markdown("Procesamiento en tiempo real basado en las tablas operativas cargadas.")
    st.info("Visualización operativa activa para el periodo seleccionado.")

with tab_historico:
    st.subheader("📈 Análisis Histórico y Tendencias (Datos Válidos)")
    st.markdown("Se excluyen automáticamente los errores de interfaz (contenido entre paréntesis) para reflejar únicamente los **datos válidos**.")

    if not historicos_detectados:
        st.warning("No se detectaron hojas de resultados históricos en los archivos cargados.")
    else:
        agrupacion_hist = st.selectbox("Agrupar histórico por:", ["Mes", "Bimestre", "Trimestre", "Semestre", "Año"], index=0)
        
        historicos_agrupados = agrupar_consolidados(historicos_detectados, agrupacion_hist)
        historicos_ordenados = _ordenar_llaves_cronologicamente(historicos_agrupados)

        periodos_eje = list(historicos_ordenados.keys())
        
        st.markdown("### Gráfico 5 — Cobertura total por periodo (todas las sedes)")
        
        datos_grafico_5 = []
        for p in periodos_eje:
            sedes_p = historicos_ordenados[p]
            # Se utilizan exclusivamente los valores válidos extraídos fuera del paréntesis
            total_rev = sum(d["revisadas"] for d in sedes_p.values())
            total_ventas = sum(d["total_ventas"] for d in sedes_p.values())
            cobertura = (total_rev / total_ventas * 100) if total_ventas > 0 else 0
            datos_grafico_5.append({
                "Periodo": _etiqueta_periodo_corta(p),
                "Cobertura (%)": cobertura,
                "Revisadas Válidas": total_rev,
                "Total Ventas Válidas": total_ventas
            })

        df_g5 = pd.DataFrame(datos_grafico_5)
        if not df_g5.empty:
            fig, ax = plt.subplots(figsize=(10, 4))
            sns.lineplot(data=df_g5, x="Periodo", y="Cobertura (%)", marker="o", ax=ax, color="#1f77b4", linewidth=2.5)
            
            for idx, row in df_g5.iterrows():
                ax.annotate(
                    f"{row['Cobertura (%)']:.1f}%",
                    (row["Periodo"], row["Cobertura (%)"]),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=9,
                    fontweight="bold"
                )
                
            ax.set_title("Gráfico 5 — Cobertura total por periodo (todas las sedes - Solo Datos Válidos)", fontsize=12, fontweight="bold")
            ax.set_xlabel("Periodo", fontsize=10)
            ax.set_ylabel("Cobertura (%)", fontsize=10)
            ax.set_ylim(0, 110)
            ax.grid(True, linestyle="--", alpha=0.6)
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)
            plt.clf()
        else:
            st.info("No hay datos suficientes para generar el Gráfico 5.")
