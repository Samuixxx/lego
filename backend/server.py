"""
Modulo: server

Descrizione:
Server WebSocket per la gestione delle comunicazioni tra client e dispositivi

Questo modulo contiene la classe principale Server che gestisce:
- Connessioni WebSocket sicure (WSS)
- Comunicazione con dispositivi hardware (motori, telecamera, audio)
- Gestione dei comandi dai client
- Elaborazione di messaggi JSON

Dipendenze:
- websockets: Per la gestione delle connessioni WebSocket
- asyncio: Per la gestione asincrona delle operazioni
- mutagen: Per l'elaborazione dei file audio
- ssl: Per la gestione della sicurezza delle connessioni

Author: Zs
Date: 02-04-2025
Version: 1.0.0
"""

import websockets
import json
import asyncio
import base64
from mutagen import File
from dotenv import load_dotenv, get_key
import os
import logging
import ssl
from pathlib import Path
import time
from utils.camera.CameraUtils import CameraUtils
from utils.motor.MotorUtils import MotorUtils
from utils.audio.AudioUtils import AudioUtils
from utils.audio.audioenums.audio_settings import AudioSettings
from utils.motor.motorenums.direction import Direction
from utils.motor.motorenums.turn import Turn
from utils.motor.motorenums.gears import Gear
from utils.serverutils import ServerUtils

ServerUtils.configure_logging()

class Server:
    """
    Classe Server che gestisce connessioni WebSocket e la comunicazione tra i client.

    Attributes:
        - clients (set): Insieme che tiene traccia di tutte le connessioni client attive.
        - port (int): Porta su cui il server è in ascolto.
        - host (str): Indirizzo host del server.
        - ssl_context (ssl.SSLContext): Contesto SSL per connessioni sicure.
        - _movement_task (Task): Riferimento al task corrente per il movimento del motore.
        - _steering_task (Task): Riferimento al task corrente per lo sterzo.
        - _decelerating (bool): Flag che indica se il veicolo sta decelerando.
        - _temp_sound (str): Nome del file audio temporaneo in riproduzione.
    """
    def __init__(self, port: int, host: str, ssl_context):
        """
        Inizializza un'istanza del server WebSocket.

        Questo costruttore configura le proprietà fondamentali del server e inizializza 
        variabili di stato necessarie per la gestione delle connessioni e delle operazioni.

        Args:
            port (int): La porta su cui il server ascolterà le connessioni in entrata.
                        Deve essere un numero intero compreso tra 1 e 65535.
            host (str): L'indirizzo host su cui il server verrà avviato. Può essere un 
                        indirizzo IP o un nome di dominio (es. "localhost", "127.0.0.1").
            ssl_context (ssl.SSLContext): Il contesto SSL utilizzato per abilitare 
                        connessioni sicure (WSS - WebSocket Secure). Deve essere un'istanza 
                        valida di ssl.SSLContext configurata con certificati appropriati.
        """
        self.clients = set() # Set to track singular client 
        self.port = port # Websocket server listening port
        self.host = host # Server url
        self.ssl_context = ssl_context
        self._movement_task = None
        self._steering_task = None
        self._decelerating = False
        self._temp_sound = None

    async def handle_connection(self, websocket):
        """
        Gestisce una nuova connessione WebSocket.

        Args:
            websocket (websockets.WebSocketServerProtocol): L'oggetto WebSocket per la connessione.
        """
        logging.info("Nuovo client connesso!")
        self.clients.add(websocket)

        client_max_hz = ServerUtils.get_monitor_refresh_rate()

        # Creating instance of CameraUtils 
        camera_controller = CameraUtils(websocket=websocket, monitor_max_hz=client_max_hz)
        motor_controller = MotorUtils(websocket=websocket)
        audio_controller = AudioUtils()

        try:
            async for message in websocket:
                await self.handle_message( message=message, 
                                           camera_controller=camera_controller, 
                                           motor_controller=motor_controller, 
                                           audio_controller=audio_controller,
                                           websocket=websocket
                                        )
        except websockets.exceptions.ConnectionClosed:
            logging.info("Client disconnesso")
        finally:
            self.clients.remove(websocket)

    async def handle_message(self, message: dict, camera_controller: CameraUtils, motor_controller: MotorUtils, audio_controller: AudioUtils, websocket) -> None:
        """
        Gestisce un messaggio ricevuto da un client.

        Questo metodo analizza il messaggio JSON ricevuto dal client e lo instrada verso
        le funzionalità appropriate in base al tipo di messaggio. Supporta operazioni
        relative alla telecamera, ai motori e all'audio.

        Args:
            message (str): Il messaggio ricevuto, tipicamente in formato JSON.
            camera_controller (CameraUtils): Istanza del controller della telecamera,
                utilizzata per gestire operazioni relative alla videocamera e alle impostazioni visive.
            motor_controller (MotorUtils): Istanza del controller dei motori,
                utilizzata per gestire il movimento e le impostazioni del veicolo LEGO.
            audio_controller (AudioUtils): Istanza del controller audio,
                utilizzata per gestire la riproduzione e le impostazioni dei file audio.
            websocket (websockets.WebSocketServerProtocol): L'istanza WebSocket associata
                al client che ha inviato il messaggio.

        Raises:
            json.JSONDecodeError: Se il messaggio ricevuto non è un JSON valido.
            KeyError: Se il messaggio JSON non contiene chiavi obbligatorie (es. "type").
            ValueError: Se i valori forniti nel messaggio non sono validi (es. valori numerici fuori range).
            TypeError: Se il tipo di dati fornito non corrisponde a quello atteso.
            FileNotFoundError: Se si verifica un errore durante l'accesso a file richiesti (es. audio).
            PermissionError: Se si verificano problemi di permessi durante l'accesso a risorse o file.
            websockets.exceptions.ConnectionClosed: Se la connessione WebSocket viene chiusa durante l'elaborazione.
            asyncio.CancelledError: Se un task asincrono viene annullato durante l'esecuzione.
            OSError: Per errori generici relativi al sistema operativo (es. accesso a risorse hardware).

        Returns:
            None.
        """
        try:
            data = json.loads(message)
            content = data.get("content", {})

            match data.get("type"):
                case "start-video-streaming":
                    asyncio.create_task(camera_controller.start_video_streaming())

                # CAMERA
                case "toggle-night-mode":
                    if content in [0, 1]:
                        # Attivazione o disattivazione della modalità notte
                        asyncio.create_task(camera_controller.toggle_night_mode(value=content))  # Aggiungi await se la funzione è async
                    else:
                        logging.warning(f"Valore non valido per la modalità notturna: {content}")

                case "set-zoom":
                    try:
                        # Converti il valore in float e limita il range tra 0.5 e 3 usando `min` e `max`
                        slider_value = max(0.5, min(3.0, float(content)))
                        # Imposta il valore di zoom
                        camera_controller.set_zoom_value(slider_value)
                    except ValueError:
                        logging.warning(f"Valore non valido per il zoom: {content}")

                case "start-recording":
                    camera_controller.start_recording()

                case "stop-recording":
                    asyncio.create_task(camera_controller.stop_recording())

                case "take-picture":
                    camera_controller.set_photo_request() # scatto una foto se il client lo richiede

                # MOVEMENT
                case "toggle-motor-status":
                    # Attivazione o disattivazione del motore
                    asyncio.create_task(motor_controller.toggle_motor_status())

                case "switch-gear":
                    # Verifico che il valore della marcia sia valido
                    try:
                        if content not in {gear.value for gear in Gear}:
                            return
                        # Imposta la marcia
                        motor_controller.set_gear(content)
                    except ValueError:
                        raise

                case "set-turbo":
                    # Attivazione del livello del turbo
                    try:
                        turbo_value = int(content.replace('%', ''))
                        if not 0 <= turbo_value <= 100:
                            raise ValueError
                        motor_controller.set_turbo(value=turbo_value)
                    except ValueError:
                        logging.error("Valore non valido per il turbo")

                case "set-brake-intensity":
                    # Imposta l'intensità del freno
                    try:
                        brake_value = int(content.replace('%', ''))
                        if not 1 <= brake_value <= 100:
                            raise ValueError
                        motor_controller.set_brake_value(value=brake_value)
                    except ValueError:
                        logging.error("Valore non valido per l'intensità del freno")
                
                case "move-forward":
                    # Esegui il movimento in avanti senza sterzare
                    if self._movement_task and not self._movement_task.get_name() == "stopper":
                        self._movement_task.cancel()
                    
                    if motor_controller.get_motor_status():
                        self._movement_task = asyncio.create_task(motor_controller.move_forward())

                case "move-backward":
                    # Esegui il movimento all'indietro senza sterzare
                    if self._movement_task and not self._movement_task.get_name() == "stopper":
                        self._movement_task.cancel()
                    
                    if motor_controller.get_motor_status():
                        self._movement_task = asyncio.create_task(motor_controller.move_backward())
                
                case "stop-moving":
                    # Fermare il movimento
                    if self._movement_task:
                        self._movement_task.cancel()

                    if motor_controller.get_motor_status():
                        self._movement_task = asyncio.create_task(motor_controller.stop())
                        self._movement_task.set_name("stopper")

                case "turn-left":
                    # Sterza a sinistra
                    if self._steering_task and not self._steering_task.get_name() == "steering-reset":
                        self._steering_task.cancel()

                    if motor_controller.get_motor_status():
                        self._steering_task = asyncio.create_task(motor_controller.turn(Turn.LEFT))

                case "turn-right":
                    # Sterza a destra
                    if self._steering_task and not self._steering_task.get_name() == "steering-reset":
                        self._steering_task.cancel()

                    if motor_controller.get_motor_status():
                        self._steering_task = asyncio.create_task(motor_controller.turn(Turn.RIGHT))
                
                case "unturn":
                    # Esegui il movimento a sinistra senza avanzare
                    if self._steering_task:
                        self._steering_task.cancel()
                    
                    if motor_controller.get_motor_status():
                        self._steering_task = asyncio.create_task(motor_controller.unturn())
                        self._steering_task.set_name("steering-reset")
                
                # AUDIO
                case "new-audio":
                    # Percorso cartella temporanea
                    temp_dir = "../user/audio/temp/"
                    os.makedirs(temp_dir, exist_ok=True)

                    # Nome e percorso file
                    file_name = data.get("name", "audio_temp.wav")[:100]  # Nome massimo 100 char per sicurezza
                    file_path = os.path.join(temp_dir, file_name)

                    # Decodifica e salvataggio file
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(content))

                    # Calcolo durata audio
                    try:
                        audio = File(file_path, easy=True)
                        total_seconds = round(audio.info.length)
                        duration = f"{total_seconds // 60}:{str(total_seconds % 60).zfill(2)}"
                    except Exception:
                        duration = "0:00"

                    # Invio dati al client
                    await websocket.send(json.dumps({
                        "ok": True,
                        "audioDuration": duration,
                        "audioName": file_name[:25]
                    }))

                    # Caricamento e riproduzione audio
                    audio_controller.load_sound(name=file_name, file_path=file_path)
                    
                    self._temp_sound = file_name

                    asyncio.create_task(
                        audio_controller.play_sound(
                            name=file_name,
                            channel=AudioSettings.CLIENT_CHANNEL.value,
                            websocket=websocket
                        )
                    )

                case "pause-audio":  
                    # ferma l'audio in esecuzione
                    if self._temp_sound:
                        audio_controller.pause_sound(channel=AudioSettings.CLIENT_CHANNEL.value)
                        print("canale messo in pausa")
                
                case "resume-audio":
                    # riprende l'audio in pausa
                    if self._temp_sound:
                        audio_controller.resume_sound(channel=AudioSettings.CLIENT_CHANNEL.value)
                
                case "restart-audio":
                    # ricomincia l'audio in esecuzione
                    if self._temp_sound:
                        audio_controller.restart_sound(name=self._temp_sound)

                case "set-sound-volume":
                    # Setta il volume del suono
                    if self._temp_sound:
                        audio_controller.set_volume(channel=AudioSettings.CLIENT_CHANNEL.value, new_volume=content)

                case "set-sound-pan":
                    # Setta il panning del suono
                    if self._temp_sound:
                        audio_controller.set_pan(channel=AudioSettings.CLIENT_CHANNEL.value, pan_value=content)
                
                case "toggle-mute":
                    # muto l'audio in esecuzione
                    if self._temp_sound:
                        audio_controller.toggle_mute(AudioSettings.CLIENT_CHANNEL.value)
                
                case "toggle-loop":
                    # imposto il loop per l'audio in esecuzione
                    if self._temp_sound:
                        audio_controller.toggle_loop(self._temp_sound)             
        
        except json.JSONDecodeError:
            logging.error("Errore: Messaggio non è un JSON valido")

        except TypeError as e:
            logging.error(f"Errore: Il messaggio ricevuto non ha il formato atteso. Dettagli: {e}")

        except KeyError as e:
            logging.error(f"Errore: Chiave mancante nel messaggio JSON. Dettagli: {e}")

        except ValueError as e:
            logging.error(f"Errore: Valore non valido nel messaggio. Dettagli: {e}")

        except AttributeError as e:
            logging.error(f"Errore: Attributo o metodo non trovato. Dettagli: {e}")
        
        except FileNotFoundError as e:
            logging.error(f"Errore: File non trovato. Dettagli: {e}")
        
        except PermissionError as e:
            logging.error(f"Errore: Permesso negato. Dettagli: {e}")
        
        except websockets.exceptions.ConnectionClosed as e:
            logging.warning(f"Connessione chiusa dal client. Dettagli: {e}")
        
        except asyncio.CancelledError:
            logging.info("Task cancellato correttamente.")
        
        except OSError as e:
            logging.error(f"Errore di sistema. Dettagli: {e}")
        
        except Exception as e:
            logging.error(f"Errore: Si è verificato un errore imprevisto. Dettagli: {e}")
            
    async def start_server(self) -> None:
        """
        Avvia il server WebSocket e attende la chiusura.

        Questo metodo configura e avvia il server WebSocket utilizzando la libreria `websockets`.
        Il server viene configurato per ascoltare sulle impostazioni di host e porta specificate
        durante l'inizializzazione della classe. Supporta connessioni sicure (WSS) tramite SSL/TLS.

        Configurazione principale:
        - `self.handle_connection`: Funzione callback per gestire nuove connessioni client.
        - `self.host`: Indirizzo su cui il server è in ascolto.
        - `self.port`: Porta su cui il server accetta le connessioni.
        - `ssl_context`: Contesto SSL utilizzato per abilitare connessioni sicure (WSS).
        - `max_size=None`: Dimensione massima consentita per i messaggi WebSocket (nessun limite).

        Il metodo rimane in attesa fino alla chiusura del server, garantendo che il server continui
        a funzionare anche dopo aver avviato le connessioni client.

        Nota: Questo metodo non restituisce il controllo finché il server non viene esplicitamente chiuso.
        
        Raises:
            OSError: Se si verifica un errore durante l'avvio del server (es. porta già in uso).
            ssl.SSLError: Se si verifica un problema con il contesto SSL configurato.
            KeyboardInterrupt: Se l'utente interrompe manualmente l'esecuzione del server.
            Exception: Per eventuali errori imprevisti durante l'avvio o l'esecuzione del server.

        Returns:
            None.
        """
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ssl= self.ssl_context,
            max_size=None
        )

        await server.wait_closed()