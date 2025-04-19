"""
Modulo: CameraUtils

Descrizione:
Modulo per la gestione della videocamera e della trasmissione dati via __websocket.
Questo modulo fornisce una classe `CameraUtils` per controllare una videocamera, gestire lo 
streaming di immagini, acquisire foto e registrare video. Supporta funzionalità avanzate come 
modalità notturna, zoom e calibrazione della lente per correggere distorsioni ottiche.

Dipendenze:
- cv2 per l'elaborazione delle immagini (`opencv-python`).
- NumPy per la manipolazione delle immagini (`numpy`).
- asyncio per la gestione delle operazioni asincrone (`asyncio`).
- base64 per la codifica delle immagini in stringhe trasmissibili via __websocket (`builtin`).
- json per la gestione della comunicazione dei dati (`builtin`).
- logging per il monitoraggio delle operazioni (`logging`).
- os e pathlib per la gestione dei file (`builtin`) (`pathlib`).
- datetime per la registrazione temporale delle acquisizioni (`builtin`).
- shutil per la gestione dei file di output (`builtin`).

Autore: Zs
Data di Creazione: 02-04-2025
"""

import cv2
import base64
import asyncio
import json
import logging
import os
import numpy as np
from pathlib import Path
from datetime import datetime
import shutil
from utils.camera.cameraenums.night_mode import NightMode

class CameraUtils:
    """
    Classe per la gestione della videocamera e della trasmissione video tramite __websocket.

    Attributi:
        __websocket (websockets): Connessione websocket con il client.
        _camera_index (int): Indice della videocamera da utilizzare.
        __cap (cv2.VideoCapture): Istanza della videocamera per acquisire i frame.
        _is_streaming (bool): Indica se il server sta trasmettendo i frame al client.
        _is_recording (bool): Indica se il client ha richiesto la registrazione di un video.
        _want_photo (bool): Indica se il client ha richiesto una foto.
        __out (cv2.VideoWriter | None): Oggetto per la registrazione del video (se attiva).
        _night_mode (NightMode): Modalità notturna attiva/disattiva.
        _monitor_max_hz (int): Frequenza di aggiornamento del monitor del client.
        _zoom_factor (float): Fattore di zoom per la trasmissione delle immagini.
        calibration_data (dict): Dati di calibrazione della videocamera.
        map1 (numpy.ndarray): Mappa di distorsione per la correzione dell'immagine.
        map2 (numpy.ndarray): Seconda mappa di distorsione per la correzione dell'immagine.
    """

    def __init__(self, websocket, camera_index:int = 0, monitor_max_hz:int = 60, camera_dimension: tuple[int, int] = (640, 480)):
        """
        Inizializza la videocamera e configura le variabili di stato.

        Args:
            websocket (websockets): Connessione websocket per la trasmissione dati.
            camera_index (int, opzionale): Indice della videocamera da utilizzare (default: 0).
            _monitor_max_hz (int, opzionale): Frequenza di aggiornamento del client (default: 60).
            camera_dimension (tuple[int, int], opzionale): Dimensioni massime supportate dalla videocamera (default: (640, 480)).
        """
        self.__websocket = websocket  # Connessione __websocket con il client
        self._camera_index = camera_index
        self.__cap = cv2.VideoCapture(self._camera_index)  # Istanza della videocamera
        self._camera_width, self._camera_height = camera_dimension # Lunghezza e altezza massima supportata dalla videocamera del client.
        self._is_streaming = False  # Stato della trasmissione video
        self._is_recording = False  # Stato della registrazione video
        self._want_photo = False  # Stato della richiesta di una foto
        self.__out = None  # Oggetto per la registrazione video (inizialmente nullo)
        self._night_mode = NightMode.OFF  # Modalità notturna (OFF per default)
        self._monitor_max_hz = monitor_max_hz  # Frequenza di aggiornamento del client
        self._zoom_factor = 1.0  # Valore di zoom per la trasmissione video
        self.calibration_data = self._load_calibration()  # Caricamento dati di calibrazione
        self.map1, self.map2 = self._init_distortion_maps()  # Creazione delle mappe di distorsione

    def _load_calibration(self):
        """
        Carica i parametri di calibrazione della fotocamera.

        Questa funzione restituisce i parametri di calibrazione della fotocamera, inclusa la matrice della fotocamera
        e i coefficienti di distorsione. I valori sono utilizzati per correggere la distorsione ottica durante l'elaborazione
        delle immagini.

        I valori di calibrazione sono tipicamente ottenuti da una procedura di calibrazione della fotocamera (ad esempio, 
        utilizzando il modulo `cv2.calibrateCamera` di OpenCV) e devono essere personalizzati in base alla fotocamera in uso.

        Raises:
            ValueError: Se i parametri di calibrazione non sono validi o non possono essere caricati correttamente.
        Returns:
            dict: Un dizionario contenente la matrice della fotocamera e i coefficienti di distorsione.
        """
        try:
            # Parametri di calibrazione per la fotocamera
            camera_matrix = np.array([
                [1.100e+03, 0.000e+00, 9.600e+02],
                [0.000e+00, 1.100e+03, 5.400e+02],
                [0.000e+00, 0.000e+00, 1.000e+00]
            ])

            dist_coeffs = np.array([-0.15, 0.05, 0.001, 0.001, 0.000])  # Coefficienti di distorsione

            # Verifica che la matrice della fotocamera e i coefficienti di distorsione abbiano la forma corretta
            if camera_matrix.shape != (3, 3):
                raise ValueError("La matrice della fotocamera non ha la forma corretta (3x3).")
            if dist_coeffs.shape != (5,):
                raise ValueError("I coefficienti di distorsione non hanno la forma corretta (5 valori).")

            logging.info("Calibrazione della fotocamera caricata correttamente.")
            return {
                'camera_matrix': camera_matrix,
                'dist_coeffs': dist_coeffs
            }

        except ValueError as e:
            logging.error(f"Errore nei parametri di calibrazione: {e}")
            raise
        except Exception as e:
            logging.exception(f"Errore imprevisto durante il caricamento della calibrazione: {e}")
            raise

    def _init_distortion_maps(self):
        """
        Precalcola le mappe di distorsione per ottimizzare la correzione della distorsione ottica.

        Questa funzione utilizza i dati di calibrazione della fotocamera per generare le mappe di distorsione, 
        consentendo la correzione geometrica in tempo reale senza dover ricalcolare i parametri di calibrazione 
        per ogni frame.

        Raises:
            ValueError: Se i dati di calibrazione non sono validi o non sono stati forniti.
            KeyError: Se manca la chiave di calibrazione.
            cv2.error: Se si verifica un errore durante la creazione delle mappe di distorsione.
            RuntimeError: Se si verifica un errore imprevisto durante la creazione delle mappe di distorsione.

        Returns:
            tuple: Una tupla contenente le mappe di distorsione necessarie per la correzione delle immagini.
        """
        try:
            # Verifica se i dati di calibrazione sono presenti e validi
            if 'camera_matrix' not in self.calibration_data or 'dist_coeffs' not in self.calibration_data:
                raise ValueError("I dati di calibrazione della fotocamera non sono validi o mancanti.")

            h, w = self._camera_height, self._camera_width  # Risoluzione della fotocamera; adattabile in base alla tua configurazione
            # Calcola le mappe di distorsione
            map1, map2 = cv2.initUndistortRectifyMap(
                self.calibration_data['camera_matrix'],
                self.calibration_data['dist_coeffs'],
                None,  
                self.calibration_data['camera_matrix'],  # La matrice di proiezione dopo la rettifica
                (w, h),  
                cv2.CV_16SC2  
            )
            logging.info("Mappe di distorsione calcolate con successo.")
            return map1, map2

        except KeyError as e:
            logging.error(f"Errore nei dati di calibrazione: chiave mancante {e}")
            raise ValueError(f"I dati di calibrazione sono incompleti: {e}")
        except cv2.error as e:
            logging.error(f"Errore OpenCV durante la creazione delle mappe di distorsione: {e}")
            raise RuntimeError("Errore durante la creazione delle mappe di distorsione con OpenCV.")
        except Exception as e:
            logging.exception(f"Errore imprevisto nella creazione delle mappe di distorsione: {e}")
            raise

    async def start_video_streaming(self):        
        """
        Avvia lo streaming video con zoom, supportando modalità notturna, registrazione e cattura foto.

        Raises:
            StreamingException: Se si verifica un errore durante la lettura, elaborazione o invio dei frame.
        """
        self._is_streaming = True

        try:
            if not self.__cap or not self.__cap.isOpened():
                raise RuntimeError("La videocamera non è inizializzata correttamente.")

            while self._is_streaming:
                ret, frame = self.__cap.read()

                if not ret:
                    logging.warning("Frame non letto correttamente dalla videocamera.")
                    break

                try:
                    # Applica zoom
                    processed_frame = self._apply_zoom(frame)

                    # Modalità notturna se abilitata
                    if self._night_mode == NightMode.ON:
                        processed_frame = self._apply_night_mode(processed_frame)

                    # Conversione in RGB e codifica JPEG
                    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                    success, buffer = cv2.imencode(".jpg", rgb_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                    if not success:
                        raise ValueError("Impossibile codificare il frame in JPEG.")

                    # Scrittura su file se registrazione attiva
                    if self._is_recording and self.__out:
                        self.__out.write(processed_frame)

                    # Cattura foto se richiesto
                    if self._want_photo:
                        self._want_photo = False
                        await self._save_photo(processed_frame)

                    # Invio al client via websocket
                    await self.__websocket.send(json.dumps({
                        "ok": True,
                        "streaming": True,
                        "frame": base64.b64encode(buffer).decode("utf-8"),
                    }))

                    await asyncio.sleep(1 / self._monitor_max_hz)

                except cv2.error as e:
                    logging.error(f"Errore OpenCV durante lo streaming: {e}")
                    break

                except Exception as e:
                    logging.error(f"Errore imprevisto durante lo streaming: {e}")
                    break

        except Exception as e:
            logging.exception(f"Errore all'inizio dello streaming video: {e}")

        finally:
            if self.__cap and self.__cap.isOpened():
                self.__cap.release()
            if self.__out:
                self.__out.release()

            self._is_streaming = False
            logging.info("Streaming video terminato.")


    def set_zoom_value(self, value: float):
        """
        Imposta il valore dello zoom quando il client lo modifica, assicurandosi che rientri nei limiti consentiti.

        Il valore dello zoom viene limitato automaticamente tra 0.5x e 3.0x per 
        evitare distorsioni o problemi di visualizzazione.

        Args:
            value (float): Il valore desiderato per lo zoom.

        Returns:
            None
        """
        self._zoom_factor = np.clip(float(value), 0.5, 3.0)  # Limita tra 0.5x e 3.0x
        logging.info(f"Zoom aggiornato a: {self._zoom_factor}x")

    def _apply_zoom(self, frame):
        """
        Applica zoom o grandangolo (dezoom) su un frame.

        Il metodo gestisce lo zoom digitale quando il fattore è maggiore di 1.0,
        mentre applica un effetto grandangolo (dezoom) quando il fattore è minore di 1.0.

        Args:
            frame (numpy.ndarray): Il frame su cui applicare lo zoom.

        Returns:
            numpy.ndarray: Il frame con lo zoom applicato, o il frame originale in caso di errore.
        """
        if frame is None or frame.size == 0:
            logging.error("Errore: frame vuoto ricevuto!")
            return frame

        if self._zoom_factor == 1.0:
            return frame

        h, w = frame.shape[:2]

        # Zoom digitale (ingrandisce l'immagine)
        if self._zoom_factor > 1.0:
            try:
                # 1. Calcolo ritaglio centrale
                crop_w, crop_h = int(w / self._zoom_factor), int(h / self._zoom_factor)
                start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2
                end_x, end_y = start_x + crop_w, start_y + crop_h

                # Verifica validità del ritaglio
                if crop_w <= 0 or crop_h <= 0:
                    logging.error("Errore: ritaglio con dimensioni non valide!")
                    return frame

                cropped = frame[start_y:end_y, start_x:end_x]

                # 2. Ridimensionamento per riportare il frame alle dimensioni originali
                return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

            except Exception as e:
                logging.error(f"Errore durante lo zoom digitale: {e}")
                return frame

        # Grandangolo (dezoom): riduce l'ingrandimento e amplia il campo visivo
        else:
            try:
                new_h, new_w = int(h / self._zoom_factor), int(w / self._zoom_factor)

                # Verifica validità dimensioni
                if new_w <= 0 or new_h <= 0:
                    logging.error("Errore: dimensioni grandangolo non valide!")
                    return frame

                # 1. Espansione dell'immagine
                expanded_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

                # 2. Correzione distorsione grandangolo (se disponibile)
                if hasattr(self, "map1") and hasattr(self, "map2"):
                    expanded_frame = cv2.remap(expanded_frame, self.map1, self.map2, cv2.INTER_LINEAR)

                # 3. Ritaglio al centro per mantenere le proporzioni originali
                start_x, start_y = (new_w - w) // 2, (new_h - h) // 2
                end_x, end_y = start_x + w, start_y + h

                return expanded_frame[start_y:end_y, start_x:end_x]

            except Exception as e:
                logging.error(f"Errore durante il dezoom (grandangolo): {e}")
                return frame

    async def toggle_night_mode(self, value: int):
        """
        Abilita o disabilita la modalità notte.

        Args:
            value (int): 0 per disattivare, 1 per attivare la modalità notte.
        
        Raises:
            ValueError: se il valore non è 0 o 1.
        
        Returns:
            None.
        """
        try:
            self._night_mode = NightMode(value)  # Converte il valore in Enum
            status = (self._night_mode == NightMode.ON)
            logging.info(f"Modalità notte attivata: {status}")
        except ValueError:
            logging.error(f"Valore non valido per la modalità notte: {value}")


    def _apply_night_mode(self, frame):
        """
        Applica un effetto di visione notturna all'immagine fornita, migliorando il contrasto e la luminosità 
        per adattarsi a una modalità a bassa luminosità.

        Se la modalità notturna è abilitata dal client, questa funzione converte il frame in scala di grigi, 
        aumenta il contrasto, normalizza la luminosità e applica un filtro verde per simulare un effetto di visione notturna.

        Args:
            frame (numpy.ndarray): L'immagine del frame da processare (BGR).

        Returns: 
            numpy.ndarray: L'immagine con effetto di visione notturna applicato, mantenendo i dettagli chiari e scuri.
        """
        try:
            # Converti l'immagine in scala di grigi per facilitare il miglioramento del contrasto
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Aumenta il contrasto utilizzando l'equalizzazione dell'istogramma
            enhanced = cv2.equalizeHist(gray)

            # Normalizza la luminosità per migliorare i dettagli scuri e chiari
            normalized = cv2.normalize(enhanced, None, 50, 255, cv2.NORM_MINMAX)

            # Crea un'immagine in cui il canale verde simula l'effetto di visione notturna
            night_vision = np.zeros_like(frame)
            night_vision[:, :, 1] = normalized  # Solo il canale verde contiene i dettagli migliorati

            logging.info("Modalità notturna applicata correttamente.")

            return night_vision

        except Exception as e:
            logging.error(f"Errore nell'applicazione della modalità notturna: {str(e)}")
            raise RuntimeError("Impossibile applicare la modalità notturna al frame.") from e

    def start_recording(self):
        """
        Avvia la registrazione video utilizzando la videocamera attuale (self.__cap)
        e salva il video in un file temporaneo nella cartella "user/videos/temp".

        Raises:
            RuntimeError: Se la videocamera o il VideoWriter non possono essere inizializzati.
        """
        if self._is_recording:
            logging.warning("La registrazione è già in corso. Impossibile avviarne un'altra.")
            return

        try:
            if not self.__cap or not self.__cap.isOpened():
                raise RuntimeError("La videocamera non è inizializzata correttamente.")

            self._is_recording = True

            # Percorso salvataggio
            temp_filename = "temp_video.avi"
            save_dir = Path(__file__).parent.parent.parent / "user/videos/temp"
            os.makedirs(save_dir, exist_ok=True)
            temp_path = save_dir / temp_filename

            # Parametri camera
            cam_fps = int(self.__cap.get(cv2.CAP_PROP_FPS))
            cam_fps = cam_fps if cam_fps > 0 else 30

            width = int(self.__cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.__cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if width == 0 or height == 0:
                logging.warning("Dimensioni non valide dalla camera. Uso fallback 640x480.")
                width, height = 640, 480

            logging.debug(f"FPS: {cam_fps}, Width: {width}, Height: {height}")

            # Codec video e VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec più compatibile
            self.__out = cv2.VideoWriter(str(temp_path), fourcc, cam_fps, (width, height))

            if not self.__out.isOpened():
                raise RuntimeError("Impossibile inizializzare il VideoWriter. Verifica la videocamera o il codec.")

            logging.info(f"Registrazione avviata. File: {temp_path}")

        except Exception as e:
            logging.error(f"Errore durante l'avvio della registrazione: {str(e)}")
            self._is_recording = False
            raise

    async def stop_recording(self):
        """
        Termina la registrazione video e salva il file.

        Se la registrazione non è in corso (`self._is_recording` è `False`), la funzione esce senza eseguire alcuna operazione.

        La funzione rilascia il `VideoWriter` e salva il video registrato nella cartella di destinazione, utilizzando un nome basato sul timestamp corrente. La cartella di destinazione viene creata se non esiste già. Il file temporaneo utilizzato per la registrazione viene rinominato e spostato nella destinazione finale.

        Inoltre, invia una notifica tramite il __websocket con il percorso del video salvato.

        Raises:
            FileNotFoundError: Se la cartella di salvataggio non può essere trovata o creata.
            RuntimeError: Se la videocamera non può essere inizializzata o se la registrazione non può essere fermata.

        Returns:
            None.
        """

        if not self._is_recording:
            logging.warning("Tentativo di fermare una registrazione che non è in corso.")
            return  

        self._is_recording = False  # Segnala che la registrazione è terminata
        base_dir = Path(__file__).parent.parent.parent.parent

        if self.__out:
            self.__out.release()  # Rilascia il VideoWriter
            self.__out = None
            logging.info("Registrazione terminata correttamente.")

        # Genera il timestamp per il nome definitivo del file
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        final_filename = f"video_{timestamp}.avi"

        # Percorso di salvataggio del video
        temp_dir = base_dir / "user/videos/temp"
        save_dir = base_dir / "user/videos"
        os.makedirs(save_dir, exist_ok=True)  # Crea la cartella di salvataggio se non esiste

        # Percorso del file temporaneo (assumendo che sia stato salvato con un nome fisso)
        temp_filename =  temp_dir / "temp_video.avi"
        temp_path = Path(temp_filename)

        # Percorso del file finale con timestamp
        final_path = save_dir / final_filename

        # Verifica che il file temporaneo esista prima di rinominarlo
        if temp_path.exists():
            os.rename(temp_path, final_path)  # Rinomina/sposta il file
            shutil.rmtree(temp_dir) # elimino la cartella temporanea

            relative_path = final_path.relative_to(base_dir)
            await self.__websocket.send(json.dumps({
                "ok": True, "videoPath": str(relative_path)
            }))
            logging.info(f"Video salvato correttamente: {final_path}")
        else:
            logging.error("Errore: il file temporaneo non esiste, impossibile salvarlo.")
    
    def set_photo_request(self):
        """
        Imposta il flag `_want_photo` a `True`, segnalando la richiesta di acquisire una foto.

        Questo flag verrà controllato durante lo streaming per catturare un frame 
        e salvarlo come immagine quando necessario.
        """
        if self._want_photo:
            logging.warning("Una richiesta di foto è già in corso.")
            return

        self._want_photo = True

    async def _save_photo(self, frame):
        """
        Cattura un frame e lo salva come immagine nella directory predefinita.

        La funzione salva l'immagine in formato JPG, assegnandole un nome unico basato 
        sul timestamp corrente. Se la directory di destinazione non esiste, viene creata automaticamente.

        Args:
            frame: Il frame catturato dalla videocamera (matrice numpy di OpenCV).
        """
        # Definisce la cartella di salvataggio delle immagini
        base_dir = Path(__file__).parent.parent.parent.parent
        save_dir = base_dir / "user/photos"

        # Crea la directory se non esiste (evita errori di scrittura)
        os.makedirs(save_dir, exist_ok=True)

        # Genera il nome file con timestamp per garantire unicità
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        filename = f"picture_{timestamp}.jpg"
        photo_path = save_dir / filename

        # Salva il frame come immagine JPG
        success = cv2.imwrite(str(photo_path), frame)

        relative_photo_path = photo_path.relative_to(base_dir)

        await self.__websocket.send(json.dumps({
            "ok": True, "photoPath": str(relative_photo_path)
        }))

        if success:
            logging.info(f"Foto salvata con successo: {photo_path}")
        else:
            logging.error("Errore durante il salvataggio della foto.")


