import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

MIN_CONTRATOS = 5
MIN_DONACION = 50000


def normalizar_representantes(representantes):
    df = representantes.copy()
    
    # Mapeo de nombres de columnas
    mapeo = {}

    for col in df.columns:
        col_lower = col.lower()
        if 'cedula' in col_lower and 'juridica' in col_lower:
            mapeo[col] = 'cedula_juridica'
        elif 'cedula' in col_lower and 'identidad' in col_lower:
            mapeo[col] = 'cedula_identidad'
        elif 'nombre' in col_lower and ('empleado' in col_lower or 'representante' in col_lower):
            mapeo[col] = 'nombre_representante'
        elif 'clasificacion' in col_lower:
            mapeo[col] = 'clasificacion'
        elif 'nombre' in col_lower and 'empresa' in col_lower:
            mapeo[col] = 'nombre_empresa'

    df = df.rename(columns=mapeo)

    # Normalizar cédulas
    if 'cedula_juridica' in df.columns:
        df['cedula_juridica'] = (
            df['cedula_juridica']
            .astype(str)
            .str.replace('-', '')
            .str.strip()
        )

    if 'cedula_identidad' in df.columns:
        df['cedula_identidad'] = (
            df['cedula_identidad']
            .astype(str)
            .str.replace('-', '')
            .str.strip()
        )
    
    return df

def preparar_contratos(contratos):
    df = contratos.copy()
    
    # Detectar y normalizar columnas de contratos
    for col in df.columns:
        col_lower = col.lower()
        if 'cédula' in col_lower and 'proveedor' in col_lower:
            df['cedula_proveedor'] = (
                df[col]
                .astype(str)
                .str.replace('-', '')
                .str.strip()
            )
            break
        elif 'cedula' in col_lower and 'proveedor' in col_lower:
            df['cedula_proveedor'] = (
                df[col]
                .astype(str)
                .str.replace('-', '')
                .str.strip()
            )
            break
    
    return df

def preparar_aportaciones(aportaciones):
    df = aportaciones.copy()
    
    # Normalizar cédulas en aportaciones
    if 'CÉDULA' in df.columns:
        df['cedula'] = (
            df['CÉDULA']
            .astype(str)
            .str.replace('-', '')
            .str.strip()
        )
    
    return df

def analizar_empresas(contratos, aportaciones, representantes):
    contratos = preparar_contratos(contratos)
    aportaciones = preparar_aportaciones(aportaciones)
    representantes = normalizar_representantes(representantes)
    
    # 1. Contar contratos por empresa
    contratos_por_empresa = (
        contratos
        .groupby('cedula_proveedor')
        .size()
        .reset_index(name='num_contratos')
    )

    # Filtrar empresas con suficientes contratos
    empresas_interes = contratos_por_empresa[contratos_por_empresa['num_contratos'] >= MIN_CONTRATOS].copy()

    # 2. Obtener representantes de estas empresas
    representantes_empresas = representantes[representantes['cedula_juridica'].isin(empresas_interes['cedula_proveedor'])].copy()

    # 3. Buscar donaciones de estos representantes
    cedulas_representantes = set(representantes_empresas['cedula_identidad'].unique())

    donaciones_representantes = aportaciones[aportaciones['cedula'].isin(cedulas_representantes)].copy()

    # 4. Sumar donaciones por representante
    col_monto = 'MONTO'
    col_partido = 'PARTIDO POLÍTICO'

    donaciones_agregadas = (
        donaciones_representantes
        .groupby(['cedula', col_partido])
        .agg({
            col_monto: 'sum',
            'cedula': 'count'
        })
        .rename(columns={col_monto: 'total_donado', 'cedula': 'num_donaciones'})
        .reset_index()
    )
    
    donaciones_agregadas['total_donado'] = donaciones_agregadas['total_donado'].astype(int)

    # Filtrar donaciones significativas
    donaciones_significativas = donaciones_agregadas[donaciones_agregadas['total_donado'] >= MIN_DONACION]

    # 5. Cruzar información
    resultados = []

    for _, empresa in empresas_interes.iterrows():
        cedula_juridica = empresa['cedula_proveedor']
        num_contratos = empresa['num_contratos']

        # Obtener representantes de esta empresa
        reps = representantes_empresas[
            representantes_empresas['cedula_juridica'] == cedula_juridica
        ]

        for _, rep in reps.iterrows():
            cedula_rep = rep['cedula_identidad']

            # Buscar donaciones de este representante
            donaciones_rep = donaciones_significativas[
                donaciones_significativas['cedula'] == cedula_rep
            ]

            if len(donaciones_rep) > 0:
                for _, donacion in donaciones_rep.iterrows():
                    resultado = {
                        'cedula_juridica': cedula_juridica,
                        'nombre_empresa': rep.get('nombre_empresa', 'N/A'),
                        'num_contratos': num_contratos,
                        'cedula_representante': cedula_rep,
                        'nombre_representante': rep.get('nombre_representante', 'N/A'),
                        'clasificacion_representante': rep.get('clasificacion', 'N/A'),
                        'partido_donado': donacion[col_partido],
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
            with st.spinner("🔍 Analizando datos de empresas y representantes..."):
                resultados = analizar_empresas(contratos, donaciones, representantes)
                st.session_state['resultados_empresas'] = resultados
        
        resultados = st.session_state['resultados_empresas']

        if len(resultados) > 0:
                # Tabs para diferentes visualizaciones
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📈 Visualizaciones",
                    "📋 Tabla Completa",
                    "🏢 Por Empresa",
                    "👤 Por Representante"
                ])

                with tab1:
                    mostrar_visualizaciones(resultados)

                with tab2:
                    mostrar_tabla_completa(resultados)

                with tab3:
                    mostrar_resumen_empresas(resultados)

                with tab4:
                    mostrar_resumen_representantes(resultados)

        else:
            st.warning("⚠️ No se encontraron casos que cumplan los criterios especificados")
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el analizador: {e}")
        st.exception(e)

def mostrar_visualizaciones(resultados):
    st.markdown("#### Top 20 Empresas por Número de Contratos")

    top_empresas = (
        resultados
        .groupby(['cedula_juridica', 'nombre_empresa'])
        .agg({'num_contratos': 'first', 'total_donado': 'sum'})
        .reset_index()
        .nlargest(20, 'num_contratos')
    )

    fig1 = px.bar(
        top_empresas,
        y='nombre_empresa',
        x='num_contratos',
        orientation='h',
        color='total_donado',
        color_continuous_scale='Reds',
        labels={
            'nombre_empresa': 'Empresa',
            'num_contratos': 'Número de Contratos',
            'total_donado': 'Total Donado'
        },
        hover_data={'total_donado': ':,.0f'}
    )

    fig1.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig1, use_container_width=True)

    # 2. Top representantes por monto donado
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Top 15 Representantes por Donaciones")

        top_representantes = (
            resultados
            .groupby(['cedula_representante', 'nombre_representante'])
            .agg({'total_donado': 'sum', 'num_contratos': 'sum'})
            .reset_index()
            .nlargest(15, 'total_donado')
        )

        fig2 = px.bar(
            top_representantes,
            y='nombre_representante',
            x='total_donado',
            orientation='h',
            color='num_contratos',
            color_continuous_scale='Blues',
            labels={
                'nombre_representante': 'Representante',
                'total_donado': 'Total Donado (₡)',
                'num_contratos': 'Contratos'
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
        'nombre_empresa',
        'num_contratos',
        'nombre_representante',
        'partido_donado',
        'total_donado',
        'clasificacion_representante',
        'num_donaciones'
    ]

    tabla_final = tabla_display[columnas_mostrar].sort_values('total_donado', ascending=False)

    tabla_final['total_donado'] = tabla_final['total_donado'].astype(int)
    
    tabla_final = tabla_final.rename(columns={
        'nombre_empresa': 'Empresa',
        'num_contratos': 'Contratos',
        'nombre_representante': 'Representante',
        'partido_donado': 'Partido',
        'total_donado': 'Total Donado',
        'clasificacion_representante': 'Clasificación',
        'num_donaciones': 'Nº Donaciones'
    })
    st.dataframe(
        tabla_final, 
        use_container_width=True, 
        column_config={
            "total_donado": st.column_config.NumberColumn(
                format="₡%.0f"
            )
        },
        )

    # Botón de descarga
    csv = resultados.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name='analisis_empresas_representantes.csv',
        mime='text/csv'
    )

def mostrar_resumen_empresas(resultados):
    st.markdown("#### Resumen por Empresa")

    resumen_empresa = (
        resultados
        .groupby(['cedula_juridica', 'nombre_empresa'])
        .agg({
            'num_contratos': 'first',
            'total_donado': 'sum',
            'cedula_representante': 'count',
            'partido_donado': lambda x: ', '.join(sorted(set(x)))
        })
        .reset_index()
        .sort_values('total_donado', ascending=False)
    )

    st.dataframe(
        resumen_empresa[[
            'nombre_empresa',
            'num_contratos',
            'total_donado',
            'partido_donado'
        ]].rename(columns={
            'nombre_empresa': 'Empresa',
            'num_contratos': 'Contratos',
            'total_donado': 'Total Donado',
            'partido_donado': 'Partidos'
        }),
        use_container_width=True,
        height=600
    )

def mostrar_resumen_representantes(resultados):
    st.markdown("#### Resumen por Representante")

    resumen_representante = (
        resultados
        .groupby(['cedula_representante', 'nombre_representante'])
        .agg({
            'total_donado': 'sum',
            'num_donaciones': 'sum',
            'cedula_juridica': 'count',
            'partido_donado': lambda x: ', '.join(sorted(set(x)))
        })
        .rename(columns={'cedula_juridica': 'num_empresas'})
        .reset_index()
        .sort_values('total_donado', ascending=False)
    )

    st.dataframe(
        resumen_representante[[
            'nombre_representante',
            'num_empresas',
            'num_donaciones',
            'total_donado',
            'partido_donado'
        ]].rename(columns={
            'nombre_representante': 'Representante',
            'num_empresas': 'Empresas Representadas',
            'num_donaciones': 'Nº Donaciones',
            'total_donado': 'Total Donado',
            'partido_donado': 'Partidos'
        }),
        use_container_width=True,
        height=600
    )
