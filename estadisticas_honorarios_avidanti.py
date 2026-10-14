import streamlit as st
import pandas as pd

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
    """Normaliza strings para comparaciones robustas:
    - Quita tildes y mojibake común
    - Unifica mayúsculas/minúsculas
    - Reemplaza separadores por espacios
    - Colapsa espacios múltiples
    """
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
# PROCESAR ARCHIVOS
# ============================================================
bases = {nombre: [] for nombre in ESTRUCTURAS}
no_clasificados = []
errores = []

progress = st.progress(0, text="Procesando archivos...")

for idx, f in enumerate(uploaded_files):
    hojas, err = leer_excel(f.getvalue(), f.name)
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

        # Conservamos TODAS las columnas originales para no perder información.
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
# ------------------------------------------------------------
# Se añaden columnas de trazabilidad (_archivo, _hoja) y se
# eliminan filas exactamente duplicadas para evitar doble conteo.
# ============================================================
if bases["Atenciones del especialista"]:
    partes = []
    for arch, hoja, df in bases["Atenciones del especialista"]:
        df_aux = df.copy()
        df_aux["_archivo"] = arch
        df_aux["_hoja"] = hoja
        partes.append(df_aux)

    atenciones_df = pd.concat(partes, ignore_index=True)

    # Diagnóstico: filas leídas por archivo/hoja
    diag_filas = (
        atenciones_df
        .groupby(["_archivo", "_hoja"])
        .size()
        .reset_index(name="Filas leídas")
    )

    # Deduplicar filas idénticas (sin contar _archivo ni _hoja)
    cols_datos = [c for c in atenciones_df.columns if c not in ("_archivo", "_hoja")]
    filas_antes = len(atenciones_df)
    atenciones_df = (
        atenciones_df
        .drop_duplicates(subset=cols_datos, keep="first")
        .reset_index(drop=True)
    )
    filas_despues = len(atenciones_df)
    duplicados_eliminados = filas_antes - filas_despues
else:
    atenciones_df = pd.DataFrame()
    diag_filas = pd.DataFrame()
    filas_antes = filas_despues = duplicados_eliminados = 0


# ============================================================
# CÁLCULO: "Revisadas por analistas" (columna ADC)
# ------------------------------------------------------------
# Cuenta registros de "Atenciones del especialista" donde:
#   - "Ubicación de la venta" ∈ {VILL-Consulta Externa,
#                                VILL-Electrofisiología,
#                                VILL-Imagenología}
#   - "Nombre de Usuario que Verifica" no esté vacío
#
# El conteo se hace por filas únicas después de deduplicar.
# ============================================================
conteo_adc = 0
df_filtrado_adc = pd.DataFrame()
diagnostico_adc = {}

if not atenciones_df.empty:
    col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
    col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")

    if col_ubicacion is None or col_verifica is None:
        st.error(
            "⚠️ No se encontraron las columnas necesarias en la base "
            "'Atenciones del especialista': "
            f"'Ubicación de la venta'={'OK' if col_ubicacion else 'FALTA'}, "
            f"'Nombre de Usuario que Verifica'={'OK' if col_verifica else 'FALTA'}."
        )
    else:
        # Normalizar ubicaciones
        ubicaciones_norm = {normalizar(u) for u in UBICACIONES_ADC}
        ubicaciones_serie = (
            atenciones_df[col_ubicacion]
            .astype(str)
            .map(normalizar)
        )

        # Verificadores limpios
        verificadores_serie = (
            atenciones_df[col_verifica]
            .astype(str)
            .str.strip()
            .replace({"nan": "", "None": "", "NaN": ""})
        )

        # Máscaras
        mask_ubicacion = ubicaciones_serie.isin(ubicaciones_norm)
        mask_verifica = verificadores_serie != ""
        mask_final = mask_ubicacion & mask_verifica

        # Filtrado (solo filas únicas)
        df_filtrado_adc = atenciones_df.loc[mask_final].copy()

        # Conteo final
        conteo_adc = int(mask_final.sum())

        # Diagnóstico: desglose por archivo/hoja
        if "_archivo" in df_filtrado_adc.columns:
            diagnostico_adc["Por archivo/hoja"] = (
                df_filtrado_adc
                .groupby(["_archivo", "_hoja"])
                .size()
                .reset_index(name="Registros filtrados")
            )

        # Diagnóstico: desglose por ubicación
        diagnostico_adc["Por ubicación"] = (
            df_filtrado_adc
            .assign(_ubicacion_norm=df_filtrado_adc[col_ubicacion].astype(str).map(normalizar))
            .groupby("_ubicacion_norm")
            .size()
            .reset_index(name="Registros")
            .rename(columns={"_ubicacion_norm": "Ubicación (normalizada)"})
        )


# ============================================================
# RESUMEN GLOBAL (SIDEBAR)
# ============================================================
with st.sidebar:
    st.header("📈 Resumen de carga")
    st.metric("Archivos cargados", len(uploaded_files))
    for nombre in ESTRUCTURAS:
        st.metric(nombre, f"{len(bases[nombre])} hoja(s)")
    if no_clasificados:
        st.metric("No clasificados", len(no_clasificados))


# ============================================================
# TABLA RESUMEN "FASE 1 - AMBULATORIO"
# ============================================================
st.subheader("📋 FASE 1 - AMBULATORIO")

tabla_resumen = construir_tabla_resumen()
tabla_resumen.loc["Revisadas por analistas", "ADC"] = f"{conteo_adc:,}"

st.dataframe(tabla_resumen, use_container_width=True, height=380)

csv_resumen = tabla_resumen.to_csv().encode("utf-8")
st.download_button(
    label="⬇️ Descargar tabla resumen (CSV)",
    data=csv_resumen,
    file_name="FASE_1_AMBULATORIO.csv",
    mime="text/csv",
)


# ============================================================
# DIAGNÓSTICO DE DUPLICADOS
# ============================================================
with st.expander("🧪 Diagnóstico de conteo y duplicados", expanded=False):
    st.markdown("**Resumen de la base Atenciones del especialista:**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Filas leídas (antes de deduplicar)", f"{filas_antes:,}")
    c2.metric("Duplicados exactos eliminados", f"{duplicados_eliminados:,}")
    c3.metric("Filas únicas", f"{filas_despues:,}")

    if not diag_filas.empty:
        st.markdown("**Filas leídas por archivo/hoja (antes de deduplicar):**")
        st.dataframe(diag_filas, use_container_width=True)

    if diagnostico_adc.get("Por archivo/hoja") is not None:
        st.markdown("**Registros que cumplen los filtros ADC, por archivo/hoja:**")
        st.dataframe(diagnostico_adc["Por archivo/hoja"], use_container_width=True)

    if diagnostico_adc.get("Por ubicación") is not None:
        st.markdown("**Registros que cumplen los filtros ADC, por ubicación:**")
        st.dataframe(diagnostico_adc["Por ubicación"], use_container_width=True)

    st.markdown(f"**Conteo final ADC:** {conteo_adc:,}")


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
        f"**Total de registros que cumplen los filtros:** {conteo_adc:,}  \n"
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

    # Comparación con Sub Médico (normalizada)
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
