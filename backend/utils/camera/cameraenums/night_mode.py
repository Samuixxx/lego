"""
Modulo: night_mode

Descrizione:
Modulo per la gestione della night mode per alterare i frame inviati al client durante la trasmissione.

Dipendenze:
- enum per la gestione della night mode tramite enumerazione.

Autore: Zs
Data: 2025-04-02
"""

import enum

class NightMode(enum.Enum):
    """
    Enumerazione per la gestione della Modalità Notte.

    Attributi:
        OFF (int): Modalità normale (disattivata).
        ON (int): Modalità notte attivata.
    """
    OFF = 0  # Modalità normale
    ON = 1   # Modalità notte attivata

    def __str__(self):
        """
        Restituisce una rappresentazione in stringa della modalità notte.
        
        Returns:
            str: "Attivata" se la modalità notte è ON, altrimenti "Disattivata".
        """
        return "Attivata" if self == NightMode.ON else "Disattivata"