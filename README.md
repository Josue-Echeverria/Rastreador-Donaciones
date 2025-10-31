# Rastreador de Donaciones

Una aplicación web interactiva para el análisis de donaciones políticas y contratos gubernamentales en Costa Rica. Esta herramienta permite visualizar patrones, tendencias y relaciones entre donaciones políticas y la adjudicación de contratos públicos.

## Características

- **Dashboard Interactivo**: Interfaz web moderna construida con Streamlit
- **Análisis de Partidos**: Visualización de donaciones por partido político
- **Análisis Temporal**: Seguimiento de ingresos por períodos gubernamentales
- **Análisis de Donantes**: Identificación de los principales contribuyentes
- **Detección de Alertas**: Identificación automática de posibles irregularidades temporales
- **Exportación de Datos**: Descarga de resultados en formato Excel
- **Visualizaciones Avanzadas**: Gráficos interactivos con Matplotlib y Seaborn

## Tecnologías Utilizadas

- **Python 3.8+**
- **Streamlit** - Framework web para aplicaciones de datos
- **Pandas** - Manipulación y análisis de datos
- **Matplotlib** - Visualización de datos
- **Seaborn** - Visualización estadística
- **NumPy** - Computación numérica
- **OpenPyXL** - Lectura/escritura de archivos Excel

## Requisitos

```bash
pip install streamlit pandas matplotlib seaborn numpy openpyxl
```

## Instalación y Uso

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Josue-Echeverria/Rastreador-Donaciones.git
cd Rastreador-Donaciones
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar la Aplicación

```bash
streamlit run main.py
```

### 4. Acceder a la Aplicación

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## Estructura del Proyecto

```
Rastreador-Donaciones/
├── main.py                          # Aplicación principal de Streamlit
├── dashboard_panel.py               # Dashboard alternativo con Panel
├── analisis_contratos_colab.ipynb   # Notebook de análisis avanzado
├── Concurso_PIDA.ipynb             # Notebook de procesamiento inicial
├── README.md                        # Documentación del proyecto
└── requirements.txt                 # Dependencias del proyecto
```

## Funcionalidades del Dashboard

### 1. Análisis de Partidos Políticos
- Visualización de donaciones por partido
- Ranking de partidos más financiados
- Métricas de participación

### 2. Análisis de Ingresos
- Evolución temporal de donaciones
- Ingresos anuales por partido
- Comparaciones entre períodos gubernamentales

### 3. Análisis de Donantes
- Identificación de principales contribuyentes
- Análisis de patrones de donación
- Distribución de montos por cédula

### 4. Vista de Datos Completos
- Tabla interactiva con todos los registros
- Filtrado y búsqueda avanzada
- Exportación de datos procesados

## Configuración de Datos

### Formato de Archivo de Aportaciones
El archivo Excel debe contener una hoja llamada `BBDD` with the following columns:
- `FECHA`: Fecha de la donación
- `PARTIDO POLÍTICO`: Nombre del partido político
- `CÉDULA`: Identificación del donante
- `MONTO`: Monto de la donación
- `NOMBRE DEL CONTRIBUYENTE`: Nombre del donante

### Carga de Datos
1. Ejecute la aplicación con `streamlit run main.py`
2. Use la barra lateral para cargar el archivo Excel de aportaciones
3. Los datos se procesarán automáticamente

## Análisis Avanzado

### Notebook de Jupyter
Para análisis más detallados, utilice `analisis_contratos_colab.ipynb`:

```bash
jupyter notebook analisis_contratos_colab.ipynb
```

Este notebook incluye:
- Análisis temporal avanzado
- Detección de alertas por proximidad temporal
- Visualizaciones personalizadas por partido
- Exportación de reportes detallados

## Métricas y Alertas

El sistema detecta automáticamente:
- Donantes que también son proveedores del estado
- Proximidad temporal entre donaciones y adjudicación de contratos
- Patrones sospechosos en el financiamiento político
- Tendencias por período gubernamental

## Casos de Uso

- **Investigación Periodística**: Análisis de financiamiento político
- **Transparencia Gubernamental**: Monitoreo de donaciones y contratos
- **Investigación Académica**: Estudios sobre política y economía
- **Auditoría Ciudadana**: Vigilancia de la administración pública

## Contribuciones

Las contribuciones son bienvenidas. Para contribuir:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Autor

**Josué Echeverría**
- GitHub: [@Josue-Echeverria](https://github.com/Josue-Echeverria)

## Agradecimientos

- Tribunal Supremo de Elecciones de Costa Rica por los datos públicos
- Comunidad de Python y Streamlit por las herramientas
- Contribuidores y usuarios del proyecto

---

**Nota Importante**: Esta herramienta está diseñada para fines de transparencia e investigación. Los resultados deben interpretarse con cuidado y verificarse con fuentes adicionales antes de llegar a conclusiones definitivas.
