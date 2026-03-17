import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

MIN_CONTRATOS = 5
MIN_DONACION = 100000

def analizar_empresas(contratos, aportaciones, representantes):
    contratos = contratos.copy()
    aportaciones = aportaciones.copy()
    representantes = representantes.copy()
    
    representantes["CEDULA_IDENTIDAD"] = representantes["CEDULA_IDENTIDAD"].astype(str).str.replace('-', '').str.strip()
    representantes["CEDULA_JURIDICA"] = representantes["CEDULA_JURIDICA"].astype(str).str.replace('-', '').str.strip()
    contratos["Cédula Proveedor"] = contratos["Cédula Proveedor"].astype(str).str.replace('-', '').str.strip()
    aportaciones["CÉDULA"] = aportaciones["CÉDULA"].astype(str).str.replace('-', '').str.strip()

    # 1. Contar contratos únicos por empresa
    contratos_por_empresa = (
        contratos
        .drop_duplicates(subset=['Cédula Proveedor', 'Nro Contrato'])
        .groupby('Cédula Proveedor')
        .size()
        .reset_index(name='num_contratos')
    )

    # Filtrar empresas con suficientes contratos
    empresas_interes = contratos_por_empresa[contratos_por_empresa['num_contratos'] >= MIN_CONTRATOS].copy()

    # 2. Obtener representantes de estas empresas
    representantes_empresas = representantes[representantes["CEDULA_JURIDICA"].isin(empresas_interes['Cédula Proveedor'])].copy()

    # 3. Buscar donaciones de estos representantes
    cedulas_representantes = set(representantes_empresas["CEDULA_IDENTIDAD"].unique())
    donaciones_representantes = aportaciones[aportaciones['CÉDULA'].isin(cedulas_representantes)].copy()

    # 4. Sumar donaciones por representante
    donaciones_agregadas = (
        donaciones_representantes
        .groupby(['CÉDULA', 'PARTIDO POLÍTICO'])
        .agg({
            'MONTO': 'sum',
            'CÉDULA': 'count'
        })
        .rename(columns={'MONTO': 'total_donado', 'CÉDULA': 'num_donaciones'})
        .reset_index()
    )
    
    donaciones_agregadas['total_donado'] = donaciones_agregadas['total_donado'].astype(int)

    # Filtrar donaciones significativas
    donaciones_significativas = donaciones_agregadas[donaciones_agregadas['total_donado'] >= MIN_DONACION]

    # 5. Cruzar información
    resultados = []

    for _, empresa in empresas_interes.iterrows():
        cedula_juridica = empresa['Cédula Proveedor']
        num_contratos = empresa['num_contratos']

        # Obtener representantes de esta empresa
        reps = representantes_empresas[
            representantes_empresas["CEDULA_JURIDICA"] == cedula_juridica
        ]

        for _, rep in reps.iterrows():
            cedula_rep = rep["CEDULA_IDENTIDAD"]

            # Buscar donaciones de este representante
            donaciones_rep = donaciones_significativas[
                donaciones_significativas['CÉDULA'] == cedula_rep
            ]

            if len(donaciones_rep) > 0:
                for _, donacion in donaciones_rep.iterrows():
                    resultado = {
                        'cedula_juridica': cedula_juridica,
                        'nombre_empresa': rep.get("NOMBRE_EMPRESA", 'N/A') if "NOMBRE_EMPRESA" else 'N/A',
                        'num_contratos': num_contratos,
                        'cedula_representante': cedula_rep,
                        'nombre_representante': rep.get("NOMBRE_EMPLEADO", 'N/A') if "NOMBRE_EMPLEADO" else 'N/A',
                        'clasificacion_representante': rep.get("CLASIFICACION_EMPLEADO", 'N/A') if "CLASIFICACION_EMPLEADO" else 'N/A',
                        'partido_donado': donacion['PARTIDO POLÍTICO'],
                        'total_donado': donacion['total_donado'],
                        'num_donaciones': donacion['num_donaciones']
                    }
                    resultados.append(resultado)

    resultados = pd.DataFrame(resultados)

    if len(resultados) > 0:
        # Ordenar por número de contratos y monto donado
        resultados = resultados.sort_values(
            'total_donado',
            ascending=[False]
        )

    return resultados

def mostrar_tab_empresas(donaciones, contratos, representantes):
    st.markdown("## Análisis de Empresas y Representantes Legales")
    st.markdown("---")

    try:
        if 'resultados_empresas' not in st.session_state:
            with st.spinner("Analizando datos de empresas y representantes..."):
                resultados = analizar_empresas(contratos, donaciones, representantes)
                st.session_state['resultados_empresas'] = resultados
        
        resultados = st.session_state['resultados_empresas']

        if len(resultados) > 0:
            mostrar_visualizaciones(resultados)
            mostrar_tabla_completa(resultados)
            mostrar_series_temporales(donaciones, contratos, resultados)

        else:
            st.warning("No se encontraron casos que cumplan los criterios especificados")
        
    except Exception as e:
        st.error(f"Error al inicializar el analizador: {e}")
        st.exception(e)

def mostrar_series_temporales(donaciones, contratos, resultados):
    st.markdown("#### Donaciones y Contratos en el Tiempo")

    combinaciones = (
        resultados[['cedula_representante', 'nombre_representante', 'cedula_juridica', 'nombre_empresa']]
        .drop_duplicates()
        .sort_values('nombre_representante')
        .copy()
    )
    combinaciones['label'] = combinaciones.apply(
        lambda r: f"{r['nombre_representante']} ({r['cedula_representante']}) Representante Legal de {r['nombre_empresa']} ({r['cedula_juridica']})",
        axis=1
    )

    seleccion = st.selectbox(
        "Representante y empresa",
        combinaciones['label'].tolist(),
        key='combo_series_empresas'
    )
    fila = combinaciones.loc[combinaciones['label'] == seleccion].iloc[0]

    don_persona = donaciones.copy()
    don_persona['CÉDULA'] = don_persona['CÉDULA'].astype(str).str.replace('-', '').str.strip()
    don_persona['FECHA'] = pd.to_datetime(don_persona['FECHA'], errors='coerce', dayfirst=True)
    serie_donaciones = (
        don_persona[don_persona['CÉDULA'] == fila['cedula_representante']]
        .dropna(subset=['FECHA'])
        .groupby(pd.Grouper(key='FECHA', freq='M'))['MONTO']
        .sum()
        .reset_index()
        .rename(columns={'FECHA': 'MES'})
    )

    contratos_empresa = contratos.copy()
    contratos_empresa['Cédula Proveedor'] = contratos_empresa['Cédula Proveedor'].astype(str).str.replace('-', '').str.strip()
    contratos_empresa['Fecha Notificación'] = pd.to_datetime(contratos_empresa['Fecha Notificación'], errors='coerce', dayfirst=True)
    serie_contratos = (
        contratos_empresa[contratos_empresa['Cédula Proveedor'] == fila['cedula_juridica']]
        .dropna(subset=['Fecha Notificación'])
        .groupby(pd.Grouper(key='Fecha Notificación', freq='M'))['Nro Contrato']
        .nunique()
        .reset_index(name='CONTRATOS')
        .rename(columns={'Fecha Notificación': 'MES'})
    )

    if len(serie_donaciones) == 0 and len(serie_contratos) == 0:
        st.info("No hay datos con fecha para esta combinación")
        return

    serie = pd.merge(serie_donaciones, serie_contratos, on='MES', how='outer').sort_values('MES').fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=serie['MES'], y=serie['MONTO'], name='Donaciones (₡)', marker_color='#3b82f6'))
    fig.add_trace(go.Bar(x=serie['MES'], y=serie['CONTRATOS'], name='Contratos', yaxis='y2', marker_color='#ef4444', opacity=0.7))
    fig.update_layout(
        height=430,
        barmode='group',
        xaxis=dict(title='Fecha'),
        yaxis=dict(title='Donaciones (₡)'),
        yaxis2=dict(title='Contratos', overlaying='y', side='right'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )
    st.plotly_chart(fig, use_container_width=True)

def mostrar_visualizaciones(resultados):
    st.markdown("#### Top 20 Empresas por Número de Contratos")

    top_empresas = (
        resultados
        .groupby(['cedula_juridica', 'nombre_empresa'])
        .agg({'num_contratos': 'first'})
        .reset_index()
        .nlargest(20, 'num_contratos')
    )

    fig1 = px.bar(
        top_empresas,
        y='nombre_empresa',
        x='num_contratos',
        orientation='h',
        labels={
            'nombre_empresa': 'Empresa',
            'num_contratos': 'Número de Contratos'
        }
    )

    fig1.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig1, use_container_width=True)

    # 2. Top representantes por monto donado
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Top 20 Representantes por Donaciones")

        top_representantes = (
            resultados
            .groupby(['cedula_representante', 'nombre_representante'])
            .agg({'total_donado': 'sum', 'num_contratos': 'sum'})
            .reset_index()
            .nlargest(20, 'total_donado')
        )

        fig2 = px.bar(
            top_representantes,
            y='nombre_representante',
            x='total_donado',
            orientation='h',
            labels={
                'nombre_representante': 'Representante',
                'total_donado': 'Total Donado (₡)'
            }
        )

        fig2.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown("#### Distribución por Partido")

        partidos = resultados['partido_donado'].value_counts().head(10)

        fig3 = px.pie(
            values=partidos.values,
            names=partidos.index,
            hole=0.4
        )

        fig3.update_layout(height=500)
        st.plotly_chart(fig3, use_container_width=True)

def mostrar_tabla_completa(resultados):
    st.markdown("#### Todos los Casos Encontrados")

    # Preparar datos para mostrar
    tabla_display = resultados.copy()

    # Seleccionar columnas a mostrar
    columnas_mostrar = [
        'nombre_representante',
        'nombre_empresa',
        'clasificacion_representante',
        'partido_donado',
        'num_contratos',
        'total_donado',
        'num_donaciones'
    ]

    tabla_final = tabla_display[columnas_mostrar].sort_values('total_donado', ascending=False)

    tabla_final['total_donado'] = tabla_final['total_donado'].astype(int)
    
    tabla_final = tabla_final.rename(columns={
        'nombre_representante': 'Representante',
        'nombre_empresa': 'Empresa',
        'clasificacion_representante': 'Clasificación',
        'partido_donado': 'Partido',
        'num_contratos': 'Contratos',
        'total_donado': 'Total Donado',
        'num_donaciones': 'Nº Donaciones'
    })
    st.dataframe(
        tabla_final, 
        use_container_width=True, 
        column_config={
            "Contratos": st.column_config.NumberColumn(
                "Contratos",
                format="%,d"
            ),
            "Total Donado": st.column_config.NumberColumn(
                "Total Donado (₡)",
                format="₡%,d"
            ),
            "Nº Donaciones": st.column_config.NumberColumn(
                "Nº Donaciones", 
                format="%,d"
            )
        },
        )

    # Botón de descarga
    csv = resultados.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar CSV",
        data=csv,
        file_name='analisis_empresas_representantes.csv',
        mime='text/csv'
    )
