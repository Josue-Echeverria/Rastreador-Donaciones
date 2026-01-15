import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import io


class AnalizadorCedulasJuridicas:
    """
    Clase para analizar la relación entre cédulas jurídicas con múltiples contratos
    y las donaciones de sus representantes legales
    """

    def __init__(self, df_contratos, df_aportaciones, df_representantes):
        """
        Inicializa el analizador

        Parámetros:
        -----------
        df_contratos : DataFrame con contratos gubernamentales
        df_aportaciones : DataFrame con aportaciones políticas
        df_representantes : DataFrame con representantes legales de empresas
        """
        self.df_contratos = df_contratos.copy()
        self.df_aportaciones = df_aportaciones.copy()
        self.df_representantes = df_representantes.copy()

        # Normalizar columnas de representantes
        self._normalizar_representantes()

        # Preparar datos
        self._preparar_datos()

    def _normalizar_representantes(self):
        """Normaliza las columnas del DataFrame de representantes"""
        # Mapeo de nombres de columnas
        mapeo = {}

        for col in self.df_representantes.columns:
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

        self.df_representantes = self.df_representantes.rename(columns=mapeo)

        # Normalizar cédulas
        if 'cedula_juridica' in self.df_representantes.columns:
            self.df_representantes['cedula_juridica'] = (
                self.df_representantes['cedula_juridica']
                .astype(str)
                .str.replace('-', '')
                .str.strip()
            )

        if 'cedula_identidad' in self.df_representantes.columns:
            self.df_representantes['cedula_identidad'] = (
                self.df_representantes['cedula_identidad']
                .astype(str)
                .str.replace('-', '')
                .str.strip()
            )

    def _preparar_datos(self):
        """Prepara los datos de contratos y aportaciones"""
        # Detectar y normalizar columnas de contratos
        for col in self.df_contratos.columns:
            col_lower = col.lower()
            if 'cédula' in col_lower and 'proveedor' in col_lower:
                self.df_contratos['cedula_proveedor'] = (
                    self.df_contratos[col]
                    .astype(str)
                    .str.replace('-', '')
                    .str.strip()
                )
                break
            elif 'cedula' in col_lower and 'proveedor' in col_lower:
                self.df_contratos['cedula_proveedor'] = (
                    self.df_contratos[col]
                    .astype(str)
                    .str.replace('-', '')
                    .str.strip()
                )
                break

        # Normalizar cédulas en aportaciones
        if 'CÉDULA' in self.df_aportaciones.columns:
            self.df_aportaciones['cedula'] = (
                self.df_aportaciones['CÉDULA']
                .astype(str)
                .str.replace('-', '')
                .str.strip()
            )

    def analizar_empresas_contratos_donaciones(self, min_contratos=5, min_donacion=50000, partido=None):
        """
        Identifica empresas con múltiples contratos cuyos representantes han donado al partido
        """
        # 1. Contar contratos por empresa
        contratos_por_empresa = (
            self.df_contratos
            .groupby('cedula_proveedor')
            .size()
            .reset_index(name='num_contratos')
        )

        # Filtrar empresas con suficientes contratos
        empresas_interes = contratos_por_empresa[
            contratos_por_empresa['num_contratos'] >= min_contratos
        ]

        # 2. Obtener representantes de estas empresas
        representantes_empresas = self.df_representantes[
            self.df_representantes['cedula_juridica'].isin(empresas_interes['cedula_proveedor'])
        ].copy()

        # 3. Buscar donaciones de estos representantes
        cedulas_representantes = set(representantes_empresas['cedula_identidad'].unique())

        donaciones_representantes = self.df_aportaciones[
            self.df_aportaciones['cedula'].isin(cedulas_representantes)
        ].copy()

        # Filtrar por partido si se especificó
        if partido:
            col_partido = 'PARTIDO POLÍTICO'
            donaciones_representantes = donaciones_representantes[
                donaciones_representantes[col_partido].str.upper() == partido.upper()
            ]

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

        # Filtrar donaciones significativas
        donaciones_significativas = donaciones_agregadas[
            donaciones_agregadas['total_donado'] >= min_donacion
        ]

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

        df_resultados = pd.DataFrame(resultados)

        if len(df_resultados) > 0:
            # Ordenar por número de contratos y monto donado
            df_resultados = df_resultados.sort_values(
                ['num_contratos', 'total_donado'],
                ascending=[False, False]
            )

        return df_resultados


def mostrar_tab_empresas(aportaciones):
    """
    Tab principal para análisis de cédulas jurídicas y representantes
    """
    st.markdown("## Análisis de Empresas y Representantes Legales")

    st.markdown("""
    Este análisis identifica **empresas (cédulas jurídicas)** con múltiples contratos gubernamentales
    cuyos **representantes legales** han realizado donaciones significativas a partidos políticos.
    """)

    # Cargar contratos
    contratos_raw = None
    if 'contratos' in st.session_state:
        contratos_raw = st.session_state['contratos']
    else:
        try:
            contratos_raw = pd.read_excel('./contratos.xlsx')
            st.session_state['contratos'] = contratos_raw
        except:
            st.warning("⚠️ No se pudo cargar el archivo de contratos")
            return

    # Verificar si hay datos de representantes
    if 'representantes' not in st.session_state:
        st.info("""
        ### No hay datos de representantes legales cargados

        **Para usar este análisis:**

        1. Sube un archivo Excel desde la **barra lateral** (sección "🏢 Representantes Legales")

        2. El archivo debe contener las siguientes columnas:
           - `CEDULA_JURIDICA` o `Cédula Jurídica`: Identificación de la empresa
           - `NOMBRE_EMPRESA`: Nombre de la empresa
           - `NOMBRE_EMPLEADO` o `Nombre Representante`: Nombre del representante
           - `CEDULA_IDENTIDAD` o `Cédula Identidad`: Cédula del representante
           - `CLASIFICACION_EMPLEADO` (opcional): Tipo de empleado/representante

        3. Una vez cargado, regresa a este tab para ejecutar el análisis
        """)
        return

    # Obtener datos de representantes
    df_representantes = st.session_state['representantes']

    st.success(f"✅ Datos de representantes cargados: {len(df_representantes):,} registros")

    # Mostrar preview colapsado
    with st.expander("Vista previa de los datos de representantes"):
        st.write("**Columnas encontradas:**")
        st.write(", ".join(df_representantes.columns))
        st.dataframe(df_representantes.head(10), use_container_width=True)

    # Inicializar analizador
    try:
        analizador = AnalizadorCedulasJuridicas(
            df_contratos=contratos_raw,
            df_aportaciones=aportaciones,
            df_representantes=df_representantes
        )

        st.markdown("---")
        st.markdown("### Configurar Análisis")

        col_config1, col_config2, col_config3 = st.columns(3)

        with col_config1:
            min_contratos = st.number_input(
                "Mínimo de contratos",
                min_value=1,
                max_value=100,
                value=5,
                help="Número mínimo de contratos que debe tener la empresa"
            )

        with col_config2:
            min_donacion = st.number_input(
                "Donación mínima (₡)",
                min_value=0,
                max_value=10000000,
                value=50000,
                step=10000,
                help="Monto mínimo de donación para considerar significativa"
            )

        with col_config3:
            # Obtener lista de partidos únicos
            partidos_disponibles = sorted(aportaciones['PARTIDO POLÍTICO'].unique())
            partido_filtro = st.selectbox(
                "Filtrar por partido (opcional)",
                options=['Todos'] + partidos_disponibles,
                help="Analizar solo donaciones a un partido específico"
            )

        # Botón para ejecutar análisis
        if st.button("Ejecutar Análisis", type="primary", use_container_width=True):
            with st.spinner("Analizando datos..."):
                partido_seleccionado = None if partido_filtro == 'Todos' else partido_filtro

                resultados = analizador.analizar_empresas_contratos_donaciones(
                    min_contratos=min_contratos,
                    min_donacion=min_donacion,
                    partido=partido_seleccionado
                )

                # Guardar resultados en session state
                st.session_state['resultados_empresas'] = resultados

        # Mostrar resultados si existen
        if 'resultados_empresas' in st.session_state:
            resultados = st.session_state['resultados_empresas']

            if len(resultados) > 0:
                st.markdown("---")
                st.markdown("### Resultados del Análisis")

                # Métricas principales
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)

                with col_m1:
                    st.metric("Total de Casos", len(resultados))

                with col_m2:
                    empresas_unicas = resultados['cedula_juridica'].nunique()
                    st.metric("Empresas Únicas", empresas_unicas)

                with col_m3:
                    representantes_unicos = resultados['cedula_representante'].nunique()
                    st.metric("Representantes Únicos", representantes_unicos)

                with col_m4:
                    total_donado = resultados['total_donado'].sum()
                    st.metric("Total Donado", f"₡{total_donado:,.0f}")

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
                st.info("**Sugerencias:**\n- Reduzca el número mínimo de contratos\n- Reduzca el monto mínimo de donación\n- Intente con 'Todos' los partidos")

    except Exception as e:
        st.error(f"❌ Error al inicializar el analizador: {e}")
        st.exception(e)


def mostrar_visualizaciones(resultados):
    """Genera visualizaciones de los resultados"""

    # 1. Top empresas por número de contratos
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
    """Muestra tabla con todos los resultados"""
    st.markdown("#### Todos los Casos Encontrados")

    # Preparar datos para mostrar
    tabla_display = resultados.copy()
    tabla_display['total_donado_fmt'] = tabla_display['total_donado'].apply(lambda x: f"₡{x:,.0f}")

    # Seleccionar columnas a mostrar
    columnas_mostrar = [
        'nombre_empresa',
        'num_contratos',
        'nombre_representante',
        'clasificacion_representante',
        'partido_donado',
        'total_donado_fmt',
        'num_donaciones'
    ]

    tabla_final = tabla_display[columnas_mostrar].rename(columns={
        'nombre_empresa': 'Empresa',
        'num_contratos': 'Contratos',
        'nombre_representante': 'Representante',
        'clasificacion_representante': 'Clasificación',
        'partido_donado': 'Partido',
        'total_donado_fmt': 'Total Donado',
        'num_donaciones': 'Nº Donaciones'
    })

    st.dataframe(tabla_final, use_container_width=True, height=600)

    # Botón de descarga
    csv = resultados.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name='analisis_empresas_representantes.csv',
        mime='text/csv'
    )


def mostrar_resumen_empresas(resultados):
    """Muestra resumen agrupado por empresa"""
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
        .rename(columns={'cedula_representante': 'num_representantes_donantes'})
        .reset_index()
        .sort_values('num_contratos', ascending=False)
    )

    resumen_empresa['total_donado_fmt'] = resumen_empresa['total_donado'].apply(lambda x: f"₡{x:,.0f}")

    st.dataframe(
        resumen_empresa[[
            'nombre_empresa',
            'num_contratos',
            'num_representantes_donantes',
            'total_donado_fmt',
            'partido_donado'
        ]].rename(columns={
            'nombre_empresa': 'Empresa',
            'num_contratos': 'Contratos',
            'num_representantes_donantes': 'Representantes que Donaron',
            'total_donado_fmt': 'Total Donado',
            'partido_donado': 'Partidos'
        }),
        use_container_width=True,
        height=600
    )


def mostrar_resumen_representantes(resultados):
    """Muestra resumen agrupado por representante"""
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

    resumen_representante['total_donado_fmt'] = resumen_representante['total_donado'].apply(lambda x: f"₡{x:,.0f}")

    st.dataframe(
        resumen_representante[[
            'nombre_representante',
            'num_empresas',
            'num_donaciones',
            'total_donado_fmt',
            'partido_donado'
        ]].rename(columns={
            'nombre_representante': 'Representante',
            'num_empresas': 'Empresas Representadas',
            'num_donaciones': 'Nº Donaciones',
            'total_donado_fmt': 'Total Donado',
            'partido_donado': 'Partidos'
        }),
        use_container_width=True,
        height=600
    )
