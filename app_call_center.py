import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

def process_call_reports(csv_content):
    """
    Procesa el archivo CSV de reportes de llamadas
    """
    try:
        # Leer el CSV manejando posibles problemas de encoding y delimitadores
        df = pd.read_csv(
            io.StringIO(csv_content),
            encoding='utf-8-sig',  # Manejar BOM
            delimiter=',',
            quotechar='"',
            skipinitialspace=True,
            low_memory=False
        )
        
        print(f"✅ CSV cargado exitosamente: {len(df)} registros")
        print(f"📊 Columnas disponibles: {list(df.columns)}")
        print(f"📅 Rango temporal: {df['Call Time'].min()} a {df['Call Time'].max()}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error al procesar el CSV: {e}")
        return None

def analyze_call_data(df):
    """
    Realiza análisis básico de los datos de llamadas
    """
    if df is None or df.empty:
        print("No hay datos para analizar")
        return
    
    print("\n" + "="*50)
    print("📈 ANÁLISIS DE REPORTES DE LLAMADAS")
    print("="*50)
    
    # Estadísticas básicas
    total_calls = len(df)
    answered_calls = len(df[df['Status'] == 'Answered'])
    unanswered_calls = len(df[df['Status'] == 'Unanswered'])
    
    print(f"\n📞 ESTADÍSTICAS GENERALES:")
    print(f"   • Total de llamadas: {total_calls}")
    print(f"   • Llamadas contestadas: {answered_calls} ({answered_calls/total_calls*100:.1f}%)")
    print(f"   • Llamadas no contestadas: {unanswered_calls} ({unanswered_calls/total_calls*100:.1f}%)")
    
    # Tipos de llamada
    print(f"\n📊 TIPOS DE LLAMADA:")
    call_types = df['Direction'].value_counts()
    for call_type, count in call_types.items():
        print(f"   • {call_type}: {count} ({count/total_calls*100:.1f}%)")
    
    # Costo total
    total_cost = df['Cost'].sum()
    print(f"\n💰 COSTO TOTAL: ${total_cost:.2f}")
    
    # Llamadas por origen (top 10)
    print(f"\n🏢 TOP 10 ORÍGENES DE LLAMADAS:")
    top_origins = df['From'].value_counts().head(10)
    for origin, count in top_origins.items():
        print(f"   • {origin}: {count} llamadas")
    
    # Análisis por hora
    print(f"\n⏰ DISTRIBUCIÓN POR ESTADO:")
    status_dist = df['Status'].value_counts()
    for status, count in status_dist.items():
        print(f"   • {status}: {count}")

def filter_call_data(df, direction=None, status=None, date_range=None):
    """
    Filtra los datos según criterios específicos
    """
    filtered_df = df.copy()
    
    # Aplicar filtros
    if direction:
        filtered_df = filtered_df[filtered_df['Direction'] == direction]
    
    if status:
        filtered_df = filtered_df[filtered_df['Status'] == status]
    
    if date_range:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['Call Time'] >= start_date) & 
            (filtered_df['Call Time'] <= end_date)
        ]
    
    print(f"📋 Datos después del filtrado: {len(filtered_df)} registros")
    return filtered_df

# EJEMPLO DE USO:
if __name__ == "__main__":
    # Cargar el archivo (aquí necesitarías la ruta real o el contenido)
    try:
        # Si tienes el archivo localmente:
        with open('call_reports.csv', 'r', encoding='utf-8-sig') as file:
            csv_content = file.read()
        
        # Procesar el CSV
        df = process_call_reports(csv_content)
        
        if df is not None:
            # Análisis completo
            analyze_call_data(df)
            
            # Ejemplos de filtrado
            print("\n" + "="*50)
            print("🎯 EJEMPLOS DE FILTRADO")
            print("="*50)
            
            # Solo llamadas salientes contestadas
            outgoing_answered = filter_call_data(df, direction='Outbound', status='Answered')
            print(f"   • Llamadas salientes contestadas: {len(outgoing_answered)}")
            
            # Solo llamadas entrantes
            inbound_calls = filter_call_data(df, direction='Inbound')
            print(f"   • Llamadas entrantes: {len(inbound_calls)}")
            
    except FileNotFoundError:
        print("❌ Archivo no encontrado. Asegúrate de que 'call_reports.csv' esté en el directorio correcto.")
    except Exception as e:
        print(f"❌ Error: {e}")
