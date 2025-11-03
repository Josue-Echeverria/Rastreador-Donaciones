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
from tabs import mostrar_tab_partidos, mostrar_tab_cedulas, mostrar_tab_datos, mostrar_tab_contratos

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
                contratos_raw = pd.concat(dataframes, ignore_index=True)
                print("aopfingaoív: ",len(contratos_raw))
                return contratos_raw
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
    
    # Buscar columna de número de contrato
    contrato_col = None
    for col in df.columns:
        if any(word in col.lower() for word in ['nro', 'numero', 'contrato', 'número']):
            contrato_col = col
            break
    
    if not contrato_col:
        st.warning("No se encontró columna de número de contrato")
    
    # Renombrar columnas
    rename_dict = {
        fecha_col: 'fecha_notificacion',
        cedula_col: 'cedula_proveedor'
    }
    if contrato_col:
        rename_dict[contrato_col] = 'nro_contrato'
    
    df = df.rename(columns=rename_dict)
    
    # Convertir fecha con formato más robusto
    df['fecha_notificacion'] = pd.to_datetime(df['fecha_notificacion'], errors='coerce', dayfirst=True)
    
    # Normalizar cédula
    df['cedula_proveedor'] = df['cedula_proveedor'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    
    # Eliminar filas con fecha inválida o cédulas vacías
    df = df.dropna(subset=['fecha_notificacion'])
    df = df[df['cedula_proveedor'].str.len() > 0]
    
    return df

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

        tab1, tab2, tab3, tab4 = st.tabs(["Partidos", "Cédulas", "Datos", "Análisis de Contratos"])

        with tab1:
            mostrar_tab_partidos(aportaciones, party_colors)
        
        with tab2:
            mostrar_tab_cedulas(aportaciones)
        
        with tab3:
            mostrar_tab_datos(aportaciones)
        
        with tab4:
            mostrar_tab_contratos(
                aportaciones, 
                contratos_folder, 
                preparar_contratos, 
                preparar_donaciones, 
                detectar_alertas_temporales, 
                load_contratos_from_folder
            )
    
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
