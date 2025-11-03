import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from datetime import datetime, timedelta
import os

# Configure page to use wide layout
st.set_page_config(
    page_title="Rastreador de Donaciones",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to maximize content width
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding-left: 1rem;
        padding-right: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("Rastreador de Donaciones - Análisis de Aportaciones")

@st.cache_data
def load_aportaciones_from_file(file_path):
    if file_path is not None:
        return pd.read_excel(file_path, sheet_name='BBDD')
    return None

@st.cache_data
def load_contratos_from_folder(folder_path):
    if folder_path and os.path.exists(folder_path):
        try:
            all_files = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith('.xlsx')
            ]

            dataframes = []
            for file in all_files:
                try:
                    df = pd.read_excel(file, sheet_name='Informacion de contratos')
                    dataframes.append(df)
                except Exception as e:
                    st.warning(f"Skipping file {file} due to error: {e}")

            if dataframes:
                return pd.concat(dataframes, ignore_index=True)
            else:
                st.error("No valid files could be loaded.")
                return None
        except Exception as e:
            st.error(f"Error: {e}")
            return None
    return None

def get_period(year):
    if pd.isna(year):
        return None
    year = year.year
    periodos = {'PPSD':[2022, 2026],
                'PAC':[2018, 2022],
                'PAC':[2014, 2018],
                'PLN':[2010, 2014],
                'PLN':[2006, 2010]}
    
    for partido, periodo in periodos.items():
        if periodo[0] <= year <= periodo[1]:
            return f'{periodo[0]}-{periodo[1]} ({partido})'
    return None

def create_party_color_map(parties):
    """Crea un mapeo consistente de colores para partidos políticos"""
    colors = [
        '#00a74e', '#ff7f0e', '#d62728', '#9edae5', '#9467bd',
        '#ffffff', '#e377c2', '#7f7f7f', '#bcbd22', '#f9ec00',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d3', '#c7c7c7', '#215b9e', '#9edae5'
    ]
    color_map = {}
    for i, party in enumerate(parties):
        color_map[party] = colors[i % len(colors)]
    return color_map

def preparar_contratos(df_contratos):
    """Prepara y normaliza datos de contratos"""
    if df_contratos is None or len(df_contratos) == 0:
        return None
    
    df = df_contratos.copy()
    
    # Buscar columnas de fecha
    fecha_col = None
    for col in df.columns:
        if any(word in col.lower() for word in ['fecha', 'notif']):
            fecha_col = col
            break
    
    if not fecha_col:
        st.error("No se encontró columna de fecha en contratos")
        return None
    
    # Buscar columna de cédula del proveedor
    cedula_col = None
    for col in df.columns:
        if any(word in col.lower() for word in ['cédula', 'cedula', 'proveedor']):
            cedula_col = col
            break
    
    if not cedula_col:
        st.error("No se encontró columna de cédula del proveedor")
        return None
    
    # Renombrar columnas
    df = df.rename(columns={
        fecha_col: 'fecha_notificacion',
        cedula_col: 'cedula_proveedor'
    })
    
    # Convertir fecha
    df['fecha_notificacion'] = pd.to_datetime(df['fecha_notificacion'], errors='coerce')
    
    # Normalizar cédula
    df['cedula_proveedor'] = df['cedula_proveedor'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    
    # Eliminar filas con fecha inválida
    df = df.dropna(subset=['fecha_notificacion'])
    
    return df

def preparar_donaciones(df_donaciones):
    """Prepara y normaliza datos de donaciones"""
    if df_donaciones is None or len(df_donaciones) == 0:
        return None
    
    df = df_donaciones.copy()
    
    # Normalizar cédula (ya se hace en el main, pero por consistencia)
    df['CÉDULA'] = df['CÉDULA'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    
    return df

def detectar_alertas_temporales(df_contratos, df_donaciones, ventana_meses=6):
    """Detecta casos donde una donación y un contrato ocurren en menos de X meses"""
    
    if df_contratos is None or df_donaciones is None:
        return pd.DataFrame()
    
    # Encontrar coincidencias
    cedulas_contratos = set(df_contratos['cedula_proveedor'].unique())
    cedulas_donaciones = set(df_donaciones['CÉDULA'].unique())
    coincidencias = cedulas_contratos & cedulas_donaciones
    
    alertas = []
    
    for cedula in coincidencias:
        donaciones = df_donaciones[df_donaciones['CÉDULA'] == cedula]
        contratos = df_contratos[df_contratos['cedula_proveedor'] == cedula]
        
        for _, donacion in donaciones.iterrows():
            for _, contrato in contratos.iterrows():
                diferencia_dias = abs((contrato['fecha_notificacion'] - donacion['FECHA']).days)
                diferencia_meses = diferencia_dias / 30.44
                
                if diferencia_meses <= ventana_meses:
                    alerta = {
                        'cedula': cedula,
                        'fecha_donacion': donacion['FECHA'],
                        'fecha_contrato': contrato['fecha_notificacion'],
                        'partido_donado': donacion.get('PARTIDO POLÍTICO', 'N/A'),
                        'monto_donacion': donacion.get('MONTO', 0),
                        'diferencia_dias': diferencia_dias,
                        'diferencia_meses': diferencia_meses,
                        'donacion_antes': donacion['FECHA'] < contrato['fecha_notificacion'],
                        'año_donacion': donacion['FECHA'].year if pd.notna(donacion['FECHA']) else None,
                        'año_contrato': contrato['fecha_notificacion'].year if pd.notna(contrato['fecha_notificacion']) else None
                    }
                    
                    if 'NOMBRE DEL CONTRIBUYENTE' in donacion:
                        alerta['nombre_contribuyente'] = donacion['NOMBRE DEL CONTRIBUYENTE']
                    
                    alertas.append(alerta)
    
    return pd.DataFrame(alertas)

def analizar_contratos_por_partido(df_contratos, df_donaciones, partido_seleccionado=None):
    """Analiza contratos filtrados por partido político"""
    
    if df_contratos is None or df_donaciones is None:
        return None, None
    
    if partido_seleccionado:
        donaciones_partido = df_donaciones[
            df_donaciones['PARTIDO POLÍTICO'].str.upper() == partido_seleccionado.upper()
        ]
        cedulas_partido = set(donaciones_partido['CÉDULA'].unique())
        contratos_donantes = df_contratos[
            df_contratos['cedula_proveedor'].isin(cedulas_partido)
        ].copy()
    else:
        # Encontrar coincidencias generales
        cedulas_contratos = set(df_contratos['cedula_proveedor'].unique())
        cedulas_donaciones = set(df_donaciones['CÉDULA'].unique())
        coincidencias = cedulas_contratos & cedulas_donaciones
        contratos_donantes = df_contratos[
            df_contratos['cedula_proveedor'].isin(coincidencias)
        ].copy()
    
    if len(contratos_donantes) == 0:
        return None, None
    
    # Agrupar por mes
    contratos_mensuales = contratos_donantes.groupby(
        pd.Grouper(key='fecha_notificacion', freq='M')
    ).size().reset_index()
    contratos_mensuales.columns = ['fecha', 'cantidad_contratos']
    
    return contratos_donantes, contratos_mensuales

def main():
    with st.sidebar:

        file_path = st.file_uploader("Archivo de aportaciones (Excel)", type=['xlsx'])

        
        # Verificar si la carpeta de contratos existe
        contratos_folder = "c:\\Users\\Asus\\Desktop\\Rastreador-Donaciones\\Contratos"
        if os.path.exists(contratos_folder):
            archivos_contratos = [f for f in os.listdir(contratos_folder) if f.lower().endswith('.xlsx')]
            if archivos_contratos:
                with st.expander("Ver archivos detectados"):
                    for archivo in archivos_contratos:
                        st.write(f"• {archivo}")
            else:
                st.warning("! Carpeta 'Contratos' está vacía")
        else:
            st.error("X Carpeta 'Contratos' no encontrada")
        
        # Manual path input (optional)
        folder_path = st.text_input("Ruta alternativa de contratos:")
        
        if st.button("Cargar Contratos Manualmente", type="secondary"):
            if folder_path:
                contratos = load_contratos_from_folder(folder_path)
                if contratos is not None:
                    st.session_state['contratos'] = contratos
                    st.success("Contratos cargados exitosamente")
            else:
                st.warning("Por favor ingrese una ruta")
        


    aportaciones = load_aportaciones_from_file(file_path)
    
    if aportaciones is not None:
        # Validación de cédulas: solo mantener registros con cédulas de 7, 8 o 9 dígitos
        initial_count = len(aportaciones)
        
        # Limpiar cédulas: remover espacios, guiones y caracteres no numéricos
        aportaciones['CÉDULA'] = aportaciones['CÉDULA'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        
        # Filtrar cédulas válidas (7, 8 o 9 dígitos)
        valid_cedula_mask = aportaciones['CÉDULA'].str.len().isin([7, 8, 9]) & aportaciones['CÉDULA'].str.isdigit()
        aportaciones = aportaciones[valid_cedula_mask]
        
        filtered_count = len(aportaciones)
        excluded_count = initial_count - filtered_count

        
        active_aportaciones = aportaciones[~aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)]
        
        party_contributions_count = active_aportaciones['PARTIDO POLÍTICO'].value_counts()
        top_20 = party_contributions_count.head(20)
        
        # Crear mapeo de colores consistente para los partidos
        all_parties = active_aportaciones['PARTIDO POLÍTICO'].unique()
        party_colors = create_party_color_map(all_parties)
        
        aportaciones['FECHA'] = pd.to_datetime(aportaciones['FECHA'], errors='coerce')
        aportaciones['PERIODO'] = aportaciones['FECHA'].apply(get_period)

        tab1, tab2, tab3, tab4 = st.tabs(["Partidos", "Cédulas", "Datos", "Análisis de Contratos"])

        with tab1:
            st.header("Análisis de Partidos Políticos")
            
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
                st.metric("Partido Líder (Cantidad)", top_20.index[0] if len(top_20) > 0 else "N/A")
                
                # Calcular partido líder por monto
                party_total_amounts = active_aportaciones.groupby('PARTIDO POLÍTICO')['MONTO'].sum()
                top_amount_party = party_total_amounts.nlargest(1)
                st.metric("Partido Líder (Monto)", top_amount_party.index[0] if len(top_amount_party) > 0 else "N/A")
                
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
        
        with tab2:
            
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
        
        with tab3:            
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
        
        with tab4:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(43, 24, 16, 0.1), rgba(255, 140, 0, 0.1)); 
                        padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem; border-left: 5px solid #ff8c00;">
                <h2 style="color: #2b1810; margin: 0; font-size: 1.8rem;">
                    Análisis de Contratos Post-Electorales
                </h2>
                <p style="color: #5d3317; margin: 0.5rem 0 0 0;">
                    Análisis de la relación temporal entre donaciones políticas y contratos gubernamentales
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Cargar contratos automáticamente desde la carpeta
            contratos_folder = "c:\\Users\\Asus\\Desktop\\Rastreador-Donaciones\\Contratos"
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
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, #ff8c00, #ffa500); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(43, 24, 16, 0.3);">
                            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Total Contratos</h3>
                            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
                        </div>
                        """.format(len(contratos_prep)), unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, #ffffff00, #ff8c00); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(43, 24, 16, 0.3);">
                            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Proveedores Únicos</h3>
                            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
                        </div>
                        """.format(len(cedulas_contratos)), unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, #ffffff00, #d2691e); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(43, 24, 16, 0.3);">
                            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Donantes Únicos</h3>
                            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
                        </div>
                        """.format(len(cedulas_donaciones)), unsafe_allow_html=True)
                    
                    with col4:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, #ffffff00, #8b4513); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(43, 24, 16, 0.3);">
                            <h3 style="color: white; margin: 0; font-size: 1.1rem;">Coincidencias</h3>
                            <h2 style="color: white; margin: 0.5rem 0 0 0; font-size: 2rem;">{:,}</h2>
                        </div>
                        """.format(len(coincidencias)), unsafe_allow_html=True)
                    
                    # Controles para el análisis
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
                    
                    # Detectar alertas
                    if st.button("Analizar Alertas Temporales", type="primary"):
                        with st.spinner("Analizando relaciones temporales..."):
                            alertas = detectar_alertas_temporales(contratos_prep, donaciones_prep, ventana_meses)
                            
                            if partido_filtro != 'Todos':
                                alertas = alertas[alertas['partido_donado'].str.upper() == partido_filtro.upper()]
                            
                            if len(alertas) > 0:
                                st.success(f"Se detectaron {len(alertas)} alertas temporales")
                                
                                # Mostrar estadísticas de alertas
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
                                
                                # Distribución por partido (solo si no se filtró)
                                if partido_filtro == 'Todos':
                                    st.markdown("### Alertas por Partido")
                                    alertas_por_partido = alertas['partido_donado'].value_counts().head(10)
                                    
                                    fig_alertas = px.bar(
                                        x=alertas_por_partido.values,
                                        y=alertas_por_partido.index,
                                        orientation='h',
                                        title='Top 10 Partidos con Más Alertas',
                                        labels={'x': 'Número de Alertas', 'y': 'Partido Político'},
                                        color=alertas_por_partido.values,
                                        color_continuous_scale='Reds',
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
                                    title='Relación Temporal: Donaciones vs Contratos',
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
                                
                                # Tabla de alertas más críticas
                                st.markdown("### Top 20 Alertas Más Críticas")
                                alertas_criticas = alertas.nsmallest(20, 'diferencia_dias')
                                
                                # Preparar datos para mostrar
                                tabla_alertas = alertas_criticas[['cedula', 'partido_donado', 'fecha_donacion', 
                                                                'fecha_contrato', 'diferencia_dias', 'monto_donacion', 
                                                                'donacion_antes']].copy()
                                
                                tabla_alertas['secuencia'] = tabla_alertas['donacion_antes'].map({
                                    True: 'Donación → Contrato',
                                    False: 'Contrato → Donación'
                                })
                                
                                tabla_alertas = tabla_alertas.drop('donacion_antes', axis=1)
                                tabla_alertas.columns = ['Cédula', 'Partido', 'Fecha Donación', 'Fecha Contrato', 
                                                       'Días Diferencia', 'Monto Donación', 'Secuencia']
                                
                                st.dataframe(
                                    tabla_alertas,
                                    column_config={
                                        "Monto Donación": st.column_config.NumberColumn(
                                            "Monto Donación (₡)",
                                            format="₡%.0f"
                                        ),
                                        "Días Diferencia": st.column_config.NumberColumn(
                                            "Días de Diferencia",
                                            format="%.0f días"
                                        )
                                    },
                                    use_container_width=True
                                )
                                
                                # Opción de descarga
                                csv_alertas = alertas.to_csv(index=False)
                                st.download_button(
                                    label="Descargar Alertas (CSV)",
                                    data=csv_alertas,
                                    file_name=f'alertas_contratos_{ventana_meses}meses.csv',
                                    mime='text/csv'
                                )
                                
                            else:
                                if partido_filtro != 'Todos':
                                    st.info(f"No se detectaron alertas para {partido_filtro} en una ventana de {ventana_meses} meses")
                                else:
                                    st.info(f"No se detectaron alertas temporales en una ventana de {ventana_meses} meses")
                    
                    # Análisis general de coincidencias
                    st.markdown("### Análisis de Coincidencias Generales")
                    
                    if len(coincidencias) > 0:
                        contratos_coincidencias = contratos_prep[
                            contratos_prep['cedula_proveedor'].isin(coincidencias)
                        ]
                        
                        # Distribución temporal de contratos de donantes
                        contratos_mensuales = contratos_coincidencias.groupby(
                            pd.Grouper(key='fecha_notificacion', freq='M')
                        ).size().reset_index()
                        contratos_mensuales.columns = ['fecha', 'cantidad_contratos']
                        
                        if len(contratos_mensuales) > 0:
                            fig_temporal = px.line(
                                contratos_mensuales,
                                x='fecha',
                                y='cantidad_contratos',
                                title='Evolución Temporal de Contratos (Proveedores que son Donantes)',
                                labels={'fecha': 'Fecha', 'cantidad_contratos': 'Contratos por Mes'},
                                height=400
                            )
                            
                            # Marcar elecciones
                            elecciones = [
                                {'fecha': '2010-02-07', 'partido': 'PLN'},
                                {'fecha': '2014-02-02', 'partido': 'PAC'},
                                {'fecha': '2018-04-01', 'partido': 'PAC'},
                                {'fecha': '2022-04-03', 'partido': 'PPSD'}
                            ]
                            
                            for eleccion in elecciones:
                                fecha_elec = pd.to_datetime(eleccion['fecha'])
                                if (fecha_elec >= contratos_mensuales['fecha'].min() and 
                                    fecha_elec <= contratos_mensuales['fecha'].max()):
                                    fig_temporal.add_vline(
                                        x=fecha_elec,
                                        line_dash="dash",
                                        line_color="red",
                                        annotation_text=f"Elección {eleccion['partido']}"
                                    )
                            
                            st.plotly_chart(fig_temporal, use_container_width=True)
                    else:
                        st.info("No se encontraron coincidencias entre donantes y proveedores")
                
                else:
                    st.error("No se pudieron preparar los datos de contratos o donaciones")
            else:
                st.warning("No se pudieron cargar los contratos. Verifique que la carpeta 'Contratos' esté disponible.")
    
    else:
        st.markdown("""
        ## Bienvenido al Rastreador de Donaciones
        
        ### Instrucciones de Uso:
        
        1. **Cargar Datos**: Use la barra lateral para subir el archivo Excel de aportaciones
        2. **Contratos**: Opcionalmente, ingrese la ruta de la carpeta de contratos
        3. **Análisis**: Use las pestañas para navegar entre diferentes análisis
        4. **Exportar**: Descargue los resultados en formato CSV
        
        ### Características:
        
        - Análisis interactivo de partidos políticos
        - Visualización de ingresos anuales
        - Análisis detallado de donantes
        - Vista completa de datos
        - Métricas en tiempo real
        - Rankings y estadísticas
        
        **Comience cargando sus datos usando la barra lateral**
        """)
    
    st.markdown("---")
    st.markdown("**Rastreador de Donaciones** - Dashboard de Análisis Político")
    

if __name__ == "__main__":
    main()