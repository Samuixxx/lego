"""
Modulo: gears

Descrizione:
Questo modulo definisce un'enumerazione (Gear) per rappresentare gli stati del cambio di un veicolo.

Dipendenze:
- enum per la gestione degli stati del cambio tramite enumerazione.

Autore: Zs
Data: 02-05-2025
"""

import enum

class Gear(enum.Enum):
    """
    Enumerazione per rappresentare gli stati del cambio di un veicolo.
    """
    FOURTH = "4"   # Quarta marcia
    THIRD = "3"    # Terza marcia
    SECOND = "2"   # Seconda marcia
    FIRST = "1"    # Prima marcia
    NEUTRAL = "F"  # Marcia neutra
    RETRO = "R"   # Retromarcia
