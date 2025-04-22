"""
Modulo: ServerUtils

Descrizione:
Questo modulo fornisce un metodo per ottenere la frequenza di aggiornamento del monitor primario
compatibile con Windows, Linux, MacOS e Raspberry Pi.

Dipendenze:
- sys per accedere alla piattaforma del client.
- ctypes per creare un'istanza dell'api windows di gestione dello schermo.
- subprocess per aprire un cmd ed eseguire un comando senza doverlo far fare all'utente.
- cv2 per ottenere la lunghezza e l'altezza supportate dalla videocamera del client.
- logging per configurare le impostazioni di logging del server.
- os per utils di directory.

Autore: ZS
Data: 2025-04-02
"""

import sys
import ctypes
import subprocess
import cv2
import logging
import os

class ServerUtils:
    """
    Classe contenente metodi di utilità per il server.
    """

    @staticmethod
    def get_monitor_refresh_rate():
        """
        Restituisce la frequenza di aggiornamento del monitor primario.
        Supporta Windows, Linux, MacOS e Raspberry Pi.
        
        Returns:
            int: Frequenza di aggiornamento del monitor in Hertz (Hz), oppure None se non disponibile.
        """
        if sys.platform.startswith("win"):  # Controllo per Windows
            user32 = ctypes.windll.user32  # Ottenere un'istanza dell'API di Windows per la gestione dello schermo
            dc = user32.GetDC(0)  # Ottenere il device context (DC) per il desktop
            refresh_rate = ctypes.windll.gdi32.GetDeviceCaps(dc, 116)  # 116 è l'indice per VREFRESH
            user32.ReleaseDC(0, dc)  # Rilascia il device context per evitare perdite di risorse
            return refresh_rate
        
        elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):  # Controllo per Linux e MacOS
            try:
                output = subprocess.check_output(["xrandr"], stderr=subprocess.DEVNULL).decode()
                for line in output.split("\n"):
                    if "*" in line:  # La frequenza di aggiornamento attuale è segnata con un asterisco
                        return int(float(line.split()[0]))
            except Exception:
                return 30  
        
        elif sys.platform.startswith("raspberrypi"):  # Controllo per Raspberry Pi
            try:
                output = subprocess.check_output(["tvservice", "-s"]).decode()
                for part in output.split(","):
                    if "Hz" in part:
                        return int(float(part.split()[0]))
            except Exception:
                return 30
        
        return None  # Se il sistema operativo non è supportato, restituisce None
    
    def get_camera_resolution(camera_index=0):
        """
        Ottiene la risoluzione (larghezza e altezza) supportata dalla videocamera.

        Args:
            camera_index (int): Indice della videocamera da aprire (default: 0).

        Returns:
            tuple: (larghezza, altezza) della videocamera.
        """
        cap = cv2.VideoCapture(camera_index)  # Apri la videocamera
        if not cap.isOpened():
            print("Errore: impossibile aprire la videocamera")
            return None

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # Ottieni la larghezza
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # Ottieni l'altezza

        cap.release()  # Rilascia la videocamera
        return width, height
    
    @staticmethod
    def configure_logging():
        """
        Configura il sistema di logging dell'applicazione.

        Imposta un formato standard per i messaggi di log, salva i log in un file "log.txt"
        e li visualizza anche sul terminale. Riduce al minimo i messaggi di default di Pygame
        impostando il livello di logging del modulo "pygame" a CRITICAL.

        Returns:
            None
        """
        # Configurazione del sistema di logging
        logging.basicConfig(
            level=logging.INFO,  # Livello di logging: INFO
            format="%(asctime)s [%(levelname)s] %(message)s",  # Formato del messaggio di log
            datefmt="%Y-%m-%d %H:%M:%S",  # Formato della data/ora
            handlers=[
                logging.FileHandler(os.path.join(os.getcwd(), "log.txt")),  # Salva i log in un file
                logging.StreamHandler()  # Visualizza i log sul terminale
            ]
        )

        # Riduci al minimo i messaggi di default di Pygame
        logging.getLogger("pygame").setLevel(logging.CRITICAL)

        # Messaggio di conferma
        logging.info("Logging configurato correttamente. I log verranno salvati in 'log.txt'.")