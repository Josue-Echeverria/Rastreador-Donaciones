import streamlit as st
import pandas as pd
import plotly.express as px

def create_party_color_map():
    color_map = {}
    color_map["ACCION CIUDADANA"] = '#bc2e2a'
    color_map["AGENDA DEMOCRATICA NACIONAL"] = '#f16c37'
    color_map["ALIANZA POR SAN JOSE"] = '#01abe8'
    color_map["AVANCE MONTES DE OCA"] = '#2a5035'
    color_map["CURRIDABAT SIGLO XXI"] = '#2c3791'
    color_map["DEL SOL"] = '#0f76ba'
    color_map["EN COMUN"] = '#000000'
    color_map["FRENTE AMPLIO"] = '#f7df00'
    color_map["LA GRAN NICOYA"] = '#078736'
    color_map["LIBERACION NACIONAL"] = '#008800'
    color_map["LIBERAL PROGRESISTA"] = '#ff7300'
    color_map["MOVIMIENTO AVANCE SANTO DOMINGO"] = '#009bb8'
    color_map["MOVIMIENTO LIBERTARIO"] = '#d90638'
    color_map["NUEVA GENERACION"] = '#016caf'
    color_map["NUEVA REPUBLICA"] = '#5ec0da'
    color_map["PROGRESO SOCIAL DEMOCRATICO"] = '#002878'
    color_map["REPUBLICANO SOCIAL CRISTIANO"] = '#253e8f'
    color_map["UNIDAD SOCIAL CRISTIANA"] = '#ec2029'
    color_map["YUNTA PROGRESISTA ESCAZUCE?A"]= '#000000'
    color_map["UNIDOS PODEMOS"] = '#000000'
    color_map["INTEGRACION NACIONAL"] = '#000000'
    return color_map

def _ingresos_anuales(aportaciones, party_colors):
    """Visualiza los ingresos anuales por partido"""
    active_aportaciones = aportaciones[~aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)]
    party_contributions_count = active_aportaciones['PARTIDO POLÍTICO'].value_counts()
    
    aportaciones_valid_dates = aportaciones.dropna(subset=['FECHA'])
    aportaciones_valid_dates['MONTH_YEAR'] = aportaciones_valid_dates['FECHA'].dt.to_period('M')
    monthly_income = aportaciones_valid_dates.groupby(['PARTIDO POLÍTICO', 'MONTH_YEAR'])['MONTO'].sum().reset_index()
    monthly_income['MONTH_YEAR'] = monthly_income['MONTH_YEAR'].dt.to_timestamp()
    
    top_parties_list = party_contributions_count.head(20).index.tolist()
    monthly_income_filtered = monthly_income[monthly_income['PARTIDO POLÍTICO'].isin(top_parties_list)].copy()
    monthly_income_filtered['MONTO'] = monthly_income_filtered['MONTO'] / 1_000_000
    monthly_income_filtered['YEAR'] = monthly_income_filtered['MONTH_YEAR'].dt.to_period('Y').astype(str)
    
    yearly_income = monthly_income_filtered.groupby(['PARTIDO POLÍTICO', 'YEAR'])['MONTO'].sum().reset_index()
    
    st.subheader("Ingresos Anuales por Partido")
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

def _distribucion_partidos(aportaciones, party_colors):
    """Visualiza la distribución de aportaciones por cantidad y monto"""
    active_aportaciones = aportaciones[~aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)]
    party_contributions_count = active_aportaciones['PARTIDO POLÍTICO'].value_counts()
    top_20 = party_contributions_count.head(20)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Distribución de Aportaciones por Cantidad")
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
        party_total_amounts = active_aportaciones.groupby('PARTIDO POLÍTICO')['MONTO'].sum()
        top_amounts_parties = party_total_amounts.nlargest(10)
        
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
        _resumen_partidos(aportaciones)

def _resumen_partidos(aportaciones):
    """Muestra las métricas resumidas de partidos y donaciones"""
    active_aportaciones = aportaciones[~aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)]
    party_total_amounts = active_aportaciones.groupby('PARTIDO POLÍTICO')['MONTO'].sum()
    
    st.subheader("Resumen")
    st.metric("Total Partidos Activos", len(active_aportaciones['PARTIDO POLÍTICO'].unique()))
    st.metric("Total Aportaciones", len(active_aportaciones))
    
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

def _donantes_destacados(aportaciones):
    """Visualiza los donantes más importantes y sus estadísticas"""
    cedula_counts = aportaciones['CÉDULA'].value_counts()
    cedula_amounts = aportaciones.groupby('CÉDULA')['MONTO'].sum()
    
    st.session_state['cedula_amounts'] = cedula_amounts

    col1_don, col2_don = st.columns([2, 1])
    
    with col1_don:
        st.subheader("Top 20 Donantes por Monto Total")
        top_amounts = cedula_amounts.nlargest(20)
        amount_data = pd.DataFrame({
            'Cédula': top_amounts.index,
            'Monto Total Donaciones': top_amounts.values,
            'Cantidad de Donaciones': cedula_counts.loc[top_amounts.index]
        }).reset_index(drop=True)
        amount_data.index = amount_data.index + 1
        
        amount_data['Monto Total Donaciones'] = amount_data['Monto Total Donaciones'].astype(int)
        amount_data['Cantidad de Donaciones'] = amount_data['Cantidad de Donaciones'].astype(int)
        
        st.dataframe(
            amount_data,
            column_config={
                "Monto Total Donaciones": st.column_config.NumberColumn(
                    "Monto Total Donaciones (₡)",
                    help="Monto total donado por cada cédula",
                    format="₡%,d"
                ),
                "Cantidad de Donaciones": st.column_config.NumberColumn(
                    "Cantidad de Donaciones",
                    format="%,d"
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

def _analisis_tipo_contribucion(aportaciones):
    """Analiza las donaciones por tipo de contribución (efectivo vs en especie)"""
    # Filtrar datos válidos
    aportaciones_tipo_valid = aportaciones.dropna(subset=['FECHA', 'TIPO CONTRIBUCIÓN'])
    aportaciones_tipo_valid['MONTH_YEAR'] = aportaciones_tipo_valid['FECHA'].dt.to_period('M')
    
    # Agrupar por tipo de contribución y mes
    monthly_by_type = aportaciones_tipo_valid.groupby(['TIPO CONTRIBUCIÓN', 'MONTH_YEAR'])['MONTO'].sum().reset_index()
    monthly_by_type['MONTH_YEAR'] = monthly_by_type['MONTH_YEAR'].dt.to_timestamp()
    monthly_by_type['MONTO_MILLONES'] = monthly_by_type['MONTO'] / 1_000_000
    
    # Gráficos temporales por tipo
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

def _distribucion_tipo_contribucion(aportaciones):
    """Visualiza la distribución y estadísticas por tipo de contribución"""
    tipo_totals = aportaciones.groupby('TIPO CONTRIBUCIÓN')['MONTO'].sum()
    
    st.subheader("Distribución por Tipo de Contribución")
    
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
        
        with col4_tipo:
            st.subheader("Estadísticas por Tipo")
            for tipo, monto in tipo_totals.items():
                porcentaje = (monto / tipo_totals.sum()) * 100
                st.metric(f"{tipo}", f"₡{monto:,.0f}", f"{porcentaje:.1f}%")
    else:
        st.warning("No hay datos de tipo de contribución disponibles")

def mostrar_tab_partidos(aportaciones):
    party_colors = create_party_color_map()

    st.header("Análisis de Partidos Políticos")
    
    _ingresos_anuales(aportaciones, party_colors)
    
    _distribucion_partidos(aportaciones, party_colors)
    
    st.divider()
    
    _donantes_destacados(aportaciones)
    
    st.divider()
    
    st.header("Análisis por Tipo de Contribución")
    _analisis_tipo_contribucion(aportaciones)
    
    _distribucion_tipo_contribucion(aportaciones)

