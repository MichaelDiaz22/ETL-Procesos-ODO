import streamlit as st
import pandas as pd
import hashlib

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="FASES 1 - 2 - 3", page_icon="📊", layout="wide")

st.title("📊 TABLEROS POR FASE")
st.markdown(
    "Carga múltiples archivos Excel. Se clasificarán automáticamente en "
    "**Ventas**, **Atenciones del especialista** o **Totales**."
)

# ============================================================
# ESTRUCTURAS ESPERADAS
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

# ============================================================
# TABLA BASE: SEDE + UBICACIÓN + FASE
# ============================================================
MAPA_FASES = [
    ("ADC", "VILL-Oncología", "Fase 1"),
    ("ADC", "VILL-Rehabilitación Cardiaca", "Fase 1"),
    ("ADC", "VILL-Consulta Externa", "Fase 1"),
    ("ADC", "VILL-Hospitalización 2 Piso", "Fase 2"),
    ("ADC", "VILL-Hemodinamia", "Fase 3"),
    ("ADC", "VILL-Laboratorio Clínico", "Fase 1"),
    ("ADC", "VILL-UCINT 6 Piso", "Fase 2"),
    ("ADC", "VILL-UCI 5 Piso", "Fase 2"),
    ("ADC", "VILL-Imagenología", "Fase 1"),
    ("ADC", "VILL-Sala de Cirugía 1 Cardiovascular", "Fase 3"),
    ("ADC", "VILL-Hospitalización 6 Piso", "Fase 2"),
    ("ADC", "VILL-Sala de Cirugía 2", "Fase 3"),
    ("ADC", "VILL-Electrofisiologia", "Fase 1"),
    ("ADC", "VILL-Gestión Pre-transfusional", "Fase 3"),
    ("ADC", "SAN-Consulta Externa", "Fase 1"),
    ("CAA", "CAA-Hospitalización 5 Piso", "Fase 2"),
    ("CAA", "CAA-Urgencias", "Fase 2"),
    ("CAA", "CAA-Consulta Externa", "Fase 1"),
    ("CAA", "CAA-Sala de Cirugía 3", "Fase 3"),
    ("CAA", "CAA-Sala de Cirugía 4", "Fase 3"),
    ("CAA", "CAA-Hemodinamia", "Fase 3"),
    ("CAA", "CAC-UCINT Adulto", "Fase 2"),
    ("CAA", "CAA-UCI Adulto", "Fase 2"),
    ("CAA", "CAA-Imagenología", "Fase 1"),
    ("CAA", "CAA-Cardiología No Invasiva", "Fase 1"),
    ("CAA", "CAA-Laboratorio Clínico", "Fase 1"),
    ("CAI", "CAI-Consulta Externa Nueva", "Fase 1"),
    ("CAI", "CAI-Sala de Cirugía 2", "Fase 3"),
    ("CAI", "CAI-Urgencias Nueva", "Fase 2"),
    ("CAI", "CAI-Hospitalización 6 Piso Norte Nueva", "Fase 2"),
    ("CAI", "CAI-Hospitalización 5 Piso Norte Nueva", "Fase 2"),
    ("CAI", "CAI-UCI 2 Piso 2 Nueva", "Fase 2"),
    ("CAI", "CAI-Hospitalización 5 Piso Sur Nueva", "Fase 2"),
    ("CAI", "CAI-Hospitalización 4 Piso Sur Nueva", "Fase 2"),
    ("CAI", "CAI-Sala de Cirugía 4 (Urgencias)", "Fase 2"),
    ("CAI", "CAI-Hospitalización 6 Piso Sur Nueva", "Fase 2"),
    ("CAI", "CAI-UCINT  Piso 2 Nueva", "Fase 2"),
    ("CAI", "CAI-UCI 1 Piso 2 Nueva", "Fase 2"),
    ("CAI", "CAI-Electrofisiología", "Fase 1"),
    ("CAI", "CAI-Imagenologia", "Fase 1"),
    ("CAI", "CAI-Sala de Cirugía 1 (Cardiovascular)", "Fase 3"),
    ("CAI", "CAI-Cardiología No Invasiva Nueva", "Fase 1"),
    ("CAI", "CAI-Sala de Cirugía 3", "Fase 3"),
    ("CAI", "CAI-Hemodinamia", "Fase 3"),
    ("CAI", "CAI-Laboratorio Clínico", "Fase 1"),
    ("CAI", "CAI-TeleConsulta", "Fase 1"),
    ("CAI", "CAI-Gestion pre transfusional", "Fase 3"),
    ("CAI", "CAI-Terapias", "Fase 1"),
    ("CAM", "CAM-Consulta Externa", "Fase 1"),
    ("CAM", "CAM-Urgencias", "Fase 2"),
    ("CAM", "CAM-Hospitalización 7 Piso Sur", "Fase 2"),
    ("CAM", "CAM-Hospitalización 6 Piso Norte", "Fase 2"),
    ("CAM", "CAM-Hospitalización 4 Piso Sur", "Fase 2"),
    ("CAM", "CAM-UCI 7 Piso", "Fase 2"),
    ("CAM", "CAM-Hospitalización 6 Piso Sur", "Fase 2"),
    ("CAM", "CAM-Sala de Cirugía 1 (Urgencias)", "Fase 2"),
    ("CAM", "CAM-Sala de Cirugía 4", "Fase 3"),
    ("CAM", "CAM-Sala de Cirugía 3", "Fase 3"),
    ("CAM", "CAM-Sala de Cirugía 2", "Fase 3"),
    ("CAM", "CAM-Sala de Cirugía 5", "Fase 3"),
    ("CAM", "CAM-Hospitalización 3 Piso Sur", "Fase 2"),
    ("CAM", "CAM-Hospitalización 3 Piso Norte", "Fase 2"),
    ("CAM", "CAM-Hospitalización 5 Piso Sur", "Fase 2"),
    ("CAM", "CAM-UCINT 3 Piso", "Fase 2"),
    ("CAM", "CAM-UCI 3 Piso", "Fase 2"),
    ("CAM", "CAM-TeleConsulta", "Fase 1"),
    ("CAM", "CAM- Sala de Cirugía 7", "Fase 3"),
    ("CAM", "CAM-UCINT 5 Piso", "Fase 2"),
    ("CAM", "CAM-Cardiología No Invasiva", "Fase 1"),
    ("CAM", "CAM-Hemodinamia Piso 5", "Fase 3"),
    ("CAM", "CAM-Electrofisiología Piso 5", "Fase 1"),
    ("CAM", "CAM-Resonancia Magnética", "Fase 1"),
    ("CAM", "CAM-Imagenología", "Fase 1"),
    ("CAM", "CAM-Sala de Cirugía 6 Cardiovascular", "Fase 3"),
    ("CAM", "CAM-Laboratorio Clínico", "Fase 1"),
    ("CAM", "CAM - Sala de Cirugía 8", "Fase 3"),
    ("CAM", "CAM - Terapias", "Fase 1"),
    ("CAM", "CAM - Hospitalizacion 4 piso norte", "Fase 2"),
    ("CASM", "CASM- Consulta Externa", "Fase 1"),
    ("CASM", "CASM-Hospitalización VIP 2", "Fase 2"),
    ("CASM", "CASM-Hospitalización 2 Piso Norte", "Fase 2"),
    ("CASM", "CASM-Hospitalización 2 Piso Sur", "Fase 2"),
    ("CASM", "CASM-Urgencias", "Fase 2"),
    ("CASM", "CASM-Hospitalización VIP 1", "Fase 2"),
    ("CASM", "CASM-Hospitalización 1 piso Norte", "Fase 2"),
    ("CASM", "CASM-Hospitalización 1 piso", "Fase 2"),
    ("CASM", "CASM-UCI Adulto 1", "Fase 2"),
    ("CASM", "CASM-Sala de Cirugía 2", "Fase 3"),
    ("CASM", "CASM-UCINT", "Fase 2"),
    ("CASM", "CASM-UCI Adulto 2", "Fase 2"),
    ("CASM", "CASM-Hospitalización 2 Piso Centro", "Fase 2"),
    ("CASM", "CASM-Cardiología No Invasiva", "Fase 1"),
    ("CASM", "CASM-Sala de Cirugía 4", "Fase 3"),
    ("CASM", "CASM-Sala de Preparacion Cirugia", "Fase 3"),
    ("CASM", "CASM-Sala de Cirugía 3 (Urgencias)", "Fase 2"),
    ("CASM", "CASM- Hemodinamia", "Fase 3"),
    ("CASM", "CASM-Imagenología", "Fase 1"),
    ("CASM", "CASM-Sala de Cirugía 1 Cardiovascular", "Fase 3"),
    ("CASM", "CASM-Recuperación Cirugía", "Fase 3"),
    ("CASM", "CASM-Laboratorio Clínico", "Fase 1"),
    ("CASM", "CASM-Electrofisiología", "Fase 1"),
    ("CASM", "CASM-Gestion pre transfusional", "Fase 3"),
    ("CASM", "CASM-Hemodialisis", "Fase 3"),
    ("CASM", "CASM-Tomografia", "Fase 1"),
    ("CACV", "CACV-Hospitalización 5 Piso Norte", "Fase 2"),
    ("CACV", "CACV-Hospitalización 5 Piso Sur", "Fase 2"),
    ("CACV", "CACV-Laboratorio Clínico", "Fase 1"),
    ("CACV", "CACV-Urgencias", "Fase 2"),
    ("CACV", "CACV-Imagenología", "Fase 1"),
    ("CACV", "CACV-Sala de Cirugía 3", "Fase 3"),
    ("CACV", "CACV-Sala de Cirugía 4", "Fase 3"),
    ("CACV", "CACV-Unidad Basico Neonatal", "Fase 3"),
    ("CACV", "CACV-Terapias", "Fase 1"),
    ("CACV", "CACV-Gestión Pre-transfusional", "Fase 3"),
    ("CACV", "CACV-Sala de Cirugía 5", "Fase 3"),
    ("CACV", "CACV-Hospitalización 6 Piso Norte", "Fase 2"),
    ("CACV", "CACV-Hospitalización 6 Piso Sur", "Fase 2"),
    ("CACV", "CACV- Hemodinamia 1", "Fase 3"),
    ("CACV", "CACV-UCI Adulto", "Fase 2"),
    ("CACV", "CACV-UCINT Adulto", "Fase 2"),
    ("CACV", "CACV-UCI Neonatal", "Fase 2"),
    ("CACV", "CACV-Sala de Partos 1", "Fase 3"),
    ("CACV", "CACV-Sala Trabajo de Parto", "Fase 3"),
    ("CACV", "CACV- Consulta Externa", "Fase 1"),
    ("CACV", "CACV-UCINT Neonatal", "Fase 2"),
    ("CACV", "CACV-Sala Postparto", "Fase 3"),
    ("CACV", "CACV-Sala de Cesaria", "Fase 3"),
    ("CACV", "CACV-Sala de Partos 2", "Fase 3"),
    ("CACV", "CACV-Ecografía", "Fase 1"),
    ("CACV", "CACV-UCINT Alto Riesgo", "Fase 2"),
    ("CACV", "CACV-Sala de Procedimientos", "Fase 3"),
    ("CACV", "CACV-Tomografía", "Fase 1"),
    ("CACV", "CACV-Resonancia Magnética", "Fase 1"),
    ("CACV", "CACV-Recuperación Cirugía", "Fase 3"),
    ("CACV", "CACV-Cardiología No Invasiva", "Fase 1"),
]

COLUMNAS_RESUMEN = [
    "Angiografía Villavicencio",
    "Clínica Avidanti Ibagué",
    "Clínica Avidanti Manizales",
    "Clínica Avidanti Santa Marta",
    "Clínica Avidanti Ciudad Verde",
    "Clínica Avidanti Armenia",
]

CODIGOS_SEDE = ["ADC", "CAI", "CAM", "CASM", "CACV", "CAA"]
MAPA_CODIGO_A_COLUMNA = dict(zip(CODIGOS_SEDE, COLUMNAS_RESUMEN))

FILAS_RESUMEN = [
    "Revisadas por analistas",
    "Avaladas subgerencia médica",
    "Dinero enviado por interfaz",
    "Total ventas consulta externa (ACTIVO Y FACTURADO)",
    "Dinero ventas ambulatorio",
    "Porcentual faltante (META 30%)",
    "Ventas relacionadas en factura (FACTURADO)",
    "Porcentual impactado (META 0%)",
]

FASES = ["Fase 1", "Fase 2", "Fase 3"]
TITULOS_FASES = {
    "Fase 1": "FASE 1 - AMBULATORIO",
    "Fase 2": "FASE 2 - HOSPITALARIO",
    "Fase 3": "FASE 3 - QUIRÚRGICO",
}

ESTADOS_ACTIVA_FACTURADA = {"activa", "facturada"}
ESTADO_FACTURADA = {"facturada"}


def construir_tabla_resumen():
    df = pd.DataFrame("", index=FILAS_RESUMEN, columns=COLUMNAS_RESUMEN)
    df.index.name = "Concepto"
    return df


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def normalizar(s):
    return (
        str(s).strip().lower()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        .replace("Ã³", "o").replace("Ã¡", "a").replace("Ã©", "e")
        .replace("Ã", "i").replace("Ãº", "u")
        .replace("_", " ").replace("-", " ")
        .replace(".", "").replace(",", "").replace("/", " ")
        .replace("  ", " ").strip()
    )


ESTRUCTURAS_NORM = {
    nombre: {normalizar(c) for c in cols}
    for nombre, cols in ESTRUCTURAS.items()
}


def clasificar_estructura(columnas_df):
    cols_df_norm = {normalizar(c) for c in columnas_df}
    mejor = (None, 0.0)
    for nombre, esperadas in ESTRUCTURAS_NORM.items():
        if not esperadas:
            continue
        coincidencias = len(esperadas & cols_df_norm)
        score = coincidencias / len(esperadas)
        if score > mejor[1]:
            mejor = (nombre, score)
    return mejor


def obtener_columna(df, nombre_esperado):
    objetivo = normalizar(nombre_esperado)
    for c in df.columns:
        if normalizar(c) == objetivo:
            return c
    return None


def hash_df(df):
    return hashlib.md5(
        pd.util.hash_pandas_object(df, index=False).values.tobytes()
    ).hexdigest()


def es_vacio(serie):
    s = serie.astype(str).str.strip()
    return ~s.isin(["", "nan", "None", "NaN", "null", "NULL"])


def normalizar_llave_venta(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.isdigit():
        s = s.lstrip("0") or "0"
    return s


def convertir_a_numero(serie):
    return pd.to_numeric(
        serie.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip(),
        errors="coerce"
    ).fillna(0)


MAPA_UBICACION = {}
for sede_cod, ubicacion, fase in MAPA_FASES:
    fase_canonica = str(fase).strip()
    MAPA_UBICACION[normalizar(ubicacion)] = (sede_cod, fase_canonica)


def _palabras_clave(texto):
    palabras = normalizar(texto).split()
    return frozenset(p for p in palabras if p != "vill")


MAPA_UBICACION_TOKENS = {
    ubi_norm: (sede, fase, _palabras_clave(ubi_norm))
    for ubi_norm, (sede, fase) in MAPA_UBICACION.items()
}


def detectar_ubicacion_flexible(valor):
    if pd.isna(valor):
        return (None, None)
    txt_norm = normalizar(valor)
    if txt_norm in MAPA_UBICACION:
        return MAPA_UBICACION[txt_norm]
    tokens_valor = _palabras_clave(txt_norm)
    for ubi_norm, (sede, fase, tokens_ubi) in MAPA_UBICACION_TOKENS.items():
        if tokens_ubi and tokens_ubi.issubset(tokens_valor):
            return (sede, fase)
    return (None, None)


# ============================================================
# CARGA DE ARCHIVOS
# ============================================================
uploaded_files = st.file_uploader(
    "Selecciona los archivos Excel (.xlsx, .xls)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("👆 Carga al menos un archivo Excel para comenzar.")
    for fase in FASES:
        st.subheader(f"📋 {TITULOS_FASES[fase]}")
        st.dataframe(construir_tabla_resumen(), use_container_width=True)
    st.stop()


@st.cache_data(show_spinner=False)
def leer_excel(file_bytes, file_name):
    import io
    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        return {name: df for name, df in sheets.items() if not df.empty}, None
    except Exception as e:
        return {}, str(e)


# ============================================================
# PROCESAR ARCHIVOS
# ============================================================
bases = {nombre: [] for nombre in ESTRUCTURAS}
no_clasificados = []
errores = []
archivos_duplicados = []
hojas_duplicadas = []

hashes_archivos_vistos = {}
hashes_hojas_vistos = {}

progress = st.progress(0, text="Procesando archivos...")

for idx, f in enumerate(uploaded_files):
    file_bytes = f.getvalue()
    hash_archivo = hashlib.md5(file_bytes).hexdigest()

    if hash_archivo in hashes_archivos_vistos:
        archivos_duplicados.append({
            "Archivo": f.name,
            "Ya cargado como": hashes_archivos_vistos[hash_archivo],
        })
        progress.progress((idx + 1) / len(uploaded_files))
        continue

    hashes_archivos_vistos[hash_archivo] = f.name

    hojas, err = leer_excel(file_bytes, f.name)
    if err:
        errores.append((f.name, err))
        progress.progress((idx + 1) / len(uploaded_files))
        continue

    for hoja, df in hojas.items():
        estructura, score = clasificar_estructura(df.columns)

        if estructura is None or score < UMBRAL_COINCIDENCIA:
            no_clasificados.append({
                "Archivo": f.name,
                "Hoja": hoja,
                "Mejor candidato": estructura or "—",
                "Coincidencia": f"{score:.0%}",
                "Columnas": len(df.columns),
                "Filas": len(df),
            })
            continue

        # Filtro previo para "Totales": Total tarifas y recargos/descuentos >= 1000
        if estructura == "Totales":
            col_tot_tarifas = obtener_columna(df, "Total tarifas y recargos/descuentos")
            if col_tot_tarifas is not None:
                valores_tot = pd.to_numeric(
                    df[col_tot_tarifas]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("$", "", regex=False)
                    .str.replace(" ", "", regex=False)
                    .str.strip(),
                    errors="coerce"
                )
                df = df[valores_tot >= 1000].copy()

        h = hash_df(df)
        if h in hashes_hojas_vistos:
            hojas_duplicadas.append({
                "Archivo": f.name,
                "Hoja": hoja,
                "Estructura": estructura,
                "Duplicado de": hashes_hojas_vistos[h],
            })
            continue

        hashes_hojas_vistos[h] = f"{f.name}::{hoja}"
        bases[estructura].append((f.name, hoja, df.copy()))

    progress.progress((idx + 1) / len(uploaded_files))

progress.empty()


# ============================================================
# ERRORES Y NO CLASIFICADOS
# ============================================================
if errores:
    with st.expander("❌ Errores al leer archivos", expanded=False):
        for nombre, err in errores:
            st.write(f"- **{nombre}**: {err}")

if no_clasificados:
    with st.expander("⚠️ Archivos/hojas NO clasificados", expanded=False):
        st.dataframe(pd.DataFrame(no_clasificados), use_container_width=True)


# ============================================================
# CONSTRUIR BASE "ATENCIONES DEL ESPECIALISTA"
# ============================================================
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


# ============================================================
# CÁLCULOS: Revisadas / Avaladas / Dinero interfaz
# ============================================================
conteos = {
    fase: {cod: {"revisadas": 0, "avaladas": 0} for cod in CODIGOS_SEDE}
    for fase in FASES
}
dinero_interfaz = {
    fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES
}
errores_valor_bajo = {
    fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
    for fase in FASES
}
df_filtrado_revisadas = pd.DataFrame()
ubicaciones_no_mapeadas = pd.Series(dtype=int)

sede_serie = None
fase_serie = None
mask_verifica = None

if not atenciones_df.empty:
    col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
    col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(atenciones_df, "Usuario / Sub Medico")
    col_valor_liquidado = obtener_columna(atenciones_df, "Valor liquidado")

    if col_ubicacion is None or col_verifica is None:
        st.error("⚠️ Faltan columnas clave en 'Atenciones del especialista'.")
    else:
        ubicacion_norm_serie = (
            atenciones_df[col_ubicacion].astype(str).map(normalizar)
        )
        sede_serie = ubicacion_norm_serie.map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[0]
        )
        fase_serie = ubicacion_norm_serie.map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[1]
        )

        mask_verifica = es_vacio(atenciones_df[col_verifica])
        mask_submedico = (
            es_vacio(atenciones_df[col_submedico])
            if col_submedico is not None
            else pd.Series(False, index=atenciones_df.index)
        )

        sin_match = ubicacion_norm_serie[sede_serie.isna()]
        if not sin_match.empty:
            ubicaciones_no_mapeadas = (
                sin_match
                .value_counts()
                .rename_axis("Ubicación (normalizada)")
                .reset_index(name="Registros")
            )

        for fase in FASES:
            for cod in CODIGOS_SEDE:
                mask_sede_fase = (sede_serie == cod) & (fase_serie == fase)
                mask_rev = mask_sede_fase & mask_verifica
                mask_ava = mask_rev & mask_submedico
                conteos[fase][cod]["revisadas"] = int(mask_rev.sum())
                conteos[fase][cod]["avaladas"] = int(mask_ava.sum())

        df_filtrado_revisadas = atenciones_df.loc[mask_verifica].copy()

        if col_valor_liquidado is not None:
            valor_liquidado_num = convertir_a_numero(
                atenciones_df[col_valor_liquidado]
            )
            for i in range(len(atenciones_df)):
                sede_cod = sede_serie.iloc[i]
                fase_val = fase_serie.iloc[i]
                if fase_val is None or sede_cod is None:
                    continue
                fase_val = str(fase_val).strip()
                if fase_val not in dinero_interfaz:
                    continue
                if sede_cod not in dinero_interfaz[fase_val]:
                    continue
                if not bool(mask_verifica.iloc[i]):
                    continue

                valor = float(valor_liquidado_num.iloc[i])
                if valor < 1000:
                    errores_valor_bajo[fase_val][sede_cod]["cantidad"] += 1
                    errores_valor_bajo[fase_val][sede_cod]["suma"] += valor
                else:
                    dinero_interfaz[fase_val][sede_cod] += valor
else:
    st.warning("⚠️ No hay datos de 'Atenciones del especialista' cargados.")


# ============================================================
# CÁLCULOS SOBRE "Totales" cruzado con "Ventas"
# ------------------------------------------------------------
# Para cada (sede, fase):
#
#   Total ventas consulta externa =
#       count(Totales ∩ Ventas)     ← SIN filtro de tarifa
#
#   Dinero ventas ambulatorio =
#       sum(tarifas)               ← SIN filtro de tarifa
#
#   Ventas relacionadas en factura =
#       count(Totales ∩ Ventas con tarifa >= 1000)   ← CON filtro
#
#   Errores (relacionados con "Ventas relacionadas"):
#       count/suma(Totales ∩ Ventas con tarifa < 1000)
#       % = errores / Avaladas
# ============================================================
total_ventas_ce = {fase: {cod: 0 for cod in CODIGOS_SEDE} for fase in FASES}
dinero_ambulatorio = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
ventas_relacionadas_factura = {fase: {cod: 0 for cod in CODIGOS_SEDE} for fase in FASES}
errores_tarifa = {
    fase: {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
    for fase in FASES
}
ubicaciones_totales_no_mapeadas = pd.Series(dtype=int)

if bases["Totales"]:
    totales_df = pd.concat(
        [df for _, _, df in bases["Totales"]],
        ignore_index=True
    )

    col_totales_venta_no = obtener_columna(totales_df, "No. de venta")
    col_totales_centro_costo = obtener_columna(totales_df, "Centro De Costo")
    col_totales_tarifa_reliq = obtener_columna(totales_df, "tarifas (reliquidado)")

    if col_totales_venta_no is not None and col_totales_centro_costo is not None:
        totales_df["_venta_no_norm"] = (
            totales_df[col_totales_venta_no].map(normalizar_llave_venta)
        )
        totales_ubic = totales_df[col_totales_centro_costo].astype(str).map(detectar_ubicacion_flexible)
        totales_df["_sede"] = totales_ubic.map(lambda x: x[0])
        totales_df["_fase"] = totales_ubic.map(lambda x: x[1])

        sin_match_totales = (
            totales_df.loc[totales_df["_sede"].isna(), col_totales_centro_costo]
            .astype(str).map(normalizar)
        )
        if not sin_match_totales.empty:
            ubicaciones_totales_no_mapeadas = (
                sin_match_totales
                .value_counts()
                .rename_axis("Centro De Costo (normalizado)")
                .reset_index(name="Registros")
            )

        if col_totales_tarifa_reliq is not None:
            totales_tarifa_num = convertir_a_numero(totales_df[col_totales_tarifa_reliq])
        else:
            totales_tarifa_num = pd.Series(0.0, index=totales_df.index)

        ventas_nos_existentes = set()
        if bases["Ventas"]:
            ventas_para_cruce = pd.concat(
                [df for _, _, df in bases["Ventas"]],
                ignore_index=True
            )
            col_venta_no_v = obtener_columna(ventas_para_cruce, "Venta No.")
            if col_venta_no_v is not None:
                ventas_nos_existentes = set(
                    ventas_para_cruce[col_venta_no_v]
                    .map(normalizar_llave_venta).dropna().unique()
                )

        mask_venta_en_ventas = totales_df["_venta_no_norm"].isin(ventas_nos_existentes)

        for fase in FASES:
            for cod in CODIGOS_SEDE:
                mask_sede_fase = (totales_df["_sede"] == cod) & (totales_df["_fase"] == fase)
                mask_final = mask_sede_fase & mask_venta_en_ventas

                # Total ventas: count de TODOS los Totales ∩ Ventas (sin filtro de tarifa)
                total_ventas_ce[fase][cod] = int(mask_final.sum())

                # Dinero ambulatorio: sum de tarifas de TODOS (sin filtro de tarifa)
                dinero_ambulatorio[fase][cod] = float(
                    totales_tarifa_num[mask_final].sum()
                )

                # Ventas relacionadas en factura: solo tarifa >= 1000
                tarifas_para_analisis = totales_tarifa_num[mask_final]
                indices = tarifas_para_analisis.index

                mask_valida = totales_tarifa_num.loc[indices] >= 1000
                mask_error = ~mask_valida

                ventas_relacionadas_factura[fase][cod] = int(mask_valida.sum())

                if mask_error.any():
                    errores_tarifa[fase][cod]["cantidad"] = int(mask_error.sum())
                    errores_tarifa[fase][cod]["suma"] = float(
                        totales_tarifa_num.loc[indices][mask_error].sum()
                    )


# ============================================================
# PORCENTUALES
# ============================================================
porcentual_faltante = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
porcentual_impactado = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
porcentaje_errores = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}
porcentaje_errores_valor = {fase: {cod: 0.0 for cod in CODIGOS_SEDE} for fase in FASES}

for fase in FASES:
    for cod in CODIGOS_SEDE:
        avaladas = conteos[fase][cod]["avaladas"]
        total_ventas = total_ventas_ce[fase][cod]
        relacionadas = ventas_relacionadas_factura[fase][cod]
        cant_err_v = errores_valor_bajo[fase][cod]["cantidad"]
        cant_err_t = errores_tarifa[fase][cod]["cantidad"]

        if total_ventas > 0:
            porcentual_faltante[fase][cod] = (avaladas / total_ventas) * 100.0
            porcentual_impactado[fase][cod] = (relacionadas / total_ventas) * 100.0
        if avaladas > 0:
            porcentaje_errores_valor[fase][cod] = (cant_err_v / avaladas) * 100.0
            porcentaje_errores[fase][cod] = (cant_err_t / avaladas) * 100.0


# ============================================================
# CONSOLIDADO
# ============================================================
conteos_consolidado = {cod: {"revisadas": 0, "avaladas": 0} for cod in CODIGOS_SEDE}
dinero_interfaz_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
errores_valor_bajo_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}
total_ventas_ce_consolidado = {cod: 0 for cod in CODIGOS_SEDE}
dinero_ambulatorio_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
ventas_relacionadas_factura_consolidado = {cod: 0 for cod in CODIGOS_SEDE}
errores_tarifa_consolidado = {cod: {"cantidad": 0, "suma": 0.0} for cod in CODIGOS_SEDE}

for cod in CODIGOS_SEDE:
    for fase in FASES:
        conteos_consolidado[cod]["revisadas"] += conteos[fase][cod]["revisadas"]
        conteos_consolidado[cod]["avaladas"] += conteos[fase][cod]["avaladas"]
        dinero_interfaz_consolidado[cod] += dinero_interfaz[fase][cod]
        errores_valor_bajo_consolidado[cod]["cantidad"] += errores_valor_bajo[fase][cod]["cantidad"]
        errores_valor_bajo_consolidado[cod]["suma"] += errores_valor_bajo[fase][cod]["suma"]
        total_ventas_ce_consolidado[cod] += total_ventas_ce[fase][cod]
        dinero_ambulatorio_consolidado[cod] += dinero_ambulatorio[fase][cod]
        ventas_relacionadas_factura_consolidado[cod] += ventas_relacionadas_factura[fase][cod]
        errores_tarifa_consolidado[cod]["cantidad"] += errores_tarifa[fase][cod]["cantidad"]
        errores_tarifa_consolidado[cod]["suma"] += errores_tarifa[fase][cod]["suma"]

porcentual_faltante_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
porcentual_impactado_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
porcentaje_errores_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}
porcentaje_errores_valor_consolidado = {cod: 0.0 for cod in CODIGOS_SEDE}

for cod in CODIGOS_SEDE:
    avaladas = conteos_consolidado[cod]["avaladas"]
    total_ventas = total_ventas_ce_consolidado[cod]
    relacionadas = ventas_relacionadas_factura_consolidado[cod]
    cant_err_v = errores_valor_bajo_consolidado[cod]["cantidad"]
    cant_err_t = errores_tarifa_consolidado[cod]["cantidad"]

    if total_ventas > 0:
        porcentual_faltante_consolidado[cod] = (avaladas / total_ventas) * 100.0
        porcentual_impactado_consolidado[cod] = (relacionadas / total_ventas) * 100.0
    if avaladas > 0:
        porcentaje_errores_valor_consolidado[cod] = (cant_err_v / avaladas) * 100.0
        porcentaje_errores_consolidado[cod] = (cant_err_t / avaladas) * 100.0


# ============================================================
# Helpers de formato
# ============================================================
def formatear_dinero_interfaz(total, cant_err, suma_err, pct_err):
    if cant_err > 0:
        return (
            f"${total:,.0f} "
            f"(Errores: ${suma_err:,.0f} en {cant_err} registros — {pct_err:.2f}%)"
        )
    return f"${total:,.0f}"


def formatear_ventas_relacionadas(total, cant_err, suma_err, pct_err):
    if cant_err > 0:
        return (
            f"{total:,} "
            f"(Errores: ${suma_err:,.0f} en {cant_err} registros — {pct_err:.2f}%)"
        )
    return f"{total:,}"


# ============================================================
# TABLA CONSOLIDADA
# ============================================================
tabla_consolidada = construir_tabla_resumen()
for cod in CODIGOS_SEDE:
    columna = MAPA_CODIGO_A_COLUMNA[cod]
    tabla_consolidada.loc["Revisadas por analistas", columna] = f"{conteos_consolidado[cod]['revisadas']:,}"
    tabla_consolidada.loc["Avaladas subgerencia médica", columna] = f"{conteos_consolidado[cod]['avaladas']:,}"
    tabla_consolidada.loc["Dinero enviado por interfaz", columna] = formatear_dinero_interfaz(
        dinero_interfaz_consolidado[cod],
        errores_valor_bajo_consolidado[cod]["cantidad"],
        errores_valor_bajo_consolidado[cod]["suma"],
        porcentaje_errores_valor_consolidado[cod],
    )
    tabla_consolidada.loc["Total ventas consulta externa (ACTIVO Y FACTURADO)", columna] = f"{total_ventas_ce_consolidado[cod]:,}"
    tabla_consolidada.loc["Dinero ventas ambulatorio", columna] = f"${dinero_ambulatorio_consolidado[cod]:,.0f}"
    tabla_consolidada.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante_consolidado[cod]:,.2f}%"
    tabla_consolidada.loc["Ventas relacionadas en factura (FACTURADO)", columna] = formatear_ventas_relacionadas(
        ventas_relacionadas_factura_consolidado[cod],
        errores_tarifa_consolidado[cod]["cantidad"],
        errores_tarifa_consolidado[cod]["suma"],
        porcentaje_errores_consolidado[cod],
    )
    tabla_consolidada.loc["Porcentual impactado (META 0%)", columna] = f"{porcentual_impactado_consolidado[cod]:,.2f}%"


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("📈 Resumen de carga")
    st.metric("Archivos cargados", len(uploaded_files))
    for nombre in ESTRUCTURAS:
        st.metric(nombre, f"{len(bases[nombre])} hoja(s)")
    if archivos_duplicados:
        st.metric("Archivos duplicados (descartados)", len(archivos_duplicados))
    if hojas_duplicadas:
        st.metric("Hojas duplicadas (descartadas)", len(hojas_duplicadas))
    if no_clasificados:
        st.metric("No clasificados", len(no_clasificados))


# ============================================================
# DIAGNÓSTICOS
# ============================================================
if not ubicaciones_no_mapeadas.empty:
    with st.expander("⚠️ Ubicaciones de la venta (Atenciones) sin coincidencia", expanded=False):
        st.dataframe(ubicaciones_no_mapeadas, use_container_width=True)

if not ubicaciones_totales_no_mapeadas.empty:
    with st.expander("⚠️ Centros de Costo (Totales) sin coincidencia en la tabla base", expanded=False):
        st.dataframe(ubicaciones_totales_no_mapeadas, use_container_width=True)


# ============================================================
# TABLAS POR FASE
# ============================================================
for fase in FASES:
    st.subheader(f"📋 {TITULOS_FASES[fase]}")

    tabla = construir_tabla_resumen()
    for cod in CODIGOS_SEDE:
        columna = MAPA_CODIGO_A_COLUMNA[cod]
        tabla.loc["Revisadas por analistas", columna] = f"{conteos[fase][cod]['revisadas']:,}"
        tabla.loc["Avaladas subgerencia médica", columna] = f"{conteos[fase][cod]['avaladas']:,}"
        tabla.loc["Dinero enviado por interfaz", columna] = formatear_dinero_interfaz(
            dinero_interfaz[fase][cod],
            errores_valor_bajo[fase][cod]["cantidad"],
            errores_valor_bajo[fase][cod]["suma"],
            porcentaje_errores_valor[fase][cod],
        )
        tabla.loc["Total ventas consulta externa (ACTIVO Y FACTURADO)", columna] = f"{total_ventas_ce[fase][cod]:,}"
        tabla.loc["Dinero ventas ambulatorio", columna] = f"${dinero_ambulatorio[fase][cod]:,.0f}"
        tabla.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante[fase][cod]:,.2f}%"
        tabla.loc["Ventas relacionadas en factura (FACTURADO)", columna] = formatear_ventas_relacionadas(
            ventas_relacionadas_factura[fase][cod],
            errores_tarifa[fase][cod]["cantidad"],
            errores_tarifa[fase][cod]["suma"],
            porcentaje_errores[fase][cod],
        )
        tabla.loc["Porcentual impactado (META 0%)", columna] = f"{porcentual_impactado[fase][cod]:,.2f}%"

    st.dataframe(tabla, use_container_width=True, height=380)
    st.download_button(
        label=f"⬇️ Descargar {TITULOS_FASES[fase]} (CSV)",
        data=tabla.to_csv().encode("utf-8"),
        file_name=f"{TITULOS_FASES[fase].replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"dl_{fase}",
    )
    st.divider()


# ============================================================
# CONSOLIDADO
# ============================================================
st.subheader("📋 CONSOLIDADO - TODAS LAS FASES")
st.dataframe(tabla_consolidada, use_container_width=True, height=380)
st.download_button(
    label="⬇️ Descargar CONSOLIDADO (CSV)",
    data=tabla_consolidada.to_csv().encode("utf-8"),
    file_name="CONSOLIDADO_FASES.csv",
    mime="text/csv",
    key="dl_consolidado",
)
st.divider()


# ============================================================
# NOVEDADES
# ============================================================
st.subheader("🔎 Novedades")

if df_filtrado_revisadas.empty:
    st.info("No hay registros que cumplan los filtros de 'Revisadas por analistas'.")
else:
    col_verifica = obtener_columna(df_filtrado_revisadas, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(df_filtrado_revisadas, "Usuario / Sub Medico")

    st.markdown(f"**Total de registros que cumplen los filtros:** {len(df_filtrado_revisadas):,}")

    verificadores_limpios = (
        df_filtrado_revisadas[col_verifica]
        .astype(str).str.strip()
        .replace({"nan": "", "None": "", "NaN": ""})
    )
    df_filtrado_revisadas = df_filtrado_revisadas.assign(_verifica_limpio=verificadores_limpios)

    resumen_verifica = (
        df_filtrado_revisadas
        .groupby("_verifica_limpio", dropna=False)
        .size()
        .reset_index(name="Registros")
        .rename(columns={"_verifica_limpio": "Nombre de Usuario que Verifica"})
    )

    def comparar_con_submedico(nombre_verifica):
        if not col_submedico:
            return "Sin datos de Sub Médico"
        valores_sub = (
            df_filtrado_revisadas[col_submedico]
            .dropna().astype(str).str.strip()
        )
        valores_sub = valores_sub[~valores_sub.isin(["", "nan", "None", "NaN"])]
        if valores_sub.empty:
            return "Sin datos de Sub Médico"
        norm_verifica = normalizar(nombre_verifica)
        set_sub_norm = {normalizar(v) for v in valores_sub.unique()}
        return "Misma persona" if norm_verifica in set_sub_norm else "Diferente persona"

    resumen_verifica["¿Coincide con Usuario / Sub Médico?"] = (
        resumen_verifica["Nombre de Usuario que Verifica"]
        .apply(comparar_con_submedico)
    )
    resumen_verifica = (
        resumen_verifica
        .sort_values("Registros", ascending=False)
        .reset_index(drop=True)
    )

    st.markdown("#### 👥 Verificadores y comparación con Sub Médico")
    st.dataframe(resumen_verifica, use_container_width=True)
