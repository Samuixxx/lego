"""
Modulo: turn

Descrizione:
Questo modulo definisce una enumerazione per le direzioni di svolta di un veicolo.

Dipendenze:
- enum per la gestione delle direzioni tramite enumerazione (`builtin`).

Autore: ZS
Data: 2025-04-02
"""

import enum

class Turn(enum.Enum):
    """
    Enumerazione che rappresenta le possibili direzioni di svolta di un veicolo.
    """
    LEFT = 1      # Svolta a sinistra
    RIGHT = 2     # Svolta a destra
    STRAIGHT = 3  # Proseguire dritto