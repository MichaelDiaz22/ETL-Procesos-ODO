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
    # Angiografía Villavicencio
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

    # Clínica Avidanti Armenia
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

    # Clínica Avidanti Ibagué
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

    # Clínica Avidanti Manizales
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

    # Clínica Avidanti Santa Marta
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

    # Clínica Avidanti Ciudad Verde
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

# Nombres completos para los encabezados
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

# Estados permitidos (normalizados, sin tilde/mayúscula)
# en la base Ventas:
#   - "Activa"
#   - "Facturada"
ESTADOS_PERMITIDOS = {"activa", "facturada"}


def construir_tabla_resumen():
    df = pd.DataFrame("", index=FILAS_RESUMEN, columns=COLUMNAS_RESUMEN)
    df.index.name = "Concepto"
    return df


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def normalizar(s):
    """Normaliza strings para comparaciones robustas."""
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
    """Devuelve una máscara booleana: True donde el valor NO es vacío."""
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
    """Convierte una serie de valores monetarios a float."""
    return pd.to_numeric(
        serie.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip(),
        errors="coerce"
    ).fillna(0)


# ============================================================
# MAPA INVERTIDO: {ubicacion_normalizada: (codigo_sede, fase)}
# ============================================================
MAPA_UBICACION = {}
for sede_cod, ubicacion, fase in MAPA_FASES:
    fase_canonica = str(fase).strip()
    MAPA_UBICACION[normalizar(ubicacion)] = (sede_cod, fase_canonica)


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
# CÁLCULOS: "Revisadas por analistas" y "Avaladas subgerencia médica"
# ============================================================
conteos = {
    fase: {cod: {"revisadas": 0, "avaladas": 0} for cod in CODIGOS_SEDE}
    for fase in FASES
}
df_filtrado_revisadas = pd.DataFrame()
df_filtrado_avaladas = pd.DataFrame()
ubicaciones_no_mapeadas = pd.Series(dtype=int)

sede_serie = None
fase_serie = None
mask_verifica = None
mask_submedico = None
venta_norm_atenciones_serie = None

if not atenciones_df.empty:
    col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
    col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(atenciones_df, "Usuario / Sub Medico")
    col_num_venta = obtener_columna(atenciones_df, "Numero Venta")

    if col_ubicacion is None or col_verifica is None:
        st.error(
            "⚠️ Faltan columnas clave en 'Atenciones del especialista': "
            f"'Ubicación de la venta'={'OK' if col_ubicacion else 'FALTA'}, "
            f"'Nombre de Usuario que Verifica'={'OK' if col_verifica else 'FALTA'}."
        )
    else:
        ubicacion_norm_serie = (
            atenciones_df[col_ubicacion]
            .astype(str)
            .map(normalizar)
        )

        sede_serie = ubicacion_norm_serie.map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[0]
        )
        fase_serie = ubicacion_norm_serie.map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[1]
        )

        mask_verifica = es_vacio(atenciones_df[col_verifica])
        if col_submedico is not None:
            mask_submedico = es_vacio(atenciones_df[col_submedico])
        else:
            mask_submedico = pd.Series(False, index=atenciones_df.index)

        if col_num_venta is not None:
            venta_norm_atenciones_serie = (
                atenciones_df[col_num_venta]
                .map(normalizar_llave_venta)
            )
        else:
            venta_norm_atenciones_serie = pd.Series("", index=atenciones_df.index)

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
        df_filtrado_avaladas = atenciones_df.loc[mask_verifica & mask_submedico].copy()
else:
    st.warning(
        "⚠️ No hay datos de 'Atenciones del especialista' cargados. "
        "Los conteos quedarán en cero."
    )


# ============================================================
# CÁLCULO: "Dinero enviado por interfaz" por fase y sede
# ============================================================
dinero_interfaz = {
    fase: {cod: 0.0 for cod in CODIGOS_SEDE}
    for fase in FASES
}
ventas_sin_match = set()
ventas_sin_ubicacion_fase = set()

if bases["Ventas"]:
    ventas_df = pd.concat(
        [df for _, _, df in bases["Ventas"]],
        ignore_index=True
    )

    col_venta_no = obtener_columna(ventas_df, "Venta No.")
    col_valor_facturado = obtener_columna(ventas_df, "Valor facturado")
    col_ubicacion_despacho = obtener_columna(ventas_df, "Ubicación despacho")

    if (
        col_venta_no is None
        or col_valor_facturado is None
        or col_ubicacion_despacho is None
    ):
        st.warning(
            "⚠️ Faltan columnas en Ventas para calcular 'Dinero enviado por "
            "interfaz': 'Venta No.', 'Valor facturado' o 'Ubicación despacho'."
        )
    else:
        ventas_df["_venta_no_norm"] = (
            ventas_df[col_venta_no].map(normalizar_llave_venta)
        )
        ventas_df["_valor_facturado_num"] = convertir_a_numero(
            ventas_df[col_valor_facturado]
        )
        ventas_df["_ubicacion_norm"] = (
            ventas_df[col_ubicacion_despacho].astype(str).map(normalizar)
        )
        ventas_df["_sede_venta"] = ventas_df["_ubicacion_norm"].map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[0]
        )
        ventas_df["_fase_venta"] = ventas_df["_ubicacion_norm"].map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[1]
        )

        # Deduplicar: UNA fila por (Venta No., sede, fase)
        ventas_dedupe = (
            ventas_df
            .dropna(subset=["_sede_venta", "_fase_venta"])
            .drop_duplicates(
                subset=["_venta_no_norm", "_sede_venta", "_fase_venta"],
                keep="first",
            )
        )

        ventas_valor = (
            ventas_dedupe
            .set_index(["_venta_no_norm", "_sede_venta", "_fase_venta"])[
                "_valor_facturado_num"
            ]
            .to_dict()
        )

        ventas_conocidas = set(ventas_df["_venta_no_norm"].unique())

        if not atenciones_df.empty and venta_norm_atenciones_serie is not None:
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

                venta_no = venta_norm_atenciones_serie.iloc[i]
                if not venta_no:
                    continue

                if venta_no not in ventas_conocidas:
                    ventas_sin_match.add(venta_no)
                    continue

                llave = (venta_no, sede_cod, fase_val)
                valor = ventas_valor.get(llave)

                if valor is not None:
                    dinero_interfaz[fase_val][sede_cod] += float(valor)
                else:
                    ventas_sin_ubicacion_fase.add(
                        f"{venta_no} ({sede_cod} - {fase_val})"
                    )
else:
    ventas_df = pd.DataFrame()


# ============================================================
# CÁLCULO: "Total ventas consulta externa (ACTIVO Y FACTURADO)"
# y        "Dinero ventas ambulatorio"
# ------------------------------------------------------------
# Filtros:
#   - "Ubicación despacho" ∈ tabla base (define sede y fase)
#   - "Estado" ∈ {"Activa", "Facturada"} (normalizado)
# ============================================================
total_ventas_ce = {
    fase: {cod: 0 for cod in CODIGOS_SEDE}
    for fase in FASES
}
dinero_ambulatorio = {
    fase: {cod: 0.0 for cod in CODIGOS_SEDE}
    for fase in FASES
}
ubicaciones_ventas_no_mapeadas = pd.Series(dtype=int)
estados_no_incluidos = pd.Series(dtype=int)

if bases["Ventas"]:
    col_ubicacion_despacho = obtener_columna(ventas_df, "Ubicación despacho")
    col_estado = obtener_columna(ventas_df, "Estado")
    col_valor_total_recalc = obtener_columna(ventas_df, "Valor Total Recalculado")

    if col_ubicacion_despacho is None:
        st.warning(
            "⚠️ No se encontró la columna 'Ubicación despacho' en la base Ventas."
        )
    elif col_estado is None:
        st.warning(
            "⚠️ No se encontró la columna 'Estado' en la base Ventas. "
            "No se puede aplicar el filtro ACTIVO Y FACTURADO."
        )
    else:
        ubicacion_despacho_norm = (
            ventas_df[col_ubicacion_despacho]
            .astype(str)
            .map(normalizar)
        )

        sede_ventas = ubicacion_despacho_norm.map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[0]
        )
        fase_ventas = ubicacion_despacho_norm.map(
            lambda u: MAPA_UBICACION.get(u, (None, None))[1]
        )

        # --- Normalizar Estado y filtrar solo "Activa" y "Facturada" ---
        estado_norm = (
            ventas_df[col_estado]
            .astype(str)
            .str.strip()
            .str.lower()
        )
        mask_estado_valido = estado_norm.isin(ESTADOS_PERMITIDOS)

        # Diagnóstico: estados distintos que NO se incluyen
        estados_excluidos = estado_norm[~mask_estado_valido]
        if not estados_excluidos.empty:
            estados_no_incluidos = (
                estados_excluidos
                .value_counts()
                .rename_axis("Estado (normalizado)")
                .reset_index(name="Registros")
            )

        # Diagnóstico: ubicaciones de despacho sin match
        sin_match_ventas = ubicacion_despacho_norm[sede_ventas.isna()]
        if not sin_match_ventas.empty:
            ubicaciones_ventas_no_mapeadas = (
                sin_match_ventas
                .value_counts()
                .rename_axis("Ubicación despacho (normalizada)")
                .reset_index(name="Registros")
            )

        if col_valor_total_recalc is not None:
            valor_total_recalc_num = convertir_a_numero(
                ventas_df[col_valor_total_recalc]
            )
        else:
            valor_total_recalc_num = pd.Series(0.0, index=ventas_df.index)
            st.warning(
                "⚠️ No se encontró la columna 'Valor Total Recalculado' en Ventas."
            )

        for fase in FASES:
            for cod in CODIGOS_SEDE:
                mask_sede_fase = (sede_ventas == cod) & (fase_ventas == fase)
                mask_final = mask_sede_fase & mask_estado_valido

                total_ventas_ce[fase][cod] = int(mask_final.sum())
                dinero_ambulatorio[fase][cod] = float(
                    valor_total_recalc_num[mask_final].sum()
                )


# ============================================================
# CÁLCULO: "Porcentual faltante (META 30%)"
# ============================================================
porcentual_faltante = {
    fase: {cod: 0.0 for cod in CODIGOS_SEDE}
    for fase in FASES
}

for fase in FASES:
    for cod in CODIGOS_SEDE:
        avaladas = conteos[fase][cod]["avaladas"]
        total_ventas = total_ventas_ce[fase][cod]

        if avaladas > 0:
            porcentual_faltante[fase][cod] = (
                (total_ventas - avaladas) / avaladas
            ) * 100.0
        else:
            porcentual_faltante[fase][cod] = 0.0


# ============================================================
# RESUMEN GLOBAL (SIDEBAR)
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
    with st.expander("⚠️ Ubicaciones de la venta (Atenciones) sin coincidencia en la tabla base", expanded=False):
        st.dataframe(ubicaciones_no_mapeadas, use_container_width=True)

if not ubicaciones_ventas_no_mapeadas.empty:
    with st.expander("⚠️ Ubicaciones de despacho (Ventas) sin coincidencia en la tabla base", expanded=False):
        st.dataframe(ubicaciones_ventas_no_mapeadas, use_container_width=True)

if not estados_no_incluidos.empty:
    with st.expander("ℹ️ Estados en Ventas NO incluidos (solo se cuentan 'Activa' y 'Facturada')", expanded=False):
        st.markdown(
            "Estos valores de `Estado` no coinciden con **Activa** o **Facturada**, "
            "por lo que quedan fuera de **Total ventas consulta externa** y "
            "**Dinero ventas ambulatorio**."
        )
        st.dataframe(estados_no_incluidos, use_container_width=True)

if ventas_sin_match:
    with st.expander("⚠️ Ventas de Atenciones sin coincidencia en la base Ventas", expanded=False):
        st.markdown(
            f"**{len(ventas_sin_match):,}** valores de `Numero Venta` (Atenciones) "
            "no se encontraron en `Venta No.` (Ventas)."
        )
        st.dataframe(
            pd.DataFrame({"Numero Venta (sin match)": sorted(ventas_sin_match)}).head(200),
            use_container_width=True,
        )

if ventas_sin_ubicacion_fase:
    with st.expander(
        "⚠️ Ventas cuyo folio existe pero sin filas en la misma (sede, fase)",
        expanded=False,
    ):
        st.markdown(
            f"**{len(ventas_sin_ubicacion_fase):,}** ventas existen en Ventas, "
            "pero ninguna de sus filas tiene `Ubicación despacho` correspondiente "
            "a la (sede, fase) del registro en Atenciones."
        )
        st.dataframe(
            pd.DataFrame(
                {"Venta (sede - fase)": sorted(ventas_sin_ubicacion_fase)}
            ).head(200),
            use_container_width=True,
        )


# ============================================================
# TABLAS RESUMEN POR FASE
# ============================================================
for fase in FASES:
    st.subheader(f"📋 {TITULOS_FASES[fase]}")

    tabla = construir_tabla_resumen()

    for cod in CODIGOS_SEDE:
        columna = MAPA_CODIGO_A_COLUMNA[cod]
        tabla.loc["Revisadas por analistas", columna] = f"{conteos[fase][cod]['revisadas']:,}"
        tabla.loc["Avaladas subgerencia médica", columna] = f"{conteos[fase][cod]['avaladas']:,}"
        tabla.loc["Dinero enviado por interfaz", columna] = f"${dinero_interfaz[fase][cod]:,.0f}"
        tabla.loc["Total ventas consulta externa (ACTIVO Y FACTURADO)", columna] = f"{total_ventas_ce[fase][cod]:,}"
        tabla.loc["Dinero ventas ambulatorio", columna] = f"${dinero_ambulatorio[fase][cod]:,.0f}"
        tabla.loc["Porcentual faltante (META 30%)", columna] = f"{porcentual_faltante[fase][cod]:,.2f}%"

    st.dataframe(tabla, use_container_width=True, height=380)

    csv = tabla.to_csv().encode("utf-8")
    st.download_button(
        label=f"⬇️ Descargar {TITULOS_FASES[fase]} (CSV)",
        data=csv,
        file_name=f"{TITULOS_FASES[fase].replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"dl_{fase}",
    )
    st.divider()


# ============================================================
# SECCIÓN DE NOVEDADES
# ============================================================
st.subheader("🔎 Novedades")

if df_filtrado_revisadas.empty:
    st.info("No hay registros que cumplan los filtros de 'Revisadas por analistas'.")
else:
    col_verifica = obtener_columna(df_filtrado_revisadas, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(df_filtrado_revisadas, "Usuario / Sub Medico")

    st.markdown(
        f"**Total de registros que cumplen los filtros:** {len(df_filtrado_revisadas):,}"
    )

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
