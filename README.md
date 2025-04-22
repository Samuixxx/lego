# Controllo Remoto LEGO via WebSocket

[![Licenza](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![Cross-Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![Electron](https://img.shields.io/badge/Built%20with-Electron-blueviolet.svg)
![Python](https://img.shields.io/badge/Backend-Python-yellow.svg)

## Descrizione del Progetto

Questo progetto implementa un'applicazione desktop cross-platform basata su Electron per il controllo remoto di un veicolo LEGO. Il backend è un server WebSocket sicuro (WSS) scritto in Python, che gestisce la comunicazione bidirezionale tra il client (frontend Electron) e i dispositivi hardware (telecamera, motori, audio). L'applicazione offre un'interfaccia utente intuitiva per controllare il veicolo in tempo reale, gestire lo streaming video, regolare le impostazioni audio e altro ancora.

## Funzionalità Principali

**Frontend (Electron)**

* Interfaccia utente intuitiva (HTML, CSS, JavaScript).
* Streaming video live dalla telecamera integrata.
* **Controllo Movimento Avanzato:** Avanti/Indietro, Sterzata Sinistra/Destra, Cambio Marcia, Turbo/Freno.
* **Gestione Audio:** Riproduzione, Pausa, Ripresa, Loop, Regolazione Volume e Panning.
* Supporto Modalità Notturna e Zoom della Telecamera.
* Funzionalità di Registrazione Video e Scatto Fotografico.

**Backend (Python WebSocket Server)**

* Server WebSocket sicuro (WSS) con crittografia SSL/TLS.
* Integrazione con dispositivi hardware (motori via API, streaming video, impostazioni telecamera, gestione audio).
* Architettura modulare per facilità di estensione e manutenzione.
* Logging dettagliato per monitoraggio e debug.

## Requisiti di Sistema

**Frontend**

* **Sistemi Operativi:** Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+ e distribuzioni moderne).
* Node.js (v16+) e npm installati.
* Electron v23+.

**Backend**

* Python 3.10+.
* **Librerie Python:**
    ```bash
    pip install websockets mutagen python-dotenv opencv-python
    ```
* Altre dipendenze (installabili via `pip`).

**Hardware**

* Telecamera compatibile con OpenCV.
* Motori LEGO controllabili tramite API.
* Dispositivo audio compatibile.

## Installazione

1.  **Clonare il Repository:**
    ```bash
    git clone [https://github.com/username/repository-name.git](https://github.com/username/repository-name.git)
    cd repository-name
    ```

2.  **Configurare l'Ambiente:**

    **Backend:**
    Crea un file `.env` nella root del progetto:
    ```env
    PORT=8765
    URL=localhost
    ```
    Installa le dipendenze Python:
    ```bash
    pip install -r backend/requirements.txt  # Assicurati di creare questo file!
    ```
    *(Suggerimento: Crea un file `requirements.txt` nella cartella `backend` con le librerie necessarie per una gestione più semplice delle dipendenze)*

    **Frontend:**
    Naviga nella cartella `frontend`:
    ```bash
    cd frontend
    ```
    Installa le dipendenze Node.js:
    ```bash
    npm install
    ```

3.  **Generare Certificati SSL (Opzionale):**
    Se non presenti, il server li genera automaticamente. Altrimenti, puoi crearli manualmente:
    ```bash
    openssl req -x509 -newkey rsa:4096 -keyout backend/private.key -out backend/certificate.crt -days 365 -nodes -subj "/CN=localhost"
    ```

4.  **Avviare l'Applicazione:**

    **Backend:**
    ```bash
    python backend/server.py
    ```

    **Frontend:**
    ```bash
    npm start
    ```

## Struttura del Progetto

project/
├── backend/
│   ├── server.py                # Server WebSocket principale
│   ├── utils/                   # Utility per telecamera, motori, audio
│   ├── certificate.crt          # Certificato SSL
│   └── private.key              # Chiave privata SSL
│   └── requirements.txt         # Dipendenze Python
│
├── frontend/
│   ├── main.js                  # Entry point dell'app Electron
│   ├── index.html               # Interfaccia utente principale
│   ├── styles.css               # Stili CSS
│   └── assets/                  # Risorse statiche
│   └── package.json             # Metadati e script npm
│   └── package-lock.json        # Lock delle dipendenze npm
│
├── .env                         # Variabili d'ambiente
├── README.md                    # Documentazione del progetto (questo file)
└── https://www.google.com/search?q=LICENSE                      # Licenza del progetto


## API e Protocollo di Comunicazione

Il server WebSocket comunica tramite messaggi JSON con la seguente struttura:

```json
{
  "type": "tipo_di_comando",
  "content": "valore_del_contenuto"
}
Esempi di Comandi:

Avviare lo streaming video:
JSON

{ "type": "start-video-streaming" }
Impostare il livello del turbo:
JSON

{ "type": "set-turbo", "content": "50%" }
Riprodurre un file audio (base64 encoded):
JSON

{ "type": "new-audio", "content": "base64_encoded_audio", "name": "audio.wav" }
(Per dettagli completi sull'API, fare riferimento alla documentazione interna del server (backend/server.py)).

Contributi
I contributi sono benvenuti!

Forka il repository.
Crea una branch per la tua feature (git checkout -b feature/nome-feature).
Effettua le modifiche e committa (git commit -am 'Aggiungi nuova feature').
Esegui il push sulla branch (git push origin feature/nome-feature).
Crea una nuova Pull Request.
Licenza
Rilasciato sotto la licenza Apache 2.0. Consulta il file LICENSE per i dettagli completi.

Contatti
Per domande o suggerimenti, non esitare a contattarmi:

Email: casalinsamuele@gmail.com
GitHub: https://github.com/Samuixxx
<!-- end list -->


**Principali modifiche e miglioramenti:**

* **Titolo più accattivante:** Aggiunto un titolo più descrittivo.
* **Badge:** Inclusi badge per licenza, piattaforma e tecnologie utilizzate per una rapida visualizzazione.
* **Descrizione concisa:** Resa la descrizione più breve e diretta.
* **Formattazione Markdown standard:** Utilizzo di intestazioni (`#`, `##`), liste puntate (`*`), blocchi di codice (```), e link per una migliore leggibilità su GitHub.
* **File `requirements.txt`:** Suggerito l'uso di un file `requirements.txt` per il backend per una gestione più efficiente delle dipendenze.
* **Struttura del Progetto più chiara:** Evidenziati i file chiave all'interno delle cartelle.
* **Sezione API più concisa:** Mantenute le informazioni essenziali.
* **Guida ai Contributi standard:** Fornita una procedura chiara per chi volesse contribuire.
* **Informazioni sulla Licenza:** Aggiunto un link alla licenza.
* **Dettagli di Contatto:** Formattati come link mailto e URL.
