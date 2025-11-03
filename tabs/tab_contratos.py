import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def mostrar_tab_contratos(aportaciones, contratos_folder, preparar_contratos, preparar_donaciones, detectar_alertas_temporales, load_contratos_from_folder):
    """Muestra la pestaña de análisis de contratos"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(47, 16, 0, 0.1), rgba(199, 80, 0, 0.1)); 
                padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem; border-left: 5px solid #C75000;">
        <h2 style="color: #2F1000; margin: 0; font-size: 1.8rem;">
            Análisis de Contratos Post-Electorales
        </h2>
        <p style="color: #621B00; margin: 0.5rem 0 0 0;">
            Análisis de la relación temporal entre donaciones políticas y contratos gubernamentales
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Usar contratos ya cargados o cargar desde la carpeta por defecto
    contratos_raw = None
    if 'contratos' in st.session_state:
        contratos_raw = st.session_state['contratos']
    else:
        contratos_raw = load_contratos_from_folder(contratos_folder)
    
    if contratos_raw is not None:
        # Preparar datos
        contratos_prep = preparar_contratos(contratos_raw)
        donaciones_prep = preparar_donaciones(aportaciones)
        
        if contratos_prep is not None and donaciones_prep is not None:
            
            # Encontrar coincidencias
            cedulas_contratos = set(contratos_prep['cedula_proveedor'].unique())
            cedulas_donaciones = set(donaciones_prep['CÉDULA'].unique())
            coincidencias = cedulas_contratos & cedulas_donaciones
            
            # Métricas principales
            _mostrar_metricas_principales(contratos_prep, cedulas_contratos, cedulas_donaciones, coincidencias)
            
            # Controles para el análisis
            ventana_meses, partido_filtro = _mostrar_controles_analisis(donaciones_prep)
            
            # Detectar alertas
            alertas = detectar_alertas_temporales(contratos_prep, donaciones_prep, ventana_meses)
            
            if partido_filtro != 'Todos':
                alertas = alertas[alertas['partido_donado'].str.upper() == partido_filtro.upper()]
            
            if len(alertas) > 0:
                st.success(f"Se detectaron {len(alertas)} alertas temporales")
                
                # Mostrar estadísticas y visualizaciones
                _mostrar_estadisticas_alertas(alertas)
                _mostrar_graficos_alertas(alertas, partido_filtro)
                _mostrar_top_sospechosos(alertas, contratos_prep)
                _mostrar_tabla_alertas(alertas)
                _mostrar_descarga_alertas(alertas, ventana_meses)
                
            else:
                if partido_filtro != 'Todos':
                    st.info(f"No se detectaron alertas para {partido_filtro} en una ventana de {ventana_meses} meses")
                else:
                    st.info(f"No se detectaron alertas temporales en una ventana de {ventana_meses} meses")
        else:
            st.error("No se pudieron preparar los datos de contratos o donaciones")
    else:
        st.warning("No se pudieron cargar los contratos. Verifique que la carpeta 'Contratos' esté disponible.")

def _mostrar_metricas_principales(contratos_prep, cedulas_contratos, cedulas_donaciones, coincidencias):
    """Muestra las métricas principales del análisis"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #C75000, #945600); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(47, 16, 0, 0.3);">
            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Total Contratos</h3>
            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
        </div>
        """.format(len(contratos_prep["nro_contrato"].unique())), unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #621B00, #C75000); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(47, 16, 0, 0.3);">
            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Proveedores Únicos</h3>
            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
        </div>
        """.format(len(cedulas_contratos)), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #2F1000, #945600); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(47, 16, 0, 0.3);">
            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Donantes Únicos</h3>
            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
        </div>
        """.format(len(cedulas_donaciones)), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #621B00, #945600); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(47, 16, 0, 0.3);">
            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Coincidencias</h3>
            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
        </div>
        """.format(len(coincidencias)), unsafe_allow_html=True)

def _mostrar_controles_analisis(donaciones_prep):
    """Muestra los controles para configurar el análisis"""
    st.markdown("### Configuración del Análisis")
    
    col1, col2 = st.columns(2)
    with col1:
        ventana_meses = st.slider(
            "Ventana temporal para alertas (meses)",
            min_value=1,
            max_value=24,
            value=6,
            help="Período máximo entre donación y contrato para generar alerta"
        )
    
    with col2:
        partidos_disponibles = ['Todos'] + sorted(donaciones_prep['PARTIDO POLÍTICO'].unique().tolist())
        partido_filtro = st.selectbox(
            "Filtrar por partido político",
            partidos_disponibles,
            help="Analizar solo donantes de un partido específico"
        )
    
    return ventana_meses, partido_filtro

def _mostrar_estadisticas_alertas(alertas):
    """Muestra estadísticas resumen de las alertas"""
    st.markdown("### Resumen de Alertas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        diferencia_min = alertas['diferencia_dias'].min()
        st.metric("Menor diferencia", f"{int(diferencia_min)} días")
    
    with col2:
        diferencia_promedio = alertas['diferencia_dias'].mean()
        st.metric("Diferencia promedio", f"{diferencia_promedio:.1f} días")
    
    with col3:
        donaciones_antes = (alertas['donacion_antes'] == True).sum()
        st.metric("Donaciones antes del contrato", f"{donaciones_antes}/{len(alertas)}")

def _mostrar_graficos_alertas(alertas, partido_filtro):
    """Muestra los gráficos de análisis de alertas"""
    # Distribución por partido (solo si no se filtró)
    if partido_filtro == 'Todos':
        st.markdown("### Alertas por Partido")
        alertas_por_partido = alertas['partido_donado'].value_counts().head(10)
        
        fig_alertas = px.bar(
            x=alertas_por_partido.values,
            y=alertas_por_partido.index,
            orientation='h',
            labels={'x': 'Número de Alertas', 'y': 'Partido Político'},
            color=alertas_por_partido.values,
            color_continuous_scale=[[0, '#2F1000'], [0.33, '#621B00'], [0.66, '#945600'], [1, '#C75000']],
            height=400
        )
        fig_alertas.update_layout(showlegend=False)
        st.plotly_chart(fig_alertas, use_container_width=True)
    
    # Visualización temporal
    st.markdown("### Distribución Temporal de Alertas")
    
    # Gráfico de dispersión de alertas
    fig_scatter = px.scatter(
        alertas,
        x='fecha_donacion',
        y='fecha_contrato',
        color='partido_donado',
        size='monto_donacion',
        hover_data=['cedula', 'diferencia_dias'],
        labels={
            'fecha_donacion': 'Fecha de Donación',
            'fecha_contrato': 'Fecha de Contrato',
            'partido_donado': 'Partido'
        },
        height=500
    )
    
    # Añadir línea diagonal para mostrar casos donde donación = contrato
    min_fecha = min(alertas['fecha_donacion'].min(), alertas['fecha_contrato'].min())
    max_fecha = max(alertas['fecha_donacion'].max(), alertas['fecha_contrato'].max())
    
    fig_scatter.add_trace(
        go.Scatter(
            x=[min_fecha, max_fecha],
            y=[min_fecha, max_fecha],
            mode='lines',
            line=dict(color='red', dash='dash'),
            name='Línea de Referencia',
            showlegend=True
        )
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)

def _mostrar_top_sospechosos(alertas, contratos_prep):
    """Muestra el top 5 de personas más sospechosas con gráficos gauge"""
    st.markdown("### Top 5 Personas Más Sospechosas")
    
    # Calcular porcentaje de sospecha para cada persona y ordenar
    alertas_con_porcentaje = []
    for cedula in alertas['cedula'].unique():
        alertas_persona = alertas[alertas['cedula'] == cedula]
        total_contratos_proveedor = len(contratos_prep[contratos_prep['cedula_proveedor'] == cedula])
        contratos_sospechosos = len(alertas_persona)
        porcentaje_sospecha = (contratos_sospechosos / total_contratos_proveedor) * 100 if total_contratos_proveedor > 0 else 0
        
        # Tomar la primera alerta para obtener los datos de la persona
        primera_alerta = alertas_persona.iloc[0]
        alertas_con_porcentaje.append({
            'cedula': cedula,
            'porcentaje_sospecha': porcentaje_sospecha,
            'contratos_sospechosos': contratos_sospechosos,
            'total_contratos': total_contratos_proveedor,
            'partido_donado': primera_alerta['partido_donado'],
            'monto_donacion': primera_alerta['monto_donacion'],
            'diferencia_dias': primera_alerta['diferencia_dias']
        })
    
    # Convertir a DataFrame y ordenar por porcentaje de sospecha descendente
    df_sospechosos = pd.DataFrame(alertas_con_porcentaje)
    alertas_criticas = df_sospechosos.nlargest(5, 'porcentaje_sospecha')
    
    # Crear grid de 4 columnas con componentes nativos
    cols = st.columns(4)
    
    for i, (idx, alerta) in enumerate(alertas_criticas.iterrows()):
        with cols[i]:
            # Usar los datos ya calculados
            porcentaje_sospecha = int(alerta['porcentaje_sospecha'])
            contratos_sospechosos = alerta['contratos_sospechosos']
            total_contratos_proveedor = alerta['total_contratos']
            
            # Determinar nivel de alerta
            if porcentaje_sospecha >= 80:
                nivel_alerta = "CRÍTICO"
            elif porcentaje_sospecha >= 60:
                nivel_alerta = "ALTO"
            else:
                nivel_alerta = "MEDIO"
            
            # Contenedor con borde
            with st.container():
                # Crear gráfico gauge para el porcentaje
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = porcentaje_sospecha,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Nivel de Sospecha"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "#2F1000"},
                        'steps': [
                            {'range': [0, 40], 'color': "#E8F5E8"},
                            {'range': [40, 70], 'color': "#FFE8CC"},
                            {'range': [70, 100], 'color': "#FFE0E0"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                
                fig_gauge.update_layout(
                    height=200,
                    margin=dict(l=20, r=20, t=40, b=20),
                    font={'color': "#2F1000", 'family': "Arial"}
                )
                
                st.plotly_chart(fig_gauge, use_container_width=True)
                
                # Mostrar nivel de alerta
                if porcentaje_sospecha >= 80:
                    st.error(f"**{nivel_alerta}**")
                elif porcentaje_sospecha >= 60:
                    st.warning(f"**{nivel_alerta}**")
                else:
                    st.info(f"**{nivel_alerta}**")
                
                # Información detallada usando columnas y métricas
                st.write("**Datos del Caso:**")
                
                # Métricas pequeñas
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("C. Sospechosos", contratos_sospechosos)
                with col_b:
                    st.metric("Total C.", total_contratos_proveedor)
                
                # Información adicional
                st.write(f"**ID:** {alerta['cedula'][:3]}***")
                st.write(f"**Partido:** {alerta['partido_donado'][:12]}{'...' if len(alerta['partido_donado']) > 12 else ''}")
                st.write(f"**Monto:** ₡{alerta['monto_donacion']:,.0f}")
                st.write(f"**Días Dif:** {int(alerta['diferencia_dias'])} días")
                
                # Separador visual
                st.divider()

def _mostrar_tabla_alertas(alertas):
    """Muestra la tabla detallada de alertas"""
    st.markdown("### Tabla Detallada de Alertas")
    
    # Preparar datos para la tabla
    tabla_alertas = alertas.copy()
    tabla_alertas['cedula_enmascarada'] = tabla_alertas['cedula'].str[:3] + '***'
    tabla_alertas['fecha_donacion_str'] = tabla_alertas['fecha_donacion'].dt.strftime('%Y-%m-%d')
    tabla_alertas['fecha_contrato_str'] = tabla_alertas['fecha_contrato'].dt.strftime('%Y-%m-%d')
    tabla_alertas['monto_formateado'] = tabla_alertas['monto_donacion'].apply(lambda x: f"₡{x:,.0f}")
    tabla_alertas['diferencia_dias_int'] = tabla_alertas['diferencia_dias'].astype(int)
    tabla_alertas['donacion_antes_str'] = tabla_alertas['donacion_antes'].map({True: 'Sí', False: 'No'})
    
    # Seleccionar y renombrar columnas para mostrar
    columnas_mostrar = {
        'cedula_enmascarada': 'ID Persona',
        'nro_contrato': 'Número Contrato',
        'fecha_donacion_str': 'Fecha Donación',
        'fecha_contrato_str': 'Fecha Contrato',
        'diferencia_dias_int': 'Días Diferencia',
        'donacion_antes_str': 'Donación Antes',
        'partido_donado': 'Partido',
        'monto_formateado': 'Monto Donación'
    }
    
    tabla_display = tabla_alertas[list(columnas_mostrar.keys())].rename(columns=columnas_mostrar)
    
    # Configurar la tabla con colores
    st.dataframe(
        tabla_display,
        column_config={
            "Días Diferencia": st.column_config.NumberColumn(
                "Días Diferencia",
                help="Número de días entre donación y contrato",
                format="%d"
            ),
            "Partido": st.column_config.TextColumn(
                "Partido",
                help="Partido político al que se donó",
                width="medium"
            ),
            "Monto Donación": st.column_config.TextColumn(
                "Monto Donación",
                help="Monto de la donación realizada"
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
        monto_total = tabla_alertas['monto_donacion'].sum()
        st.metric("Monto Total Donaciones", f"₡{monto_total:,.0f}")

def _mostrar_descarga_alertas(alertas, ventana_meses):
    """Muestra el botón de descarga de alertas"""
    csv_alertas = alertas.to_csv(index=False)
    st.download_button(
        label="Descargar Alertas (CSV)",
        data=csv_alertas,
        file_name=f'alertas_contratos_{ventana_meses}meses.csv',
        mime='text/csv'
    )