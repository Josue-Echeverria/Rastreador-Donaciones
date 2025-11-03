# Paquete de tabs para el Rastreador de Donaciones
from .tab_partidos import mostrar_tab_partidos
from .tab_cedulas import mostrar_tab_cedulas
from .tab_datos import mostrar_tab_datos
from .tab_contratos import mostrar_tab_contratos

__all__ = [
    'mostrar_tab_partidos',
    'mostrar_tab_cedulas', 
    'mostrar_tab_datos',
    'mostrar_tab_contratos'
]