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
- json: Per serializzare i dati del server e inviarli al client.
- asyncio: Per gestire operazioni asincrone, come l'invio di aggiornamenti temporali al client.
- time: Per ottenere il tempo corrente durante la riproduzione.

Autore: Zs  
Data: 02-04-2025
"""

import pygame
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
        self._loop_status = AudioLoop.DISACTIVATED # Variabile che tiene lo stato dell loop della riproduzione
        self._is_playing = {} # {channel, bool}
        self._current_sound = None # Variabile che contiene temporaneamente il nome del suono in esecuzione

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
            asyncio.create_task(audio.play_sound("musica", channel=1))
        """

        if name not in self.sounds:
            print(f"Il suono '{name}' non è stato caricato.")
            return

        ch = self.channels.get(channel)

        if not ch or ch.get_busy():
            print(f"Il canale {channel} e occupato.")
            return
        
        self._is_playing[channel] = (channel, True)
        self._current_sound = name

        sound = self.sounds[name][0]
        if not sound:
            raise ValueError(f"Il suono '{name}' non è stato caricato correttamente.")
                  
        ch.play(sound)
        ch.set_volume(AudioSettings.DEFAULT_VOLUME.value)

        self.websocket = websocket
        self.is_paused = False
        self.elapsed_time = 0.0
        self._start_time = time.time()

        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(self._send_updates(channel, sound))

    async def _send_updates(self, channel: int, sound: str) -> None:
        """
        Invia aggiornamenti temporali al client tramite WebSocket durante la riproduzione audio.

        Questo metodo viene eseguito come un task asincrono e invia immediatamente il tempo trascorso
        appena il suono parte, e continua ad aggiornare il client ogni secondo finché la riproduzione è attiva
        e non è in pausa.

        Args:
            channel (int): Canale audio (0 o 1) per il quale inviare gli aggiornamenti temporali.
            sound (str): Nome del suono in riproduzione (non utilizzato direttamente in questa funzione ma utile per logging o estensioni future).

        Comportamento:
            - Invia subito un aggiornamento temporale appena parte il suono.
            - Verifica se il canale è attivo e in riproduzione (`ch.get_busy()`).
            - Se non è in pausa (`not self.is_paused`), calcola e invia il tempo trascorso.
            - Attende 1 secondo tra gli aggiornamenti successivi.
            - Invia un ultimo aggiornamento al termine della riproduzione.
            - Se il loop è attivo, riavvia la riproduzione del suono.

        Esempio di messaggio inviato al client:
            {
                "ok": True,
                "currentAudioTime": 12.345
            }
        """

        ch = self.channels.get(channel)
        if not ch:
            print(f"Canale {channel} non trovato.")
            return

        self.elapsed_time = 0.0

        async def send_current_time():
            """
            Calcola e invia il tempo corrente di riproduzione al client tramite WebSocket.
            Ritorna False in caso di errore, True altrimenti.
            """
            current_time_sec = self.elapsed_time + (time.time() - self._start_time)
            if self.websocket:
                try:
                    await self.websocket.send(json.dumps({
                        "ok": True,
                        "currentAudioTime": current_time_sec
                    }))
                except Exception as e:
                    print(f"Errore nell'invio tramite WebSocket: {e}")
                    return False
            return True

        # 🔥 Invia subito il primo aggiornamento appena parte il suono
        if not await send_current_time():
            return

        # 🔁 Continua a inviare ogni secondo finché il canale è attivo
        while ch.get_busy():
            if not self.is_paused:
                if not await send_current_time():
                    break
            await asyncio.sleep(1)

        # ✅ Invia un ultimo aggiornamento al termine della riproduzione
        await send_current_time()

        ch.stop()
        self._is_playing[channel] = (channel, False)

        if self._loop_status == AudioLoop.ACTIVATED:
            await asyncio.sleep(1)
            asyncio.create_task(
                self.play_sound(self._current_sound, AudioSettings.CLIENT_CHANNEL.value, self.websocket)
            )


    def restart_sound(self, name: str) -> None:
        """
        Riavvia un suono azzerando timer e stato del canale.

        Se il suono è già in riproduzione, viene interrotto e riavviato da capo.
        Se il suono non è disponibile, la funzione termina senza eseguire azioni.

        Args:
            name (str): Nome del suono da riavviare.
        """
        if name not in self.sounds:
            print(f"[Errore] Suono '{name}' non trovato.")
            return

        channel = AudioSettings.CLIENT_CHANNEL.value
        ch = self.channels.get(channel)

        if ch and ch.get_busy():
            ch.stop()
            print(f"[Info] Riproduzione precedente fermata sul canale {channel}.")

        self._current_sound = name
        self._start_time = time.time()
        self.elapsed_time = 0.0
        self._is_playing[channel] = (channel, True)

        asyncio.create_task(self.play_sound(name, channel, self.websocket))
        print(f"[Info] Suono '{name}' riavviato sul canale {channel}.")


    def pause_sound(self, channel: int = 0) -> None:
        """
        Mette in pausa la riproduzione audio su un canale specificato.

        Args:
            channel (int): Indice del canale audio da mettere in pausa. Default: 0.
        """
        ch = self.channels.get(channel)

        if ch and ch.get_busy():
            ch.pause()
            self.is_paused = True
            self.elapsed_time += time.time() - getattr(self, "_start_time", 0)


    def resume_sound(self, channel: int = 0) -> None:
        """
        Riprende la riproduzione audio su un canale specificato.

        Args:
            channel (int): Indice del canale audio da riprendere. Default: 0.
        """
        ch = self.channels.get(channel)

        if ch and ch.get_busy():
            ch.unpause()
            self.is_paused = False
            self._start_time = time.time()

    def set_volume(self, channel: int, new_volume: float) -> None:
        """
        Imposta il volume del canale specificato.

        Args:
            channel (int): ID del canale da modificare.
            new_volume (float): Valore da -60 a 60 che rappresenta il livello di volume.

        Returns:
            None
        """
        if channel not in self.channels:
            print(f"Canale {channel} non trovato.")
            return

        # range tra [-60, 60]
        new_volume = max(-60, min(60, new_volume))

        # Normalize volume to [0.0, 1.0]
        normalized_volume = round((new_volume + 60) / 120, 2)

        self.channels[channel].set_volume(normalized_volume)

    def set_pan(self, channel: int, pan_value: float) -> None:
        """
        Imposta il bilanciamento stereo (pan) del canale specificato.

        Args:
            channel (int): ID del canale da modificare.
            pan_value (float): Valore da -60 a 60 dove:
                               -60 = sinistra, 0 = centro, 60 = destra.

        Returns:
            None
        """
        if channel not in self.channels:
            print(f"Canale {channel} non trovato.")
            return
        
        # Normalizzazione del pan
        left_volume = 1.0 if pan_value <= 0 else 1.0 - pan_value
        right_volume = 1.0 if pan_value >= 0 else 1.0 + pan_value
        # Ottieni il volume corrente (predefinito a 1.0)
        self.channels[channel].set_volume(left_volume, right_volume)
        
    def toggle_mute(self, channel: int) -> None:
        """
        Alterna lo stato di mute per l'audio del suono specificato.

        Args:
            channel (int): Numero identificativo del channel da mutare.

        Returns:
            None
        """
        ch = self.channels.get(channel)
        if not ch:
            return

        current_volume = ch.get_volume()
        is_muted = current_volume == 0.0

        if is_muted:
            ch.set_volume(getattr(self, '_last_volume', 1.0))
        else:
            self._last_volume = current_volume
            ch.set_volume(0.0)

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
    