import websockets
import json
import asyncio
import dotenv
import os
import logging
import ssl
from pathlib import Path
import time
# importing utils modules
from utils.camera.CameraUtils import CameraUtils
from utils.motor.MotorUtils import MotorUtils
from utils.motor.motorenums.direction import Direction
from utils.motor.motorenums.turn import Turn

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(os.getcwd(), "log.txt")),
        logging.StreamHandler()
    ]
)

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
        self._temp_side = Direction.STOP

    async def handle_connection(self, websocket):
        """
        Gestisce una nuova connessione WebSocket.

        Args:
            websocket (websockets.WebSocketServerProtocol): L'oggetto WebSocket per la connessione.
            path (str): Il percorso della connessione.
        """
        logging.info("Nuovo client connesso!")
        self.clients.add(websocket)

        # Creating instance of CameraUtils 
        camera_controller = CameraUtils(websocket=websocket, client_fps=240)
        motor_controller = MotorUtils(websocket=websocket)

        try:
            async for message in websocket:
                await self.handle_message(message, camera_controller, motor_controller)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Client disconnesso")
        finally:
            self.clients.remove(websocket)

    async def handle_message(self, message, camera_controller, motor_controller):
        """
        Gestisce un messaggio ricevuto da un client.

        Args:
            message (str): Il messaggio ricevuto.
            camera_controller (CameraUtils): Camera controller instance
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            content = data.get("content", {})

            match message_type:
                case "start-video-streaming":
                    asyncio.create_task(camera_controller.startVideoStreaming())
                    logging.info("Avvio video")
                case "toggle-night-mode":
                    logging.info(f"nightmodesended {content}")
                    if content in [0, 1]:
                        # Attivazione o disattivazione della modalità notte
                        asyncio.create_task(camera_controller.toggleNightMode(value=content))  # Aggiungi await se la funzione è async
                        status = "attivato" if content == 1 else "disattivato"
                        logging.info(f"Modo notturno {status}")
                    else:
                        logging.warning(f"Valore non valido per la modalità notturna: {content}")
                case "set-zoom":
                    try:
                        # Assicurati che content contenga un valore da 0 a 3 (range dello slider)
                        slider_value = float(content)
                        
                        # Limita il valore tra 0 e 3
                        if slider_value < 0.5:
                            slider_value = 0.5
                        elif slider_value > 3:
                            slider_value = 3
                        
                        # Imposta il valore di zoom
                        camera_controller.setZoomValue(slider_value)
                    except ValueError:
                        logging.warning(f"Valore non valido per il zoom: {content}")
                case "start-recording":
                    camera_controller.startRecording()
                    logging.info("Inizio registrazione")
                case "stop-recording":
                    asyncio.create_task(camera_controller.stopRecording())
                    logging.info("Fine registrazione")
                case "take-picture":
                    camera_controller.wantPhoto() # scatto una foto se il client lo richiede
                    logging.info("Scatto foto")
                # movements cases
                case "toggle-motor-status":
                    # Attivazione o disattivazione del motore
                    motor_controller._toggle_motor_status()
                case "move-forward":
                    # Esegui il movimento in avanti senza sterzare
                    self._temp_side = Direction.FORWARD
                    asyncio.create_task(motor_controller._execute_move(self._temp_side))

                case "move-backward":
                    # Esegui il movimento indietro senza sterzare
                    self._temp_side = Direction.BACKWARD
                    asyncio.create_task(motor_controller._execute_move(self._temp_side))
                
                case "stop-moving":
                    # Fermati
                    self._temp_side = Direction.STOP
                    asyncio.create_task(motor_controller._execute_move(Direction.STOP))

                case "turn-left":
                    if self._temp_side == Direction.STOP:
                        asyncio.create_task(motor_controller._turn(Turn.LEFT))
                    else:
                        asyncio.create_task(motor_controller._execute_move(self._temp_side, Turn.LEFT))
                
                case "turn-right":
                    if self._temp_side == Direction.STOP:
                        asyncio.create_task(motor_controller._turn(Turn.RIGHT))
                    else:
                        asyncio.create_task(motor_controller._execute_move(self._temp_side, Turn.RIGHT))
                
                case "unturn-left":
                    # Esegui l'annullamento della sterzata verso sinistra senza movimento
                    asyncio.create_task(motor_controller._execute_move(self._temp_side, Turn.STRAIGHT))
                
                case "unturn-right":
                    # Esegui l'annullamento della sterzata verso destra senza movimento
                    asyncio.create_task(motor_controller._execute_move(self._temp_side, Turn.STRAIGHT))

                    
        except json.JSONDecodeError:
            logging.error("Errore: Messaggio non è un JSON valido")


    async def _continuous_movement(self, motor_controller):
        """Loop asincrono per eseguire movimenti continui basati sul set."""
        while self._forward or self._backward or self._left or self._right:
            direction = Direction.STOP
            turn = Turn.STRAIGHT

            if self._forward:
                direction = Direction.FORWARD
            elif self._backward:
                direction = Direction.BACKWARD

            if self._left:
                turn = Turn.LEFT
            elif self._right:
                turn = Turn.RIGHT

            await motor_controller._execute_move(direction, turn)
            await asyncio.sleep(0.05)  # Aggiorna ogni 50ms

        await motor_controller._execute_move(Direction.STOP, Turn.STRAIGHT) #stop when no movement is setted

    async def start_server(self):
        """
        Avvia il server WebSocket.
        """
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ssl= self.ssl_context
        )

        logging.info("Server WebSocket avviato su wss://%s:%s", self.host, self.port)

        await server.wait_closed()

if __name__ == "__main__":
    dotenv.load_dotenv()
    port = int(os.getenv("PORT", 8765))
    host = os.getenv("HOST", "localhost")

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