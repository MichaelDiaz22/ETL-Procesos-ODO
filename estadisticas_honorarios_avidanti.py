import streamlit as st
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="FASE 1 - AMBULATORIO", page_icon="📊", layout="wide")

st.title("📊 FASE 1 - AMBULATORIO")
st.markdown("Carga múltiples archivos Excel. Se clasificarán automáticamente en **Ventas**, **Atenciones del especialista** o **Totales**.")

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
# TABLA RESUMEN "FASE 1 - AMBULATORIO"
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

def construir_tabla_resumen():
    """Crea un DataFrame vacío con las columnas y filas del resumen FASE 1."""
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


def filtrar_columnas_minimas(df, estructura):
    esperadas = ESTRUCTURAS[estructura]
    mapa_norm = {normalizar(c): c for c in df.columns}
    columnas_presentes = [
        mapa_norm[normalizar(c)] for c in esperadas
        if normalizar(c) in mapa_norm
    ]
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
    # Aún así mostramos la tabla resumen vacía
    st.subheader("📋 FASE 1 - AMBULATORIO")
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
# ERRORES Y NO CLASIFICADOS
# ============================================================
if errores:
    with st.expander("❌ Errores al leer archivos", expanded=True):
        for nombre, err in errores:
            st.write(f"- **{nombre}**: {err}")

if no_clasificados:
    with st.expander("⚠️ Archivos/hojas NO clasificados", expanded=True):
        st.dataframe(pd.DataFrame(no_clasificados), use_container_width=True)

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
st.dataframe(tabla_resumen, use_container_width=True, height=380)

# Botón de descarga del esqueleto
csv_resumen = tabla_resumen.to_csv().encode("utf-8")
st.download_button(
    label="⬇️ Descargar tabla resumen (CSV)",
    data=csv_resumen,
    file_name="FASE_1_AMBULATORIO.csv",
    mime="text/csv",
)
