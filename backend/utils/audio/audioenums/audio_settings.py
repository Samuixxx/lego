"""
Nome: audio_settings.py

Descrizione: 
Questo modulo definisce un'enumerazione per la gestione delle risorse audio.

Dipendenze:
- enum per la definizione della classe (`builtin`).

Autore: Zs
Data: 02/04/2025
"""

import enum

class AudioSettings(enum.Enum):
    """
    Enum che contiene specifiche per le impostazioni audio del progetto lego.
    
    Values:
        MAX_VOLUME (int): Indica il volume massimo supportato dalle casse
        MIN_VOLUME (int): Indica il volume minimo supportato dalle casse
    """
    MAX_VOLUME = 100                    # Valore massimo del volume
    MIN_VOLUME = 0                      # Valore minimo del volume