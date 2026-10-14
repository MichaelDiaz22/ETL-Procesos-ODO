import streamlit as st
import pandas as pd
import hashlib

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="FASE 1 - AMBULATORIO", page_icon="📊", layout="wide")

st.title("📊 FASE 1 - AMBULATORIO")
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
# TABLA RESUMEN
# ============================================================
COLUMNAS_RESUMEN = ["ADC", "CAI", "CAM", "CASM", "CACV", "CAA"]

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

UBICACIONES_ADC = [
    "VILL-Consulta Externa",
    "VILL-Electrofisiología",
    "VILL-Imagenología",
]


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
    """Devuelve (nombre_estructura, score) del mejor match."""
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
    """Devuelve el nombre real de la columna cuyo nombre normalizado coincide."""
    objetivo = normalizar(nombre_esperado)
    for c in df.columns:
        if normalizar(c) == objetivo:
            return c
    return None


def hash_df(df):
    """Hash estable del contenido del DataFrame (para detectar hojas duplicadas)."""
    return hashlib.md5(
        pd.util.hash_pandas_object(df, index=False).values.tobytes()
    ).hexdigest()


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
    st.subheader("📋 FASE 1 - AMBULATORIO")
    st.dataframe(construir_tabla_resumen(), use_container_width=True)
    st.stop()


@st.cache_data(show_spinner=False)
def leer_excel(file_bytes, file_name):
    """Lee un Excel desde bytes y devuelve {hoja: DataFrame}."""
    import io
    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        return {name: df for name, df in sheets.items() if not df.empty}, None
    except Exception as e:
        return {}, str(e)


# ============================================================
# PROCESAR ARCHIVOS (con detección de duplicados en la fuente)
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

    # --- 1. ¿Archivo repetido? ---
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

        # --- 2. ¿Hoja repetida? (mismo contenido exacto) ---
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
# CÁLCULOS ADC
# ------------------------------------------------------------
# - Revisadas por analistas:
#     "Ubicación de la venta" ∈ {VILL-Consulta Externa,
#                                VILL-Electrofisiología,
#                                VILL-Imagenología}
#     Y "Nombre de Usuario que Verifica" no vacío
#
# - Avaladas subgerencia médica:
#     MISMOS filtros anteriores
#     Y ADEMÁS "Usuario / Sub Medico" no vacío
# ============================================================
conteo_adc_revisadas = 0
conteo_adc_avaladas = 0
df_filtrado_adc = pd.DataFrame()
df_filtrado_avaladas = pd.DataFrame()

if not atenciones_df.empty:
    col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
    col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(atenciones_df, "Usuario / Sub Medico")

    if col_ubicacion is None or col_verifica is None:
        st.error(
            "⚠️ No se encontraron las columnas necesarias en la base "
            "'Atenciones del especialista': "
            f"'Ubicación de la venta'={'OK' if col_ubicacion else 'FALTA'}, "
            f"'Nombre de Usuario que Verifica'={'OK' if col_verifica else 'FALTA'}."
        )
    else:
        # --- Normalizar ubicaciones ---
        ubicaciones_norm = {normalizar(u) for u in UBICACIONES_ADC}
        ubicaciones_serie = (
            atenciones_df[col_ubicacion]
            .astype(str)
            .map(normalizar)
        )

        # --- Verificadores limpios ---
        verificadores_serie = (
            atenciones_df[col_verifica]
            .astype(str)
            .str.strip()
            .replace({"nan": "", "None": "", "NaN": ""})
        )

        # --- Máscara base: ubicación + verificador no vacío ---
        mask_ubicacion = ubicaciones_serie.isin(ubicaciones_norm)
        mask_verifica = verificadores_serie != ""
        mask_revisadas = mask_ubicacion & mask_verifica

        df_filtrado_adc = atenciones_df.loc[mask_revisadas].copy()
        conteo_adc_revisadas = int(mask_revisadas.sum())

        # --- Avaladas: además, "Usuario / Sub Medico" no vacío ---
        if col_submedico is not None:
            submedico_serie = (
                atenciones_df[col_submedico]
                .astype(str)
                .str.strip()
                .replace({"nan": "", "None": "", "NaN": ""})
            )
            mask_submedico = submedico_serie != ""
            mask_avaladas = mask_revisadas & mask_submedico

            df_filtrado_avaladas = atenciones_df.loc[mask_avaladas].copy()
            conteo_adc_avaladas = int(mask_avaladas.sum())
        else:
            st.warning(
                "⚠️ No se encontró la columna 'Usuario / Sub Medico' en la base "
                "'Atenciones del especialista'. No se puede calcular "
                "'Avaladas subgerencia médica'."
            )


# ============================================================
# CÁLCULO ADC: "Dinero enviado por interfaz"
# ------------------------------------------------------------
# Suma de "Valor Total Recalculado" en la base Ventas cuando
# "Centro de costo" coincide (por similitud) con las ubicaciones
# filtradas en Atenciones del especialista.
#
# En Ventas:    "Consulta Externa VILL", "Electrofisiología VILL", ...
# En Atenciones: "VILL-Consulta Externa", "VILL-Electrofisiología", ...
#
# Estrategia: normalizar y comparar por conjunto de palabras
# ignorando la palabra "vill" y el orden.
# ============================================================
conteo_dinero_interfaz = 0.0
df_ventas_adc = pd.DataFrame()


def palabras_clave_ubicacion(texto):
    """Devuelve un frozenset de palabras normalizadas, sin 'vill'."""
    palabras = normalizar(texto).split()
    return frozenset(p for p in palabras if p != "vill")


CLAVES_UBICACION_ADC = {
    palabras_clave_ubicacion(u) for u in UBICACIONES_ADC
}


if bases["Ventas"]:
    ventas_df = pd.concat(
        [df for _, _, df in bases["Ventas"]],
        ignore_index=True
    )

    col_centro = obtener_columna(ventas_df, "Centro de costo")
    col_valor = obtener_columna(ventas_df, "Valor Total Recalculado")

    if col_centro is None or col_valor is None:
        st.warning(
            "⚠️ No se encontraron las columnas 'Centro de costo' o "
            "'Valor Total Recalculado' en la base Ventas."
        )
    else:
        # Palabras clave del Centro de costo en Ventas
        centro_claves = ventas_df[col_centro].astype(str).map(palabras_clave_ubicacion)

        # Máscara: contiene todas las palabras clave de alguna ubicación objetivo
        def coincide(claves_venta):
            for claves_ubi in CLAVES_UBICACION_ADC:
                if claves_venta.issuperset(claves_ubi):
                    return True
            return False

        mask_centro = centro_claves.map(coincide)
        df_ventas_adc = ventas_df.loc[mask_centro].copy()

        # Convertir "Valor Total Recalculado" a numérico
        valores_num = pd.to_numeric(
            df_ventas_adc[col_valor]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.strip(),
            errors="coerce"
        ).fillna(0)

        conteo_dinero_interfaz = float(valores_num.sum())
else:
    ventas_df = pd.DataFrame()


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
# TABLA RESUMEN "FASE 1 - AMBULATORIO"
# ============================================================
st.subheader("📋 FASE 1 - AMBULATORIO")

tabla_resumen = construir_tabla_resumen()
tabla_resumen.loc["Revisadas por analistas", "ADC"] = f"{conteo_adc_revisadas:,}"
tabla_resumen.loc["Avaladas subgerencia médica", "ADC"] = f"{conteo_adc_avaladas:,}"
tabla_resumen.loc["Dinero enviado por interfaz", "ADC"] = f"{conteo_dinero_interfaz:,.0f}"

st.dataframe(tabla_resumen, use_container_width=True, height=380)

csv_resumen = tabla_resumen.to_csv().encode("utf-8")
st.download_button(
    label="⬇️ Descargar tabla resumen (CSV)",
    data=csv_resumen,
    file_name="FASE_1_AMBULATORIO.csv",
    mime="text/csv",
)


# ============================================================
# SECCIÓN DE NOVEDADES
# ============================================================
st.subheader("🔎 Novedades")

if df_filtrado_adc.empty:
    st.info(
        "No hay registros que cumplan los filtros para 'Revisadas por analistas' "
        "(columna ADC)."
    )
else:
    col_verifica = obtener_columna(df_filtrado_adc, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(df_filtrado_adc, "Usuario / Sub Medico")

    st.markdown(
        f"**Total de registros que cumplen los filtros:** {conteo_adc_revisadas:,}  \n"
        f"**Ubicaciones incluidas:** {', '.join(UBICACIONES_ADC)}"
    )

    # Limpiar verificadores
    verificadores_limpios = (
        df_filtrado_adc[col_verifica]
        .astype(str)
        .str.strip()
        .replace({"nan": "", "None": "", "NaN": ""})
    )
    df_filtrado_adc = df_filtrado_adc.assign(_verifica_limpio=verificadores_limpios)

    # Agrupar por verificador
    resumen_verifica = (
        df_filtrado_adc
        .groupby("_verifica_limpio", dropna=False)
        .size()
        .reset_index(name="Registros")
        .rename(columns={"_verifica_limpio": "Nombre de Usuario que Verifica"})
    )

    # Comparación con Sub Médico
    def comparar_con_submedico(nombre_verifica):
        if not col_submedico:
            return "Sin datos de Sub Médico"

        valores_sub = (
            df_filtrado_adc[col_submedico]
            .dropna()
            .astype(str)
            .str.strip()
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

    # Detalle de valores únicos de Sub Médico
    if col_submedico:
        with st.expander("Ver valores únicos en 'Usuario / Sub Medico' (registros filtrados)"):
            valores_sub = (
                df_filtrado_adc[col_submedico]
                .dropna()
                .astype(str)
                .str.strip()
            )
            valores_sub = sorted({
                v for v in valores_sub.unique()
                if v and v.lower() not in ("nan", "none")
            })
            st.write(valores_sub if valores_sub else "Sin valores registrados.")
