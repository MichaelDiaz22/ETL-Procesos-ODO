import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Unir Excel", page_icon="📊", layout="wide")

st.title("📊 Unificador de Archivos Excel")
st.markdown("Carga múltiples archivos Excel con la misma estructura y únelos en una sola base de datos.")

# --- Cargar archivos ---
uploaded_files = st.file_uploader(
    "Selecciona los archivos Excel (.xlsx, .xls)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("👆 Por favor, carga al menos un archivo Excel para comenzar.")
    st.stop()

# --- Leer cada archivo ---
@st.cache_data(show_spinner=False)
def leer_excel(file):
    """Lee un archivo Excel y devuelve un diccionario de {hoja: DataFrame}."""
    try:
        sheets = pd.read_excel(file, sheet_name=None)
        return {name: df for name, df in sheets.items() if not df.empty}
    except Exception as e:
        return {"__error__": str(e)}

archivos_data = {}   # {nombre_archivo: {hoja: df}}
errores = []

with st.spinner("Leyendo archivos..."):
    for f in uploaded_files:
        resultado = leer_excel(f)
        if "__error__" in resultado:
            errores.append((f.name, resultado["__error__"]))
        else:
            archivos_data[f.name] = resultado

# Mostrar errores si hay
if errores:
    for nombre, err in errores:
        st.error(f"❌ Error al leer **{nombre}**: {err}")

if not archivos_data:
    st.warning("No se pudieron leer archivos válidos.")
    st.stop()

# --- Detectar estructura (columnas) de cada archivo/hoja ---
def firma_columnas(df):
    """Devuelve una firma basada en las columnas para agrupar por estructura."""
    return tuple(df.columns.astype(str).tolist())

# Agrupar por estructura: {firma: [(archivo, hoja, df), ...]}
grupos = {}
for archivo, hojas in archivos_data.items():
    for hoja, df in hojas.items():
        firma = firma_columnas(df)
        grupos.setdefault(firma, []).append((archivo, hoja, df))

# --- Mostrar resumen de estructuras detectadas ---
st.subheader("🔍 Estructuras detectadas")
st.write(f"Se encontraron **{len(grupos)}** estructura(s) distinta(s) de datos.")

for i, (firma, items) in enumerate(grupos.items(), start=1):
    with st.expander(f"📁 Estructura #{i} — {len(items)} archivo(s)/hoja(s) — {len(firma)} columnas", expanded=False):
        st.markdown("**Archivos/hojas que pertenecen a esta estructura:**")
        for arch, hoja, _ in items:
            st.write(f"- `{arch}` → hoja: **{hoja}**")
        st.markdown("**Columnas:**")
        st.code(", ".join(firma))

# --- Unir cada grupo y mostrar resumen ---
st.subheader("📋 Bases unificadas")

for i, (firma, items) in enumerate(grupos.items(), start=1):
    st.markdown(f"### 🔗 Base unificada #{i}")

    # Unir todos los DataFrames del grupo
    dfs = [df.assign(_archivo=arch, _hoja=hoja) for arch, hoja, df in items]
    base_unificada = pd.concat(dfs, ignore_index=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Archivos/Hojas", len(items))
    col2.metric("Filas totales", f"{len(base_unificada):,}")
    col3.metric("Columnas", base_unificada.shape[1] - 2)  # -2 por columnas auxiliares

    # Mostrar los primeros 10 registros
    st.markdown("**Vista previa (primeros 10 registros):**")
    st.dataframe(base_unificada.head(10), use_container_width=True)

    # Botón de descarga
    csv = base_unificada.drop(columns=["_archivo", "_hoja"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇️ Descargar base unificada #{i} (CSV)",
        data=csv,
        file_name=f"base_unificada_{i}.csv",
        mime="text/csv",
        key=f"download_{i}"
    )
    st.divider()

# --- Resumen global ---
with st.sidebar:
    st.header("📈 Resumen global")
    total_filas = sum(len(df) for hojas in archivos_data.values() for df in hojas.values())
    total_hojas = sum(len(hojas) for hojas in archivos_data.values())
    st.metric("Archivos cargados", len(archivos_data))
    st.metric("Hojas totales", total_hojas)
    st.metric("Estructuras distintas", len(grupos))
    st.metric("Filas totales", f"{total_filas:,}")
