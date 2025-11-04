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

# Importar las tabs modularizadas
from tabs import mostrar_tab_partidos, mostrar_tab_datos, mostrar_tab_contratos

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
.st-emotion-cache-zy6yx3{
        padding-top: 3rem;
            }
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
def load_aportaciones_local():
    """Carga aportaciones desde archivo local"""
    try:
        return pd.read_excel('./acumulado.xlsx', sheet_name='BBDD')
    except:
        return None

@st.cache_data
def load_contratos_local():
    """Carga contratos desde archivo local"""
    try:
        return pd.read_excel('./contratos_completo_todas_columnas.xlsx')
    except:
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

def preparar_donaciones(df_donaciones):
    """Prepara y normaliza datos de donaciones"""
    if df_donaciones is None or len(df_donaciones) == 0:
        return None
    
    df = df_donaciones.copy()
    
    # Normalizar cédula
    df['CÉDULA'] = df['CÉDULA'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    
    # Convertir fechas si existe la columna FECHA
    if 'FECHA' in df.columns:
        df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce', dayfirst=True)
    
    # Eliminar filas con cédulas vacías
    df = df[df['CÉDULA'].str.len() > 0]
    
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
                # Convertir a timestamp si es necesario para el cálculo
                fecha_donacion = pd.to_datetime(donacion['FECHA'])
                fecha_contrato = pd.to_datetime(contrato['fecha_notificacion'])
                
                # Calcular diferencia usando timedelta
                diferencia_timedelta = abs(fecha_contrato - fecha_donacion)
                diferencia_dias = diferencia_timedelta.days
                diferencia_meses = diferencia_dias / 30.44
                
                if diferencia_meses <= ventana_meses:
                    alerta = {
                        'cedula': cedula,
                        'fecha_donacion': fecha_donacion,
                        'fecha_contrato': fecha_contrato,
                        'partido_donado': donacion.get('PARTIDO POLÍTICO', 'N/A'),
                        'monto_donacion': donacion.get('MONTO', 0),
                        'diferencia_dias': diferencia_dias,
                        'diferencia_meses': diferencia_meses,
                        'donacion_antes': fecha_donacion < fecha_contrato,
                        'año_donacion': fecha_donacion.year if pd.notna(fecha_donacion) else None,
                        'año_contrato': fecha_contrato.year if pd.notna(fecha_contrato) else None,
                        'nro_contrato': contrato.get('nro_contrato', 'N/A') if 'nro_contrato' in contrato else 'N/A'
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
    
    # Agrupar por mes - Asegurar que las fechas sean válidas
    contratos_validos = contratos_donantes.dropna(subset=['fecha_notificacion']).copy()
    contratos_mensuales = contratos_validos.groupby(
        pd.Grouper(key='fecha_notificacion', freq='ME')
    ).size().reset_index()
    contratos_mensuales.columns = ['fecha', 'cantidad_contratos']
    
    return contratos_donantes, contratos_mensuales

def main():
    # Cargar datos locales automáticamente al inicio
    if 'aportaciones_local' not in st.session_state:
        aportaciones_local = load_aportaciones_local()
        if aportaciones_local is not None:
            st.session_state['aportaciones_local'] = aportaciones_local
    
    if 'contratos' not in st.session_state:
        contratos_local = load_contratos_local()
        if contratos_local is not None:
            st.session_state['contratos'] = contratos_local

    with st.sidebar:
        # Sección de aportaciones
        st.markdown("### 📊 Aportaciones")
        
        # Mostrar estado del archivo local
        if os.path.exists('./aportaciones.xlsx'):
            st.info("📄 ./aportaciones.xlsx")

        file_path = st.file_uploader("Subir archivo personalizado (Excel)", type=['xlsx'], key="aportaciones_upload")

        st.markdown("---")
        
        # Sección de contratos
        st.markdown("### 📋 Contratos")
        
        # Opción para subir archivo personalizado de contratos
        contratos_file = st.file_uploader("Subir archivo personalizado (Excel)", type=['xlsx'], key="contratos_upload")
        
        if contratos_file is not None:
            try:
                contratos = pd.read_excel(contratos_file)
                st.session_state['contratos'] = contratos
                st.info(f"📄 {contratos_file.name}")
            except Exception as e:
                st.error(f"Error al cargar contratos: {e}")

    # Determinar qué archivo de aportaciones usar
    aportaciones = None
    if file_path is not None:
        # Usar archivo subido por el usuario
        aportaciones = load_aportaciones_from_file(file_path)
        st.success("📤 Usando aportaciones subidas por el usuario")
    elif 'aportaciones_local' in st.session_state:
        # Usar archivo local
        aportaciones = st.session_state['aportaciones_local']
        st.info("📂 Usando aportaciones del archivo local")
    
    if aportaciones is not None:
        # Validación de cédulas: solo mantener registros con cédulas de 7, 8 o 9 dígitos
        initial_count = len(aportaciones)
        
        # Limpiar cédulas: remover espacios, guiones y caracteres no numéricos
        aportaciones['CÉDULA'] = aportaciones['CÉDULA'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        
        # Filtrar cédulas válidas (7, 8 o 9 dígitos)
        valid_cedula_mask = aportaciones['CÉDULA'].str.len().isin([7, 8, 9]) & aportaciones['CÉDULA'].str.isdigit()
        aportaciones = aportaciones[valid_cedula_mask]
        
        # Validación de fechas si la columna existe
        if 'FECHA' in aportaciones.columns:
            aportaciones['FECHA'] = pd.to_datetime(aportaciones['FECHA'], errors='coerce', dayfirst=True)
            # Eliminar registros con fechas inválidas
            fecha_valida_mask = aportaciones['FECHA'].notna()
            aportaciones = aportaciones[fecha_valida_mask]
        
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

        tab1, tab3, tab4 = st.tabs(["Partidos", "Datos", "Análisis de Contratos"])

        with tab1:
            mostrar_tab_partidos(aportaciones, party_colors)
        
        with tab3:
            mostrar_tab_datos(aportaciones)
        
        with tab4:
            mostrar_tab_contratos(
                aportaciones, 
                preparar_donaciones
            )
    
    else:
        st.markdown("""
        ## Bienvenido al Rastreador de Donaciones
        
        ### Sistema de Carga Automática:
        
        El sistema intenta cargar automáticamente:
        - **Aportaciones**: `./aportaciones.xlsx` (hoja 'BBDD')
        - **Contratos**: `./contratos_completo_todas_columnas.xlsx`
        
        ### Personalización:
        
        Puede subir sus propios archivos usando la barra lateral para:
        - Reemplazar los datos de aportaciones
        - Reemplazar los datos de contratos
        
        ### Análisis Disponibles:
        
        1. **Partidos**: Análisis interactivo de partidos políticos
        2. **Datos**: Visualización completa de datos y métricas
        3. **Contratos**: Análisis de contratos post-electorales con alertas temporales
        
        ### Características:
        
        - Carga automática de archivos locales
        - Análisis en tiempo real
        - Visualizaciones interactivas
        - Detección de alertas temporales
        - Exportación de resultados
        
        **Los datos se cargan automáticamente si están disponibles**
        """)
    
    st.markdown("---")
    st.markdown("**Rastreador de Donaciones** - Dashboard de Análisis Político")
    

if __name__ == "__main__":
    main()
