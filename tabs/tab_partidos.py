import streamlit as st
import pandas as pd
import plotly.express as px

def mostrar_tab_partidos(aportaciones, party_colors):
    """Muestra la pestaña de análisis de partidos políticos"""
    st.header("Análisis de Partidos Políticos")
    
    active_aportaciones = aportaciones[~aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)]
    party_contributions_count = active_aportaciones['PARTIDO POLÍTICO'].value_counts()
    top_20 = party_contributions_count.head(20)
    
    aportaciones_valid_dates = aportaciones.dropna(subset=['FECHA'])
    aportaciones_valid_dates['MONTH_YEAR'] = aportaciones_valid_dates['FECHA'].dt.to_period('M')
    monthly_income = aportaciones_valid_dates.groupby(['PARTIDO POLÍTICO', 'MONTH_YEAR'])['MONTO'].sum().reset_index()
    monthly_income['MONTH_YEAR'] = monthly_income['MONTH_YEAR'].dt.to_timestamp()
    
    top_parties_list = top_20.index.tolist()
    monthly_income_filtered = monthly_income[monthly_income['PARTIDO POLÍTICO'].isin(top_parties_list)].copy()
    monthly_income_filtered['MONTO'] = monthly_income_filtered['MONTO'] / 1_000_000
    monthly_income_filtered['YEAR'] = monthly_income_filtered['MONTH_YEAR'].dt.to_period('Y').astype(str)
    
    yearly_income = monthly_income_filtered.groupby(['PARTIDO POLÍTICO', 'YEAR'])['MONTO'].sum().reset_index()
            
    st.subheader("Ingresos Anuales por Partido")
    # Gráfico interactivo con Plotly y colores consistentes
    fig_income = px.bar(
        yearly_income, 
        x='YEAR', 
        y='MONTO', 
        color='PARTIDO POLÍTICO',
        color_discrete_map=party_colors,
        labels={'MONTO': 'Ingresos (Millones ₡)', 'YEAR': 'Año'},
        height=500
    )
    fig_income.update_layout(
        xaxis_tickangle=-45,
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
    )
    st.plotly_chart(fig_income, use_container_width=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Distribución de Aportaciones por Cantidad")
        # Gráfico circular interactivo por cantidad con colores consistentes
        top_20_colors = [party_colors[party] for party in top_20.index]
        fig_pie = px.pie(
            values=top_20.values,
            names=top_20.index,
            height=500,
            color_discrete_sequence=top_20_colors
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.subheader("Distribución de Ingresos por Monto Total")
        # Calcular montos totales por partido
        party_total_amounts = active_aportaciones.groupby('PARTIDO POLÍTICO')['MONTO'].sum()
        top_amounts_parties = party_total_amounts.nlargest(10)
        
        # Gráfico circular por monto total con colores consistentes
        top_amounts_colors = [party_colors[party] for party in top_amounts_parties.index]
        fig_pie_amount = px.pie(
            values=top_amounts_parties.values,
            names=top_amounts_parties.index,
            height=500,
            color_discrete_sequence=top_amounts_colors
        )
        fig_pie_amount.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Monto: ₡%{value:,.0f}<br>Porcentaje: %{percent}<extra></extra>'
        )
        fig_pie_amount.update_layout(showlegend=False)
        st.plotly_chart(fig_pie_amount, use_container_width=True)
    
    with col2:
        st.subheader("Resumen")
        st.metric("Total Partidos Activos", len(active_aportaciones['PARTIDO POLÍTICO'].unique()))
        st.metric("Total Aportaciones", len(active_aportaciones))        
        # Calcular partido líder por monto
        party_total_amounts = active_aportaciones.groupby('PARTIDO POLÍTICO')['MONTO'].sum()
        top_amount_party = party_total_amounts.nlargest(1)
        st.metric("Partido Líder", top_amount_party.index[0] if len(top_amount_party) > 0 else "N/A")
        
        total_income = aportaciones['MONTO'].sum()
        avg_donation = aportaciones['MONTO'].mean()
        max_donation = aportaciones['MONTO'].max()
        
        st.metric("Total Recaudado", f"₡{total_income:,.0f}")
        st.metric("Donación Promedio", f"₡{avg_donation:,.0f}")
        st.metric("Donación Máxima", f"₡{max_donation:,.0f}")
        
        st.subheader("Top 3 Partidos por Monto")
        top_3_amounts = party_total_amounts.nlargest(3)
        for i, (partido, monto) in enumerate(top_3_amounts.items(), 1):
            st.metric(f"{i}. {partido[:20]}...", f"₡{monto:,.0f}")


    
    # Crear dos columnas para los gráficos temporales
    col1_don, col2_don = st.columns([2, 1])

    with col1_don:
        cedula_counts = aportaciones['CÉDULA'].value_counts()
        cedula_amounts = aportaciones.groupby('CÉDULA')['MONTO'].sum()
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
    with col2_don:
        st.subheader("Estadísticas de Donantes")
        
        total_donors = len(aportaciones['CÉDULA'].unique())
        repeat_donors = len(cedula_counts[cedula_counts > 1])
        top_donor_amount = cedula_amounts.max()
        top_donor_count = cedula_counts.max()
        
        st.metric("Total Donantes", total_donors)
        st.metric("Donantes Recurrentes", repeat_donors)
        st.metric("Mayor Donación", f"₡{top_donor_amount:,.0f}")
        st.metric("Más Donaciones", f"{top_donor_count} veces")
    # Separador visual
    st.divider()
    
    # Análisis por Tipo de Contribución
    st.header("Análisis por Tipo de Contribución")
    
    # Filtrar datos válidos para análisis temporal por tipo
    aportaciones_tipo_valid = aportaciones.dropna(subset=['FECHA', 'TIPO CONTRIBUCIÓN'])
    aportaciones_tipo_valid['MONTH_YEAR'] = aportaciones_tipo_valid['FECHA'].dt.to_period('M')
    
    # Agrupar por tipo de contribución y mes
    monthly_by_type = aportaciones_tipo_valid.groupby(['TIPO CONTRIBUCIÓN', 'MONTH_YEAR'])['MONTO'].sum().reset_index()
    monthly_by_type['MONTH_YEAR'] = monthly_by_type['MONTH_YEAR'].dt.to_timestamp()
    monthly_by_type['MONTO_MILLONES'] = monthly_by_type['MONTO'] / 1_000_000
    
    # Crear dos columnas para los gráficos temporales
    col1_tipo, col2_tipo = st.columns(2)
    
    with col1_tipo:
        st.subheader("Donaciones en EFECTIVO")
        efectivo_data = monthly_by_type[monthly_by_type['TIPO CONTRIBUCIÓN'] == 'EFECTIVO']
        
        if not efectivo_data.empty:
            fig_efectivo = px.bar(
                efectivo_data,
                x='MONTH_YEAR',
                y='MONTO_MILLONES',
                labels={'MONTO_MILLONES': 'Monto (Millones ₡)', 'MONTH_YEAR': 'Fecha'},
                color_discrete_sequence=['#2E8B57']
            )
            fig_efectivo.update_layout(height=400)
            st.plotly_chart(fig_efectivo, use_container_width=True)
        else:
            st.info("No hay datos de donaciones en efectivo disponibles")
    
    with col2_tipo:
        st.subheader("Donaciones EN ESPECIE")
        especie_data = monthly_by_type[monthly_by_type['TIPO CONTRIBUCIÓN'] == 'EN ESPECIE']
        
        if not especie_data.empty:
            fig_especie = px.bar(
                especie_data,
                x='MONTH_YEAR',
                y='MONTO_MILLONES',
                labels={'MONTO_MILLONES': 'Monto (Millones ₡)', 'MONTH_YEAR': 'Fecha'},
                color_discrete_sequence=['#8B4513']
            )
            fig_especie.update_layout(height=400)
            st.plotly_chart(fig_especie, use_container_width=True)
        else:
            st.info("No hay datos de donaciones en especie disponibles")
    
    # Gráfico circular con distribución por tipo de contribución
    st.subheader("Distribución por Tipo de Contribución")
    
    # Calcular totales por tipo de contribución
    tipo_totals = aportaciones.groupby('TIPO CONTRIBUCIÓN')['MONTO'].sum()
    col3_tipo, col4_tipo = st.columns(2)
    if not tipo_totals.empty:
        with col3_tipo:
            fig_pie_tipo = px.pie(
                values=tipo_totals.values,
                names=tipo_totals.index,
                height=500,
                color_discrete_sequence=['#2E8B57', '#8B4513', '#4682B4', '#CD853F']
            )
            fig_pie_tipo.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Monto: ₡%{value:,.0f}<br>Porcentaje: %{percent}<extra></extra>'
            )
            fig_pie_tipo.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
            st.plotly_chart(fig_pie_tipo, use_container_width=True)
            
            # Mostrar estadísticas detalladas
        
        with col4_tipo:
            st.subheader("Estadísticas por Tipo")
            for tipo, monto in tipo_totals.items():
                porcentaje = (monto / tipo_totals.sum()) * 100
                st.metric(f"{tipo}", f"₡{monto:,.0f}", f"{porcentaje:.1f}%")
        
    else:
        st.warning("No hay datos de tipo de contribución disponibles")


