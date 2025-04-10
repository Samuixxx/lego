"""
Modulo: AudioUtils

Descrizione:
Modulo AudioUtils per la gestione avanzata della riproduzione audio utilizzando pygame e altre librerie.
Fornisce funzionalità per la gestione di suoni multicanale, inclusa la modifica della velocità di riproduzione,
il controllo del volume e la prevenzione della duplicazione di suoni già in riproduzione.

Funzionalità principali:
- Supporto per più formati audio (MP3, WAV, OGG, FLAC, ecc.).
- Riproduzione simultanea su due canali indipendenti.
- Cambio dinamico della velocità di riproduzione senza alterare il pitch.
- Controllo del volume per ogni suono.
- Prevenzione della riproduzione simultanea dello stesso suono.

Dipendenze:
- pygame: Per interfacciarsi con i sistemi audio.
- audiotsm: Per modificare la velocità di riproduzione mantenendo il pitch originale.
- numpy: Per gestire i dati audio come array numerici.
- soundfile: Per leggere e scrivere file audio.
- io: Per gestire i dati audio in memoria come stringhe di bytes.
- json: Per serializzare i dati del server e inviarli al client.
- asyncio: Per gestire operazioni asincrone, come l'invio di aggiornamenti temporali al client.
- time: Per ottenere il tempo corrente durante la riproduzione.

Autore: Zs  
Data: 02-04-2025
"""

import pygame
import numpy as np
import soundfile as sf
from audiotsm import phasevocoder
from audiotsm.io.array import ArrayReader, ArrayWriter
import io
import json
import asyncio
import time
from utils.audio.audioenums.audio_loop import AudioLoop
from utils.audio.audioenums.audio_settings import AudioSettings

class AudioUtils:
    """
    Classe per la gestione avanzata dell'audio utilizzando pygame e altre librerie.

    Questa classe fornisce un'interfaccia per la gestione della riproduzione audio,
    inclusa la modifica della velocità di riproduzione, il controllo del volume
    e la gestione di più canali audio indipendenti.

    Funzionalità principali:
    - Caricamento e riproduzione di file audio in vari formati.
    - Gestione di due canali audio indipendenti.
    - Modifica della velocità di riproduzione mantenendo il pitch originale.
    - Controllo del volume per ogni suono.
    - Prevenzione della riproduzione simultanea dello stesso suono.

    Esempio di utilizzo:
        audio = AudioUtils()
        audio.load_sound("suono1", "path/to/sound.wav")
        asyncio.run(audio.play_sound("suono1", channel=0))
        audio.set_volume("suono1", 0.5)
        audio.change_speed("suono1", 1.5)
    """

    def __init__(self):
        """
        Inizializza il sistema audio e configura due canali indipendenti.

        Attributes:
            sounds (dict): Dizionario che associa i nomi dei suoni ai loro dati (pygame.mixer.Sound, file_path).
            channels (dict): Mappa dei canali audio disponibili (0 e 1).
            is_paused (bool): Variabile che segna se la riproduzione audio è stata messa in pausa.
            elapsed_time (float): Indica il tempo trascorso nella riproduzione audio.
        """
        pygame.mixer.init()
        self.sounds = {}  # {nome: (pygame.mixer.Sound, file_path)}
        self.channels = {
            0: pygame.mixer.Channel(0),
            1: pygame.mixer.Channel(1)
        }
        self.is_paused = False
        self.elapsed_time = 0.0
        self._start_time = None
        self.websocket = None
        self._update_task = None  # Task per l'aggiornamento temporale
        self._last_volume = 0
        self._loop_status = AudioLoop.DISACTIVATED
        self._is_playing = {} # {channel, bool}
        self._current_sound = None

    def load_sound(self, name: str, file_path: str) -> None:
        """
        Carica un file audio e lo memorizza con il suo nome di riferimento.

        Args:
            name (str): Nome identificativo del suono.
            file_path (str): Percorso del file audio.

        Returns:
            None

        Esempio:
            audio.load_sound("musica", "path/to/music.mp3")
        """
        try:
            self.sounds[name] = (pygame.mixer.Sound(file_path), file_path)
        except Exception as e:
            print(f"Errore durante il caricamento del suono '{name}': {e}")

    async def play_sound(self, name: str, channel: int = 0, websocket=None) -> None:
        """
        Riproduce un suono su uno dei due canali disponibili.

        Se il suono specificato non esiste o il canale è occupato, il metodo non esegue alcuna azione.
        Durante la riproduzione, invia aggiornamenti temporali al client tramite WebSocket (se connesso).

        Args:
            name (str): Nome del suono da riprodurre.
            channel (int): Canale su cui riprodurre il suono (0 o 1). Default: 0.
            websocket: Oggetto WebSocket per inviare aggiornamenti temporali. Default: None.

        Returns:
            None

        Esempio:
            asyncio.run(audio.play_sound("musica", channel=1))
        """

        if name not in self.sounds:
            print(f"Il suono '{name}' non è stato caricato.")
            return
        
        print(f"Tentativo di riproduzione suono '{name}' su canale {channel}")

        ch = self.channels.get(channel)

        timeout = 5  # Numero massimo di tentativi per evitare un loop infinito
        while ch and ch.get_busy() and timeout > 0:
            print(f"⏳ Attendo liberazione canale {channel}... Timeout: {timeout}")
            await asyncio.sleep(0.1)
            timeout -= 1

        if not ch or ch.get_busy():
            print(f"Il canale {channel} e occupato.")
            return
        
        self._is_playing[channel] = (channel, True)
        self._current_sound = name

        sound = self.sounds[name][0]

        ch.stop()

        print(f"DEBUG: Loop status = {self._loop_status}, Current sound = {self._current_sound}")

        if not sound:
            print(f"Il suono '{name}' non è stato caricato correttamente.")
        
        ch.play(sound)
        self.websocket = websocket
        self.is_paused = False
        self.elapsed_time = 0.0
        self._start_time = time.time()

        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(self._send_updates(channel))

    async def _send_updates(self, channel: int) -> None:
        """
        Invia aggiornamenti temporali al client tramite WebSocket durante la riproduzione audio.

        Questo metodo viene eseguito come un task asincrono e invia periodicamente il tempo trascorso
        al client tramite WebSocket. L'invio degli aggiornamenti continua finché il suono è in riproduzione
        e non è in pausa.

        Args:
            channel (int): Canale audio (0 o 1) per il quale inviare gli aggiornamenti temporali.

        Comportamento:
            - Verifica se il canale specificato è attivo e in riproduzione (`ch.get_busy()`).
            - Se il suono non è in pausa (`not self.is_paused`), calcola il tempo trascorso (`current_time_sec`)
            sommando il tempo accumulato durante eventuali pause (`self.elapsed_time`) al tempo trascorso
            dall'ultima ripresa della riproduzione.
            - Invia il tempo corrente al client tramite WebSocket, serializzando i dati in formato JSON.
            - Attende 1 secondo tra un aggiornamento e il successivo per evitare un carico eccessivo sul server.

        Note:
            - Il metodo si interrompe automaticamente quando il suono termina o il canale diventa inattivo.
            - Durante la pausa, il timer non viene azzerato, ma l'invio degli aggiornamenti viene sospeso.

        Esempio di messaggio inviato al client:
            {
                "ok": True,
                "currentAudioTime": 12.345  # Tempo trascorso in secondi
            }
        """

        ch = self.channels.get(channel)

        if not ch:
            print(f"Canale {channel} non trovato.")
            return

        # Verifica che il canale sia attivo e in riproduzione
        while ch.get_busy():
            if not self.is_paused:
                current_time_sec = self.elapsed_time + (time.time() - self._start_time)
                if self.websocket:
                    try:
                        await self.websocket.send(json.dumps({
                            "ok": True,
                            "currentAudioTime": current_time_sec
                        }))
                    except Exception as e:
                        print(f"Errore nell'invio tramite WebSocket: {e}")
                        break  # Esci in caso di errore
            await asyncio.sleep(1)

        #  INVIA UN ULTIMO AGGIORNAMENTO PER IL TEMPO FINALE
        final_time_sec = self.elapsed_time + (time.time() - self._start_time)
        if self.websocket:
            try:
                await self.websocket.send(json.dumps({
                    "ok": True,
                    "currentAudioTime": final_time_sec
                }))
            except Exception as e:
                print(f"Errore nell'invio dell'ultimo aggiornamento: {e}")

        print(f"Canale {channel} non più occupato. Liberazione...")

        ch.unpause()
        ch.stop()  # Ferma il suono attuale per sicurezza
        await asyncio.sleep(0.1)  # Assicura la liberazione del canale

        self._is_playing[channel] = (channel, False)  # Segna il canale come libero

        if self._loop_status == AudioLoop.ACTIVATED:
            print("Riavvio del suono in loop...")
            await self.play_sound(self._current_sound, AudioSettings.CLIENT_CHANNEL.value, self.websocket)
                
    def pause_sound(self, channel: int = 0) -> None:
        """
        Mette in pausa la riproduzione di un suono su un canale specifico.

        Args:
            channel (int): Canale da mettere in pausa (0 o 1). Default: 0.

        Returns:
            None

        Esempio:
            audio.pause_sound(channel=1)
        """
        ch = self.channels.get(channel)
        if ch and ch.get_busy():
            ch.pause()
            self.is_paused = True
            self.elapsed_time += time.time() - getattr(self, "_start_time", 0)
            print("Riproduzione messa in pausa.")

    def resume_sound(self, channel: int = 0) -> None:
        """
        Riprende la riproduzione di un suono su un canale specifico.

        Args:
            channel (int): Canale da riprendere (0 o 1). Default: 0.

        Returns:
            None

        Esempio:
            audio.resume_sound(channel=1)
        """
        ch = self.channels.get(channel)
        if ch and ch.get_busy():
            ch.unpause()
            self.is_paused = False
            self._start_time = time.time()
            print("Riproduzione ripresa.")

    def change_speed(self, name: str, speed: float) -> None:
        """
        Modifica la velocità di un suono senza riavviarlo da capo utilizzando audiotsm.

        Args:
            name (str): Nome del suono da modificare.
            speed (float): Fattore di velocità (es. 2.0 = doppia velocità, 0.5 = metà velocità).

        Returns:
            None

        Note:
            - La velocità deve essere maggiore di zero.
            - L'operazione può richiedere tempo per file audio di grandi dimensioni.

        Esempio:
            audio.change_speed("musica", 1.5)
        """
        if name not in self.sounds:
            print(f"Il suono '{name}' non è stato caricato.")
            return

        if speed <= 0:
            print("La velocità deve essere maggiore di zero.")
            return

        _, file_path = self.sounds[name]
        try:
            audio, samplerate = sf.read(file_path)
            reader = ArrayReader(audio.T)
            writer = ArrayWriter()
            tsm = phasevocoder(reader.channels, speed)
            tsm.run(reader, writer)
            modified_audio = writer.data.T

            buffer = io.BytesIO()
            sf.write(buffer, modified_audio, samplerate, format="WAV")
            buffer.seek(0)

            self.sounds[name] = (pygame.mixer.Sound(buffer), file_path)
        except Exception as e:
            print(f"Errore durante la modifica della velocità del suono '{name}': {e}")

    def set_volume(self, name: str, volume: float) -> None:
        """
        Imposta il volume del suono specificato.

        Args:
            name (str): Nome del suono da modificare.
            volume (float): Livello del volume (da 0.0 a 1.0).

        Returns:
            None

        Note:
            - Il volume viene clippato automaticamente nel range [0.0, 1.0].

        Esempio:
            audio.set_volume("musica", 0.75)
        """
        if name not in self.sounds:
            return

        volume = max(0.0, min(1.0, volume))
        self.sounds[name][0].set_volume(volume)
    
    def toggle_mute(self, name: str) -> None:
        """
        Alterna lo stato di mute per l'audio della canzone.

        Args:
            name (str): Nome del suono da modificare.
        
        Returns:
            None
        
        Esempio:
            audio.mute("musica")  # Muta
            audio.mute("musica")  # Riattiva l'audio
        """
        if name not in self.sounds:
            return

        current_volume = self.sounds[name][0].get_volume()

        if current_volume == 0.0:
            # Se il suono è mutato, ripristina il volume originale
            self.sounds[name][0].set_volume(self._last_volume)
        else:
            # Salva il volume attuale e muta l'audio
            self._last_volume = current_volume
            self.sounds[name][0].set_volume(0.0)

    def toggle_loop(self, name: str) -> None:
        """
        Imposta il loop attivo/disattivo per il suono selezionato.

        Args:
            name (str): Nome del suono da modificare.
        
        Returns:
            None.
        
        Esempio:
            audio.toggle_loop("musica") 
        """
        if name not in self.sounds:
            print(f"Suono '{name}' non trovato.")
            return
        
        self._loop_status = AudioLoop.ACTIVATED if self._loop_status == AudioLoop.DISACTIVATED else AudioLoop.ACTIVATED
    
    async def _cleanup(self) -> None:
        """
        Ferma tutti i suoni in riproduzione, cancella i task asincroni e pulisce le risorse.
        Questo metodo viene chiamato quando il client si disconnette dal WebSocket.
        """
        print("Pulizia delle risorse in corso...")
        for channel in self.channels.values():
            if channel.get_busy():
                channel.stop()
        self.is_paused = False
        self.elapsed_time = 0.0
        self._start_time = None
        self.websocket = None
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
        print("Risorse pulite e classe pronta per essere distrutta.")

    async def monitor_websocket(self) -> None:
        """
        Monitora lo stato del WebSocket e pulisce le risorse se il client si disconnette.
        """
        while self.websocket:
            try:
                # Verifica se il WebSocket è ancora aperto
                await self.websocket.ping()
                await asyncio.sleep(1)  # Controlla ogni secondo
            except Exception as e:
                print(f"Client disconnesso: {e}")
                await self._cleanup()
                break