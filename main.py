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
from tabs import mostrar_tab_partidos, mostrar_tab_datos, mostrar_tab_contratos, mostrar_tab_empresas

CONTRATOS_PATH = './contratos2.xlsx'
DONACIONES_PATH = './donaciones.xlsx'
REPRESENTANTES_PATH = './representantes_juridicas.xlsx'

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
def load_file(file_path):
    if file_path is not None:
        return pd.read_excel(file_path)
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

def main():
    # Cargar datos locales automáticamente al inicio
    donaciones = None
    contratos = None
    representantes = None

    if 'donaciones' not in st.session_state:
        donaciones = load_file(DONACIONES_PATH)
        if donaciones is not None:
            st.session_state['donaciones'] = donaciones
    
    if 'contratos' not in st.session_state:
        contratos = load_file(CONTRATOS_PATH)
        if contratos is not None:
            st.session_state['contratos'] = contratos

    if 'representantes' not in st.session_state:
        representantes = load_file(REPRESENTANTES_PATH)
        if representantes is not None:
            st.session_state['representantes'] = representantes

    with st.sidebar:
        # Sección de donaciones
        st.markdown("### 📊 Donaciones")

        donaciones_path = st.file_uploader("Subir archivo personalizado (Excel)", type=['xlsx'], key="donaciones_upload")
        
        if donaciones_path is not None:
            try:
                donaciones = load_file(donaciones_path)
                st.session_state['donaciones'] = donaciones
                st.info(f"📄 {donaciones_path.name}")
            except Exception as e:
                st.error(f"Error al cargar donaciones: {e}")

        st.markdown("---")

        # Sección de contratos
        st.markdown("### 📋 Contratos")

        # Opción para subir archivo personalizado de contratos
        contratos_file = st.file_uploader("Subir archivo personalizado (Excel)", type=['xlsx'], key="contratos_upload")

        if contratos_file is not None:
            try:
                contratos = load_file(contratos_file)
                st.session_state['contratos'] = contratos
                st.info(f"📄 {contratos_file.name}")
            except Exception as e:
                st.error(f"Error al cargar contratos: {e}")

        st.markdown("---")

        # Sección de representantes legales
        st.markdown("### 🏢 Representantes Legales")

        # Opción para subir archivo de representantes
        representantes_file = st.file_uploader("Subir archivo personalizado (Excel)", type=['xlsx'], key="representantes_upload")

        if representantes_file is not None:
            try:
                representantes = load_file(representantes_file)
                st.session_state['representantes'] = representantes
                st.info(f"📄 {representantes_file.name}")
                st.caption(f"{len(representantes):,} registros")
            except Exception as e:
                st.error(f"Error al cargar representantes: {e}")
    
    # Obtener datos de session_state
    donaciones = st.session_state.get('donaciones')
    contratos = st.session_state.get('contratos')
    representantes = st.session_state.get('representantes')
    
    # Solo proceder si tenemos donaciones cargadas
    if donaciones is None:
        st.warning("⚠️ No hay datos de donaciones cargados. Por favor, suba un archivo.")
        return
    
    # Limpiar cédulas: remover espacios, guiones y caracteres no numéricos
    donaciones['CÉDULA'] = donaciones['CÉDULA'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    
    # Filtrar cédulas válidas (7, 8 o 9 dígitos)
    valid_cedula_mask = donaciones['CÉDULA'].str.len().isin([7, 8, 9]) & donaciones['CÉDULA'].str.isdigit()
    donaciones = donaciones[valid_cedula_mask]
    
    # Validación de fechas si la columna existe
    if 'FECHA' in donaciones.columns:
        donaciones['FECHA'] = pd.to_datetime(donaciones['FECHA'], errors='coerce', dayfirst=True)
        # Eliminar registros con fechas inválidas
        fecha_valida_mask = donaciones['FECHA'].notna()
        donaciones = donaciones[fecha_valida_mask]
            
    donaciones['FECHA'] = pd.to_datetime(donaciones['FECHA'], errors='coerce')
    donaciones['PERIODO'] = donaciones['FECHA'].apply(get_period)
    
    tab1, tab4, tab5, tab3 = st.tabs(["Partidos", "Análisis de Contratos", "Empresas y Representantes", "Datos"])

    with tab1:
        mostrar_tab_partidos(donaciones)

    with tab3:
        mostrar_tab_datos(donaciones)

    with tab4:
        mostrar_tab_contratos(donaciones, contratos)

    with tab5:
        mostrar_tab_empresas(donaciones, contratos, representantes)

    

if __name__ == "__main__":
    main()
