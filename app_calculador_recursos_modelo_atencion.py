import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import re
import calendar
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile
import os

st.set_page_config(page_title="Procesador de Excel", layout="wide")

st.title("📊 Procesador de Archivos Excel")
st.write("Carga un archivo Excel con las hojas: **FECHA DE CITA**, **FECHA DE REGISTRO** y **USUARIOS**")

# Inicializar estado de sesión
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'dfs' not in st.session_state:
    st.session_state.dfs = {}
if 'process_clicked' not in st.session_state:
    st.session_state.process_clicked = False

def convertir_a_hora(valor):
    """
    Convierte diferentes formatos a objeto datetime
    """
    try:
        if pd.isna(valor) or valor == '' or valor is None:
            return None
        
        # Si es un número (formato Excel)
        if isinstance(valor, (int, float)):
            if valor > 40000:
                base_date = datetime(1899, 12, 30)
                fecha_excel = base_date + timedelta(days=valor)
                return fecha_excel
            elif 0 <= valor <= 1:
                total_seconds = valor * 86400
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return datetime(2000, 1, 1, hours, minutes)
        
        # Si es string
        if isinstance(valor, str):
            valor = valor.strip()
            
            formatos = [
                '%H:%M:%S',
                '%H:%M',
                '%I:%M:%S %p',
                '%I:%M %p',
                '%H:%M:%S.%f',
                '%I:%M:%S.%f %p',
                '%H:%M:%S %p',
                '%I:%M:%S.%f',
                '%I:%M'
            ]
            
            for formato in formatos:
                try:
                    return datetime.strptime(valor, formato)
                except:
                    continue
            
            match = re.search(r'(\d{1,2}):(\d{2})', valor)
            if match:
                hora = int(match.group(1))
                minuto = int(match.group(2))
                return datetime(2000, 1, 1, hora, minuto)
            
            return None
        
        if isinstance(valor, (datetime, pd.Timestamp)):
            return valor
        
        if hasattr(valor, 'hour') and hasattr(valor, 'minute'):
            return datetime(2000, 1, 1, valor.hour, valor.minute)
        
        if isinstance(valor, timedelta):
            total_seconds = valor.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return datetime(2000, 1, 1, hours, minutes)
        
        return None
    except Exception as e:
        return None

def extraer_hora_de_fecha(fecha_datetime):
    """
    Extrae solo la hora de un objeto datetime
    """
    if fecha_datetime is None:
        return None
    return datetime(2000, 1, 1, fecha_datetime.hour, fecha_datetime.minute)

def redondear_hora_5_minutos(hora_str):
    """
    Redondea una hora al siguiente intervalo de 5 minutos
    """
    try:
        if pd.isna(hora_str) or hora_str is None:
            return None
        hora_dt = datetime.strptime(hora_str, '%H:%M')
        minutos = hora_dt.minute
        # Redondear hacia arriba al siguiente múltiplo de 5
        minutos_redondeados = ((minutos + 4) // 5) * 5
        if minutos_redondeados >= 60:
            hora_dt = hora_dt.replace(hour=hora_dt.hour + 1, minute=0)
        else:
            hora_dt = hora_dt.replace(minute=minutos_redondeados)
        return hora_dt.strftime('%H:%M')
    except:
        return hora_str

def generar_tabla_horas():
    """
    Genera una tabla con las horas desde 06:30 hasta 19:00 cada 5 minutos
    """
    horas = []
    hora_actual = datetime(2000, 1, 1, 6, 30)
    hora_fin = datetime(2000, 1, 1, 19, 0)
    
    while hora_actual <= hora_fin:
        horas.append(hora_actual.strftime('%H:%M'))
        hora_actual += timedelta(minutes=5)
    
    return pd.DataFrame({'Hora': horas})

def contar_dias_mes(fecha):
    """
    Cuenta cuántos días del mismo día de la semana tiene el mes
    """
    try:
        dia_semana = fecha.weekday()
        mes = fecha.month
        año = fecha.year
        
        # Contar cuántos días del mismo día de la semana hay en el mes
        count = 0
        for dia in range(1, calendar.monthrange(año, mes)[1] + 1):
            fecha_temp = datetime(año, mes, dia)
            if fecha_temp.weekday() == dia_semana:
                count += 1
        return count
    except:
        return 1

def convertir_fecha(fecha_valor):
    """
    Convierte diferentes formatos de fecha a datetime
    """
    try:
        if pd.isna(fecha_valor):
            return None
        # Si es número (formato Excel)
        if isinstance(fecha_valor, (int, float)):
            if fecha_valor > 40000:
                base_date = datetime(1899, 12, 30)
                return base_date + timedelta(days=fecha_valor)
        # Si es string
        if isinstance(fecha_valor, str):
            formatos = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y']
            for formato in formatos:
                try:
                    return datetime.strptime(fecha_valor, formato)
                except:
                    continue
        # Si ya es datetime
        if isinstance(fecha_valor, (datetime, pd.Timestamp)):
            return fecha_valor
        return None
    except:
        return None

def procesar_datos(df_cita, df_registro, df_usuarios, unidades_seleccionadas):
    """
    Procesa los datos filtrando por unidades funcionales y estado cumplida
    """
    # Filtrar por unidades funcionales seleccionadas
    df_cita_filtrado = df_cita[df_cita['unidad funcional'].isin(unidades_seleccionadas)].copy()
    df_registro_filtrado = df_registro[df_registro['unidad funcional'].isin(unidades_seleccionadas)].copy()
    
    # Filtrar FECHA DE CITA por estado "Cumplida"
    df_cita_filtrado = df_cita_filtrado[df_cita_filtrado['estado cita'] == 'Cumplida'].copy()
    
    # Cruzar datos de usuarios
    usuario_rol_map = dict(zip(df_usuarios['usuario registra'], df_usuarios['rol']))
    df_cita_filtrado['rol'] = df_cita_filtrado['usuario registra'].map(usuario_rol_map)
    df_registro_filtrado['rol'] = df_registro_filtrado['usuario registra'].map(usuario_rol_map)
    
    # Calcular hora ingreso a cita (hora inicio cita - 30 minutos)
    def calcular_hora_ingreso(hora_valor):
        try:
            hora_dt = convertir_a_hora(hora_valor)
            if hora_dt is None:
                return None
            hora_solo = extraer_hora_de_fecha(hora_dt)
            if hora_solo is None:
                return None
            nueva_hora = hora_solo - timedelta(minutes=30)
            return nueva_hora.strftime('%H:%M')
        except Exception as e:
            return None
    
    df_cita_filtrado['hora ingreso a cita'] = df_cita_filtrado['hora inicio cita'].apply(calcular_hora_ingreso)
    
    # Redondear hora ingreso a cita al siguiente intervalo de 5 minutos
    df_cita_filtrado['hora ingreso redondeada'] = df_cita_filtrado['hora ingreso a cita'].apply(redondear_hora_5_minutos)
    
    # Calcular hora entrega documentos
    def convertir_hora_entrega(hora_valor):
        try:
            hora_dt = convertir_a_hora(hora_valor)
            if hora_dt is None:
                return None
            hora_solo = extraer_hora_de_fecha(hora_dt)
            if hora_solo is None:
                return None
            return hora_solo.strftime('%H:%M')
        except Exception as e:
            return None
    
    df_cita_filtrado['hora entrega documentos'] = df_cita_filtrado['hora final cita'].apply(convertir_hora_entrega)
    
    # Convertir fecha cita a datetime
    df_cita_filtrado['fecha_cita_dt'] = df_cita_filtrado['fecha cita'].apply(convertir_fecha)
    
    # Eliminar registros con fecha inválida
    df_cita_filtrado = df_cita_filtrado.dropna(subset=['fecha_cita_dt'])
    
    # Agregar información de fecha
    df_cita_filtrado['dia_semana'] = df_cita_filtrado['fecha_cita_dt'].dt.weekday
    df_cita_filtrado['mes'] = df_cita_filtrado['fecha_cita_dt'].dt.month
    df_cita_filtrado['año'] = df_cita_filtrado['fecha_cita_dt'].dt.year
    
    return df_cita_filtrado, df_registro_filtrado

def agregar_columnas_adicionales(df, unidades_seleccionadas):
    """
    Agrega las columnas de Tiempo atención, Total pacientes en cola, Total tiempo requerido y Recurso a necesidad
    """
    df_resultado = df.copy()
    
    # 1. Agregar columnas de Tiempo atención para cada unidad
    for unidad in unidades_seleccionadas:
        columna_conteo = f'En cola de admisiones {unidad}'
        columna_tiempo = f'Tiempo atención {unidad}'
        if columna_conteo in df_resultado.columns:
            df_resultado[columna_tiempo] = df_resultado[columna_conteo] * 2.5
        else:
            df_resultado[columna_tiempo] = 0
    
    # 2. Agregar columna Total pacientes en cola (suma de todos los conteos)
    columnas_conteo = [f'En cola de admisiones {unidad}' for unidad in unidades_seleccionadas if f'En cola de admisiones {unidad}' in df_resultado.columns]
    if columnas_conteo:
        df_resultado['Total pacientes en cola'] = df_resultado[columnas_conteo].sum(axis=1)
    else:
        df_resultado['Total pacientes en cola'] = 0
    
    # 3. Agregar columna Total tiempo requerido del segmento (suma de todos los tiempos)
    columnas_tiempo = [f'Tiempo atención {unidad}' for unidad in unidades_seleccionadas if f'Tiempo atención {unidad}' in df_resultado.columns]
    if columnas_tiempo:
        df_resultado['Total tiempo requerido del segmento (mins)'] = df_resultado[columnas_tiempo].sum(axis=1)
    else:
        df_resultado['Total tiempo requerido del segmento (mins)'] = 0
    
    # 4. Agregar columna Recurso a necesidad (Total pacientes en cola / 1.72)
    if 'Total pacientes en cola' in df_resultado.columns:
        df_resultado['Recurso a necesidad'] = df_resultado['Total pacientes en cola'] / 1.72
    else:
        df_resultado['Recurso a necesidad'] = 0
    
    return df_resultado

def generar_grafico_matplotlib(df, titulo, guardar=False, ruta=None):
    """
    Genera un gráfico de líneas con matplotlib mostrando todos los datos sin agrupar
    con etiquetas legibles (mostrando cada 30 minutos)
    """
    try:
        if df.empty or 'Recurso a necesidad' not in df.columns:
            fig, ax = plt.subplots(figsize=(14, 5))
            ax.text(0.5, 0.5, 'No hay datos disponibles para graficar', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=14)
            ax.set_title(titulo)
            ax.set_xlabel('Hora')
            ax.set_ylabel('Recurso a necesidad')
            plt.tight_layout()
            if guardar and ruta:
                plt.savefig(ruta, dpi=100, bbox_inches='tight')
                plt.close()
            return fig
        
        df_grafico = df.copy()
        df_grafico = df_grafico[df_grafico['Recurso a necesidad'] > 0]
        
        if df_grafico.empty:
            fig, ax = plt.subplots(figsize=(14, 5))
            ax.text(0.5, 0.5, 'No hay datos con valores positivos para graficar', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=14)
            ax.set_title(titulo)
            ax.set_xlabel('Hora')
            ax.set_ylabel('Recurso a necesidad')
            plt.tight_layout()
            if guardar and ruta:
                plt.savefig(ruta, dpi=100, bbox_inches='tight')
                plt.close()
            return fig
        
        fig, ax = plt.subplots(figsize=(14, 5))
        
        ax.plot(df_grafico['Hora'], df_grafico['Recurso a necesidad'], 
                marker='o', linewidth=2, markersize=4, 
                color='#E84A5F', label='Recurso a necesidad')
        
        ax.set_xlabel('Hora', fontsize=11)
        ax.set_ylabel('Recurso a necesidad', fontsize=11)
        ax.set_title(titulo, fontsize=13, fontweight='bold')
        
        # Configurar ticks cada 30 minutos
        tick_positions = []
        tick_labels = []
        hora_actual = datetime(2000, 1, 1, 6, 30)
        hora_fin = datetime(2000, 1, 1, 19, 0)
        
        while hora_actual <= hora_fin:
            hora_str = hora_actual.strftime('%H:%M')
            tick_positions.append(hora_str)
            tick_labels.append(hora_str)
            hora_actual += timedelta(minutes=30)
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=9)
        
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        if guardar and ruta:
            plt.savefig(ruta, dpi=100, bbox_inches='tight')
            plt.close()
        
        return fig
    except Exception as e:
        st.error(f"Error al generar gráfico: {str(e)}")
        return None

def generar_tablas_resumen(df_cita_proc, unidades_seleccionadas):
    """
    Genera las tablas de resumen por día de la semana y promedio
    """
    # Nombres de los días de la semana
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    # Generar tabla base de horas (cada 5 minutos)
    df_base = generar_tabla_horas()
    
    # Diccionario para almacenar las tablas
    tablas = {}
    
    # Procesar por cada día de la semana
    for dia_idx, dia_nombre in enumerate(dias_semana):
        # Filtrar por día de la semana
        df_dia = df_cita_proc[df_cita_proc['dia_semana'] == dia_idx].copy()
        
        if len(df_dia) == 0:
            # Si no hay datos para este día, crear tabla vacía
            df_resultado = df_base.copy()
            for unidad in unidades_seleccionadas:
                df_resultado[f'En cola de admisiones {unidad}'] = 0
            df_resultado = agregar_columnas_adicionales(df_resultado, unidades_seleccionadas)
            tablas[dia_nombre] = df_resultado
            continue
        
        # Crear tabla de resumen para este día
        df_resultado = df_base.copy()
        
        # Para cada unidad funcional
        for unidad in unidades_seleccionadas:
            # Filtrar por unidad
            df_unidad = df_dia[df_dia['unidad funcional'] == unidad].copy()
            
            if len(df_unidad) == 0:
                df_resultado[f'En cola de admisiones {unidad}'] = 0
                continue
            
            # Crear llave única combinando: mes + profesional + centro de atención
            df_unidad['mes'] = df_unidad['fecha_cita_dt'].dt.month
            df_unidad['año'] = df_unidad['fecha_cita_dt'].dt.year
            df_unidad['llave_unica'] = df_unidad['año'].astype(str) + '-' + \
                                       df_unidad['mes'].astype(str) + '_' + \
                                       df_unidad['profesional'].astype(str) + '_' + \
                                       df_unidad['centro de atencion'].astype(str)
            
            # Identificar registros únicos por llave y hora redondeada
            df_unicos = df_unidad.drop_duplicates(subset=['llave_unica', 'hora ingreso redondeada'])
            
            # Calcular días del mismo día de semana en el mes para cada fecha
            df_unicos['dias_mes'] = df_unicos['fecha_cita_dt'].apply(contar_dias_mes)
            
            # Calcular el peso de cada registro único (1 / dias_mes)
            df_unicos['peso_registro'] = 1 / df_unicos['dias_mes']
            
            # Agrupar por hora redondeada, sumando los pesos
            df_horas = df_unicos.groupby('hora ingreso redondeada')['peso_registro'].sum().reset_index()
            
            # Mapear los valores a las horas
            df_resultado[f'En cola de admisiones {unidad}'] = df_resultado['Hora'].map(
                dict(zip(df_horas['hora ingreso redondeada'], df_horas['peso_registro']))
            ).fillna(0)
        
        # Agregar columnas adicionales
        df_resultado = agregar_columnas_adicionales(df_resultado, unidades_seleccionadas)
        tablas[dia_nombre] = df_resultado
    
    # Generar tabla de Promedio
    df_promedio = df_base.copy()
    for unidad in unidades_seleccionadas:
        valores_unidad = []
        for dia in dias_semana:
            if dia in tablas and f'En cola de admisiones {unidad}' in tablas[dia].columns:
                valores_unidad.append(tablas[dia][f'En cola de admisiones {unidad}'])
        
        if valores_unidad:
            df_promedio[f'En cola de admisiones {unidad}'] = sum(valores_unidad) / len(valores_unidad)
        else:
            df_promedio[f'En cola de admisiones {unidad}'] = 0
    
    df_promedio = agregar_columnas_adicionales(df_promedio, unidades_seleccionadas)
    tablas['Promedio'] = df_promedio
    
    return tablas

def exportar_excel_con_graficos(tablas, df_cita_proc, titulos_graficos):
    """
    Exporta todas las tablas y gráficos a un archivo Excel
    """
    import tempfile
    import os
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils.dataframe import dataframe_to_rows
    import matplotlib.pyplot as plt
    
    # Crear un archivo temporal para guardar los gráficos
    temp_dir = tempfile.mkdtemp()
    imagenes_paths = []
    
    # Generar y guardar gráficos como imágenes
    for nombre_tab, df in tablas.items():
        if nombre_tab != 'Promedio':
            titulo = f"{nombre_tab} - Recurso a necesidad por hora"
            ruta_imagen = os.path.join(temp_dir, f"{nombre_tab}.png")
            fig = generar_grafico_matplotlib(df, titulo, guardar=True, ruta=ruta_imagen)
            if fig:
                imagenes_paths.append((nombre_tab, ruta_imagen))
    
    # Crear el archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Escribir cada tabla en una hoja
        for nombre, df in tablas.items():
            df.to_excel(writer, sheet_name=nombre, index=False)
        
        # Escribir datos procesados
        df_cita_proc.to_excel(writer, sheet_name='CITAS_FILTRADAS', index=False)
        
        # Obtener el workbook para insertar imágenes
        workbook = writer.book
        
        # Insertar gráficos en hojas correspondientes
        for nombre_tab, ruta_imagen in imagenes_paths:
            if nombre_tab in workbook.sheetnames:
                ws = workbook[nombre_tab]
                # Insertar imagen debajo de los datos
                img = XLImage(ruta_imagen)
                # Calcular posición (debajo de los datos)
                df = tablas[nombre_tab]
                row_offset = len(df) + 5  # 5 filas de espacio después de los datos
                img.anchor = f'A{row_offset}'
                ws.add_image(img)
    
    # Limpiar archivos temporales
    for _, path in imagenes_paths:
        try:
            os.remove(path)
        except:
            pass
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    return output

# Cargar archivo
uploaded_file = st.file_uploader(
    "Selecciona un archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las hojas: FECHA DE CITA, FECHA DE REGISTRO y USUARIOS"
)

if uploaded_file is not None:
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        required_sheets = ['FECHA DE CITA', 'FECHA DE REGISTRO', 'USUARIOS']
        missing_sheets = [sheet for sheet in required_sheets if sheet not in sheet_names]
        
        if missing_sheets:
            st.error(f"❌ Faltan las siguientes hojas en el archivo: {', '.join(missing_sheets)}")
            st.info(f"Hojas encontradas: {', '.join(sheet_names)}")
        else:
            df_cita = pd.read_excel(uploaded_file, sheet_name='FECHA DE CITA')
            df_registro = pd.read_excel(uploaded_file, sheet_name='FECHA DE REGISTRO')
            df_usuarios = pd.read_excel(uploaded_file, sheet_name='USUARIOS')
            
            st.session_state.dfs = {
                'FECHA DE CITA': df_cita,
                'FECHA DE REGISTRO': df_registro,
                'USUARIOS': df_usuarios
            }
            st.session_state.data_loaded = True
            st.session_state.process_clicked = False
            
            st.success("✅ Archivo cargado correctamente")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📋 FECHA DE CITA", f"{len(df_cita)} registros")
            with col2:
                st.metric("📋 FECHA DE REGISTRO", f"{len(df_registro)} registros")
            with col3:
                st.metric("👥 USUARIOS", f"{len(df_usuarios)} registros")
            
            # Obtener unidades funcionales
            unidades_cita = set(df_cita['unidad funcional'].dropna().unique())
            unidades_registro = set(df_registro['unidad funcional'].dropna().unique())
            unidades_disponibles = sorted(list(unidades_cita.union(unidades_registro)))
            
            st.subheader("🏥 Selección de Unidades Funcionales")
            unidades_seleccionadas = st.multiselect(
                "Selecciona una o más unidades funcionales:",
                options=unidades_disponibles,
                help="Puedes seleccionar múltiples unidades funcionales"
            )
            
            if unidades_seleccionadas:
                st.info(f"✅ {len(unidades_seleccionadas)} unidad(es) funcional(es) seleccionada(s)")
            else:
                st.warning("⚠️ Por favor, selecciona al menos una unidad funcional")
            
            if st.button("🔄 Procesar", type="primary", use_container_width=True):
                if not unidades_seleccionadas:
                    st.error("❌ Debes seleccionar al menos una unidad funcional")
                else:
                    with st.spinner("Procesando datos..."):
                        df_cita_proc, df_registro_proc = procesar_datos(
                            df_cita, df_registro, df_usuarios, unidades_seleccionadas
                        )
                        
                        tablas_resumen = generar_tablas_resumen(df_cita_proc, unidades_seleccionadas)
                        
                        st.session_state.dfs_procesados = {
                            'TABLAS': tablas_resumen,
                            'CITA_PROCESADA': df_cita_proc,
                            'REGISTRO_PROCESADO': df_registro_proc
                        }
                        st.session_state.process_clicked = True
                        st.session_state.unidades_seleccionadas = unidades_seleccionadas
                    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")
        st.exception(e)

# Mostrar resumen
if st.session_state.process_clicked and st.session_state.data_loaded:
    if 'dfs_procesados' in st.session_state:
        st.divider()
        
        st.subheader("🔍 Filtros Aplicados")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Unidades Funcionales:** {', '.join(st.session_state.unidades_seleccionadas)}")
        
        st.header("📊 Tablas de Resumen")
        
        tablas = st.session_state.dfs_procesados['TABLAS']
        
        # Crear pestañas: Lunes a Viernes y Promedio (sin Resumen Ejecutivo)
        nombres_tabs = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Promedio']
        tabs = st.tabs(nombres_tabs)
        
        for i, tab in enumerate(tabs):
            with tab:
                nombre_tab = nombres_tabs[i]
                df = tablas[nombre_tab]
                
                st.subheader(f"📊 {nombre_tab}")
                
                # Mostrar estadísticas
                if 'Recurso a necesidad' in df.columns:
                    max_recurso = df['Recurso a necesidad'].max()
                    min_recurso = df['Recurso a necesidad'].min()
                    hora_max = df.loc[df['Recurso a necesidad'].idxmax(), 'Hora'] if max_recurso > 0 else "N/A"
                    hora_min = df.loc[df['Recurso a necesidad'].idxmin(), 'Hora'] if min_recurso > 0 else "N/A"
                else:
                    max_recurso = 0
                    min_recurso = 0
                    hora_max = "N/A"
                    hora_min = "N/A"
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if 'Total pacientes en cola' in df.columns:
                        total = df['Total pacientes en cola'].sum()
                    else:
                        total = 0
                    st.metric("Total Pacientes en Cola", f"{total:.1f}")
                with col2:
                    st.metric("Máximo Recurso Necesario", f"{max_recurso:.1f}", delta=f"a las {hora_max}")
                with col3:
                    st.metric("Mínimo Recurso Necesario", f"{min_recurso:.1f}", delta=f"a las {hora_min}")
                with col4:
                    if 'Recurso a necesidad' in df.columns:
                        hora_pico = df.loc[df['Recurso a necesidad'].idxmax(), 'Hora'] if df['Recurso a necesidad'].max() > 0 else "N/A"
                    else:
                        hora_pico = "N/A"
                    st.metric("Hora Pico", hora_pico)
                
                st.dataframe(df, use_container_width=True, height=400)
                
                st.subheader("📈 Evolución del Recurso a Necesidad")
                fig = generar_grafico_matplotlib(df, f"{nombre_tab} - Recurso a necesidad por hora")
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)
        
        # Opción para descargar todas las tablas con gráficos
        st.divider()
        st.subheader("📥 Descargar Tablas de Resumen con Gráficos")
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("📥 Descargar Excel con Gráficos", use_container_width=True):
                with st.spinner("Generando archivo Excel con gráficos..."):
                    # Exportar Excel con gráficos
                    output = exportar_excel_con_graficos(
                        tablas, 
                        st.session_state.dfs_procesados['CITA_PROCESADA'],
                        [f"{nombre} - Recurso a necesidad por hora" for nombre in nombres_tabs]
                    )
                    
                    st.download_button(
                        label="📥 Descargar Tablas con Gráficos (Excel)",
                        data=output,
                        file_name="tablas_resumen_con_graficos.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

elif st.session_state.data_loaded and not st.session_state.process_clicked:
    st.info("📌 Selecciona las unidades funcionales y haz clic en el botón 'Procesar' para generar las tablas de resumen")

else:
    st.info("📂 Por favor, carga un archivo Excel para comenzar")
