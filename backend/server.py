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
import utils.CameraUtils

logging.basicConfig(level=logging.INFO)

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
        self.clients = set()
        self.port = port
        self.host = host
        self.ssl_context = ssl_context
        self.camera_controller = utils.CameraUtils.CameraUtils()

    async def handle_connection(self, websocket):
        """
        Gestisce una nuova connessione WebSocket.

        Args:
            websocket (websockets.WebSocketServerProtocol): L'oggetto WebSocket per la connessione.
            path (str): Il percorso della connessione.
        """
        logging.info("Nuovo client connesso!")
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Client disconnesso")
        finally:
            self.clients.remove(websocket)

    async def handle_message(self, message):
        """
        Gestisce un messaggio ricevuto da un client.

        Args:
            websocket (websockets.WebSocketServerProtocol): L'oggetto WebSocket del client.
            message (str): Il messaggio ricevuto.
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            content = data.get("content", {})
            if message_type == "toggle-motor-status":
                logging.info("Avvio motore")
            elif message_type == "start-video":
                logging.info("Avvio video")
            elif message_type == "stop-video": # Stopping the video 
                logging.info("Fermo video")
        except json.JSONDecodeError:
            logging.error("Errore: Messaggio non è un JSON valido")

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

        logging.info("Server WebSocket avviato su wws://%s:%s", self.host, self.port)

        await server.wait_closed()

if __name__ == "__main__":
    dotenv.load_dotenv()
    port = int(os.getenv('PORT', 8765))
    host = os.getenv('HOST', 'localhost')

    # Get the root directory of the project
    _dirname = Path(__file__).parent
    root_dir = _dirname.parent

    # Absolute paths of the certificates
    certfile = root_dir / "cert.pem"
    keyfile = root_dir / "key_decrypted.pem"

    if not certfile.is_file() or not keyfile.is_file():
        print("Certificates not found. Generating new certificates.")
        exit(1) 

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    try:
        ssl_context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
        print("Certificate and key loaded successfully")
    except Exception as e:
        print(f"Error loading certificate: {e}")
        exit(1)

    server = Server(port, host, ssl_context)

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        start_time = time.perf_counter()
        asyncio.run(server.start_server())
        end_time = time.perf_counter()
        logging.info(f"asyncio.run(server.start_server()) took {end_time - start_time:.4f} seconds")
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error("Error: %s", str(e))