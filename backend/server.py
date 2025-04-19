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
from serverutils import ServerUtils

ServerUtils.configure_logging()

class Server:
    """
    Classe Server che gestisce connessioni WebSocket e la comunicazione tra i client.
    """
    def __init__(self, port: int, host: str, ssl_context):
        """
        Inizializza un'istanza del server.

        Args:
            port (int): La porta su cui il server ascolterà le connessioni.
            host (str): L'indirizzo host su cui il server verrà avviato (es. "localhost").
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
            path (str): Il percorso della connessione.
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

        Args:
            message (str): Il messaggio ricevuto.
            camera_controller (CameraUtils): Camera controller instance.
            motor_controller (MotorUtils): Motor api to control LEGO.
            audio_controller (AudioUtils): Audio controller instance.

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
            

    async def start_server(self) -> None:
        """
        Avvia il server
        """
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ssl= self.ssl_context,
            max_size=None
        )

        logging.info("Server WebSocket avviato su wss://%s:%s", self.host, self.port)

        await server.wait_closed()

if __name__ == "__main__":
    load_dotenv()
    port = int(get_key(".env", "PORT"))
    host = get_key(".env", "URL")

    # Percorsi assoluti dei certificati
    _dirname = Path(__file__).parent
    root_dir = _dirname.parent
    certfile = root_dir / "certificate.crt"
    keyfile = root_dir / "private.key"

    # Genera i certificati se non esistono
    if not certfile.is_file() or not keyfile.is_file():
        print("Certificates not found. Generating new self-signed certificates...")
        os.system(f'openssl req -x509 -newkey rsa:4096 -keyout {keyfile} -out {certfile} -days 365 -nodes -subj "/CN=localhost"')

    # Creazione del contesto SSL
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        ssl_context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
        print("Certificate and key loaded successfully")
    except Exception as e:
        print(f"Error loading certificate: {e}")
        exit(1)

    # Creazione e avvio del server WebSocket
    server = Server(port, host, ssl_context)

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        start_time = time.perf_counter()
        asyncio.run(server.start_server())
        end_time = time.perf_counter()
        logging.info(f"Server started in {end_time - start_time:.4f} seconds")
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)