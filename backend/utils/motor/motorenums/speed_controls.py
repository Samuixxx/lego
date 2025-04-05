"""
Modulo: speed_controls

Descrizione:
Questo modulo definisce un'enumerazione (SpeedControls) per rappresentare i limiti di velocità
per diverse direzioni e marce di un veicolo.

Dipendenze:
- enum per la gestione dei settings per il motore tramite enumerazioni (`builtin`).

Autore: Zs
Data: 02/04/2025
"""

import enum

class SpeedControls(enum.Enum):
    """
    Enumerazione per definire i limiti di velocità per diverse direzioni e marce.
    """
    MAXIMUM_PER_GEAR = 15                 # Velocità massima per ogni marcia (es. km/h)
    MAXIMUM_VALOCITY_BACKWARD = 50        # Velocità massima in retromarcia (es. km/h)
    MAXIMUM_VALOCITY_FORWARD = 100        # Velocità massima in avanti (es. km/h)
                   
