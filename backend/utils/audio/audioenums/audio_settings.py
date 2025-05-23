"""
Nome: audio_settings.py

Descrizione: 
Questo modulo definisce un'enumerazione per la gestione delle risorse audio.

Dipendenze:
- enum per la definizione della classe.

Autore: Zs
Data: 02/04/2025
"""

import enum

class AudioSettings(enum.Enum):
    """
    Enum che contiene specifiche per le impostazioni audio del progetto lego.
    
    Values:
        MAX_VOLUME (int): Indica il volume massimo supportato dalle casse.
        MIN_VOLUME (int): Indica il volume minimo supportato dalle casse.
        CLIENT_CHANNEL (int): Indica il canale output del client.
    """
    DEFAULT_VOLUME = 0.5                # Valore di default per il volume degli audio
    CLIENT_CHANNEL = 1                  # Valore del canale di output del client
