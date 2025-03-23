import cv2
import base64
import websockets
import asyncio
import json
import logging
import os

# Configura il logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(os.getcwd(), "log.txt")),
        logging.StreamHandler()
    ]
)

class CameraUtils:
    def __init__(self, websocket, camera_index=0):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
        self.isrecording = False
        self.websocket = websocket

    async def startVideo(self):
        """Avvia lo streaming video e lo invia via WebSocket"""
        self.isrecording = True
        logging.info("Avvio dello streaming video...")

        try:
            while self.isrecording:
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("Errore: impossibile leggere il frame dalla fotocamera.")
                    break

                # Converti il frame in RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Codifica il frame in JPEG
                _, buffer = cv2.imencode(".jpg", frame)
                encoded_frame = base64.b64encode(buffer).decode("utf-8")

                # Invia il frame al client via WebSocket
                await self.websocket.send(json.dumps({
                    "ok": True,
                    "videoStarted": True,
                    "frame": encoded_frame
                }))

                await asyncio.sleep(1 / 60)  # Aggiorna ogni 60esimo di secondo il frame della videocamera

        except websockets.exceptions.ConnectionClosed:
            logging.warning("Connessione WebSocket chiusa dal client.")

        except Exception as e:
            logging.exception(f"Errore imprevisto nello streaming: {e}")

        finally:
            self.cap.release()  # Rilascia la fotocamera quando non piu richiesta
            logging.info("Fotocamera rilasciata correttamente.")

    def stopVideo(self):
        """Ferma lo streaming video"""
        self.isrecording = False
        logging.info("Fermo dello streaming video...")
