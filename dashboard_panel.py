import panel as pn
import pandas as pd
import hvplot.pandas
import holoviews as hv
from datetime import datetime, timedelta
import os

# Configure Panel
pn.extension('tabulator')
hv.extension('bokeh')

class DonationsDashboard:
    def __init__(self):
        self.aportaciones = None
        self.contratos = None
        self.file_input = pn.widgets.FileInput(accept='.xlsx', multiple=False)
        self.folder_input = pn.widgets.TextInput(placeholder="Ruta de la carpeta de contratos")
        self.load_button = pn.widgets.Button(name="Cargar Datos", button_type="primary")
        
        # Bind events
        self.load_button.on_click(self.load_data)
        
    def get_period(self, year):
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
    
    def load_aportaciones(self):
        if self.file_input.value is not None:
            try:
                # Save uploaded file temporarily
                temp_path = "temp_aportaciones.xlsx"
                with open(temp_path, "wb") as f:
                    f.write(self.file_input.value)
                
                self.aportaciones = pd.read_excel(temp_path, sheet_name='BBDD')
                os.remove(temp_path)
                return True
            except Exception as e:
                print(f"Error loading aportaciones: {e}")
                return False
        return False
    
    def load_contratos(self):
        folder_path = self.folder_input.value
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
                        print(f"Skipping file {file} due to error: {e}")
                
                if dataframes:
                    self.contratos = pd.concat(dataframes, ignore_index=True)
                    return True
            except Exception as e:
                print(f"Error loading contratos: {e}")
        return False
    
    def load_data(self, event=None):
        # Load aportaciones
        if self.load_aportaciones():
            # Process aportaciones data
            self.aportaciones['FECHA'] = pd.to_datetime(self.aportaciones['FECHA'], errors='coerce')
            self.aportaciones['PERIODO'] = self.aportaciones['FECHA'].apply(self.get_period)
        
        # Load contratos
        self.load_contratos()
    
    def create_party_chart(self):
        if self.aportaciones is None:
            return pn.pane.HTML("<p>No data loaded</p>")
        
        # Filter out inactive parties
        active_aportaciones = self.aportaciones[
            ~self.aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)
        ]
        
        party_counts = active_aportaciones['PARTIDO POLÍTICO'].value_counts().head(10)
        
        chart = party_counts.hvplot.barh(
            title="Top 10 Partidos por Número de Aportaciones",
            xlabel="Cantidad de Aportaciones",
            ylabel="Partido Político",
            color="skyblue",
            height=400,
            width=800
        )
        
        return pn.pane.HoloViews(chart)
    
    def create_yearly_income_chart(self):
        if self.aportaciones is None:
            return pn.pane.HTML("<p>No data loaded</p>")
        
        # Process data for yearly income
        active_aportaciones = self.aportaciones[
            ~self.aportaciones['PARTIDO POLÍTICO'].str.endswith('(INACTIVO)', na=False)
        ]
        
        party_counts = active_aportaciones['PARTIDO POLÍTICO'].value_counts().head(10)
        top_parties = party_counts.index.tolist()
        
        aportaciones_valid = self.aportaciones.dropna(subset=['FECHA'])
        aportaciones_valid['YEAR'] = aportaciones_valid['FECHA'].dt.year
        
        yearly_data = aportaciones_valid[
            aportaciones_valid['PARTIDO POLÍTICO'].isin(top_parties)
        ].groupby(['PARTIDO POLÍTICO', 'YEAR'])['MONTO'].sum().reset_index()
        
        yearly_data['MONTO_MILLIONS'] = yearly_data['MONTO'] / 1_000_000
        
        chart = yearly_data.hvplot.bar(
            x='YEAR',
            y='MONTO_MILLIONS',
            by='PARTIDO POLÍTICO',
            title="Ingresos Anuales por Partido (Millones ₡)",
            xlabel="Año",
            ylabel="Ingresos (Millones ₡)",
            height=500,
            width=1000,
            stacked=False
        )
        
        return pn.pane.HoloViews(chart)
    
    def create_cedula_analysis(self):
        if self.aportaciones is None:
            return pn.pane.HTML("<p>No data loaded</p>")
        
        # Count and amounts by cedula
        cedula_counts = self.aportaciones['CÉDULA'].value_counts().head(20)
        cedula_amounts = self.aportaciones.groupby('CÉDULA')['MONTO'].sum()
        
        # Combined data
        combined_data = pd.DataFrame({
            'Cantidad_Donaciones': cedula_counts,
            'Monto_Total': cedula_amounts.loc[cedula_counts.index]
        }).reset_index()
        combined_data.columns = ['Cédula', 'Cantidad de Donaciones', 'Monto Total']
        
        # Create bar chart for amounts
        amounts_chart = cedula_amounts.head(20).hvplot.barh(
            title="Top 20 Donantes por Monto Total",
            xlabel="Monto Total (₡)",
            ylabel="Cédula",
            color="lightgreen",
            height=600,
            width=800
        )
        
        # Create table
        table = pn.widgets.Tabulator(
            combined_data,
            title="Análisis de Cédulas - Aportaciones",
            height=400,
            width=600,
            formatters={'Monto Total': {'type': 'money', 'symbol': '₡'}}
        )
        
        return pn.Column(
            pn.pane.HoloViews(amounts_chart),
            table
        )
    
    def create_data_preview(self):
        if self.aportaciones is None:
            return pn.pane.HTML("<p>No data loaded</p>")
        
        preview_data = self.aportaciones.head(20)
        table = pn.widgets.Tabulator(
            preview_data,
            title="Vista Previa de Datos",
            height=400,
            pagination='remote',
            page_size=10
        )
        
        return table
    
    def create_contratos_analysis(self):
        if self.contratos is None:
            return pn.pane.HTML("<p>No contracts data loaded</p>")
        
        # Cedula analysis for contracts
        cedula_contracts = self.contratos['Cédula Proveedor'].value_counts().head(20)
        
        # Create table
        contracts_data = pd.DataFrame({
            'Cédula': cedula_contracts.index,
            'Cantidad de Contratos': cedula_contracts.values
        })
        
        table = pn.widgets.Tabulator(
            contracts_data,
            title="Análisis de Cédulas - Contratos",
            height=400,
            width=600
        )
        
        return table
    
    def create_dashboard(self):
        # File upload section
        upload_section = pn.Column(
            "## Cargar Datos",
            pn.Row("Archivo de Aportaciones (Excel):", self.file_input),
            pn.Row("Carpeta de Contratos:", self.folder_input),
            self.load_button,
            width=800
        )
        
        # Create tabs for different analyses
        tabs = pn.Tabs(
            ("📊 Partidos Políticos", self.create_party_chart),
            ("💰 Ingresos Anuales", self.create_yearly_income_chart),
            ("👤 Análisis Cédulas", self.create_cedula_analysis),
            ("📋 Vista Previa", self.create_data_preview),
            ("📄 Contratos", self.create_contratos_analysis),
            dynamic=True
        )
        
        # Main dashboard layout
        dashboard = pn.template.MaterialTemplate(
            title="🎯 Rastreador de Donaciones - Dashboard",
            sidebar=[upload_section],
            main=[tabs],
            header_background='#2596be',
        )
        
        return dashboard

# Create and serve dashboard
def create_app():
    dashboard = DonationsDashboard()
    return dashboard.create_dashboard()

# For serving with panel serve
if __name__ == "__main__":
    dashboard = DonationsDashboard()
    app = dashboard.create_dashboard()
    app.servable()