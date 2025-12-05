# ELIMINAR REGISTROS DONDE 'Nom. Actividad' SEA 'ADMINISTRACION RADIOTERAPIA' (MÚLTIPLES VARIACIONES)
if 'Nom. Actividad' in df_filtered.columns:
    # Contar registros antes de eliminar
    registros_antes = len(df_filtered)
    
    # Crear una máscara para identificar SOLO ADMINISTRACION RADIOTERAPIA
    # Buscar específicamente "ADMINISTRACION RADIOTERAPIA" o "ADMINISTRACIÓN RADIOTERAPIA"
    # NO incluir solo "RADIOTERAPIA"
    mask_radioterapia = (
        df_filtered['Nom. Actividad'].str.contains('ADMINISTRACION RADIOTERAPIA', case=False, na=False) |
        df_filtered['Nom. Actividad'].str.contains('ADMINISTRACIÓN RADIOTERAPIA', case=False, na=False)
    )
    
    # Opcionalmente, si el código específico "006 - ADMINISTRACION RADIOTERAPIA" está presente:
    # Buscar también por el código específico
    mask_codigo_especifico = df_filtered['Nom. Actividad'].str.contains('006 - ADMINISTRACION RADIOTERAPIA', case=False, na=False)
    
    # Combinar ambas máscaras
    mask_final = mask_radioterapia | mask_codigo_especifico
    
    # Aplicar el filtro inverso (mantener solo los que NO son administración de radioterapia)
    df_filtered = df_filtered[~mask_final]
    
    # Contar registros después de eliminar
    registros_despues = len(df_filtered)
    registros_eliminados = registros_antes - registros_despues
    
    if registros_eliminados > 0:
        st.success(f"✅ Se eliminaron {registros_eliminados} registros de ADMINISTRACIÓN RADIOTERAPIA")
