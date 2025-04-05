"""
Modulo: AudioUtils

Descrizione:
Modulo AudioUtils per la gestione della riproduzione audio con pygame.
Permette di riprodurre file audio ricevuti dal client.
Supporta la sovrapposizione di suoni con più canali audio.
Evita la duplicazione di suoni già in riproduzione.
Controlla e modifica il volume dei canali audio.

Dipendenze:
- pygame per interfacciarsi con i sistemi audio.
- audiotsm per modificare la velocità di riproduzione senza alterare il pitch.
- numpy per gestire i dati audio in array.
- soundfile per leggere e scrivere file audio.
- io per leggere il segmento audio in stringhe di bytes.

Autore: Zs  
Data: 02-04-2025
"""

import pygame
import numpy as np
import soundfile as sf
from audiotsm import phasevocoder
from audiotsm.io.array import ArrayReader, ArrayWriter
import io


class AudioUtils:
    """
    Classe per la gestione avanzata dell'audio utilizzando pygame e pydub.

    Funzionalità:
    - Supporto per più formati audio (MP3, WAV, OGG, FLAC, ecc.).
    - Riproduzione di suoni su due canali indipendenti.
    - Cambio di velocità del suono mantenendo la posizione attuale.
    - Controllo del volume per ogni suono.
    - Prevenzione della riproduzione simultanea dello stesso suono.
    """

    def __init__(self):
        """
        Inizializza il sistema audio e configura due canali indipendenti.

        Attributes:
            __sounds (dict): Dizionario che associa i nomi dei suoni ai loro dati (pygame.mixer.Sound, file_path).
            __channel_1 (pygame.mixer.Channel): Primo canale audio.
            __channel_2 (pygame.mixer.Channel): Secondo canale audio.
        """
        pygame.mixer.init()
        self.__sounds = {}  # {nome: (pygame.mixer.Sound, percorso originale)}
        self.__channel_1 = pygame.mixer.Channel(0)
        self.__channel_2 = pygame.mixer.Channel(1)

    def _load_sound(self, name: str, file_path: str) -> None:
        """
        Carica un file audio e lo memorizza con il suo nome di riferimento.

        Args:
            name (str): Nome identificativo del suono.
            file_path (str): Percorso del file audio.
        
        Returns:
            None
        """
        self.__sounds[name] = (pygame.mixer.Sound(file_path), file_path)

    def _play_sound(self, name: str, channel: int = 0) -> None:
        """
        Riproduce un suono su uno dei due canali disponibili.

        Args:
            name (str): Nome del suono da riprodurre.
            channel (int, opzionale): Canale su cui riprodurre il suono (0 = primo canale, 1 = secondo canale).
        
        Returns:
            None
        """
        if name in self.__sounds:
            ch = self.__channel_1 if channel == 0 else self.__channel_2
            if not ch.get_busy():
                ch.play(self.__sounds[name][0])

    def _stop_sound(self, name: str, channel: int) -> None:
        """
        Ferma la riproduzione di un suono su un canale specifico.

        Args:
            name (str): Nome del suono da fermare.
            channel (int): Canale da fermare (1 o 2).
        """
        if name in self.__sounds and channel in {1, 2}:
            getattr(self, f"__channel_{channel}").stop()


    def _change_speed(self, name: str, speed: float) -> None:
        """
        Modifica la velocità di un suono senza riavviarlo da capo utilizzando audiotsm.

        - Il suono viene rielaborato con la nuova velocità utilizzando audiotsm.
        - La riproduzione riprende dalla posizione in cui era stata interrotta.

        Args:
            name (str): Nome del suono da modificare.
            speed (float): Fattore di velocità (es. 2.0 = doppia velocità, 0.5 = metà velocità).
        
        Returns:
            None
        """
        if name in self.__sounds:
            sound, file_path = self.__sounds[name]
            ch = self.__channel_1 if self.__channel_1.get_busy() else self.__channel_2

            # Ottieni la posizione attuale in secondi
            position = ch.get_pos() / 1000  

            # Leggi il file audio originale
            audio, samplerate = sf.read(file_path)

            # Usa audiotsm per cambiare la velocità senza alterare il pitch
            reader = ArrayReader(audio.T)  # Transpose per canali corretti
            writer = ArrayWriter()
            tsm = phasevocoder(reader.channels, speed)
            tsm.run(reader, writer)
            modified_audio = writer.data.T  # Torna al formato corretto

            # Salva l'audio modificato in un buffer
            buffer = io.BytesIO()
            sf.write(buffer, modified_audio, samplerate, format="WAV")
            buffer.seek(0)

            # Sostituisci il suono e riproducilo dalla posizione salvata
            self.__sounds[name] = (pygame.mixer.Sound(buffer), file_path)
            ch.play(self.__sounds[name][0], start=position)

    def _set_volume(self, name: str, volume: float) -> None:
        """
        Imposta il volume del suono specificato.

        Args:
            name (str): Nome del suono da modificare.
            volume (float): Livello del volume (da 0.0 a 1.0).
        
        Returns:
            None
        """
        if name in self.__sounds:
            volume = max(0.0, min(1.0, volume))  # Assicura che il volume sia nel range corretto
            self.__sounds[name][0].set_volume(volume)