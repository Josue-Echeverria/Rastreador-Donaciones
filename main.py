import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from datetime import datetime, timedelta
import os

# Configure page to use wide layout
st.set_page_config(
    page_title="Rastreador de Donaciones",
    page_icon="📊",
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
                'PAC 2':[2018, 2022],
                'PAC':[2014, 2018],
                'PLN':[2010, 2014],
                'PLN 2':[2006, 2010]}
    
    for partido, periodo in periodos.items():
        if periodo[0] <= year <= periodo[1]:
            return f'{periodo[0]}-{periodo[1]} ({partido})'
    return None

def main():
    with st.sidebar:
        st.header("Cargar Datos")
        file_path = st.file_uploader("Archivo de aportaciones (Excel)", type=['xlsx'])
        
        st.header("Contratos")
        folder_path = st.text_input("Ruta de la carpeta de contratos:")
        
        if st.button("Cargar Contratos", type="primary"):
            contratos = load_contratos_from_folder(folder_path)
            if contratos is not None:
                st.session_state['contratos'] = contratos
                st.success("Contratos cargados exitosamente")
    
    aportaciones = load_aportaciones_from_file(file_path)
    
    if aportaciones is not None:
        st.success("Archivo de aportaciones cargado exitosamente")
        
        active_aportaciones = aportaciones[~aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)]
        
        party_contributions_count = active_aportaciones['PARTIDO POLÍTICO'].value_counts()
        top_20 = party_contributions_count.head(10)
        
        aportaciones['FECHA'] = pd.to_datetime(aportaciones['FECHA'], errors='coerce')
        aportaciones['PERIODO'] = aportaciones['FECHA'].apply(get_period)
        
        tab1, tab2, tab3, tab4 = st.tabs(["Partidos", "Ingresos", "Cédulas", "Datos"])
        
        with tab1:
            st.header("Análisis de Partidos Políticos")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Top 10 Partidos por Número de Aportaciones")
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.barh(top_20.index, top_20.values, color='skyblue')
                ax.set_title('Top 10 Partidos Políticos')
                ax.invert_yaxis()
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.subheader("Resumen")
                st.metric("Total Partidos Activos", len(active_aportaciones['PARTIDO POLÍTICO'].unique()))
                st.metric("Total Aportaciones", len(active_aportaciones))
                st.metric("Partido Líder", top_20.index[0] if len(top_20) > 0 else "N/A")
                
                st.subheader("Top 5 Detalle")
                top_5_df = pd.DataFrame({
                    'Partido': top_20.head(5).index,
                    'Aportaciones': top_20.head(5).values
                })
                st.dataframe(top_5_df, use_container_width=True)
        
        with tab2:
            st.header("Análisis de Ingresos")
            
            aportaciones_valid_dates = aportaciones.dropna(subset=['FECHA'])
            aportaciones_valid_dates['MONTH_YEAR'] = aportaciones_valid_dates['FECHA'].dt.to_period('M')
            monthly_income = aportaciones_valid_dates.groupby(['PARTIDO POLÍTICO', 'MONTH_YEAR'])['MONTO'].sum().reset_index()
            monthly_income['MONTH_YEAR'] = monthly_income['MONTH_YEAR'].dt.to_timestamp()
            
            top_parties_list = top_20.index.tolist()
            monthly_income_filtered = monthly_income[monthly_income['PARTIDO POLÍTICO'].isin(top_parties_list)].copy()
            monthly_income_filtered['MONTO'] = monthly_income_filtered['MONTO'] / 1_000_000
            monthly_income_filtered['YEAR'] = monthly_income_filtered['MONTH_YEAR'].dt.to_period('Y').astype(str)
            
            yearly_income = monthly_income_filtered.groupby(['PARTIDO POLÍTICO', 'YEAR'])['MONTO'].sum().reset_index()
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("Ingresos Anuales por Partido (Top 10)")
                fig2, ax2 = plt.subplots(figsize=(20, 7))
                sns.barplot(data=yearly_income, x='YEAR', y='MONTO', hue='PARTIDO POLÍTICO', dodge=False, ax=ax2)
                ax2.set_title('Ingresos Anuales por Partido')
                ax2.set_xlabel('Año')
                ax2.set_ylabel('Ingresos (Millones ₡)')
                plt.xticks(rotation=90)
                plt.tight_layout()
                st.pyplot(fig2)
            
            with col2:
                st.subheader("Métricas de Ingresos")
                total_income = aportaciones['MONTO'].sum()
                avg_donation = aportaciones['MONTO'].mean()
                max_donation = aportaciones['MONTO'].max()
                
                st.metric("Total Recaudado", f"₡{total_income:,.0f}")
                st.metric("Donación Promedio", f"₡{avg_donation:,.0f}")
                st.metric("Donación Máxima", f"₡{max_donation:,.0f}")
                
                st.subheader("Por Año")
                year_summary = yearly_income.groupby('YEAR')['MONTO'].sum().sort_values(ascending=False)
                for year, amount in year_summary.head(5).items():
                    st.metric(f"Año {year}", f"₡{amount:,.1f}M")
        
        with tab3:
            st.header("Análisis de Cédulas")
            
            cedula_counts = aportaciones['CÉDULA'].value_counts().head(20)
            cedula_amounts = aportaciones.groupby('CÉDULA')['MONTO'].sum()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Donaciones por Cédula")
                
                combined_data = pd.DataFrame({
                    'Cantidad_Donaciones': cedula_counts,
                    'Monto_Total': cedula_amounts.loc[cedula_counts.index],
                }).reset_index()
                combined_data.columns = ['Cédula', 'Cantidad de Donaciones', 'Monto Total']
                
                st.dataframe(
                    combined_data,
                    column_config={
                        "Monto Total": st.column_config.ProgressColumn(
                            "Monto Total (₡)",
                            help="Monto total donado por cada cédula",
                            min_value=0,
                            max_value=int(combined_data['Monto Total'].max()),
                            format="₡%.0f"
                        )
                    },
                    use_container_width=True
                )
            
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
                
                st.subheader("Top Donantes")
                top_amounts = cedula_amounts.sort_values(ascending=False).head(5)
                for cedula, amount in top_amounts.items():
                    st.metric(f"Cédula {cedula}", f"₡{amount:,.0f}")
        
        with tab4:
            st.header("Vista de Datos")
            
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