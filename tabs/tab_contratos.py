import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def _detectar_alertas_temporales(df_contratos, df_donaciones, ventana_meses=12):
    """Detecta casos donde una donación y un contrato ocurren en menos de X meses usando nombres reales - OPTIMIZADO"""
    
    if df_contratos is None or df_donaciones is None:
        return pd.DataFrame()
    
    # Mostrar progreso
    with st.spinner('Procesando contratos y donaciones...'):
        # Formatear datos directamente en las columnas existentes
        df_contratos['Fecha Notificación'] = pd.to_datetime(df_contratos['Fecha Notificación'], errors='coerce', dayfirst=True)
        df_contratos['Cédula Proveedor'] = df_contratos['Cédula Proveedor'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df_contratos = df_contratos.dropna(subset=['Fecha Notificación'])
        df_contratos = df_contratos[df_contratos['Cédula Proveedor'].str.len() > 0]
        
        # Preparar donaciones con fechas convertidas
        df_donaciones = df_donaciones.copy()
        df_donaciones['FECHA'] = pd.to_datetime(df_donaciones['FECHA'], errors='coerce')
        df_donaciones = df_donaciones.dropna(subset=['FECHA'])
        
        # Obtener conjunto de cédulas que aparecen en donaciones para filtrar
        cedulas_donaciones = set(df_donaciones['CÉDULA'].unique())
        
        # Filtrar contratos solo para proveedores que también tienen donaciones
        contratos_con_donaciones = df_contratos[df_contratos['Cédula Proveedor'].isin(cedulas_donaciones)]
        
        # Usar merge para optimizar la búsqueda de coincidencias
        merged_data = pd.merge(
            contratos_con_donaciones[['Cédula Proveedor', 'Fecha Notificación', 'Nro Contrato']], 
            df_donaciones[['CÉDULA', 'FECHA', 'PARTIDO POLÍTICO', 'MONTO', 'NOMBRE DEL CONTRIBUYENTE']], 
            left_on='Cédula Proveedor', 
            right_on='CÉDULA',
            how='inner'
        )
        
        if merged_data.empty:
            return pd.DataFrame()
        
        # Calcular diferencias temporales vectorizadamente
        merged_data['diferencia_dias'] = (merged_data['Fecha Notificación'] - merged_data['FECHA']).dt.days.abs()
        merged_data['diferencia_meses'] = merged_data['diferencia_dias'] / 30.44
        
        # Filtrar por ventana temporal
        alertas_data = merged_data[merged_data['diferencia_meses'] <= ventana_meses]
        
        if alertas_data.empty:
            return pd.DataFrame()
        
        # Agrupar por contrato y agregar datos
        alertas_agrupadas = alertas_data.groupby(['Cédula Proveedor', 'Fecha Notificación', 'Nro Contrato']).agg({
            'MONTO': 'sum',
            'PARTIDO POLÍTICO': lambda x: ', '.join(sorted(set(x.dropna()))),
            'FECHA': 'count',
            'NOMBRE DEL CONTRIBUYENTE': 'first'
        }).reset_index()
        
        # Renombrar columnas para el resultado final
        alertas_agrupadas.columns = [
            'cedula', 'fecha_contrato', 'nro_contrato', 'monto_total_donaciones', 
            'partidos_donados', 'cantidad_donaciones', 'nombre_contribuyente'
        ]
        
        # Añadir año del contrato
        alertas_agrupadas['año_contrato'] = alertas_agrupadas['fecha_contrato'].dt.year
    
    return alertas_agrupadas

def mostrar_tab_contratos(aportaciones, preparar_donaciones):
    # Usar contratos ya cargados o cargar desde la carpeta por defecto (caché siempre activo)
    contratos_raw = None
    if 'contratos' in st.session_state:
        contratos_raw = st.session_state['contratos']
    else:
        try:
            with st.spinner('Cargando archivo de contratos...'):
                contratos_raw = pd.read_excel('./contratos_completo_todas_columnas.xlsx')
                st.session_state['contratos'] = contratos_raw
        except:
            st.warning("No se pudo cargar el archivo de contratos desde './contratos_completo_todas_columnas.xlsx'")

    if contratos_raw is not None:
        contratos_prep = contratos_raw.copy()
            
        donaciones_prep = preparar_donaciones(aportaciones)
        
        if contratos_prep is not None and donaciones_prep is not None:
            
            # Encontrar coincidencias usando nombres directos de columnas
            cedulas_contratos = set(contratos_prep['Cédula Proveedor'].astype(str).unique())
            cedulas_donaciones = set(donaciones_prep['CÉDULA'].unique())
            coincidencias = cedulas_contratos & cedulas_donaciones
        
            
            # Detectar alertas usando función local con ventana fija de 12 meses
            alertas = _detectar_alertas_temporales(contratos_prep, donaciones_prep, 12)
            
            if len(alertas) > 0:
                # Análisis temporal de contratos
                st.subheader("Acumulación de Contratos en el Tiempo")
                
                # Preparar datos para visualización temporal usando nombres directos
                contratos_temp = contratos_prep.copy()
                contratos_temp['fecha_parsed'] = pd.to_datetime(contratos_temp['Fecha Notificación'], errors='coerce', dayfirst=True)
                contratos_temp['year'] = contratos_temp['fecha_parsed'].dt.year
                contratos_temp['month_year'] = contratos_temp['fecha_parsed'].dt.to_period('M')
                
                # Filtrar años válidos (remover valores nulos y años extremos)
                contratos_temp = contratos_temp.dropna(subset=['year'])
                contratos_temp = contratos_temp[
                    (contratos_temp['year'] >= 2000) & 
                    (contratos_temp['year'] <= datetime.now().year)
                ]

                crear_grafico_acumulacion_anual(contratos_temp)
                
                # Análisis de top proveedores
                _mostrar_top_proveedores(contratos_prep)
                
                # Mostrar estadísticas y visualizaciones
                _mostrar_graficos_alertas(alertas)
                _mostrar_tabla_alertas(alertas)

                
            else:
                st.info("No se detectaron alertas temporales en una ventana de 12 meses")
        else:
            st.error("No se pudieron preparar los datos de contratos o donaciones")
    else:
        st.warning("No se pudieron cargar los contratos. Verifique que la carpeta 'Contratos' esté disponible.")

def _mostrar_graficos_alertas(alertas):
    """Muestra los gráficos de análisis de alertas"""
    # Distribución por partido
    st.markdown("### Alertas por Partido")
    
    # Crear lista de todos los partidos mencionados
    todos_partidos = []
    for partidos in alertas['partidos_donados']:
        todos_partidos.extend([p.strip() for p in partidos.split(',')])
    
    partidos_counts = pd.Series(todos_partidos).value_counts().head(10)
    
    fig_alertas = px.bar(
        x=partidos_counts.values,
        y=partidos_counts.index,
        orientation='h',
        labels={'x': 'Número de Alertas', 'y': 'Partido Político'},
        color=partidos_counts.values,
        color_continuous_scale=[[0, '#2F1000'], [0.33, '#621B00'], [0.66, '#945600'], [1, '#C75000']],
        height=400
    )
    fig_alertas.update_layout(showlegend=False)
    st.plotly_chart(fig_alertas, use_container_width=True)

def _mostrar_tabla_alertas(alertas):
    """Muestra la tabla detallada de alertas"""
    st.markdown("### Tabla Detallada de Alertas")
    
    # Preparar datos para la tabla con anonimización
    tabla_alertas = alertas.copy()
    
    # Crear mapeo anónimo de cédulas a IDs
    cedulas_unicas = tabla_alertas['cedula'].unique()
    mapeo_anonimo = {cedula: f"Persona {i+1}" for i, cedula in enumerate(cedulas_unicas)}
    tabla_alertas['cedula_anonima'] = tabla_alertas['cedula'].map(mapeo_anonimo)
    
    tabla_alertas['fecha_contrato_str'] = tabla_alertas['fecha_contrato'].dt.strftime('%Y-%m-%d')
    tabla_alertas['monto_formateado'] = tabla_alertas['monto_total_donaciones'].apply(lambda x: f"₡{x:,.0f}")
    
    # Seleccionar y renombrar columnas para mostrar
    columnas_mostrar = {
        'cedula_anonima': 'ID Persona',
        'nro_contrato': 'Número Contrato',
        'fecha_contrato_str': 'Fecha Contrato',
        'cantidad_donaciones': 'Cantidad Donaciones',
        'partidos_donados': 'Partidos',
        'monto_formateado': 'Monto Total'
    }
    
    tabla_display = tabla_alertas[list(columnas_mostrar.keys())].rename(columns=columnas_mostrar)
    
    # Configurar la tabla con colores
    st.dataframe(
        tabla_display,
        column_config={
            "Cantidad Donaciones": st.column_config.NumberColumn(
                "Cantidad Donaciones",
                help="Número de donaciones realizadas en el rango temporal",
                format="%d"
            ),
            "Partidos": st.column_config.TextColumn(
                "Partidos",
                help="Partidos políticos a los que se donó",
                width="medium"
            ),
            "Monto Total": st.column_config.TextColumn(
                "Monto Total",
                help="Suma total de todas las donaciones en el rango"
            )
        },
        use_container_width=True,
        height=400
    )
    
    # Estadísticas de la tabla
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Alertas", len(tabla_alertas))
    with col2:
        personas_unicas = tabla_alertas['cedula'].nunique()
        st.metric("Personas Únicas", personas_unicas)
    with col3:
        contratos_unicos = tabla_alertas['nro_contrato'].nunique()
        st.metric("Contratos Únicos", contratos_unicos)
    with col4:
        monto_total = tabla_alertas['monto_total_donaciones'].sum()
        st.metric("Monto Total Donaciones", f"₡{monto_total:,.0f}")

def _mostrar_top_proveedores(contratos_prep):
    """Muestra análisis de top proveedores con contratos únicos vs duplicados"""
    st.markdown("### Top Proveedores")
    
    with st.spinner('Analizando proveedores...'):
        # Filtrar registros válidos primero
        contratos_validos = contratos_prep.dropna(subset=['Cédula Proveedor', 'Nro Contrato'])
        
        # Agregación por proveedor - corregida
        proveedor_stats = (
            contratos_validos.groupby('Cédula Proveedor')
              .agg(
                  Total_Registros=('Nro Contrato', 'count'),  # Total de filas
                  Contratos_Unicos=('Nro Contrato', 'nunique')  # Contratos únicos
              )
              .reset_index()
              .rename(columns={'Cédula Proveedor': 'Proveedor'})
        )
        
        # Cálculos de duplicados (registros duplicados) y porcentaje
        proveedor_stats['Registros_Duplicados'] = proveedor_stats['Total_Registros'] - proveedor_stats['Contratos_Unicos']
        proveedor_stats['Pct_Duplicados'] = (proveedor_stats['Registros_Duplicados'] / proveedor_stats['Total_Registros']) * 100
        
        # Asegurar que no hay valores negativos
        proveedor_stats['Registros_Duplicados'] = proveedor_stats['Registros_Duplicados'].clip(lower=0)
        
        # Ordenar por "cantidad de contratos" (contratos únicos) y tomar Top 30
        proveedor_stats = (proveedor_stats
                           .sort_values('Contratos_Unicos', ascending=False)
                           .head(30)
                           .reset_index(drop=True))
        
        # Etiqueta con ranking anonimizada
        proveedor_stats['Etiqueta'] = proveedor_stats.index.map(lambda i: f"Persona {i+1}")
        
        # Crear gráfico de barras apiladas
        fig = go.Figure()
        
        # Barra de contratos ÚNICOS (base verde)
        fig.add_trace(
            go.Bar(
                x=proveedor_stats['Contratos_Unicos'],
                y=proveedor_stats['Etiqueta'],
                name='Únicos',
                orientation='h',
                marker=dict(
                    color='rgba(0, 200, 80, 0.8)',  # Verde para únicos
                    line=dict(color='rgba(255,255,255,0.3)', width=1)
                ),
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    'Únicos: %{x:,}<extra></extra>'
                ),
                text=[f"{v:,}" for v in proveedor_stats['Contratos_Unicos']],
                textposition='inside',
                textfont=dict(color='white', size=10, family='Arial Bold')
            )
        )
        
        # Barra de DUPLICADOS - apilada encima
        fig.add_trace(
            go.Bar(
                x=proveedor_stats['Registros_Duplicados'],
                y=proveedor_stats['Etiqueta'],
                name='Registros duplicados',
                orientation='h',
                marker=dict(
                    color=proveedor_stats['Pct_Duplicados'],
                    colorscale=[[0, 'rgba(255, 140, 0, 0.6)'], [0.5, 'rgba(255, 80, 0, 0.8)'], [1, 'rgba(180, 0, 0, 0.9)']],
                    line=dict(color='rgba(255,255,255,0.3)', width=1),
                    showscale=True,
                    colorbar=dict(
                        title='% duplicados',
                        thickness=15,
                        len=0.6,
                        x=1.02
                    )
                ),
                text=[f"{n:,} ({p:.1f}%)" for n, p in zip(proveedor_stats['Registros_Duplicados'], proveedor_stats['Pct_Duplicados'])],
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=9, family='Arial Bold'),
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    'Duplicados: %{x:,} (%{customdata[0]:.1f}%)<br>' +
                    'Únicos: %{customdata[1]:,}<br>' +
                    'Total registros: %{customdata[2]:,}<extra></extra>'
                ),
                customdata=list(zip(
                    proveedor_stats['Pct_Duplicados'],
                    proveedor_stats['Contratos_Unicos'],
                    proveedor_stats['Total_Registros']
                ))
            )
        )
        
        # Configuración de layout
        fig.update_layout(
            barmode='stack',
            xaxis_title='Cantidad de registros (Únicos + Duplicados)',
            yaxis_title='Proveedor',
            plot_bgcolor='rgba(255,255,255,0.95)',
            paper_bgcolor='rgba(255,255,255,0.95)',
            font=dict(color='#2F1000', size=11),
            height=700,
            margin=dict(l=120, r=50, t=20, b=60),  # Reducir margen izquierdo y derecho
            legend=dict(
                font=dict(color='#2F1000'),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='rgba(47, 16, 0, 0.3)',
                borderwidth=1
            )
        )
        
        # Configurar ejes
        fig.update_xaxes(
            showgrid=True, 
            gridcolor='rgba(199, 80, 0, 0.2)',
            title_font=dict(color='#2F1000')
        )
        fig.update_yaxes(
            tickfont=dict(size=10, color='#2F1000'),
            title_font=dict(color='#2F1000')
        )
        
        # Layout en dos columnas para gráfico de barras y pie chart
        col_bar, col_pie = st.columns([2, 1])
        
        with col_bar:
            st.markdown("#### Top 30 Proveedores - Ranking Detallado")
            # Mostrar gráfico de barras
            st.plotly_chart(fig, use_container_width=True)
        
        with col_pie:
            st.markdown("#### Concentración de Mercado")
            
            # Obtener todos los proveedores ordenados por contratos únicos
            todos_proveedores = (
                contratos_validos.groupby('Cédula Proveedor')
                  .agg(Contratos_Unicos=('Nro Contrato', 'nunique'))
                  .reset_index()
                  .sort_values('Contratos_Unicos', ascending=False)
            )
            
            # Calcular concentración
            total_contratos = todos_proveedores['Contratos_Unicos'].sum()
            top_10_contratos = todos_proveedores.head(10)['Contratos_Unicos'].sum()
            top_11_50_contratos = todos_proveedores.iloc[10:50]['Contratos_Unicos'].sum() if len(todos_proveedores) > 10 else 0
            resto_contratos = total_contratos - top_10_contratos - top_11_50_contratos
            
            # Preparar datos para el pie chart
            concentracion_data = {
                'Grupo': ['Top 1-10', 'Top 11-50', 'Resto (51+)'],
                'Contratos': [top_10_contratos, top_11_50_contratos, resto_contratos],
                'Porcentaje': [
                    (top_10_contratos / total_contratos) * 100,
                    (top_11_50_contratos / total_contratos) * 100,
                    (resto_contratos / total_contratos) * 100
                ]
            }
            
            # Filtrar grupos con valor > 0
            datos_filtrados = {
                'Grupo': [],
                'Contratos': [],
                'Porcentaje': []
            }
            
            for i, grupo in enumerate(concentracion_data['Grupo']):
                if concentracion_data['Contratos'][i] > 0:
                    datos_filtrados['Grupo'].append(grupo)
                    datos_filtrados['Contratos'].append(concentracion_data['Contratos'][i])
                    datos_filtrados['Porcentaje'].append(concentracion_data['Porcentaje'][i])
            
            # Crear pie chart más compacto
            fig_pie = go.Figure(data=[go.Pie(
                labels=datos_filtrados['Grupo'],
                values=datos_filtrados['Contratos'],
                hole=0.4,  # Donut chart
                marker=dict(
                    colors=['#C75000', '#945600', '#621B00'],
                    line=dict(color='white', width=2)
                ),
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(size=10, color='#2F1000', family='Arial Bold'),
                hovertemplate=(
                    '<b>%{label}</b><br>' +
                    'Contratos: %{value:,}<br>' +
                    'Porcentaje: %{percent}<br>' +
                    '<extra></extra>'
                )
            )])
            
            fig_pie.update_layout(
                font=dict(color='#2F1000', size=9),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="bottom",
                    y=0,
                    xanchor="center",
                    x=0.5,
                    font=dict(color='#2F1000', size=9)
                ),
                height=400,
                margin=dict(l=10, r=10, t=10, b=40),
                plot_bgcolor='rgba(255,255,255,0.95)',
                paper_bgcolor='rgba(255,255,255,0.95)'
            )
            
            # Agregar texto en el centro del donut
            fig_pie.add_annotation(
                text=f"<b>Total<br>{total_contratos:,}<br>Contratos</b>",
                x=0.5, y=0.5,
                font=dict(size=12, color='#2F1000', family='Arial Bold'),
                showarrow=False
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Métricas de concentración compactas
            st.markdown("##### 📈 Métricas de Concentración")
            
            st.metric("🥇 Top 10", f"{(top_10_contratos/total_contratos)*100:.1f}%", 
                     f"{top_10_contratos:,} contratos")
            
            if top_11_50_contratos > 0:
                st.metric("🥈 Top 11-50", f"{(top_11_50_contratos/total_contratos)*100:.1f}%", 
                         f"{top_11_50_contratos:,} contratos")
            else:
                st.metric("🥈 Top 11-50", "0%", "Sin datos")
            
            if resto_contratos > 0:
                st.metric("🥉 Resto (51+)", f"{(resto_contratos/total_contratos)*100:.1f}%", 
                         f"{resto_contratos:,} contratos")
            else:
                st.metric("🥉 Resto (51+)", "0%", "Sin datos")
        
        # Top 5 en detalle (fuera de las columnas, ocupando todo el ancho)
        st.markdown("### Top 5 Proveedores - Análisis Detallado")
        
        for i, row in proveedor_stats.head(5).iterrows():
            with st.expander(f"Persona {i+1} ({int(row['Contratos_Unicos']):,} únicos, {row['Pct_Duplicados']:.1f}% duplicados)"):
                col_det1, col_det2, col_det3, col_det4 = st.columns(4)
                with col_det1:
                    st.metric("Contratos únicos", f"{int(row['Contratos_Unicos']):,}")
                with col_det2:
                    st.metric("Registros duplicados", f"{int(row['Registros_Duplicados']):,}")
                with col_det3:
                    st.metric("Total registros", f"{int(row['Total_Registros']):,}")
                with col_det4:
                    st.metric("% Duplicados", f"{row['Pct_Duplicados']:.1f}%")
                
                if row['Pct_Duplicados'] > 20:
                    st.warning(f"⚠️ Alto nivel de duplicación: {row['Pct_Duplicados']:.1f}%")
                elif row['Pct_Duplicados'] > 10:
                    st.info(f"ℹ️ Nivel moderado de duplicación: {row['Pct_Duplicados']:.1f}%")
                else:
                    st.success(f"✅ Bajo nivel de duplicación: {row['Pct_Duplicados']:.1f}%")

def crear_grafico_acumulacion_anual(contratos_temp):
    """Crea el gráfico principal de acumulación de contratos por año"""
    # Contar contratos por año
    contratos_por_año = contratos_temp.groupby('year').size().reset_index(name='cantidad_contratos')
    
    # Calcular acumulación
    contratos_por_año['acumulado'] = contratos_por_año['cantidad_contratos'].cumsum()
    
    # Crear gráfico de línea con acumulación
    fig = go.Figure()
    
    # Línea de acumulación
    fig.add_trace(go.Scatter(
        x=contratos_por_año['year'],
        y=contratos_por_año['acumulado'],
        mode='lines+markers',
        name='Contratos Acumulados',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8),
        hovertemplate='<b>Año:</b> %{x}<br><b>Total Acumulado:</b> %{y:,}<extra></extra>'
    ))
    
    # Barras de contratos por año
    fig.add_trace(go.Bar(
        x=contratos_por_año['year'],
        y=contratos_por_año['cantidad_contratos'],
        name='Contratos por Año',
        opacity=0.6,
        marker_color='#ff7f0e',
        yaxis='y2',
        hovertemplate='<b>Año:</b> %{x}<br><b>Contratos:</b> %{y:,}<extra></extra>'
    ))
    
    # Configurar layout con doble eje Y
    fig.update_layout(
        xaxis_title='Año',
        yaxis=dict(
            title='Contratos Acumulados',
            side='left',
            color='#1f77b4'
        ),
        yaxis2=dict(
            title='Contratos por Año',
            side='right',
            overlaying='y',
            color='#ff7f0e'
        ),
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    return contratos_por_año

