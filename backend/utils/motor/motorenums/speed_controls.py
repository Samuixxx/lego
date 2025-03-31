"""
Modulo: speed_controls.py

Descrizione:
Questo modulo definisce un'enumerazione (SpeedControls) per rappresentare i limiti di velocità
per diverse direzioni e marce di un veicolo.

Autore: [Il tuo nome]
Data: [Data di creazione o modifica]
"""

import enum

class SpeedControls(enum.Enum):
    """
    Enumerazione per definire i limiti di velocità per diverse direzioni e marce.
    """
    MAXIMUM_PER_GEAR = 15                 # Velocità massima per ogni marcia (es. km/h)
    MAXIMUM_VALOCITY_BACKWARD = 50        # Velocità massima in retromarcia (es. km/h)
    MAXIMUM_VALOCITY_FORWARD = 100        # Velocità massima in avanti (es. km/h)
                   
