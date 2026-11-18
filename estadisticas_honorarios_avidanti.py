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

# Estructuras ALTERNAS aceptadas para clasificar un archivo (NO reemplazan a ESTRUCTURAS).
# Si un archivo coincide mejor con una alterna, se clasifica con el nombre de la estructura base.
ESTRUCTURAS_ALTERNAS = {
    "Ventas": [
        "Sede", "Periodo", "Profesional principal de la venta", "Tipo Documento",
        "Documento", "Concepto", "es empleado?", "No. de venta", "Estado de la venta",
        "Fecha de venta", "Ingreso", "Fecha de atención", "Contrato paciente",
        "Paciente", "Cod. Centro de costo", "Centro de costo", "Aseguradora", "Plan",
        "Tipo atención", "Clase de Ingreso", "Cod Cuenta Contable",
        "Nombre Cuenta Contable", "Area De Negocio", "Tipo de producto", "Categoría",
        "Cod Producto venta", "Producto venta", "Cantidad", "Cod. producto componente",
        "honorario asignado a:", "Especialidad", "Carg Equi Quirurgico", "Gremio",
        "Documento Gremio", "Valor venta", "Numero factura", "valor tarifa",
        "Valor recargo", "Forma de cálculo", "Valor configurado",
        "Forma de cálculo recargo/desc", "Valor configurado Recargo/desc",
        "Valor Unitario", "Valor Total", "Usuario que elimino",
        "Fecha de eliminación", "Descripción de eliminación",
    ],
}

# Alias de columnas dentro de Ventas: si NO existe el campo esperado (clave),
# se usa el primer alias que exista en el archivo.
ALIAS_COLUMNAS_VENTAS = {
    "Venta No.": ["No. de venta"],
    "Código Producto": ["Codigo Producto", "Cod Producto venta"],
    "Valor facturado": ["Valor Total"],   # <- campo para la sumatoria de valores
    "Estado": ["Estado de la venta"],
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
ESTRUCTURAS_ALTERNAS_NORM = {nombre: {normalizar(c) for c in cols} for nombre, cols in ESTRUCTURAS_ALTERNAS.items()}

def clasificar_estructura(columnas_df):
    """
    Compara contra las estructuras esperadas y contra las alternas.
    Devuelve (nombre_estructura_base, score). Las alternas NO modifican las esperadas.
    """
    cols_df_norm = {normalizar(c) for c in columnas_df}
    mejor = (None, 0.0)
    for nombre, esperadas in ESTRUCTURAS_NORM.items():
        if not esperadas: continue
        coincidencias = len(esperadas & cols_df_norm)
        score = coincidencias / len(esperadas)
        if score > mejor[1]: mejor = (nombre, score)
    for nombre, esperadas in ESTRUCTURAS_ALTERNAS_NORM.items():
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

def adaptar_ventas(df):
    """
    Si en Ventas no existe un campo esperado pero sí uno de sus alias
    (p. ej. 'Valor facturado' -> 'Valor Total'), crea el campo esperado como copia del alias.
    No elimina ni renombra columnas originales; los campos esperados NO cambian.
    Devuelve (df_adaptado, lista_de_notas).
    """
    df = df.copy()
    notas = []
    for canonico, alias_lista in ALIAS_COLUMNAS_VENTAS.items():
        if obtener_columna(df, canonico) is not None:
            continue
        for alias in alias_lista:
            col_alias = obtener_columna(df, alias)
            if col_alias is not None:
                df[canonico] = df[col_alias]
                notas.append((canonico, str(col_alias)))
                break
    return df, notas

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
                    # Guardar SIEMPRE como string limpio (sin np.nan, sin None)
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
    Elimina espacios duros (\\xa0), BOM, %, $, etc.
    Devuelve None si no se puede parsear.
    """
    if v is None:
        return None
    # Caso nativo numérico
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
    # Eliminar paréntesis de errores
    s = re.sub(r"\(.*?\)", "", s).strip()
    # Eliminar TODO lo que no sea dígito, coma, punto o signo menos
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in ("-", ".", ","):
        return None

    tiene_coma = "," in s
    tiene_punto = "." in s

    if tiene_coma and tiene_punto:
        if s.rfind(",") > s.rfind("."):
            # CO: 1.234.567,89
            s = s.replace(".", "").replace(",", ".")
        else:
            # US: 1,234,567.89
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

# Mapa de etiqueta normalizada (histórico) -> métrica interna
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
    # Diagnóstico: cuántos valores válidos se parsearon por hoja y por sede
    diagnostico_historicos = []
    # Diagnóstico: columnas alternas utilizadas en Ventas
    ventas_columnas_alternas = []

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
                parsed = parsear_hoja_resultados(df, hoja)
                historicos_detectados[etiqueta] = parsed
                # Diagnóstico: contar cuántos conceptos y sedes se detectaron
                sedes_detectadas = set()
                valores_no_vacios = 0
                for k, vals in parsed.items():
                    for sede_k, val_k in vals.items():
                        if val_k and str(val_k).strip():
                            sedes_detectadas.add(sede_k)
                            valores_no_vacios += 1
                diagnostico_historicos.append({
                    "Hoja": hoja,
                    "Etiqueta periodo": etiqueta,
                    "Conceptos detectados": len(parsed),
                    "Sedes con datos": ", ".join(sorted(sedes_detectadas)) if sedes_detectadas else "(ninguna)",
                    "Valores no vacíos": valores_no_vacios,
                })
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

            # Ventas: si faltan campos esperados, usar alias (p. ej. 'Valor facturado' <- 'Valor Total')
            if estructura == "Ventas":
                df_con_header, notas_alias = adaptar_ventas(df_con_header)
                for canonico, alias_usado in notas_alias:
                    ventas_columnas_alternas.append({
                        "Archivo": f_name, "Hoja": hoja,
                        "Campo esperado": canonico, "Campo usado": alias_usado,
                    })

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

    # -------- CRUCE VENTAS (código de producto + valor) --------
    # El "Valor facturado" de Ventas se registra UNA sola vez por (No. venta, código producto).
    ventas_valor_por_codigo = {}
    ventas_df_global = pd.DataFrame()
    if bases["Ventas"]:
        ventas_df_global = pd.concat([df for _, _, df in bases["Ventas"]], ignore_index=True)
        col_v_venta_no = obtener_columna(ventas_df_global, "Venta No.")
        col_v_codigo = obtener_columna(ventas_df_global, "Código Producto")
        if col_v_codigo is None:
            col_v_codigo = obtener_columna(ventas_df_global, "Codigo Producto")
        col_v_valor_fact = obtener_columna(ventas_df_global, "Valor facturado")

        if col_v_venta_no is not None and col_v_codigo is not None and col_v_valor_fact is not None:
            df_vv = pd.DataFrame({
                "vno": ventas_df_global[col_v_venta_no].map(normalizar_llave_venta).values,
                "cod": ventas_df_global[col_v_codigo].astype(str).str.strip().str.extract(r"(\d{6})", expand=False).fillna("").values,
                "val": convertir_a_numero(ventas_df_global[col_v_valor_fact]).values,
            })
            df_vv = df_vv[(df_vv["vno"] != "") & (df_vv["cod"] != "")]
            # Filas idénticas (misma venta, código y valor) se cuentan una sola vez
            df_vv = df_vv.drop_duplicates(subset=["vno", "cod", "val"])
            ventas_valor_por_codigo = df_vv.groupby(["vno", "cod"])["val"].sum().to_dict()

    registros_errores_tarifas = []

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
            ubicacion_norm_serie = atenciones_df[col_ubicacion].astype(str).map(normalizar)
            
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

            # --- Cruce con Ventas: si la tarifa liquidada difiere del 'Valor facturado' de Ventas,
            # se usa el valor de Ventas (una sola vez por venta + código de producto) ---
            col_at_venta = obtener_columna(atenciones_df, "Numero Venta")
            col_at_codigo = obtener_columna(atenciones_df, "Codigo de producto")
            col_at_prod = obtener_columna(atenciones_df, "Nombre del producto Venta")
            col_at_esp = obtener_columna(atenciones_df, "Especialista Médico")
            valor_ajustado = valor_liquidado_num.copy()
            difiere = pd.Series(False, index=atenciones_df.index)
            primera = pd.Series(False, index=atenciones_df.index)
            valor_ventas_serie = pd.Series(float("nan"), index=atenciones_df.index)
            at_vno = at_cod = None
            if col_at_venta is not None and col_at_codigo is not None and ventas_valor_por_codigo:
                at_vno = atenciones_df[col_at_venta].map(normalizar_llave_venta)
                at_cod = atenciones_df[col_at_codigo].map(extraer_codigo_producto)
                valor_ventas_serie = pd.Series(
                    [ventas_valor_por_codigo.get((v, c)) for v, c in zip(at_vno, at_cod)],
                    index=atenciones_df.index, dtype="float64"
                )
                tiene_ventas = valor_ventas_serie.notna() & (valor_ventas_serie > 0)
                difiere = tiene_ventas & ((valor_ventas_serie - valor_liquidado_num).abs() > 0.01)
                elegible = difiere & mask_verifica & mask_valor_mayor_1000 & sede_serie.notna()
                clave_str = at_vno + "|" + at_cod
                primera = elegible & ~clave_str.where(elegible).duplicated()
                valor_ajustado[difiere] = 0.0
                valor_ajustado[primera] = valor_ventas_serie[primera]

            for fase in FASES:
                for cod in CODIGOS_SEDE:
                    mask_sede_fase = (sede_serie == cod) & (fase_serie == fase)
                    mask_rev_total = mask_sede_fase & mask_verifica
                    mask_rev = mask_rev_total & mask_valor_mayor_1000
                    mask_ava_total = mask_rev_total & mask_submedico
                    mask_ava = mask_ava_total & mask_valor_mayor_1000

                    conteos[fase][cod]["revisadas"] = int(mask_rev.sum())
                    conteos[fase][cod]["avaladas"] = int(mask_ava.sum())

                    mask_rev_error = mask_rev_total & ~mask_valor_mayor_1000
                    if mask_rev_error.any():
                        errores_revisadas[fase][cod]["cantidad"] = int(mask_rev_error.sum())
                        errores_revisadas[fase][cod]["suma"] = float(valor_liquidado_num[mask_rev_error].sum())

                    mask_ava_error = mask_ava_total & ~mask_valor_mayor_1000
                    if mask_ava_error.any():
                        errores_avaladas[fase][cod]["cantidad"] = int(mask_ava_error.sum())
                        errores_avaladas[fase][cod]["suma"] = float(valor_liquidado_num[mask_ava_error].sum())

                    mask_dinero_base = mask_sede_fase & mask_verifica
                    mask_dinero_val = mask_dinero_base & mask_valor_mayor_1000
                    mask_dinero_err = mask_dinero_base & ~mask_valor_mayor_1000

                    if mask_dinero_val.any():
                        dinero_interfaz[fase][cod] = float(valor_ajustado[mask_dinero_val].sum())
                        for idx_at in atenciones_df.index[mask_dinero_val & primera]:
                            registros_errores_tarifas.append({
                                "Fuente": "Atenciones",
                                "Sede": cod,
                                "Fase": fase,
                                "Categoría de error": "tarifa diferente (Atenciones)",
                                "No. de venta": atenciones_df.loc[idx_at, col_at_venta],
                                "Código producto": at_cod.loc[idx_at],
                                "Producto": atenciones_df.loc[idx_at, col_at_prod] if col_at_prod is not None else "",
                                "Profesional": atenciones_df.loc[idx_at, col_at_esp] if col_at_esp is not None else "",
                                "Valor liquidado (Atenciones)": float(valor_liquidado_num.loc[idx_at]),
                                "Valor facturado en Ventas": float(valor_ventas_serie.loc[idx_at]),
                                "Diferencia": float(valor_ventas_serie.loc[idx_at] - valor_liquidado_num.loc[idx_at]),
                            })
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
        col_totales_producto = obtener_columna(totales_df, "producto")
        col_totales_profesional = obtener_columna(totales_df, "profesional")

        if col_totales_venta_no is not None and col_totales_centro_costo is not None:
            totales_df["_venta_no_norm"] = totales_df[col_totales_venta_no].map(normalizar_llave_venta)
            totales_df["_codigo_prod"] = (
                totales_df[col_totales_producto].map(extraer_codigo_producto)
                if col_totales_producto is not None
                else ""
            )
            
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

            # Claves (venta, código) cuyo valor de Ventas ya fue sumado (evita multiplicar por profesional)
            claves_dinero_contadas = set()

            for fase in FASES:
                for cod in CODIGOS_SEDE:
                    mask_sede_fase = (totales_df["_sede"] == cod) & (totales_df["_fase"] == fase)
                    mask_base = mask_sede_fase & mask_venta_en_ventas
                    if mask_base.any():
                        tarifas_filtro = totales_tarifa_num[mask_base]
                        indices = tarifas_filtro.index
                        mask_valida = totales_tarifa_num.loc[indices] >= 1000
                        mask_error = ~mask_valida

                        for idx in indices[mask_valida]:
                            valor_totales = float(totales_tarifa_num.loc[idx])
                            vno = totales_df.loc[idx, "_venta_no_norm"]
                            cod_prod = totales_df.loc[idx, "_codigo_prod"]
                            clave = (vno, cod_prod)
                            valor_ventas = ventas_valor_por_codigo.get(clave)

                            total_ventas_ce[fase][cod] += 1

                            if valor_ventas is not None and valor_ventas > 0:
                                # Valor facturado de Ventas: se suma UNA sola vez por (venta, código)
                                if clave not in claves_dinero_contadas:
                                    claves_dinero_contadas.add(clave)
                                    dinero_ambulatorio[fase][cod] += valor_ventas
                                if abs(valor_ventas - valor_totales) > 0.01:
                                    registros_errores_tarifas.append({
                                        "Sede": cod,
                                        "Fase": fase,
                                        "Fuente": "Totales",
                                        "Categoría de error": "tarifa diferente",
                                        "No. de venta": totales_df.loc[idx, col_totales_venta_no],
                                        "Código producto": cod_prod,
                                        "Producto": totales_df.loc[idx, col_totales_producto] if col_totales_producto is not None else "",
                                        "Profesional": totales_df.loc[idx, col_totales_profesional] if col_totales_profesional is not None else "",
                                        "Tarifa Totales (reliquidado)": valor_totales,
                                        "Valor facturado en Ventas": valor_ventas,
                                        "Diferencia": valor_ventas - valor_totales,
                                    })
                            else:
                                # Sin coincidencia en Ventas: respaldo con la tarifa de Totales
                                dinero_ambulatorio[fase][cod] += valor_totales

                        if mask_error.any():
                            idxs_err = indices[mask_error]
                            errores_totales[fase][cod]["cantidad"] = len(idxs_err)
                            errores_totales[fase][cod]["suma"] = float(totales_tarifa_num.loc[idxs_err].sum())
                            for idx in idxs_err:
                                cod_prod = totales_df.loc[idx, "_codigo_prod"]
                                vno = totales_df.loc[idx, "_venta_no_norm"]
                                registros_errores_tarifas.append({
                                    "Sede": cod,
                                    "Fase": fase,
                                    "Fuente": "Totales",
                                    "Categoría de error": "tarifas no aplican",
                                    "No. de venta": totales_df.loc[idx, col_totales_venta_no],
                                    "Código producto": cod_prod,
                                    "Producto": totales_df.loc[idx, col_totales_producto] if col_totales_producto is not None else "",
                                    "Profesional": totales_df.loc[idx, col_totales_profesional] if col_totales_profesional is not None else "",
                                    "Tarifa Totales (reliquidado)": float(totales_tarifa_num.loc[idx]),
                                    "Valor facturado en Ventas": ventas_valor_por_codigo.get((vno, cod_prod)),
                                    "Diferencia": None,
                                })

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
        ventas_df = ventas_df_global if not ventas_df_global.empty else pd.concat([df for _, _, df in bases["Ventas"]], ignore_index=True)
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

            # Evitar duplicados de filas en Ventas (misma venta, código, estado y valor)
            col_ventas_codigo = obtener_columna(ventas_df, "Código Producto") or obtener_columna(ventas_df, "Codigo Producto")
            if col_ventas_venta_no is not None and col_ventas_codigo is not None:
                llave_dup = pd.DataFrame({
                    "v": ventas_df[col_ventas_venta_no].map(normalizar_llave_venta),
                    "c": ventas_df[col_ventas_codigo].astype(str).str.extract(r"(\d{6})", expand=False).fillna(""),
                    "e": mask_estado_facturada,
                    "x": valor_facturado_num,
                })
                mask_no_duplicada = ~llave_dup.duplicated()
            else:
                mask_no_duplicada = pd.Series(True, index=ventas_df.index)

            for fase in FASES:
                for cod in CODIGOS_SEDE:
                    mask_sede_fase = (ventas_df["_sede"] == cod) & (ventas_df["_fase"] == fase)
                    mask_base = mask_sede_fase & mask_estado_facturada & mask_venta_en_totales & mask_no_duplicada
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
            tabla.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante[fase][cod]:,.2f}%".replace(".", ",")
            tabla.loc["Ventas relacionadas en factura (FACTURADO)", columna] = formatear_conteo_con_error(ventas_relacionadas_factura[fase][cod], errores_ventas[fase][cod]["cantidad"], errores_ventas[fase][cod]["suma"], porcentaje_errores_ventas[fase][cod])
            tabla.loc["Dinero ventas (Facturado)", columna] = formatear_dinero_con_error(dinero_ventas_facturado[fase][cod], errores_ventas[fase][cod]["cantidad"], errores_ventas[fase][cod]["suma"], porcentaje_errores_ventas[fase][cod])
            tabla.loc["Porcentual impactado (META 0%)", columna] = f"{porcentual_impactado[fase][cod]:,.2f}%".replace(".", ",")
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
        tabla_consolidada.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante_consolidado[cod]:,.2f}%".replace(".", ",")
        tabla_consolidada.loc["Ventas relacionadas en factura (FACTURADO)", columna] = formatear_conteo_con_error(ventas_relacionadas_factura_consolidado[cod], errores_ventas_consolidado[cod]["cantidad"], errores_ventas_consolidado[cod]["suma"], porcentaje_errores_ventas_consolidado[cod])
        tabla_consolidada.loc["Dinero ventas (Facturado)", columna] = formatear_dinero_con_error(dinero_ventas_facturado_consolidado[cod], errores_ventas_consolidado[cod]["cantidad"], errores_ventas_consolidado[cod]["suma"], porcentaje_errores_ventas_consolidado[cod])
        tabla_consolidada.loc["Porcentual impactado (META 0%)", columna] = f"{porcentual_impactado_consolidado[cod]:,.2f}%".replace(".", ",")

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
    # Los valores que se grafican SON los de la tabla CONSOLIDADO (no se suman las tablas de cada fase).
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

    # Históricos: se toma ÚNICAMENTE la sección "Consolidado" de cada hoja para los totales.
    # Las secciones de fase solo se usan para el desglose por fase (gráfico de participación)
    # y como respaldo si la hoja no trae sección Consolidado.
    for etiqueta_periodo, conceptos in historicos_detectados.items():
        data_periodo = {}
        for sede in COLUMNAS_RESUMEN:
            consolidado_vals = {m: None for m in MAPA_METRICAS_HIST.values()}
            suma_fases = {m: 0.0 for m in MAPA_METRICAS_HIST.values()}
            dinero_por_fase = {"Fase 1": 0.0, "Fase 2": 0.0, "Fase 3": 0.0}

            for concepto, valores in conceptos.items():
                valor = valores.get(sede)
                if valor is None:
                    continue
                num = parsear_valor_generico(valor)
                if num is None:
                    continue

                partes = concepto.split(" - ", 1)
                prefijo = limpiar_texto(partes[0])
                concepto_sin_prefijo = partes[1] if len(partes) > 1 else concepto
                metrica = MAPA_METRICAS_HIST.get(normalizar_etiqueta_hist(concepto_sin_prefijo))
                if metrica is None:
                    continue

                if prefijo == "Consolidado":
                    consolidado_vals[metrica] = (consolidado_vals[metrica] or 0.0) + num
                elif prefijo in FASES:
                    suma_fases[metrica] += num
                    if metrica == "dinero_interfaz":
                        dinero_por_fase[prefijo] += num

            def _final(m):
                return consolidado_vals[m] if consolidado_vals[m] is not None else suma_fases[m]

            data_periodo[sede] = {
                "revisadas": _final("revisadas"),
                "avaladas": _final("avaladas"),
                "total_ventas": _final("total_ventas"),
                "dinero_interfaz": _final("dinero_interfaz"),
                "dinero_ventas": _final("dinero_ventas"),
                "ventas_relacionadas": _final("ventas_relacionadas"),
                "dinero_facturado": _final("dinero_facturado"),
                "dinero_interfaz_fase_1": dinero_por_fase["Fase 1"],
                "dinero_interfaz_fase_2": dinero_por_fase["Fase 2"],
                "dinero_interfaz_fase_3": dinero_por_fase["Fase 3"],
            }
        consolidados_por_periodo[etiqueta_periodo] = data_periodo

    df_errores_tarifas = pd.DataFrame(registros_errores_tarifas)

    return {
        "tablas_por_fase": tablas_por_fase, "tabla_consolidada": tabla_consolidada, "resumen_verifica": resumen_verifica,
        "historicos_detectados": historicos_detectados, "consolidados_por_periodo": consolidados_por_periodo,
        "periodo_etiqueta": periodo_etiqueta, "periodo_inicio": str(periodo_inicio) if periodo_inicio else "—",
        "periodo_fin": str(periodo_fin) if periodo_fin else "—", "no_clasificados": no_clasificados, "errores": errores,
        "archivos_duplicados": archivos_duplicados, "hojas_duplicadas": hojas_duplicadas,
        "ubicaciones_no_mapeadas": ubicaciones_no_mapeadas, "ubicaciones_totales_no_mapeadas": ubicaciones_totales_no_mapeadas,
        "ubicaciones_ventas_no_mapeadas": ubicaciones_ventas_no_mapeadas, "estados_no_incluidos": estados_no_incluidos,
        "totales_sin_match_atenciones_df": totales_sin_match_atenciones_df,
        "df_errores_tarifas": df_errores_tarifas,
        "diagnostico_historicos": pd.DataFrame(diagnostico_historicos),
        "ventas_columnas_alternas": pd.DataFrame(ventas_columnas_alternas),
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
# GRÁFICAS — Streamlit
# ============================================================

@st.cache_data(show_spinner=False)
def generar_grafica_dinero(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            datos.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
    df = pd.DataFrame(datos)
    if df.empty or df["Valor"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(12, 7))
    sns.barplot(data=df, x="Periodo", y="Valor", hue="Sede", ax=ax) 
    def _fmt_corto(v):
        if v <= 0: return ""
        if v >= 1_000_000: return f"${v/1_000_000:,.1f}M".replace(".", ",")
        elif v >= 1_000: return f"${v/1_000:,.0f}K".replace(",", ".")
        return f"${v:,.0f}".replace(",", ".")
    for container in ax.containers:
        ax.bar_label(container, labels=[_fmt_corto(v) for v in container.datavalues], fontsize=8, rotation=90, padding=3, label_type="edge", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}".replace(",", ".")))
    ax.set_ylim(0, df["Valor"].max() * 1.25)
    ax.set_title("Dinero enviado por interfaz por periodo y sede (Consolidado)", pad=15)
    ax.set_ylabel("Valor (COP)"); ax.set_xlabel("Periodo")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout(); plt.subplots_adjust(right=0.80)
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=110); plt.close(fig)
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def generar_grafica_cobertura(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            avaladas = vals["avaladas"]; total_ventas = vals["total_ventas"]
            cobertura = (avaladas / total_ventas * 100.0) if total_ventas > 0 else 0.0
            datos.append({"Periodo": periodo, "Sede": sede, "Cobertura": cobertura})
    df = pd.DataFrame(datos)
    if df.empty or df["Cobertura"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(12, 7))
    sns.barplot(data=df, x="Periodo", y="Cobertura", hue="Sede", ax=ax) 
    for container in ax.containers:
        ax.bar_label(container, labels=[f"{v:.1f}%".replace(".", ",") if v > 0 else "" for v in container.datavalues], fontsize=8, rotation=90, padding=3, label_type="edge", fontweight="bold")
    ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
    ax.set_ylim(0, max(df["Cobertura"].max() * 1.25, 120)) 
    ax.set_title("Cobertura general de honorarios médicos (Avaladas / Total ventas)", pad=15)
    ax.set_ylabel("Cobertura (%)"); ax.set_xlabel("Periodo")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout(); plt.subplots_adjust(right=0.80)
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=110); plt.close(fig)
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def generar_grafica_participacion_fase_general(_consolidados_por_periodo, firma):
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

    periodos = list(df["Periodo"].unique())
    orden = _ordenar_llaves_cronologicamente({p: {} for p in periodos})
    df["Periodo"] = pd.Categorical(df["Periodo"], categories=list(orden.keys()), ordered=True)

    cols_fases = ["Fase 1 - Ambulatorio", "Fase 2 - Hospitalario", "Fase 3 - Quirúrgico"]
    df = df.set_index(["Periodo", "Sede"])
    totales = df[cols_fases].sum(axis=1)
    df_pct = df[cols_fases].div(totales.replace(0, pd.NA), axis=0).fillna(0) * 100
    df_pct = df_pct.reset_index()
    df_pct["Etiqueta"] = df_pct["Periodo"].astype(str) + " — " + df_pct["Sede"]
    df_pct = df_pct.sort_values(["Periodo", "Sede"]).set_index("Etiqueta")[cols_fases]

    fig, ax = plt.subplots(figsize=(18, max(8, len(df_pct) * 0.32)))
    df_pct.plot(kind="barh", stacked=True, ax=ax,
                color=["#305496", "#D1615D", "#85C17E"], width=0.8)
    for container in ax.containers:
        vals = [v.get_width() for v in container]
        labels = [f"{v:.1f}%".replace(".", ",") if v >= 5 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=7.5, color="white", weight="bold")
    ax.set_title("Participación por fase — Vista general (todas las sedes)", pad=15)
    ax.set_xlabel("Participación (%)")
    ax.set_xlim(0, 100)
    ax.legend(title="Fase", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    plt.tight_layout(); plt.subplots_adjust(right=0.85)

    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=120); plt.close(fig)
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def generar_grafica_participacion_fase_sede_individual(_consolidados_por_periodo, sede_sel, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        vals = data_sedes.get(sede_sel)
        if vals is None: continue
        datos.append({
            "Periodo": periodo,
            "Fase 1 - Ambulatorio": vals.get("dinero_interfaz_fase_1", 0),
            "Fase 2 - Hospitalario": vals.get("dinero_interfaz_fase_2", 0),
            "Fase 3 - Quirúrgico": vals.get("dinero_interfaz_fase_3", 0),
        })
    df = pd.DataFrame(datos)
    if df.empty: return None

    orden = _ordenar_llaves_cronologicamente({p: {} for p in df["Periodo"].unique()})
    df["Periodo"] = pd.Categorical(df["Periodo"], categories=list(orden.keys()), ordered=True)
    df = df.sort_values("Periodo").reset_index(drop=True)

    cols_fases = ["Fase 1 - Ambulatorio", "Fase 2 - Hospitalario", "Fase 3 - Quirúrgico"]
    totales = df[cols_fases].sum(axis=1)
    df_pct = df[cols_fases].div(totales.replace(0, pd.NA), axis=0).fillna(0) * 100
    df_pct.index = [_etiqueta_periodo_corta(p) for p in df["Periodo"]]

    fig, ax = plt.subplots(figsize=(max(12, len(df_pct) * 0.9), 6.5))
    df_pct.plot(kind="bar", stacked=True, ax=ax,
                color=["#305496", "#D1615D", "#85C17E"], width=0.7)
    for container in ax.containers:
        vals = [v.get_height() for v in container]
        labels = [f"{v:.1f}%".replace(".", ",") if v >= 4 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=9, color="white", weight="bold")
    ax.set_title(f"Participación por fase — {sede_sel}", pad=15, fontsize=13, fontweight="bold")
    ax.set_ylabel("Participación (%)")
    ax.set_xlabel("Periodo")
    ax.set_ylim(0, 105)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.legend(title="Fase", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout(); plt.subplots_adjust(right=0.82)

    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=120); plt.close(fig)
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def generar_grafica_dinero_total(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        total_periodo = sum(vals["dinero_interfaz"] for vals in data_sedes.values())
        datos.append({"Periodo": periodo, "Valor": total_periodo})
    df = pd.DataFrame(datos)
    if df.empty or df["Valor"].sum() == 0: return None
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x="Periodo", y="Valor", ax=ax, color="#305496") 
    def _fmt_corto(v):
        if v <= 0: return ""
        if v >= 1_000_000: return f"${v/1_000_000:,.1f}M".replace(".", ",")
        elif v >= 1_000: return f"${v/1_000:,.0f}K".replace(",", ".")
        return f"${v:,.0f}".replace(",", ".")
    for container in ax.containers:
        ax.bar_label(container, labels=[_fmt_corto(v) for v in container.datavalues], fontsize=9, rotation=90, padding=3, label_type="edge", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}".replace(",", ".")))
    ax.set_ylim(0, df["Valor"].max() * 1.25)
    ax.set_title("Dinero enviado por interfaz por periodo (Todas las sedes consolidadas)", pad=15)
    ax.set_ylabel("Valor (COP)"); ax.set_xlabel("Periodo")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout(); plt.subplots_adjust(right=0.90)
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=110); plt.close(fig)
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
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x="Periodo", y="Cobertura", ax=ax, color="#305496") 
    for container in ax.containers:
        ax.bar_label(container, labels=[f"{v:.1f}%".replace(".", ",") if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=90, padding=3, label_type="edge", fontweight="bold")
    ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
    ax.set_ylim(0, max(df["Cobertura"].max() * 1.25, 120))
    ax.set_title("Cobertura general de honorarios médicos por periodo (Todas las sedes consolidadas)", pad=15)
    ax.set_ylabel("Cobertura (%)"); ax.set_xlabel("Periodo")
    plt.xticks(rotation=45, ha="right")
    ax.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout(); plt.subplots_adjust(right=0.90)
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=110); plt.close(fig)
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
    periodos_unicos = list(df.index)
    ordenados_dict = _ordenar_llaves_cronologicamente({p: {} for p in periodos_unicos})
    df = df.reindex(list(ordenados_dict.keys()))
    total_por_fila = df.sum(axis=1)
    df_pct = df.div(total_por_fila.replace(0, pd.NA), axis=0).fillna(0) * 100
    fig, ax = plt.subplots(figsize=(10, 6))
    df_pct.plot(kind="bar", stacked=True, ax=ax, color=["#305496", "#D1615D", "#85C17E"], width=0.6) 
    for container in ax.containers:
        vals = [v.get_height() for v in container]
        labels = [f"{v:.1f}%".replace(".", ",") if v > 3 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=9, color="white", weight="bold")
    ax.set_title("Participación por fase — Todas las sedes consolidadas", pad=15)
    ax.set_ylabel("Participación (%)"); ax.set_xlabel("Periodo")
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.legend(title="Fase", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.ylim(0, 105)
    plt.tight_layout(); plt.subplots_adjust(right=0.80)
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=110); plt.close(fig)
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def generar_grafica_participacion_sede_total(_consolidados_por_periodo, firma):
    datos = []
    for periodo, data_sedes in _consolidados_por_periodo.items():
        for sede, vals in data_sedes.items():
            datos.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
    df = pd.DataFrame(datos)
    if df.empty: return None
    periodos_unicos = list(df["Periodo"].unique())
    ordenados_dict = _ordenar_llaves_cronologicamente({p: {} for p in periodos_unicos})
    df["Periodo"] = pd.Categorical(df["Periodo"], categories=list(ordenados_dict.keys()), ordered=True)
    df["Total_Periodo"] = df.groupby("Periodo")["Valor"].transform("sum")
    df["Porcentaje"] = df.apply(lambda r: (r["Valor"] / r["Total_Periodo"] * 100) if r["Total_Periodo"] > 0 else 0, axis=1)
    df_melt = df.pivot_table(index="Periodo", columns="Sede", values="Porcentaje", fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 6))
    df_melt.plot(kind="bar", stacked=True, ax=ax, width=0.6, colormap="tab10") 
    for container in ax.containers:
        vals = [v.get_height() for v in container]
        labels = [f"{v:.1f}%".replace(".", ",") if v > 3 else "" for v in vals]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=8, color="white", weight="bold")
    ax.set_title("Participación de cada sede en el total general por periodo", pad=15)
    ax.set_ylabel("Participación (%)"); ax.set_xlabel("Periodo")
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.ylim(0, 105)
    plt.tight_layout(); plt.subplots_adjust(right=0.80)
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=110); plt.close(fig)
    return buf.getvalue()

# ============================================================
# EXCEL
# ============================================================
@st.cache_data(show_spinner="Generando Excel de resultados...")
def generar_excel_bytes(resultados, periodo_etiqueta, periodo_inicio, periodo_fin):
    tablas_por_fase = resultados["tablas_por_fase"]
    tabla_consolidada = resultados["tabla_consolidada"]
    resumen_verifica = resultados["resumen_verifica"]
    totales_sin_match_atenciones_df = resultados["totales_sin_match_atenciones_df"]
    consolidados_por_periodo = resultados["consolidados_por_periodo"]
    df_errores_tarifas = resultados.get("df_errores_tarifas", pd.DataFrame())

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
            c.font = bold_white; c.fill = header_fill
            c.alignment = Alignment(horizontal="center", wrap_text=True)
        fila += 1
        for idx, row in tabla_df.iterrows():
            ws.cell(row=fila, column=1, value=str(idx)).font = Font(bold=True)
            for j, col in enumerate(tabla_df.columns, start=2):
                ws.cell(row=fila, column=j, value=row[col])
            fila += 1
        return fila + 2

    ws1 = wb.active
    ws1.title = "Fases"
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
            c.font = bold_white; c.fill = header_fill
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
            c.font = bold_white; c.fill = header_fill
        for i, (_, row) in enumerate(resumen_verifica.iterrows(), start=2):
            for j, col in enumerate(resumen_verifica.columns, start=1):
                ws3.cell(row=i, column=j, value=row[col])
        ws3.column_dimensions["A"].width = 40
        ws3.column_dimensions["B"].width = 15
        ws3.column_dimensions["C"].width = 30

    ws_err = wb.create_sheet("Errores de tarifas")
    if df_errores_tarifas is None or df_errores_tarifas.empty:
        ws_err.cell(row=1, column=1, value="No hay errores de tarifas registrados.")
    else:
        for j, col in enumerate(df_errores_tarifas.columns, start=1):
            c = ws_err.cell(row=1, column=j, value=col)
            c.font = bold_white; c.fill = header_fill
        for i, (_, row) in enumerate(df_errores_tarifas.iterrows(), start=2):
            for j, col in enumerate(df_errores_tarifas.columns, start=1):
                ws_err.cell(row=i, column=j, value=row[col])
        for j in range(1, len(df_errores_tarifas.columns) + 1):
            ws_err.column_dimensions[get_column_letter(j)].width = 25

    ws4 = wb.create_sheet("Reglas")
    reglas = [
        ("Carga de archivos", ""), ("", "Se aceptan múltiples Excel (.xlsx, .xls)."),
        ("", "Cada hoja se clasifica: Ventas, Atenciones del especialista, Totales o Histórico."),
        ("", "Hojas/archivos duplicados se descartan por hash."),
        ("", "Ventas acepta un formato alterno: si falta 'Valor facturado' se usa 'Valor Total' (también 'No. de venta', 'Cod Producto venta' y 'Estado de la venta' como respaldo)."),
        ("Periodo", ""), ("", "Se extrae del nombre del archivo (YYYY-MM, MM-YYYY, nombre de mes + año)."),
        ("Filtros previos", ""), ("", "En Totales: 'Total tarifas y recargos/descuentos' >= 1000."),
        ("Mapeo de (sede, fase)", ""), ("", "Match flexible contra el mapa Sede + Ubicación → Fase."),
        ("Cálculos por (sede, fase)", ""),
        ("1. Revisadas por analistas", "Ubicación mapea + 'Nombre de Usuario que Verifica' NO vacío + 'Valor liquidado' > 1000."),
        ("2. Avaladas subgerencia médica", "Revisadas + 'Usuario / Sub Medico' NO vacío + 'Valor liquidado' > 1000."),
        ("3. Dinero enviado por interfaz", "Σ 'Valor liquidado' válido (> 1000). Si la tarifa difiere del 'Valor facturado' de Ventas (cruce por No. venta + código de producto), se suma el valor de Ventas UNA sola vez por (venta, código). Errores reportados aparte."),
        ("4. Total ventas", "count(Totales ∩ Ventas con 'tarifas' >= 1000). Errores reportados aparte."),
        ("5. Dinero ventas", "Se toma el 'Valor facturado' de Ventas (o 'Valor Total' en el formato alterno), sumado UNA sola vez por (No. venta, primeros 6 dígitos de 'producto' en Totales = 'Código Producto' de Ventas). Si no hay coincidencia en Ventas se usa la 'tarifas (reliquidado)' de Totales. Si el valor de Ventas difiere de Totales se marca 'tarifa diferente'."),
        ("6. Porcentual faltante (META 30%)", "(Total ventas − Avaladas) / Total ventas × 100."),
        ("7. Ventas relacionadas en factura", "count(Ventas con Estado=Facturada, 'Valor facturado' >= 1000 y 'Venta No.' ∈ Totales). Filas duplicadas de Ventas se cuentan una sola vez."),
        ("8. Dinero ventas (Facturado)", "Σ 'Valor facturado' válido (>= 1000) con Estado=Facturada y 'Venta No.' ∈ Totales, sin duplicados."),
        ("9. Porcentual impactado (META 0%)", "(Total ventas − Ventas relacionadas) / Total ventas × 100."),
        ("Consolidado", "Suma de las 3 fases. Porcentajes recalculados."),
        ("Gráficas / Históricos", "Las gráficas usan los valores de la tabla CONSOLIDADO de cada periodo (en históricos se lee la sección 'CONSOLIDADO - TODAS LAS FASES'); las fases solo se usan para el desglose de participación por fase."),
        ("Agrupación", "Las gráficas permiten agrupar por Mes, Bimestre, Trimestre, Semestre o Año."),
        ("Errores de tarifas", "Base única con todos los registros clasificados como 'tarifa diferente' o 'tarifas no aplican'."),
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
            xl_img.width = ancho; xl_img.height = alto
            ws.add_image(xl_img, f"A{fila}")
            return fila + int(alto / 20) + 3

        datos_g1 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            for sede, vals in data_sedes.items():
                datos_g1.append({"Periodo": periodo, "Sede": sede, "Valor": vals["dinero_interfaz"]})
        df_g1 = pd.DataFrame(datos_g1)

        if not df_g1.empty and df_g1["Valor"].sum() > 0:
            fig, ax = plt.subplots(figsize=(12, 7))
            sns.barplot(data=df_g1, x="Periodo", y="Valor", hue="Sede", ax=ax) 
            for container in ax.containers:
                ax.bar_label(container, labels=[f"${v/1e6:,.1f}M".replace(".", ",") if v > 0 else "" for v in container.datavalues], fontsize=8, rotation=90, padding=3, label_type="edge", fontweight="bold")
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}".replace(",", ".")))
            ax.set_ylim(0, df_g1["Valor"].max() * 1.25)
            ax.set_title("Dinero enviado por interfaz por periodo y sede (Consolidado)", pad=15)
            ax.set_ylabel("Valor (COP)"); ax.set_xlabel("Periodo")
            plt.xticks(rotation=45, ha="right")
            plt.legend(title="Sede", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
            plt.tight_layout(); plt.subplots_adjust(right=0.80)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, ancho=900, alto=420, titulo="Gráfico 1 — Dinero enviado por interfaz (COP)")
            plt.close(fig)

        datos_g2 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            for sede, vals in data_sedes.items():
                avaladas = vals["avaladas"]; total_ventas = vals["total_ventas"]
                cobertura = (avaladas / total_ventas * 100.0) if total_ventas > 0 else 0.0
                datos_g2.append({"Periodo": periodo, "Sede": sede, "Cobertura": cobertura})
        df_g2 = pd.DataFrame(datos_g2)

        if not df_g2.empty and df_g2["Cobertura"].sum() > 0:
            fig, ax = plt.subplots(figsize=(12, 7))
            sns.barplot(data=df_g2, x="Periodo", y="Cobertura", hue="Sede", ax=ax) 
            for container in ax.containers:
                ax.bar_label(container, labels=[f"{v:.1f}%".replace(".", ",") if v > 0 else "" for v in container.datavalues], fontsize=8, rotation=90, padding=3, label_type="edge", fontweight="bold")
            ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
            ax.set_ylim(0, max(df_g2["Cobertura"].max() * 1.25, 120))
            ax.set_title("Cobertura general de honorarios médicos (Avaladas / Total ventas)", pad=15)
            ax.set_ylabel("Cobertura (%)"); ax.set_xlabel("Periodo")
            plt.xticks(rotation=45, ha="right")
            plt.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
            plt.tight_layout(); plt.subplots_adjust(right=0.80)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, ancho=900, alto=420, titulo="Gráfico 2 — Cobertura general de honorarios médicos (meta 70%)")
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
            periodos3 = list(df_g3["Periodo"].unique())
            orden3 = _ordenar_llaves_cronologicamente({p: {} for p in periodos3})
            df_g3["Periodo"] = pd.Categorical(df_g3["Periodo"], categories=list(orden3.keys()), ordered=True)

            cols_fases3 = ["Fase 1 - Ambulatorio", "Fase 2 - Hospitalario", "Fase 3 - Quirúrgico"]
            df_g3 = df_g3.set_index(["Sede", "Periodo"])
            tot_g3 = df_g3[cols_fases3].sum(axis=1)
            df_g3_pct = df_g3[cols_fases3].div(tot_g3.replace(0, pd.NA), axis=0).fillna(0) * 100

            sedes3 = sorted(df_g3_pct.index.get_level_values("Sede").unique())
            n_sedes3 = len(sedes3)
            n_cols3 = 3
            n_filas3 = (n_sedes3 + n_cols3 - 1) // n_cols3
            fig, axes = plt.subplots(n_filas3, n_cols3, figsize=(16, 4.2 * n_filas3), sharey=True, squeeze=False)
            colores3 = ["#305496", "#D1615D", "#85C17E"]
            etiquetas_fase3 = ["Fase 1", "Fase 2", "Fase 3"]

            for i, sede in enumerate(sedes3):
                ax = axes[i // n_cols3][i % n_cols3]
                datos_sede = df_g3_pct.loc[sede].reindex(list(orden3.keys())).fillna(0)
                x = range(len(datos_sede.index))
                bottom = [0] * len(x)
                for j, col in enumerate(cols_fases3):
                    valores = datos_sede[col].values
                    ax.bar(x, valores, bottom=bottom, color=colores3[j], width=0.75,
                           label=etiquetas_fase3[j], edgecolor="white", linewidth=0.5)
                    for xi, v, b in zip(x, valores, bottom):
                        if v >= 6:
                            ax.text(xi, b + v / 2, f"{v:.0f}%", ha="center", va="center",
                                    fontsize=8.5, color="white", fontweight="bold")
                    bottom = [b + v for b, v in zip(bottom, valores)]
                ax.set_title(sede, fontsize=11, fontweight="bold")
                ax.set_ylim(0, 100)
                ax.set_xticks(list(x))
                etiquetas_periodo = [_etiqueta_periodo_corta(p) for p in datos_sede.index]
                ax.set_xticklabels(etiquetas_periodo, rotation=45, ha="right", fontsize=8)
                ax.grid(axis="y", alpha=0.3, linestyle="--")
                ax.spines[["top", "right"]].set_visible(False)
            for k in range(n_sedes3, n_filas3 * n_cols3):
                axes[k // n_cols3][k % n_cols3].set_visible(False)
            for i in range(n_filas3):
                axes[i][0].set_ylabel("Participación (%)", fontsize=9)
            handles, labels = axes[0][0].get_legend_handles_labels()
            fig.legend(handles, labels, loc="lower center", ncol=3, title="Fase", fontsize=10, bbox_to_anchor=(0.5, -0.02))
            fig.suptitle("Participación por fase — comparación entre sedes y periodos", fontsize=13, fontweight="bold", y=1.01)
            plt.tight_layout(rect=[0, 0.04, 1, 0.98])
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, ancho=950, alto=520, titulo="Gráfico 3 — Participación por fase (por sede)")
            plt.close(fig)

        datos_g4 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            total_periodo = sum(vals["dinero_interfaz"] for vals in data_sedes.values())
            datos_g4.append({"Periodo": periodo, "Valor": total_periodo})
        df_g4 = pd.DataFrame(datos_g4)
        if not df_g4.empty and df_g4["Valor"].sum() > 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=df_g4, x="Periodo", y="Valor", ax=ax, color="#305496") 
            for container in ax.containers:
                ax.bar_label(container, labels=[f"${v/1e6:,.1f}M".replace(".", ",") if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=90, padding=3, label_type="edge", fontweight="bold")
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}".replace(",", ".")))
            ax.set_ylim(0, df_g4["Valor"].max() * 1.25)
            ax.set_title("Dinero enviado por interfaz por periodo (Todas las sedes consolidadas)", pad=15)
            ax.set_ylabel("Valor (COP)"); ax.set_xlabel("Periodo")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout(); plt.subplots_adjust(right=0.90)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, ancho=900, alto=420, titulo="Gráfico 4 — Dinero total enviado por periodo")
            plt.close(fig)

        datos_g5 = []
        for periodo, data_sedes in consolidados_por_periodo.items():
            avaladas_total = sum(vals["avaladas"] for vals in data_sedes.values())
            total_ventas_total = sum(vals["total_ventas"] for vals in data_sedes.values())
            cobertura = (avaladas_total / total_ventas_total * 100.0) if total_ventas_total > 0 else 0.0
            datos_g5.append({"Periodo": periodo, "Cobertura": cobertura})
        df_g5 = pd.DataFrame(datos_g5)
        if not df_g5.empty and df_g5["Cobertura"].sum() > 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=df_g5, x="Periodo", y="Cobertura", ax=ax, color="#305496") 
            for container in ax.containers:
                ax.bar_label(container, labels=[f"{v:.1f}%".replace(".", ",") if v > 0 else "" for v in container.datavalues], fontsize=9, rotation=90, padding=3, label_type="edge", fontweight="bold")
            ax.axhline(70, color="red", linestyle="--", label="Meta 70%")
            ax.set_ylim(0, max(df_g5["Cobertura"].max() * 1.25, 120))
            ax.set_title("Cobertura general de honorarios médicos por periodo (Todas las sedes consolidadas)", pad=15)
            ax.set_ylabel("Cobertura (%)"); ax.set_xlabel("Periodo")
            plt.xticks(rotation=45, ha="right")
            ax.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
            plt.tight_layout(); plt.subplots_adjust(right=0.90)
            fila_actual = insertar_grafico(ws_analisis, fig, fila_actual, ancho=900, alto=420, titulo="Gráfico 5 — Cobertura total por periodo (meta 70%)")
            plt.close(fig)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ============================================================
# INTERFAZ STREAMLIT
# ============================================================
uploaded_files = st.file_uploader(
    "Carga los archivos Excel", type=["xlsx", "xls"], accept_multiple_files=True,
    help="Selecciona todos los archivos del periodo."
)

if uploaded_files:
    files_data = [(f.name, f.getvalue()) for f in uploaded_files]
    resultados = procesar_todo(files_data)

    st.subheader(f"Periodo detectado: {resultados['periodo_etiqueta']}")
    if resultados['periodo_etiqueta'] != "—":
        st.caption(f"Inicio: {resultados['periodo_inicio']} | Fin: {resultados['periodo_fin']}")

    tabs = st.tabs(["Fases", "Análisis histórico", "Errores de tarifas", "Novedades", "Diagnóstico"])

    with tabs[0]:
        st.markdown(f"### {TITULOS_FASES['Fase 1']}")
        st.dataframe(resultados["tablas_por_fase"]["Fase 1"], use_container_width=True)
        st.markdown(f"### {TITULOS_FASES['Fase 2']}")
        st.dataframe(resultados["tablas_por_fase"]["Fase 2"], use_container_width=True)
        st.markdown(f"### {TITULOS_FASES['Fase 3']}")
        st.dataframe(resultados["tablas_por_fase"]["Fase 3"], use_container_width=True)
        st.markdown("### CONSOLIDADO - TODAS LAS FASES")
        st.dataframe(resultados["tabla_consolidada"], use_container_width=True)

    with tabs[1]:
        st.markdown("### Análisis histórico comparativo entre periodos")
        st.caption("Los gráficos usan los valores de la tabla CONSOLIDADO de cada periodo.")
        consolidados = resultados["consolidados_por_periodo"]
        if not consolidados:
            st.info("No hay datos históricos suficientes para generar el análisis.")
        else:
            agrupacion = st.radio(
                "Agrupar por:",
                ["Mes", "Bimestre", "Trimestre", "Semestre", "Año"],
                horizontal=True, index=0, key="agrup_global"
            )
            consolidados_agrup = agrupar_consolidados(consolidados, agrupacion)
            firma = _firma_consolidados(consolidados_agrup)

            st.markdown("#### Gráfico 1 — Dinero enviado por interfaz por periodo y sede")
            img = generar_grafica_dinero(consolidados_agrup, firma)
            if img: st.image(img, use_column_width=True)

            st.markdown("#### Gráfico 2 — Cobertura general de honorarios médicos")
            img = generar_grafica_cobertura(consolidados_agrup, firma)
            if img: st.image(img, use_column_width=True)

            st.markdown("#### Gráfico 3 — Participación por fase (por sede y periodo)")
            opciones_sede = ["General"] + COLUMNAS_RESUMEN
            sede_sel = st.radio(
                "Ver:",
                opciones_sede,
                horizontal=True, index=0, key="sel_sede_grafico3",
            )
            if sede_sel == "General":
                firma_fase = "general_" + _firma_consolidados(consolidados)
                img = generar_grafica_participacion_fase_general(consolidados, firma_fase)
            else:
                firma_fase = f"sede_{sede_sel}_" + _firma_consolidados(consolidados)
                img = generar_grafica_participacion_fase_sede_individual(consolidados, sede_sel, firma_fase)
            if img:
                st.image(img, use_column_width=True)
            else:
                st.info("Sin datos suficientes para este gráfico.")

            st.markdown("#### Gráfico 4 — Dinero total enviado por periodo (todas las sedes)")
            img = generar_grafica_dinero_total(consolidados_agrup, firma)
            if img: st.image(img, use_column_width=True)

            st.markdown("#### Gráfico 5 — Cobertura total por periodo (todas las sedes)")
            img = generar_grafica_cobertura_total(consolidados_agrup, firma)
            if img: st.image(img, use_column_width=True)

            st.markdown("#### Gráfico 6 — Participación por fase — Todas las sedes consolidadas")
            img = generar_grafica_participacion_fase_total(consolidados_agrup, firma)
            if img: st.image(img, use_column_width=True)

            st.markdown("#### Gráfico 7 — Participación de cada sede en el total general por periodo")
            img = generar_grafica_participacion_sede_total(consolidados_agrup, firma)
            if img: st.image(img, use_column_width=True)

    with tabs[2]:
        st.markdown("### Base única de errores de tarifas")
        df_err = resultados.get("df_errores_tarifas", pd.DataFrame())
        if df_err.empty:
            st.info("No se detectaron errores de tarifas.")
        else:
            cat_sel = st.multiselect(
                "Filtrar por categoría de error:",
                options=sorted(df_err["Categoría de error"].dropna().unique().tolist()),
                default=sorted(df_err["Categoría de error"].dropna().unique().tolist()),
            )
            df_err_f = df_err[df_err["Categoría de error"].isin(cat_sel)] if cat_sel else df_err
            st.caption(f"Registros: {len(df_err_f)}")
            st.dataframe(df_err_f, use_container_width=True)
            csv = df_err_f.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar errores de tarifas (CSV)", csv, "errores_tarifas.csv", "text/csv")

    with tabs[3]:
        st.dataframe(resultados["resumen_verifica"], use_container_width=True)

    with tabs[4]:
        st.markdown("### Campos alternos usados en Ventas")
        alt_df = resultados.get("ventas_columnas_alternas", pd.DataFrame())
        if alt_df is None or alt_df.empty:
            st.info("Todos los archivos de Ventas trajeron los campos esperados (no se usaron alias).")
        else:
            st.caption("En estos archivos faltaba el campo esperado y se usó el campo indicado para los cálculos.")
            st.dataframe(alt_df, use_container_width=True)
        st.markdown("---")
        st.markdown("### Diagnóstico de históricos detectados")
        diag_df = resultados.get("diagnostico_historicos", pd.DataFrame())
        if diag_df is None or diag_df.empty:
            st.info("No se detectaron hojas de resultados en los archivos cargados.")
        else:
            st.dataframe(diag_df, use_container_width=True)
        st.markdown("---")
        st.markdown("**Hojas no clasificadas**")
        st.dataframe(pd.DataFrame(resultados["no_clasificados"]), use_container_width=True)
        st.markdown("**Ubicaciones no mapeadas (Atenciones)**")
        st.dataframe(resultados["ubicaciones_no_mapeadas"], use_container_width=True)
        st.markdown("**Totales sin match en Atenciones**")
        st.dataframe(resultados["totales_sin_match_atenciones_df"], use_container_width=True)

    excel_bytes = generar_excel_bytes(
        resultados,
        resultados["periodo_etiqueta"],
        resultados["periodo_inicio"],
        resultados["periodo_fin"],
    )
    st.download_button(
        "⬇️ Descargar Excel completo",
        data=excel_bytes,
        file_name=f"Analisis_honorarios_{resultados['periodo_etiqueta'].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Carga archivos para comenzar el análisis.")
