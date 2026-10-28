import streamlit as st
import pandas as pd
import openpyxl
import io
import zipfile
import xlsxwriter
from datetime import datetime
import datetime as dt
import numpy as np

st.set_page_config(page_title="Excel Data Filtering", layout="wide")

# ============================================================
# BARRA LATERAL: PASO A PASO Y REGLAS PARAMETRIZADAS
# ============================================================
with st.sidebar:
    st.header("📘 Guía de uso")

    with st.expander("📝 Paso a paso: cómo usar la app", expanded=False):
        st.markdown("""
        **1. Cargar el archivo Excel**
        - Sube tu archivo `.xlsx` con el botón **Upload your Excel file**.
        - La app mostrará cuántas filas y columnas se cargaron.

        **2. Revisar información general**
        - Aparecerá el rango de fechas detectado en los datos.

        **3. Seleccionar cantidad de archivos a generar**
        - Usa **Number of output files to generate** para definir cuántos Excel quieres producir.

        **4. Configurar los filtros por archivo**
        - Empresa(s), Sede(s), Ubicación(es), Unidad Funcional(es) y rango de fechas.

        **5. Generar los archivos**
        - Haz clic en **Generate and Download Files**.

        **6. Descargar los Excel**
        - Se generará **un único archivo ZIP** con todos los Excel dentro.
        - Cada Excel tendrá dos hojas: **Base confirmación** y **Pacientes**.
        - Solo necesitas hacer **una descarga** para obtener todos los archivos.
        """)

    with st.expander("⚙️ Reglas parametrizadas en el código", expanded=False):
        st.markdown("""
        ### 🔹 Reglas generales

        **R0. Creación de `Ubicación`** — Consulta / Procedimiento según `Actividad Médica`.

        **R1. Citas duplicadas** — Se eliminan duplicados por `Numero de Identificación + Sede + Fecha` conservando el primero según hora (después de aplicar reglas horarias).

        **R2. Dirección final** — Según `Sede` o `Modalidad == 'Teleconsulta'`.

        **R3. Teléfono de confirmación** — Lógica de móvil/fijo con prefijo `+57`.

        ---
        ### 🔹 Reglas para la sede MARAYA

        **R4. Exclusión** — `HECTOR ARTURO JAIMES` + `IMAGENES DIAGNOSTICAS MARAYA` se elimina.

        **R5. CONTRASTE** — Si `CUPS` + `Descripción Relacionada` contiene "CONTRASTE" → `07:00:00`.

        **R6. Ecografías y Doppler** — Mismo paciente/día/sede con ecografía:
          - 11:00–12:00 → `10:00:00`
          - 16:00–17:00 → `15:00:00`

        **R7. Rayos X** — `PROCEDIMIENTOS DE RAYOS X` entre 16:00–17:00 → `15:00:00`.

        **R8. Sin CONTRASTE** — Entre 16:00–17:00 → `16:00:00`.

        **R9. Hora más temprana** — Para cada grupo paciente/sede/fecha, se toma la hora más temprana resultante y se asigna a todos.

        ---
        ### 🔹 Orden de aplicación
        1. Reglas horarias (R5–R8)
        2. Eliminación de duplicados (R1)
        3. Hora más temprana (R9)
        4. Exclusión (R4)
        """)

# ============================================================
# CONTENIDO PRINCIPAL
# ============================================================
st.title("Excel Data Filtering and Export App")

uploaded_file = st.file_uploader("Upload your Excel file", type=".xlsx")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    df = pd.read_excel(uploaded_file)
    
    st.info(f"📊 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")

    if 'Numero de Identificación' in df.columns:
        df = df.sort_values(by='Numero de Identificación', ascending=True).reset_index(drop=True)

    if 'Actividad Médica' in df.columns:
        df['Actividad Médica_clean'] = df['Actividad Médica'].fillna('').astype(str).str.strip().str.lower()
        df['Ubicación'] = df['Actividad Médica_clean'].apply(
            lambda x: 'Consulta' if x.startswith('consulta') else 'Procedimiento'
        )
        df = df.drop(columns=['Actividad Médica_clean'])
    else:
        df['Ubicación'] = 'Desconocido'

    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y']
    time_formats = ['%H:%M:%S', '%H:%M', '%I:%M %p']

    def parse_datetime_robust(date_str, time_str):
        date_str = str(date_str) if not pd.isna(date_str) else ''
        time_str = str(time_str) if not pd.isna(time_str) else ''
        for d_fmt in date_formats:
            for t_fmt in time_formats:
                try:
                    datetime_str = f"{date_str} {time_str}"
                    return pd.to_datetime(datetime_str, format=f"{d_fmt} {t_fmt}")
                except (ValueError, TypeError):
                    continue
        return pd.NaT

    if 'Fecha Cita' in df.columns and 'Hora Cita' in df.columns:
        df['Fecha Hora Cita'] = df.apply(lambda row: parse_datetime_robust(row['Fecha Cita'], row['Hora Cita']), axis=1)

    def parse_spanish_date(date_str):
        if pd.isna(date_str) or str(date_str).strip() == '':
            return pd.NaT
        date_str = str(date_str).strip().lower()
        months_map = {
            'enero': 'January', 'febrero': 'February', 'marzo': 'March', 'abril': 'April',
            'mayo': 'May', 'junio': 'June', 'julio': 'July', 'agosto': 'August',
            'septiembre': 'September', 'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
        }
        days_map = {
            'lunes': 'Monday', 'martes': 'Tuesday', 'miércoles': 'Wednesday', 'miercoles': 'Wednesday',
            'jueves': 'Thursday', 'viernes': 'Friday', 'sábado': 'Saturday', 'sabado': 'Saturday',
            'domingo': 'Sunday'
        }
        try:
            for day_es, day_en in days_map.items():
                if date_str.startswith(day_es):
                    date_str = date_str.replace(day_es, '').replace(',', '').strip()
                    break
            for month_es, month_en in months_map.items():
                if month_es in date_str:
                    date_str = date_str.replace(month_es, month_en)
                    break
            return pd.to_datetime(date_str, format='%d de %B de %Y')
        except Exception:
            return pd.NaT

    if 'Fecha Programación' in df.columns:
        df['Fecha Programación_dt'] = df['Fecha Programación'].apply(parse_spanish_date)
    else:
        df['Fecha Programación_dt'] = pd.NaT

    if df['Fecha Programación_dt'].isna().all() and 'Fecha Cita' in df.columns:
        df['Fecha Programación_dt'] = df['Fecha Cita'].apply(parse_spanish_date)

    def formato_fecha_espanol(fecha_dt):
        if pd.isna(fecha_dt):
            return ""
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        dia_semana = dias_semana[fecha_dt.weekday()]
        dia = fecha_dt.day
        mes = meses[fecha_dt.month - 1]
        año = fecha_dt.year
        return f"{dia_semana}, {dia} de {mes} de {año}"

    df['Fecha Programación Formateada'] = df['Fecha Programación_dt'].apply(formato_fecha_espanol)

    def convert_decimal_to_time(decimal_time):
        try:
            if pd.isna(decimal_time) or str(decimal_time).strip() in ['', 'nan', 'NaT']:
                return ''
            if isinstance(decimal_time, str) and (':' in decimal_time or 'AM' in decimal_time.upper() or 'PM' in decimal_time.upper()):
                return decimal_time
            decimal_val = float(decimal_time)
            total_minutes = int(decimal_val * 24 * 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            time_obj = dt.time(hours, minutes)
            return time_obj.strftime('%I:%M %p').lstrip('0')
        except (ValueError, TypeError):
            return str(decimal_time)

    if 'Hora Cita' in df.columns:
        df['Hora Cita Formatted'] = df['Hora Cita'].apply(convert_decimal_to_time)
    else:
        df['Hora Cita Formatted'] = ''

    if 'Unidad Funcional' in df.columns:
        investigacion_mask = df['Unidad Funcional'] == 'INVESTIGACION MARAYA'
        df.loc[investigacion_mask, 'Hora Cita Formatted'] = '-'

    direcciones_sede = pd.DataFrame({
        'Sede': [
            'SAN MARCEL MANIZALES', 'CENTENARIO ARMENIA', 'MEDISALUD',
            'CLINICA DE ALTA TECNOLOGIA MARAYA PEREIRA', 'CIRCUNVALAR PEREIRA',
            'CARTAGO UNIDAD ONCOLOGICA CARTAGO', 'CLINICA DE ALTA TECNOLOGIA SEDE ARMENIA ARMENIA',
            'ONCOLOGOS SEDE LA DORADA LA DORADA', 'UDC CLINICA DE ALTA TECNOLOGIA ARMENIA ARMENIA',
            'UDC CLINICA MARAYA PEREIRA', 'UDC CLINICA AVIDANTI MANIZALES',
            'UDC CLINICA LA PRESENTACION MANIZALES', 'UDC SAN MARCEL MANIZALES',
            'CENTRO DE CANCEROLOGIA DE BOYACA TUNJA'
        ],
        'Dirección': [
            'Calle 92 N°  29-75,  SAN MARCEL -  MANIZALES',
            'Carrera 6 A N°  2-63, AVENIDA CENTENARIO -  ARMENIA',
            'Carrera 12 N°  0 NORTE-20, EDIFICIO MEDISALUD 6 PISO -  ARMENIA',
            'Calle 50 N° 13-10, MARAYA - PEREIRA',
            'Carrera 13 N° 1- 46, LA REBECA - PEREIRA',
            'Carrera 2 NORTE N° 23 - 12, BARRIO MILAN - CARTAGO',
            'Calle 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
            'Carrera 4 N° 11-41 CENTRO - LA DORADA',
            'Carrera 1 NORTE  N° 12 - 36, ANTIGUO SALUDCOOP - ARMENIA',
            'Calle 50 N° 13-10, MARAYA - PEREIRA',
            'Calle 10 N° 2C-10B, CLÍNICA AVIDANTI -  MANIZALES',
            'Carrera 23 N° 46 Esquina, CLÍNICA LA PRESENTACIÓN - MANIZALES',
            'Calle 92 N°  29-75,  SAN MARCEL -  MANIZALES',
            'Avenida Universitaria # 46-71 - TUNJA'
        ]
    })

    if 'Sede' in df.columns:
        df = pd.merge(df, direcciones_sede, on='Sede', how='left')

    if 'Dirección' in df.columns:
        df['Direccion Final'] = df['Dirección']
    elif 'Dirección Centro Atención' in df.columns:
        df['Direccion Final'] = df['Dirección Centro Atención']
    else:
        df['Direccion Final'] = ''

    if 'Modalidad' in df.columns:
        df.loc[df['Modalidad'] == 'Teleconsulta', 'Direccion Final'] = 'Teleconsulta'

    for col in ['Nombres', 'Apellidos', 'Actividad Médica', 'Especialista', 'Direccion Final', 'Ubicación']:
        if col in df.columns:
            df[col] = df[col].astype(str)
        else:
            df[col] = ''

    if 'Unidad Funcional' in df.columns:
        df['Unidad Funcional'] = df['Unidad Funcional'].astype(str)

    df['VARIABLE'] = df.apply(
        lambda row: f"{row.get('Nombres','') } {row.get('Apellidos','')}|{row.get('Actividad Médica','')}|{row.get('Fecha Programación Formateada','')}|{row.get('Hora Cita Formatted','')}|{row.get('Especialista','')}|{row.get('Direccion Final','')}",
        axis=1
    )

    if 'Telefono Movil' in df.columns:
        df['Telefono Movil'] = df['Telefono Movil'].astype(str).str.strip()
    else:
        df['Telefono Movil'] = ''

    if 'Telefono Fijo' in df.columns:
        df['Telefono Fijo'] = df['Telefono Fijo'].astype(str).str.strip()
    else:
        df['Telefono Fijo'] = ''

    df['TELEFONO CONFIRMACIÓN'] = 'sin número para enviar mensaje'

    movil_is_empty = (df['Telefono Movil'].isna()) | (df['Telefono Movil'] == '') | (df['Telefono Movil'] == 'nan')
    fijo_is_valid_fallback = (~df['Telefono Fijo'].isna()) & (df['Telefono Fijo'] != '') & (df['Telefono Fijo'] != 'nan') & (~df['Telefono Fijo'].str.startswith('60', na=False))

    df.loc[movil_is_empty & fijo_is_valid_fallback, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_empty & fijo_is_valid_fallback, 'Telefono Fijo']

    movil_is_valid_and_starts_with_3 = (~movil_is_empty) & (~df['Telefono Movil'].str.startswith('60', na=False)) & (df['Telefono Movil'].str.startswith('3', na=False))

    df.loc[movil_is_valid_and_starts_with_3, 'TELEFONO CONFIRMACIÓN'] = '+57' + df.loc[movil_is_valid_and_starts_with_3, 'Telefono Movil']

    df['TELEFONO CONFIRMACIÓN'] = df['TELEFONO CONFIRMACIÓN'].astype(str).str.replace(r'\.0$', '', regex=True)

    def hora_a_decimal(hora_str):
        if pd.isna(hora_str) or hora_str == '' or hora_str == 'nan':
            return 999999
        hora_str = str(hora_str).strip()
        try:
            return float(hora_str)
        except:
            pass
        try:
            hora_lower = hora_str.lower()
            es_pm = 'pm' in hora_lower
            hora_limpia = hora_str.replace('AM', '').replace('PM', '').replace('am', '').replace('pm', '').strip()
            if ':' in hora_limpia:
                partes = hora_limpia.split(':')
                horas = int(partes[0])
                minutos = int(partes[1]) if len(partes) > 1 else 0
            else:
                horas = int(hora_limpia)
                minutos = 0
            if es_pm and horas != 12:
                horas += 12
            elif not es_pm and horas == 12:
                horas = 0
            return horas + minutos / 60.0
        except:
            return 999999

    def hora_formateada_a_decimal(hora_str):
        if pd.isna(hora_str) or str(hora_str).strip() in ('', 'nan', 'NaT', '-'):
            return None
        hora_str = str(hora_str).strip()
        try:
            hora_dt = pd.to_datetime(hora_str, format='%I:%M %p')
            return hora_dt.hour + hora_dt.minute / 60.0
        except Exception:
            try:
                hora_dt = pd.to_datetime(hora_str)
                return hora_dt.hour + hora_dt.minute / 60.0
            except Exception:
                return None

    def decimal_a_hora_formateada(hora_dec):
        if hora_dec is None:
            return ''
        horas = int(hora_dec)
        minutos = int(round((hora_dec - horas) * 60))
        if minutos == 60:
            horas += 1
            minutos = 0
        return f"{horas:02d}:{minutos:02d}:00"

    # ============================================================
    # FUNCIÓN AUXILIAR: Aplicar reglas horarias Maraya sobre un DataFrame
    # ============================================================
    def aplicar_reglas_horarias_maraya(df_in):
        if len(df_in) == 0:
            return df_in
        
        df_out = df_in.copy()
        
        if 'Actividad Médica' in df_out.columns:
            actividad_norm = df_out['Actividad Médica'].fillna('').astype(str).str.upper().str.strip()
        else:
            actividad_norm = pd.Series([''] * len(df_out), index=df_out.index)
        
        cups_col = (
            df_out['CUPS'].fillna('').astype(str).str.upper().str.strip()
            if 'CUPS' in df_out.columns
            else pd.Series([''] * len(df_out), index=df_out.index)
        )
        desc_rel_col = (
            df_out['Descripción Relacionada'].fillna('').astype(str).str.upper().str.strip()
            if 'Descripción Relacionada' in df_out.columns
            else pd.Series([''] * len(df_out), index=df_out.index)
        )
        cups_norm = (cups_col + ' ' + desc_rel_col).str.strip()
        
        if 'Hora Cita Formatted' in df_out.columns:
            horas_decimales = df_out['Hora Cita Formatted'].apply(hora_formateada_a_decimal)
        else:
            horas_decimales = pd.Series([None] * len(df_out), index=df_out.index)
        
        # R5: CONTRASTE -> 07:00:00
        mascara_contraste = cups_norm.str.contains('CONTRASTE', na=False, regex=False)
        if mascara_contraste.any():
            df_out.loc[mascara_contraste, 'Hora Cita Formatted'] = '07:00:00'
            horas_decimales = df_out['Hora Cita Formatted'].apply(hora_formateada_a_decimal)
        
        # R6: Ecografías y Doppler
        mascara_eco = actividad_norm.str.contains(
            'PROCEDIMIENTOS DE ECOGRAFIAS Y DOPPLER', na=False, regex=False
        )
        if not mascara_eco.any():
            mascara_eco = actividad_norm.str.contains(
                'PROCEDIMIENTOS DE ECOGRAFÍAS Y DOPPLER', na=False, regex=False
            )
        
        if (mascara_eco.any() 
            and 'Numero de Identificación' in df_out.columns 
            and 'Sede' in df_out.columns 
            and 'Fecha Programación Formateada' in df_out.columns):
            
            clave_grupo = (
                df_out['Numero de Identificación'].astype(str).str.strip()
                + '|' + df_out['Sede'].astype(str).str.strip()
                + '|' + df_out['Fecha Programación Formateada'].astype(str).str.strip()
            )
            claves_con_eco = set(clave_grupo[mascara_eco].unique())
            mascara_mismo_grupo = clave_grupo.isin(claves_con_eco)
            
            mascara_11_12 = mascara_mismo_grupo & horas_decimales.between(11.0, 12.0, inclusive='both')
            df_out.loc[mascara_11_12, 'Hora Cita Formatted'] = '10:00:00'
            
            mascara_16_17_eco = mascara_mismo_grupo & horas_decimales.between(16.0, 17.0, inclusive='both')
            df_out.loc[mascara_16_17_eco, 'Hora Cita Formatted'] = '15:00:00'
            
            horas_decimales = df_out['Hora Cita Formatted'].apply(hora_formateada_a_decimal)
        
        # R7: Rayos X
        mascara_rayos = actividad_norm.str.contains(
            'PROCEDIMIENTOS DE RAYOS X', na=False, regex=False
        )
        if mascara_rayos.any():
            mascara_16_17_rayos = mascara_rayos & horas_decimales.between(16.0, 17.0, inclusive='both')
            df_out.loc[mascara_16_17_rayos, 'Hora Cita Formatted'] = '15:00:00'
            horas_decimales = df_out['Hora Cita Formatted'].apply(hora_formateada_a_decimal)
        
        # R8: Sin CONTRASTE y 16:00-17:00 -> 16:00:00
        mascara_sin_contraste = ~cups_norm.str.contains('CONTRASTE', na=False, regex=False)
        mascara_16_17_general = mascara_sin_contraste & horas_decimales.between(16.0, 17.0, inclusive='both')
        if mascara_16_17_general.any():
            df_out.loc[mascara_16_17_general, 'Hora Cita Formatted'] = '16:00:00'
        
        return df_out

    # ============================================================
    # FUNCIÓN AUXILIAR: Hora más temprana por grupo (R9)
    # ============================================================
    def aplicar_hora_mas_temprana(df_in):
        if len(df_in) == 0:
            return df_in
        
        df_out = df_in.copy()
        
        if not ('Numero de Identificación' in df_out.columns 
                and 'Sede' in df_out.columns 
                and 'Fecha Programación Formateada' in df_out.columns
                and 'Hora Cita Formatted' in df_out.columns):
            return df_out
        
        horas_decimales = df_out['Hora Cita Formatted'].apply(hora_formateada_a_decimal)
        
        clave_grupo_final = (
            df_out['Numero de Identificación'].astype(str).str.strip()
            + '|' + df_out['Sede'].astype(str).str.strip()
            + '|' + df_out['Fecha Programación Formateada'].astype(str).str.strip()
        )
        
        temp_horas = pd.DataFrame({
            'clave': clave_grupo_final,
            'hora_dec': horas_decimales
        })
        temp_horas_validas = temp_horas.dropna(subset=['hora_dec'])
        
        if len(temp_horas_validas) > 0:
            minimos_por_grupo = temp_horas_validas.groupby('clave')['hora_dec'].min().to_dict()
            nueva_hora_dec = clave_grupo_final.map(minimos_por_grupo)
            mascara_con_minimo = nueva_hora_dec.notna()
            df_out.loc[mascara_con_minimo, 'Hora Cita Formatted'] = (
                nueva_hora_dec[mascara_con_minimo].apply(decimal_a_hora_formateada).values
            )
        
        return df_out

    # ============================================================
    # FUNCIÓN AUXILIAR: Identificar primer servicio (eliminar duplicados)
    # ============================================================
    def identificar_primer_servicio(df_filtrado):
        if len(df_filtrado) == 0:
            return df_filtrado
        df_temp = df_filtrado.copy()
        required_cols = ['Numero de Identificación', 'Fecha Programación_dt', 'Sede', 'Hora Cita']
        for col in required_cols:
            if col not in df_temp.columns:
                st.warning(f"⚠️ No se encontró la columna requerida: {col}")
                return df_temp
        
        # Usar la hora YA FORMATEADA (post-reglas) para ordenar
        df_temp['Hora_para_orden'] = df_temp['Hora Cita Formatted'].apply(hora_formateada_a_decimal)
        df_temp['Hora_para_orden'] = df_temp['Hora_para_orden'].fillna(999999)
        
        df_temp = df_temp.sort_values([
            'Numero de Identificación', 
            'Sede', 
            'Fecha Programación_dt',
            'Hora_para_orden'
        ])
        
        df_temp['clave_duplicado'] = (
            df_temp['Numero de Identificación'].astype(str) + '|' + 
            df_temp['Sede'].astype(str) + '|' + 
            df_temp['Fecha Programación_dt'].astype(str)
        )
        
        df_final = df_temp.drop_duplicates(subset=['clave_duplicado'], keep='first')
        df_final = df_final.drop(columns=['clave_duplicado', 'Hora_para_orden'])
        
        st.success(f"✅ Después de filtrar citas duplicadas: {len(df_final)} filas (se eliminaron {len(df_temp) - len(df_final)} duplicados)")
        return df_final

    all_empresas = df['EMPRESA'].unique().tolist() if 'EMPRESA' in df.columns else []
    all_ubicaciones = df['Ubicación'].unique().tolist() if 'Ubicación' in df.columns else []
    all_sedes = df['Sede'].unique().tolist() if 'Sede' in df.columns else []
    
    if 'Unidad Funcional' in df.columns:
        all_unidades_funcionales = df['Unidad Funcional'].unique().tolist()
    else:
        all_unidades_funcionales = []

    min_date = df['Fecha Programación_dt'].min()
    max_date = df['Fecha Programación_dt'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        st.info(f"📅 Rango de fechas en los datos: {min_date.date()} a {max_date.date()}")
    else:
        st.warning("⚠️ No se pudieron detectar fechas válidas en los datos")

    num_files = st.number_input("Number of output files to generate", min_value=1, value=1, key='num_files_input')

    def get_filtered_options(selected_empresas, selected_sedes=None):
        if not selected_empresas:
            filtered_sedes = all_sedes
            if selected_sedes:
                filtered_df = df[df['Sede'].isin(selected_sedes)]
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_unidades = filtered_df['Unidad Funcional'].unique().tolist()
                else:
                    filtered_unidades = []
            else:
                filtered_unidades = all_unidades_funcionales
        else:
            filtered_df = df[df['EMPRESA'].isin(selected_empresas)]
            filtered_sedes = filtered_df['Sede'].unique().tolist()
            if selected_sedes:
                valid_sedes = [sede for sede in selected_sedes if sede in filtered_sedes]
                if valid_sedes:
                    filtered_df = filtered_df[filtered_df['Sede'].isin(valid_sedes)]
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_unidades = filtered_df['Unidad Funcional'].unique().tolist()
                else:
                    filtered_unidades = []
            else:
                if 'Unidad Funcional' in filtered_df.columns:
                    filtered_unidades = filtered_df['Unidad Funcional'].unique().tolist()
                else:
                    filtered_unidades = []
        return filtered_sedes, filtered_unidades

    filters = []
    for i in range(num_files):
        st.subheader(f"Filters for Output File {i+1}")
        col1, col2 = st.columns(2)
        with col1:
            selected_empresas = st.multiselect(
                f"Select Empresa(s) for File {i+1}", 
                options=all_empresas, 
                key=f"empresa_{i}", 
                default=all_empresas
            )
            filtered_sedes, _ = get_filtered_options(selected_empresas)
            default_sedes = [s for s in filtered_sedes]
            selected_sedes = st.multiselect(
                f"Select Sede(s) for File {i+1}", 
                options=filtered_sedes, 
                key=f"sede_{i}", 
                default=default_sedes
            )
        with col2:
            selected_ubicaciones = st.multiselect(
                f"Select Ubicación(s) for File {i+1}", 
                options=all_ubicaciones, 
                key=f"ubicacion_{i}", 
                default=all_ubicaciones
            )
            _, filtered_unidades = get_filtered_options(selected_empresas, selected_sedes)
            default_unidades = [u for u in filtered_unidades]
            selected_unidades = st.multiselect(
                f"Select Unidad Funcional(es) for File {i+1}", 
                options=filtered_unidades, 
                key=f"unidad_{i}", 
                default=default_unidades
            )

        if pd.notna(min_date) and pd.notna(max_date):
            default_start_date = min_date.date()
            default_end_date = max_date.date()
        else:
            default_start_date = datetime(2025, 10, 15).date()
            default_end_date = datetime(2025, 10, 16).date()

        start_date = st.date_input(f"Select Start Date for File {i+1}", key=f"start_date_{i}", value=default_start_date)
        end_date = st.date_input(f"Select End Date for File {i+1}", key=f"end_date_{i}", value=default_end_date)

        filters.append({
            'empresas': selected_empresas,
            'ubicaciones': selected_ubicaciones,
            'sedes': selected_sedes,
            'unidades_funcionales': selected_unidades,
            'start_date': start_date,
            'end_date': end_date
        })

    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    logs_placeholder = st.empty()
    results_placeholder = st.container()

    if st.button("Generate and Download Files"):
        progress_bar = progress_placeholder.progress(0)
        status_text = status_placeholder.empty()
        
        filtered_dfs = []
        for i, file_filters in enumerate(filters):
            status_text.text(f"Procesando archivo {i+1} de {len(filters)}...")
            
            filtered_df = df.copy()
            mask = pd.Series(True, index=filtered_df.index)
            
            if file_filters['empresas']:
                empresa_mask = filtered_df['EMPRESA'].isin(file_filters['empresas'])
                mask = mask & empresa_mask
            
            if file_filters['ubicaciones']:
                ubicacion_mask = filtered_df['Ubicación'].isin(file_filters['ubicaciones'])
                mask = mask & ubicacion_mask
            
            if file_filters['sedes']:
                sede_mask = filtered_df['Sede'].isin(file_filters['sedes'])
                mask = mask & sede_mask
            
            if file_filters['unidades_funcionales'] and 'Unidad Funcional' in filtered_df.columns:
                unidad_mask = filtered_df['Unidad Funcional'].isin(file_filters['unidades_funcionales'])
                mask = mask & unidad_mask
            
            start_date_ts = pd.Timestamp(file_filters['start_date'])
            end_date_ts = pd.Timestamp(file_filters['end_date'])
            date_mask = (filtered_df['Fecha Programación_dt'] >= start_date_ts) & (filtered_df['Fecha Programación_dt'] <= end_date_ts)
            mask = mask & date_mask
            
            filtered_df = filtered_df.loc[mask].copy()
            
            logs_placeholder.info(f"📁 Archivo {i+1}: {len(filtered_df)} filas después del filtrado inicial")
            
            # ============================================================
            # ORDEN DE APLICACIÓN:
            # 1) Reglas horarias Maraya (R5–R8)
            # 2) Identificar primer servicio / eliminar duplicados (R1)
            # 3) Hora más temprana (R9)
            # 4) Exclusión (R4)
            # ============================================================
            es_maraya = any('MARAYA' in str(s).upper() for s in file_filters['sedes'])
            
            if es_maraya and len(filtered_df) > 0:
                filtered_df = aplicar_reglas_horarias_maraya(filtered_df)
                filtered_df['VARIABLE'] = filtered_df.apply(
                    lambda row: f"{row.get('Nombres','') } {row.get('Apellidos','')}|{row.get('Actividad Médica','')}|{row.get('Fecha Programación Formateada','')}|{row.get('Hora Cita Formatted','')}|{row.get('Especialista','')}|{row.get('Direccion Final','')}",
                    axis=1
                )
            
            filtered_df = identificar_primer_servicio(filtered_df)
            
            if es_maraya and len(filtered_df) > 0:
                filtered_df = aplicar_hora_mas_temprana(filtered_df)
                filtered_df['VARIABLE'] = filtered_df.apply(
                    lambda row: f"{row.get('Nombres','') } {row.get('Apellidos','')}|{row.get('Actividad Médica','')}|{row.get('Fecha Programación Formateada','')}|{row.get('Hora Cita Formatted','')}|{row.get('Especialista','')}|{row.get('Direccion Final','')}",
                    axis=1
                )
            
            if ('Especialista' in filtered_df.columns 
                and 'Unidad Funcional' in filtered_df.columns
                and len(filtered_df) > 0):
                esp_norm = filtered_df['Especialista'].fillna('').astype(str).str.upper().str.strip()
                uf_norm = filtered_df['Unidad Funcional'].fillna('').astype(str).str.upper().str.strip()
                mascara_excluir = (
                    esp_norm.str.contains('HECTOR ARTURO JAIMES', na=False, regex=False) &
                    (uf_norm == 'IMAGENES DIAGNOSTICAS MARAYA')
                )
                if mascara_excluir.any():
                    filtered_df = filtered_df.loc[~mascara_excluir].copy()
                    filtered_df['VARIABLE'] = filtered_df.apply(
                        lambda row: f"{row.get('Nombres','') } {row.get('Apellidos','')}|{row.get('Actividad Médica','')}|{row.get('Fecha Programación Formateada','')}|{row.get('Hora Cita Formatted','')}|{row.get('Especialista','')}|{row.get('Direccion Final','')}",
                        axis=1
                    )

            if 'Fecha Programación_dt' in filtered_df.columns:
                filtered_df = filtered_df.drop(columns=['Fecha Programación_dt'])
            
            filtered_dfs.append((filtered_df, file_filters))
            progress_bar.progress((i + 1) / len(filters))
        
        status_text.text("✅ Procesamiento completado. Generando archivos...")

        # ============================================================
        # GENERACIÓN DEL ZIP CON TODOS LOS EXCEL
        # ============================================================
        zip_buffer = io.BytesIO()
        archivos_generados = []
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, (filtered_df, file_filters) in enumerate(filtered_dfs):
                if len(filtered_df) == 0:
                    archivos_generados.append(f"❌ Archivo {i+1}: sin datos con los filtros aplicados (omitido)")
                    continue
                
                buffer = io.BytesIO()

                base_confirmacion_cols = ['TELEFONO CONFIRMACIÓN', 'VARIABLE']
                pacientes_cols = ['TELEFONO CONFIRMACIÓN', 'Numero de Identificación', 'Nombre completo', 'Especialista', 'Especialidad Cita', 'Sede', 'Direccion Final', 'Fecha Programación Formateada', 'Hora Cita Formatted', 'Actividad Médica']

                if 'Nombre completo' not in filtered_df.columns and 'Nombres' in filtered_df.columns and 'Apellidos' in filtered_df.columns:
                    filtered_df['Nombre completo'] = filtered_df['Nombres'].astype(str) + ' ' + filtered_df['Apellidos'].astype(str)

                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    base_confirmacion_cols_existing = [col for col in base_confirmacion_cols if col in filtered_df.columns]
                    if base_confirmacion_cols_existing:
                        base_confirmacion_df = filtered_df[base_confirmacion_cols_existing]
                        base_confirmacion_df.to_excel(writer, sheet_name='Base confirmación', index=False)

                    pacientes_cols_existing = [col for col in pacientes_cols if col in filtered_df.columns]
                    if pacientes_cols_existing:
                        pacientes_df = filtered_df[pacientes_cols_existing].copy()
                        if 'Hora Cita Formatted' in pacientes_df.columns:
                            pacientes_df = pacientes_df.rename(columns={'Hora Cita Formatted': 'Hora Cita'})
                        if 'Fecha Programación Formateada' in pacientes_df.columns:
                            pacientes_df = pacientes_df.rename(columns={'Fecha Programación Formateada': 'Fecha Programación'})
                        pacientes_df.to_excel(writer, sheet_name='Pacientes', index=False)

                empresas_str = "_".join(file_filters['empresas']) if file_filters['empresas'] else "All_Empresas"
                ubicaciones_str = "_".join(file_filters['ubicaciones']) if file_filters['ubicaciones'] else "All_Ubicaciones"
                
                filename = f"{empresas_str}_Confirmacion_{ubicaciones_str}_{file_filters['start_date'].day}_al_{file_filters['end_date'].day}_{file_filters['start_date'].strftime('%B')}_{file_filters['start_date'].year}.xlsx"

                # Escribir el Excel directamente dentro del ZIP
                zip_file.writestr(filename, buffer.getvalue())
                buffer.close()
                
                archivos_generados.append(f"✅ {filename} ({len(filtered_df)} filas)")
        
        zip_buffer.seek(0)
        
        status_text.text("✅ Archivos generados correctamente")
        
        # Resumen de archivos incluidos
        with results_placeholder:
            st.subheader("📦 Archivos incluidos en el ZIP")
            for msg in archivos_generados:
                st.write(msg)
            
            # Un solo botón de descarga para todos los archivos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"Confirmaciones_ODO_{timestamp}.zip"
            
            num_validos = len([a for a in archivos_generados if a.startswith('✅')])
            
            if num_validos > 0:
                st.download_button(
                    label=f"📥 Descargar todos los archivos ({num_validos} Excel)",
                    data=zip_buffer.getvalue(),
                    file_name=zip_filename,
                    mime="application/zip",
                    key="download_zip_all"
                )
            else:
                st.warning("⚠️ No se generó ningún archivo válido para descargar.")
        
        zip_buffer.close()
