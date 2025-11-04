import streamlit as st

def mostrar_tab_datos(aportaciones):
    """Muestra la pestaña de datos y información general"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Datos de Aportaciones")
        st.dataframe(aportaciones.head(20), use_container_width=True)
        
        csv = aportaciones.to_csv(index=False)
        st.download_button(
            label="Descargar CSV completo",
            data=csv,
            file_name='aportaciones.csv',
            mime='text/csv'
        )
    
    with col2:
        st.subheader("Información General")
        
        st.write("**Resumen del Dataset:**")
        st.write(f"- Total de registros: {len(aportaciones):,}")
        st.write(f"- Columnas: {len(aportaciones.columns)}")
        st.write(f"- Período: {aportaciones['FECHA'].min().strftime('%Y-%m-%d')} a {aportaciones['FECHA'].max().strftime('%Y-%m-%d')}")
        
        st.subheader("Columnas Disponibles")
        for col in aportaciones.columns:
            non_null = aportaciones[col].notna().sum()
            st.write(f"- **{col}**: {non_null:,} valores")
        
    if 'contratos' in st.session_state:
        st.subheader("Datos de Contratos")
        contratos = st.session_state['contratos']
        st.dataframe(contratos.head(10), use_container_width=True)
        
        cedula_contracts = contratos['Cédula Proveedor'].value_counts().head(10)
        st.write("**Top 10 Proveedores por Contratos:**")
        st.dataframe(cedula_contracts.reset_index(), use_container_width=True)