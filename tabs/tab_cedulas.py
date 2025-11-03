import streamlit as st
import pandas as pd
import plotly.express as px

def mostrar_tab_cedulas(aportaciones):
    """Muestra la pestaña de análisis de cédulas/donantes"""
    cedula_counts = aportaciones['CÉDULA'].value_counts()
    cedula_amounts = aportaciones.groupby('CÉDULA')['MONTO'].sum()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Top 20 Donantes por Monto Total")
        top_amounts = cedula_amounts.nlargest(20)
        amount_data = pd.DataFrame({
            'Cédula': top_amounts.index,
            'Monto Total': top_amounts.values,
            'Cantidad de Donaciones': cedula_counts.loc[top_amounts.index]
        }).reset_index(drop=True)
        amount_data.index = amount_data.index + 1
        
        st.dataframe(
            amount_data,
            column_config={
                "Monto Total": st.column_config.ProgressColumn(
                    "Monto Total (₡)",
                    help="Monto total donado por cada cédula",
                    min_value=0,
                    max_value=int(amount_data['Monto Total'].max()),
                    format="₡%.0f"
                )
            },
            use_container_width=True
        )
        
        st.subheader("Visualización de Donantes")
        
        # Gráfico de dispersión interactivo
        fig_scatter = px.scatter(
            amount_data,
            x='Cantidad de Donaciones',
            y='Monto Total',
            hover_data=['Cédula'],
            title='Relación entre Cantidad de Donaciones y Monto Total',
            labels={'Monto Total': 'Monto Total (₡)', 'Cantidad de Donaciones': 'Número de Donaciones'},
            size='Monto Total',
            color='Cantidad de Donaciones',
            color_continuous_scale='viridis',
            height=500
        )
        fig_scatter.update_layout(showlegend=False)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        st.subheader("Estadísticas de Donantes")
        
        total_donors = len(aportaciones['CÉDULA'].unique())
        repeat_donors = len(cedula_counts[cedula_counts > 1])
        top_donor_amount = cedula_amounts.max()
        top_donor_count = cedula_counts.max()
        
        st.metric("Total Donantes", total_donors)
        st.metric("Donantes Recurrentes", repeat_donors)
        st.metric("Mayor Donación", f"₡{top_donor_amount:,.0f}")
        st.metric("Más Donaciones", f"{top_donor_count} veces")