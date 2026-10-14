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
    # Angiografía Villavicencio (ADC)
    ("ADC", "VILL-Hospitalización 2 Piso", "Fase 2"),
    ("ADC", "VILL-UCI 5 Piso", "Fase 2"),
    ("ADC", "VILL-Hospitalización 6 Piso", "Fase 2"),
    ("ADC", "VILL-Consulta Externa", "Fase 1"),
    ("ADC", "VILL-Sala de Cirugía 2", "Fase 3"),
    ("ADC", "VILL-Hemodinamia", "Fase 3"),
    ("ADC", "VILL-Imagenología", "Fase 1"),
    ("ADC", "VILL-UCINT 6 Piso", "Fase 2"),
    ("ADC", "VILL-Electrofisiologia", "Fase 1"),
    ("ADC", "VILL-Sala de Cirugía 1 Cardiovascular", "Fase 3"),
    # Clínica Avidanti Armenia (CAA)
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
    # Clínica Avidanti Ibagué (CAI)
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
    # Clínica Avidanti Manizales (CAM)
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
    # Clínica Avidanti Santa Marta (CASM)
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
    # Clínica Avidanti Ciudad Verde (CACV)
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


# Construir mapa normalizado: {sede: {ubicacion_norm: fase}}
MAPA_UBICACION_A_FASE = {}
for sede, ubicacion, fase in MAPA_FASES:
    MAPA_UBICACION_A_FASE.setdefault(sede, {})[normalizar(ubicacion)] = fase


def detectar_sede(ubicacion_valor):
    """Devuelve el código de sede (ADC, CAI, ...) según el prefijo."""
    txt = normalizar(ubicacion_valor)
    for codigo in CODIGOS_SEDE:
        if txt.startswith(codigo.lower()):
            return codigo
    return None


def detectar_fase(ubicacion_valor):
    """Devuelve la fase (Fase 1/2/3) según el mapa normalizado."""
    sede = detectar_sede(ubicacion_valor)
    if sede is None:
        return None

    txt = normalizar(ubicacion_valor)
    # Comparación exacta primero
    mapa_sede = MAPA_UBICACION_A_FASE.get(sede, {})
    if txt in mapa_sede:
        return mapa_sede[txt]

    # Si no hay match exacto, probar coincidencia por tokens
    for ubi_norm, fase in mapa_sede.items():
        if ubi_norm and ubi_norm in txt:
            return fase
    return None


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
# ------------------------------------------------------------
# Para cada combinación (sede, fase):
#   - Revisadas: registros con "Nombre de Usuario que Verifica" != vacío
#   - Avaladas:  registros con "Usuario / Sub Medico" != vacío
# ============================================================
# conteos[fase][codigo_sede] = {"revisadas": int, "avaladas": int}
conteos = {
    fase: {cod: {"revisadas": 0, "avaladas": 0} for cod in CODIGOS_SEDE}
    for fase in FASES
}
df_filtrado_revisadas = pd.DataFrame()
df_filtrado_avaladas = pd.DataFrame()

if not atenciones_df.empty:
    col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
    col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(atenciones_df, "Usuario / Sub Medico")

    if col_ubicacion is None or col_verifica is None:
        st.error(
            "⚠️ Faltan columnas clave en 'Atenciones del especialista': "
            f"'Ubicación de la venta'={'OK' if col_ubicacion else 'FALTA'}, "
            f"'Nombre de Usuario que Verifica'={'OK' if col_verifica else 'FALTA'}."
        )
    else:
        # Derivar sede y fase por cada fila
        sede_serie = atenciones_df[col_ubicacion].astype(str).map(detectar_sede)
        fase_serie = atenciones_df[col_ubicacion].astype(str).map(detectar_fase)

        # Verificadores y subgerentes limpios
        verificadores_serie = (
            atenciones_df[col_verifica]
            .astype(str).str.strip()
            .replace({"nan": "", "None": "", "NaN": ""})
        )
        if col_submedico is not None:
            submedico_serie = (
                atenciones_df[col_submedico]
                .astype(str).str.strip()
                .replace({"nan": "", "None": "", "NaN": ""})
            )
        else:
            submedico_serie = pd.Series([""] * len(atenciones_df), index=atenciones_df.index)

        mask_verifica = verificadores_serie != ""
        mask_submedico = submedico_serie != ""

        # Iterar por fase y sede para contar
        for fase in FASES:
            for cod in CODIGOS_SEDE:
                mask_base = (sede_serie == cod) & (fase_serie == fase)
                mask_rev = mask_base & mask_verifica
                mask_ava = mask_base & mask_verifica & mask_submedico

                conteos[fase][cod]["revisadas"] = int(mask_rev.sum())
                conteos[fase][cod]["avaladas"] = int(mask_ava.sum())

        # Guardar filtrados globales (por si se usan más adelante)
        df_filtrado_revisadas = atenciones_df.loc[mask_verifica].copy()
        df_filtrado_avaladas = atenciones_df.loc[mask_verifica & mask_submedico].copy()
else:
    st.warning(
        "⚠️ No hay datos de 'Atenciones del especialista' cargados. "
        "Los conteos quedarán en cero."
    )


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
# TABLAS RESUMEN POR FASE
# ============================================================
for fase in FASES:
    st.subheader(f"📋 {TITULOS_FASES[fase]}")

    tabla = construir_tabla_resumen()

    for cod in CODIGOS_SEDE:
        columna = MAPA_CODIGO_A_COLUMNA[cod]
        tabla.loc["Revisadas por analistas", columna] = f"{conteos[fase][cod]['revisadas']:,}"
        tabla.loc["Avaladas subgerencia médica", columna] = f"{conteos[fase][cod]['avaladas']:,}"

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
