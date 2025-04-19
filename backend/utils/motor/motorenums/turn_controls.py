"""
Modulo: turn_controls

Descrizione:
Questo modulo definisce una enumerazione per i controlli di sterzata.

Dipendenze:
- enum per la gestione dei controlli di sterzata tramite enumerazione (`builtin`).

Autore: Zs
Data: 2025-04-02
"""

import enum

class TurnControls(enum.Enum):
    """
    Enumerazione per i controlli di sterzata.
    """
    MAXIMUM_TURN_ANGLE = 60  # Angolo massimo di sterzata in gradi
    TURN_VELOCITY = 4        # Velocità di sterzata