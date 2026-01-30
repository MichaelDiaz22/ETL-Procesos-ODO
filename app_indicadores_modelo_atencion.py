import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Visor de Datos de Salud", layout="wide")

st.title("📊 Cargador de Registros de Ingresos")
st.markdown("Sube tu archivo Excel para visualizar los primeros 10 registros según la estructura definida.")

# Definimos la lista de columnas esperadas (para referencia o validación futura)
COLUMNAS_ESPERADAS = [
    "EMPRESA", "TIPO DOCUMENTO", "NRO IDENTIFICACIN", "LUGAR EXPEDICION", "PACIENTE",
    "UBICACION", "MUNICIPIO", "TELEFONO PRINCIPAL", "TELEFONO ALTERNTIVO",
    "CODIGO GRUPO ATENCION", "GRUPO ATENCION", "ENTIDAD", "CODIGO CENTRO ATENCION",
    "CENTRO ATENCION", "UNIDAD FUNCIONAL", "NRO INGRESO", "FECHA INGRESO",
    "MES INGRESO", "NRO MES INGRESO", "ESTADO INGRESO", "TIPO INGRESO",
    "CAUSA INGRESO", "FECHA ALTA MEDICA", "CIE10 INGRESO", "DIAGNOSTICO INGRESO",
    "CIE10 EGRESO", "DIAGNOSTICO EGRESO", "CODIGO USUARIO CREA INGRESO",
    "USUARIO CREA INGRESO", "FECHA CREACION", "CODIGO USUARIO MODIFICO",
    "USUARIO MODIFICO", "FECHA MODIFICACION", "UNIDADA FUNCIONAL ACTUAL",
    "OBSERVACIONES", "ENFERMEDAD ACTUAL", "TIPO RIESGO", "INGRESO ALTA MEDICA",
    "DIAS ALTA MEDICA", "FECHA BUSQUEDA", "ULT_ACTUA"
]

# Componente para subir el archivo
uploaded_file = st.file_uploader("Selecciona un archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Leer el archivo Excel
        # Usamos engine='openpyxl' para archivos .xlsx modernos
        df = pd.read_excel(uploaded_file)

        # Mostrar métricas rápidas
        col1, col2 = st.columns(2)
        col1.metric("Total Registros", len(df))
        col2.metric("Total Columnas", len(df.columns))

        st.divider()

        # Mostrar los primeros 10 registros
        st.subheader("🔍 Vista previa: Primeros 10 registros")
        
        # Estilizamos la tabla para que sea más legible
        st.dataframe(df.head(10), use_container_width=True)

        # Validación opcional: Verificar si faltan columnas importantes
        columnas_archivo = set(df.columns)
        columnas_faltantes = [c for c in COLUMNAS_ESPERADAS if c not in columnas_archivo]
        
        if columnas_faltantes:
            st.warning(f"Nota: El archivo no contiene las siguientes columnas: {', '.join(columnas_faltantes)}")
        else:
            st.success("✅ El archivo contiene todas las columnas requeridas.")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")

else:
    st.info("Esperando a que cargues un archivo Excel...")
    # Ejemplo visual de lo que se espera
    st.write("Columnas requeridas:", COLUMNAS_ESPERADAS)
