"""
Modulo: audio_loop.py

Descrizione:
    Definisce un'enumerazione per le impostazioni di loop dell'audio.

Valori:
    - ACTIVATED (1): Loop attivato.
    - DISACTIVATED (0): Loop disattivato.

Autore: Zs
Data: 02-04-2025
"""

from enum import Enum

class AudioLoop(Enum):
    """
    Enumerazione per le impostazioni del loop audio.
    """
    ACTIVATED = 1       # Loop attivo
    DISACTIVATED = 0    # Loop disattivato

    def __str__(self):
        return super().__str__()
    
    def __bool__(self):
        return super().__bool__()
    


