import cv2
import base64
import asyncio
import json
import logging
import os
import enum
import numpy as np
from pathlib import Path

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
    def __init__(self, websocket, camera_index=0, client_fps=60):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index) # Istanza della videocamera del client
        self.isrecording = False # Variabile boolean che segna se il client ha mandato un comando di avvio registrazione
        self.out = None # Variabile che conterra il videowriter con cui i client su richiesta potranno ottenere dei video
        self.websocket = websocket # Client socket
        self.night_mode = NightMode.OFF # Valore per la NightMode -> classe enum ! valori possibili -> OFF === 0 && ON == 1
        self.client_fps = client_fps # Capacità di aggiornamento del monitor del client
        self.zoom_factor = 1.0 # Valore del zoom nella trasmissione delle immagini
        self.calibration_data = self._load_calibration()
        self.map1, self.map2 = self._init_distortion_maps()
    
    def __del__(self):
        self.cap.release()

    def _load_calibration(self):
        """Carica i parametri di calibrazione della camera"""
        # Sostituisci con i tuoi valori reali o carica da file
        return {
            'camera_matrix': np.array(
                [[ 1.100e+03,  0.000e+00,  9.600e+02],
                [ 0.000e+00,  1.100e+03,  5.400e+02],
                [ 0.000e+00,  0.000e+00,  1.000e+00]]
            ),
            'dist_coeffs': np.array([-0.15,  0.05,  0.001,  0.001,  0.000])
        }

    def _init_distortion_maps(self):
        """Pre-calcola le mappe di distorsione per performance"""
        h, w = 1080, 1920  # Modifica con la risoluzione della tua camera
        return cv2.initUndistortRectifyMap(
            self.calibration_data['camera_matrix'],
            self.calibration_data['dist_coeffs'],
            None,
            self.calibration_data['camera_matrix'],
            (w, h),
            cv2.CV_16SC2
        )

    async def startVideoStreaming(self):        
        """Avvia lo streaming video con zoom ottimizzato"""
        self.isrecording = True
        logging.info("Avvio streaming video con zoom...")

        try:
            while self.isrecording:
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("Errore lettura frame")
                    break

                # Processa il frame con zoom
                processed_frame = self._apply_zoom(frame)
                
                # Converti e codifica
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                _, buffer = cv2.imencode(".jpg", rgb_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                
                await self.websocket.send(json.dumps({
                    "ok": True,
                    "videoStarted": True,
                    "frame": base64.b64encode(buffer).decode("utf-8"),
                    "zoomFactor": self.zoom_factor
                }))

                if self.out is not None and self.isrecording: # Se ce un video attivo in corso invia i frame in oltre anche al videowriter
                    self.out.write(processed_frame)

                await asyncio.sleep(1 / self.client_fps)

        except Exception as e:
            logging.exception(f"Errore streaming: {e}")
        finally:
            self.cap.release()

    def _apply_zoom(self, frame):
        """Applica zoom/dezoom mantenendo le performance"""
        if self.zoom_factor == 1.0:
            return frame

        h, w = frame.shape[:2]
        
        # Dezoom (grandangolo virtuale)
        if self.zoom_factor < 1.0:
            # 1. Correzione distorsione
            corrected = cv2.remap(frame, self.map1, self.map2, cv2.INTER_LINEAR)
            
            # 2. Ritaglio centrale
            crop_size = int(w * self.zoom_factor), int(h * self.zoom_factor) # tupla che contiente la lunghezza moltiplicata per il zoom factor e l'altezza sempre moltiplicata con esso
            start_x, start_y = (w - crop_size[0]) // 2, (h - crop_size[1]) // 2 # trova la x centrale e la y centrale sottraendo la lunghezza e l'altezza iniziali per le corrispettive dimensioni scalate ( crop ) e le divide per 2
            cropped = corrected[start_y:start_y+crop_size[1], start_x:start_x+crop_size[0]]
            
            # 3. Ridimensionamento veloce
            return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        # Zoom digitale
        else:
            crop_size = int(w / self.zoom_factor), int(h / self.zoom_factor)
            start_x, start_y = (w - crop_size[0]) // 2, (h - crop_size[1]) // 2
            cropped = frame[start_y:start_y+crop_size[1], start_x:start_x+crop_size[0]]
            return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    def setZoomValue(self, value):
        """Imposta il valore di zoom con limiti e logica aggiuntiva"""
        self.zoom_factor = np.clip(float(value), 0.5, 3.0)  # Limita tra 0.5x e 3.0x
        logging.info(f"Zoom aggiornato a: {self.zoom_factor}x")
    
    async def toggleNightMode(self, value):
        """Abilita o disabilita il night mode"""
        self.night_mode = NightMode(value)
        status = True if value == NightMode.ON.value else False
        logging.info(f"Modalità notte: {status}")
        await self.websocket.send(json.dumps({"ok": True, "nightModeStatus": status}))
    
    def setZoomValue(self, value):
        """Imposta il valore di zoom"""
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("Il valore di zoom deve essere un numero positivo")
        self.zoom_factor = min(max(value, 0.1), 3.0)
    
    def apply_night_vision(self, frame):
        """Applica un effetto di visione notturna ottimizzato per alte prestazioni"""
        # Converti in scala di grigi
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Aumenta il contrasto con equalizzazione dell'istogramma
        enhanced = cv2.equalizeHist(gray)

        # Normalizza la luminosità per mantenere dettagli chiari e scuri
        normalized = cv2.normalize(enhanced, None, 50, 255, cv2.NORM_MINMAX)

        # Crea un'immagine verde mantenendo i dettagli nitidi
        night_vision = np.zeros_like(frame)
        night_vision[:, :, 1] = normalized  # Canale verde

        return night_vision

    def startRecording(self, filename="recorded_video.avi"):
        """
        Avvia la registrazione video utilizzando la videocamera attuale (self.cap).

        Il video viene salvato nel file specificato e la registrazione continua 
        finché `self.isrecording` rimane `True`.
        
        :param filename: Nome del file in cui salvare il video (default: "recorded_video.avi").
        """
        self.isrecording = True
        fourcc = cv2.VideoWriter().fourcc(*'XVID')
        self.out = cv2.VideoWriter(filename, fourcc, self.client_fps, (640, 480))
        logging.info("Registrazione avviata.")

    async def stopRecording(self):
        """
        Ferma la registrazione, invia il video al client via WebSocket e rilascia le risorse.
        """
        self.isrecording = False
        if self.out:
            self.out.release()
            self.out = None
            logging.info("Registrazione fermata.")

        save_dir = Path(__file__).parent / "public/client" # Prendo l'uri della cartella root del progetto ed entro in public/clientvideos per salvarvi i

        video_filename = "recorded_video.avi"
        video_path = save_dir / video_filename # indico come uri di salvataggio la cartella pubblica per i video con il nome del file

        logging.info(f"Video salvato in: {video_path}")

class NightMode(enum.Enum):
    """ Enum per la gestione del night mode """
    ON = 1
    OFF = 0
