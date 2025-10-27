import streamlit as st
import pandas as pd
import io

def main():
    st.title("📊 Analizador de Reportes de Llamadas")
    
    # Subir archivo
    uploaded_file = st.file_uploader("Sube tu CSV de llamadas", type=['csv'])
    
    if uploaded_file is not None:
        # Leer y procesar
        csv_content = uploaded_file.read().decode('utf-8-sig')
        df = process_call_reports(csv_content)
        
        if df is not None:
            # Mostrar métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Llamadas", len(df))
            with col2:
                answered = len(df[df['Status'] == 'Answered'])
                st.metric("Contestadas", answered)
            with col3:
                st.metric("Costo Total", f"${df['Cost'].sum():.2f}")
            
            # Filtros
            st.sidebar.header("Filtros")
            direction = st.sidebar.selectbox("Dirección", ['Todos'] + list(df['Direction'].unique()))
            status = st.sidebar.selectbox("Estado", ['Todos'] + list(df['Status'].unique()))
            
            # Aplicar filtros
            filtered_df = df.copy()
            if direction != 'Todos':
                filtered_df = filtered_df[filtered_df['Direction'] == direction]
            if status != 'Todos':
                filtered_df = filtered_df[filtered_df['Status'] == status]
                
            st.dataframe(filtered_df)

if __name__ == "__main__":
    main()
