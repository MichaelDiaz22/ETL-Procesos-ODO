import streamlit as st
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="Unificador Excel", page_icon="📊", layout="wide")

st.title("📊 Unificador de Archivos Excel")
st.markdown("Carga múltiples archivos Excel. Se clasificarán automáticamente en **Ventas**, **Atenciones del especialista** o **Totales**.")

# ============================================================
# ESTRUCTURAS ESPERADAS (columnas mínimas para identificar)
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

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def normalizar(s):
    """Normaliza el nombre de una columna para comparación flexible."""
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

# Precalcular columnas normalizadas por estructura
ESTRUCTURAS_NORM = {
    nombre: {normalizar(c) for c in cols}
    for nombre, cols in ESTRUCTURAS.items()
}

# Umbral mínimo de coincidencia para aceptar una clasificación
UMBRAL_COINCIDENCIA = 0.60  # 60% de columnas esperadas deben estar presentes


def clasificar_estructura(columnas_df):
    """
    Devuelve (nombre_estructura, score) del mejor match.
    Score = fracción de columnas esperadas presentes en el df.
    """
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


def filtrar_columnas_minimas(df, estructura):
    """Conserva solo las columnas que pertenecen a la estructura esperada,
    respetando el orden definido (cuando existan)."""
    esperadas = ESTRUCTURAS[estructura]
    mapa_norm = {normalizar(c): c for c in df.columns}

    columnas_presentes = []
    for col_esperada in esperadas:
        col_norm = normalizar(col_esperada)
        if col_norm in mapa_norm:
            columnas_presentes.append(mapa_norm[col_norm])

    return df[columnas_presentes].copy()


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
    st.stop()


@st.cache_data(show_spinner=False)
def leer_excel(file_bytes, file_name):
    """Lee un Excel y devuelve {hoja: DataFrame}."""
    import io
    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        return {name: df for name, df in sheets.items() if not df.empty}, None
    except Exception as e:
        return {}, str(e)


# ============================================================
# PROCESAR ARCHIVOS: leer + clasificar
# ============================================================
bases = {nombre: [] for nombre in ESTRUCTURAS}  # {estructura: [ (archivo, hoja, df) ]}
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

        df_filtrado = filtrar_columnas_minimas(df, estructura)
        bases[estructura].append((f.name, hoja, df_filtrado))

    progress.progress((idx + 1) / len(uploaded_files))

progress.empty()

# ============================================================
# MOSTRAR ERRORES Y NO CLASIFICADOS
# ============================================================
if errores:
    st.error("### ❌ Errores al leer archivos")
    for nombre, err in errores:
        st.write(f"- **{nombre}**: {err}")

if no_clasificados:
    st.warning("### ⚠️ Archivos/hojas NO clasificados")
    st.dataframe(pd.DataFrame(no_clasificados), use_container_width=True)

# ============================================================
# RESUMEN GLOBAL (SIDEBAR)
# ============================================================
with st.sidebar:
    st.header("📈 Resumen global")
    st.metric("Archivos cargados", len(uploaded_files))
    for nombre in ESTRUCTURAS:
        st.metric(nombre, f"{len(bases[nombre])} hoja(s)")
    if no_clasificados:
        st.metric("No clasificados", len(no_clasificados))

# ============================================================
# MOSTRAR BASES UNIFICADAS POR ESTRUCTURA
# ============================================================
st.subheader("📋 Bases unificadas")

for estructura, items in bases.items():
    st.markdown(f"## 🔗 {estructura}")

    if not items:
        st.info(f"No se encontraron archivos con estructura **{estructura}**.")
        st.divider()
        continue

    # Unir
    dfs = [df.assign(_archivo=arch, _hoja=hoja) for arch, hoja, df in items]
    base_unificada = pd.concat(dfs, ignore_index=True)

    # Métricas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hojas unidas", len(items))
    c2.metric("Filas totales", f"{len(base_unificada):,}")
    c3.metric("Columnas", len(base_unificada.columns) - 2)
    c4.metric("Columnas esperadas", len(ESTRUCTURAS[estructura]))

    # Origen de datos
    with st.expander("📁 Archivos/hojas que componen esta base"):
        st.dataframe(
            pd.DataFrame([{"Archivo": a, "Hoja": h, "Filas": len(d)}
                          for a, h, d in items]),
            use_container_width=True
        )

    # Vista previa: 10 registros
    st.markdown("**Vista previa (primeros 10 registros):**")
    st.dataframe(base_unificada.head(10), use_container_width=True)

    # Descarga CSV
    csv = base_unificada.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇️ Descargar {estructura} (CSV)",
        data=csv,
        file_name=f"{estructura.replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"dl_{estructura}"
    )
    st.divider()
