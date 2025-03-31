"""
Modulo: direction.py

Descrizione:
Questo modulo definisce un'enumerazione (Direction) per rappresentare le direzioni di movimento di un motore.

Autore: [Il tuo nome]
Data: [Data di creazione o modifica]
"""

import enum

class Direction(enum.Enum):
    """
    Enumerazione per rappresentare le direzioni di movimento di un motore.
    """
    FORWARD = 1  # Movimento in avanti
    BACKWARD = 2 # Movimento all'indietro
    STOP = 3     # Motore fermo
    LEFT = 4     # Movimento a sinistra
    RIGHT = 5    # Movimento a destra