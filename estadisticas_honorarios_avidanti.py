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

# Filtros para "Revisadas por analistas" (columna ADC)
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


def obtener_columna(df, nombre_esperado):
    """Devuelve la columna real del df cuyo nombre normalizado coincide."""
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
    with st.expander("❌ Errores al leer archivos", expanded=False):
        for nombre, err in errores:
            st.write(f"- **{nombre}**: {err}")

if no_clasificados:
    with st.expander("⚠️ Archivos/hojas NO clasificados", expanded=False):
        st.dataframe(pd.DataFrame(no_clasificados), use_container_width=True)

# ============================================================
# CONSTRUIR BASE "ATENCIONES DEL ESPECIALISTA" UNIFICADA
# ============================================================
if bases["Atenciones del especialista"]:
    atenciones_df = pd.concat(
        [df for _, _, df in bases["Atenciones del especialista"]],
        ignore_index=True
    )
else:
    atenciones_df = pd.DataFrame()

# ============================================================
# CÁLCULO: "Revisadas por analistas" (columna ADC)
# ============================================================
conteo_adc = 0
df_filtrado_adc = pd.DataFrame()

if not atenciones_df.empty:
    col_ubicacion = obtener_columna(atenciones_df, "Ubicación de la venta")
    col_verifica = obtener_columna(atenciones_df, "Nombre de Usuario que Verifica")

    if col_ubicacion and col_verifica:
        # Normalizar valores para comparar (trim, sin distinguir mayúsculas)
        ubicaciones_norm = [u.strip().lower() for u in UBICACIONES_ADC]

        mask_ubicacion = (
            atenciones_df[col_ubicacion]
            .astype(str).str.strip().str.lower()
            .isin(ubicaciones_norm)
        )
        mask_verifica = (
            atenciones_df[col_verifica].notna()
            & (atenciones_df[col_verifica].astype(str).str.strip() != "")
            & (atenciones_df[col_verifica].astype(str).str.strip().str.lower() != "nan")
        )

        df_filtrado_adc = atenciones_df[mask_ubicacion & mask_verifica].copy()
        conteo_adc = len(df_filtrado_adc)

# ============================================================
# TABLA RESUMEN
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
# SECCIÓN DE NOVEDADES
# ============================================================
st.subheader("🔎 Novedades")

if df_filtrado_adc.empty:
    st.info("No hay registros que cumplan los filtros para 'Revisadas por analistas' (columna ADC).")
else:
    col_verifica = obtener_columna(df_filtrado_adc, "Nombre de Usuario que Verifica")
    col_submedico = obtener_columna(df_filtrado_adc, "Usuario / Sub Medico")

    st.markdown(
        f"**Total de registros que cumplen los filtros:** {conteo_adc:,}  \n"
        f"**Ubicaciones incluidas:** {', '.join(UBICACIONES_ADC)}"
    )

    # Agrupar por "Nombre de Usuario que Verifica"
    resumen_verifica = (
        df_filtrado_adc
        .groupby(col_verifica, dropna=False)
        .size()
        .reset_index(name="Registros")
        .rename(columns={col_verifica: "Nombre de Usuario que Verifica"})
    )

    # Determinar, por cada verificador, si coincide con algún "Usuario / Sub Medico"
    def comparar_con_submedico(nombre_verifica, sub_df):
        if not col_submedico:
            return "Sin datos de Sub Médico"

        valores_sub = (
            sub_df[col_submedico].dropna().astype(str).str.strip()
        )
        valores_sub = valores_sub[valores_sub != ""]
        valores_sub = valores_sub[valores_sub.str.lower() != "nan"]

        if valores_sub.empty:
            return "Sin datos de Sub Médico"

        nombre_norm = str(nombre_verifica).strip().lower()
        set_sub_norm = {v.lower() for v in valores_sub.unique()}

        return "Misma persona" if nombre_norm in set_sub_norm else "Diferente persona"

    sub_df = df_filtrado_adc[df_filtrado_adc[col_verifica].astype(str).str.strip().str.lower() ==
                             str(resumen_verifica.iloc[0][col_verifica]).strip().lower()] if False else df_filtrado_adc

    resumen_verifica["¿Coincide con Usuario / Sub Médico?"] = resumen_verifica[
        "Nombre de Usuario que Verifica"
    ].apply(lambda n: comparar_con_submedico(n, df_filtrado_adc))

    resumen_verifica = resumen_verifica.sort_values("Registros", ascending=False).reset_index(drop=True)

    st.markdown("#### 👥 Verificadores y comparación con Sub Médico")
    st.dataframe(resumen_verifica, use_container_width=True)

    # Detalle de valores únicos de Sub Médico presentes (para trazabilidad)
    if col_submedico:
        with st.expander("Ver valores únicos en 'Usuario / Sub Medico' (registros filtrados)"):
            valores_sub = (
                df_filtrado_adc[col_submedico].dropna().astype(str).str.strip()
            )
            valores_sub = sorted({v for v in valores_sub.unique() if v and v.lower() != "nan"})
            st.write(valores_sub if valores_sub else "Sin valores registrados.")
