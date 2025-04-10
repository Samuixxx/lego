/**
 * @file index.js
 * @description File principale per la gestione delle risorse disponibili di utilizzo del lego (client-side).
 * @author Zs
 * @version 1.0.0
 * @date 02-04-2025
 */

document.addEventListener("DOMContentLoaded", () => {

    // ===================== CONFIGURAZIONE BOTTONI PER GESTIRE IL BROWSER  WINDOW (MASSIMIZZAZIONE, MINIMIZZAZIONE, CHIUSURA) =====================
    const maximizeWindowButton = document.querySelector(".maximize-button");
    const minimizeWindowButton = document.querySelector(".minimize-button");
    const closeWindowButton = document.querySelector(".close-button");

    if (!maximizeWindowButton || !minimizeWindowButton || !closeWindowButton) {
        console.error("Window control buttons not found.");
        return;
    }

    /**
 * Object containing functions for controlling application windows.  Provides methods to maximize, minimize, and close the window via communication with a window API.

 * @type {Object}
 * @property {function} maximize - Sends a message to maximize the application window.
 * @property {function} minimize - Sends a message to minimize the application window.
 * @property {function} close - Sends a message to close the application window.
 */

    const windowControls = {
        maximize: () => window.windowapi.send("maximize-window", {}),
        minimize: () => window.windowapi.send("minimize-window", {}),
        close: () => window.windowapi.send("close-window", {})
    };

    maximizeWindowButton.addEventListener("click", windowControls.maximize);
    minimizeWindowButton.addEventListener("click", windowControls.minimize);
    closeWindowButton.addEventListener("click", windowControls.close);

    // ===================== CONFIGURAZIONE CLIENT SOCKET =====================
    const socket = new WebSocket("wss://localhost:8765");

    socket.onopen = () => {
        console.log("Connected to the server");
        socket.send(JSON.stringify({ type: "start-video-streaming", content: "" }));
    };

    socket.onclose = () => {
        console.log("Disconnected from the server");
    };

    socket.onerror = (error) => {
        console.log("Error occurred");
    }

    socket.onmessage = function (event) {
        try {
            const response = JSON.parse(event.data);

            if (response.ok && response.motorStarted) {
                legoStatusButton.classList.remove("off");
                legoStatusButton.classList.add("on");
            }
            else if (response.ok && response.motorTurnedoff) {
                legoStatusButton.classList.remove("on");
                legoStatusButton.classList.add("off");
            }
            else if (response.ok && response.streaming && response.frame) {
                updateCamera(response.frame);
            }
            else if (response.ok && response.photoPath) {
                showNoty("success", `Nuova immagine salvata: ${response.photoPath}`);
            }
            else if (response.ok && response.videoPath) {
                showNoty("success", `Nuova video salvato: ${response.videoPath}`);
            }
            else if (response.ok && response.motorspeed !== undefined) {
                updateSpeed(response.motorspeed);
            }
            else if (response.ok && response.motorangle !== undefined) {
                updateAngle(response.motorangle);
            }
            else if (response.ok && response.audioDuration && response.audioName) {
                updateSongPreview(response.audioName, response.audioDuration);
            }
            else if (response.ok && response.currentAudioTime) {
                updateSongTime(response.currentAudioTime);
            }
        } catch (error) {
            console.error("Errore nella risposta WebSocket:", error);
        }
    };


    /**
    * Event Listener for Keyboard Input to Control Movement.
    *
    * This function listens for keyboard events and sends messages over a socket connection 
    * to control movement based on the pressed keys. It maintains a Set of active keys 
    * to allow simultaneous movement commands.
    *
    * @param {KeyboardEvent} event - The keyboard event object containing key press information.
    * @returns {void}
    */

    document.addEventListener("keydown", (event) => {
        switch (event.key) {
            case 'w':
                socket.send(JSON.stringify({ type: "move-forward", content: "" }));
                break;
            case 's':
                socket.send(JSON.stringify({ type: "move-backward", content: "" }));
                break;
            case 'a':
                socket.send(JSON.stringify({ type: "turn-left", content: "" }));
                break;
            case 'd':
                socket.send(JSON.stringify({ type: "turn-right", content: "" }));
                break;
        }
    });

    /**
     * Event Listener for Key Up Events.
     * 
     * This function listens for keyup events and removes the released key from the Set.
     * It ensures that movement stops when no relevant keys are pressed.
     *
     * @param {KeyboardEvent} event - The keyup event object.
     * @returns {void}
     */

    document.addEventListener("keyup", (event) => {
        switch (event.key) {
            case 'w':
                socket.send(JSON.stringify({ type: "stop-moving", content: "" }));
                break;
            case 's':
                socket.send(JSON.stringify({ type: "stop-moving", content: "" }));
                break;
            case 'a':
                socket.send(JSON.stringify({ type: "unturn-left", content: "" }));
                break;
            case 'd':
                socket.send(JSON.stringify({ type: "unturn-right", content: "" }));
                break;
        }
    });


    // ===================== CONFIGURAZIONE DELLA ROTAZIONE DELL'AGO DELLA BUSSOLA QUANDO IL CLIENT STERZA =====================
    /**
 * Updates the rotation angle of a compass needle element.
 * 
 * @param {number} angle - The angle in degrees to rotate the compass needle.
 * @returns {void}  This function modifies the DOM element directly and doesn't return a value.
 */

    const updateAngle = (angle) => {
        const needle = document.querySelector('.compass-needle');
        needle.style.transformOrigin = 'bottom center';
        needle.style.transform = `translateY(-${needle.offsetHeight}px) rotate(${angle}deg)`;
    }

    // ===================== CONFIGURAZIONE DELLA VIDEOCAMERA QUANDO IL CLIENT RICEVE I FRAME OTTENUTI DAL SOCKET SERVER =====================
    /**
 * Updates the camera preview on a canvas element.  This function takes a base64 encoded JPEG image frame and renders it onto a canvas.  Handles resizing the canvas to match the image dimensions.

 * @param {string} frame -immagine jpg codificata con base64 che rappresenta il frame della videocamera.
 * @returns {void} 
 */

    const updateCamera = (frame) => {
        const canvas = document.getElementById('camera-canvas');
        const ctx = canvas.getContext('2d');
        const image = new Image();

        image.onload = function () {
            canvas.width = image.width;
            canvas.height = image.height;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            ctx.drawImage(
                image,
                0, 0,                   // coordinate sorgente (x,y)
                image.width,             // larghezza sorgente
                image.height,            // altezza sorgente
                0, 0,                   // coordinate destinazione (x,y)
                canvas.width,           // larghezza destinazione
                canvas.height           // altezza destinazione
            );
        };

        image.src = `data:image/jpeg;base64,${frame}`;
    }

    // ===================== CONFIGURAZIONE DISPLAY DELLA VELOCITÁ QUANDO IL CLIENT ACCELLERA =====================
    /**
 * Updates the displayed speed and its color based on the provided speed value.
 * 
 * @param {number} speed - The speed value in km/h.  Negative values indicate reverse.
 * @returns {void}
 */

    const updateSpeed = (speed) => {
        const speedIndicator = document.getElementById("speed-indicator");

        speed = Number(speed);

        // Determina il valore da visualizzare per la velocità
        const displaySpeed = speed === 0 ? 0 : Math.abs(speed);

        // Determina il colore in base alla direzione
        let color;
        if (speed < 0) {
            color = "red";  // Retromarcia (negativa)
        } else if (speed === 0) {
            color = "var(--text-color-secondary)";  // Velocità zero
        } else {
            color = "var(--text-color-primary)";  // Movimento in avanti
        }

        // Mostra la velocità e imposta il colore
        speedIndicator.textContent = `${displaySpeed} km/h`;
        speedIndicator.style.color = color;
    };

    // ===================== CONFIGURAZIONE DELLE NOTIFICHE MOSTRATE QUANDO IL CLIENT RICEVE I PERCORSI DOVE SONO SALVATE LE IMMAGINI/VIDEO CHE HA RICHIESTO =====================
    /**
 * Displays a notification using the Noty library.
 * 
 * @function showNoty
 * @param {string} [type="success"] - The type of notification (e.g., "success", "error", "warning", "info"). Defaults to "success".
 * @param {string} text - The text content of the notification.
 * @param {number} [timeout=5000] - The duration (in milliseconds) to display the notification before automatically closing. Defaults to 5000ms (5 seconds).
 * @returns {void}  
 */

    const showNoty = (type = "success", text, timeout = 5000) => {
        new Noty({
            type: type,
            layout: "topRight",
            text: text,
            timeout: timeout,  // Scompare dopo 5 secondi
            progressBar: true
        }).show();
    }

    // ===================== CONFIGURAZIONE DELLA PREVIEW QUANDO IL CLIENT CARICA UNA CANZONE DA RIPRODURRE =====================
    /**
 * Updates the song preview elements with the provided title and duration.
 * 
 * @param {string} songTitle - The title of the song to display.
 * @param {string} songDuration - The duration of the song to display.
 * @returns {void}  
 */

    let currentSongDuration;
    const updateSongPreview = (songTitle, songDuration) => {
        // istanzio il titolo della preview e la span che contiene la lunghezza del brano
        const songPreviewTitle = document.getElementById("song-title");
        const songPreviewDuration = document.getElementById("total-song-duration");

        // Aggiorno i testo della preview 
        songPreviewTitle.textContent = songTitle;
        songPreviewDuration.textContent = songDuration;

        // converto per utilità nel calcolare il valore della progress bar
        const [minutes, seconds] = songDuration.split(":").map(Number);
        currentSongDuration = minutes * 60 + seconds; // Store total duration in seconds
    }

    // ===================== CONFIGURAZIONE DELL'INDICATORE DEI SECONDI DI RIPRODUZIONE ATTUALI E DELLA PROGRESS BAR =====================

    /**
 * Updates the displayed song time.
 * 
 * @param {string} songCurrentTime - The current time of the song to display.  Should be formatted appropriately for display.
 * @returns {void}
 */

    const updateSongTime = (songCurrentTime) => {
        if (!currentSongDuration) return;

        const songPreviewTime = document.getElementById("current-song-time");
        const progressBar = document.getElementById("progress-bar");

        const minutes = Math.floor(songCurrentTime / 60);
        const seconds = Math.floor(songCurrentTime % 60).toString().padStart(2, "0");
        songPreviewTime.textContent = `${minutes}:${seconds}`;

        const progressPercentage = (songCurrentTime / currentSongDuration) * 100;

        // Animazione fluida della barra di progresso
        gsap.to(progressBar, { width: `${progressPercentage}%`, duration: 0.3, ease: "power2.out", overwrite: true });
    };

    const knobs = document.querySelectorAll('.volume-knob');

    knobs.forEach(knob => {
        const handle = knob.querySelector('.volume-handle');
        let isDragging = false;
        let startAngle = 0;
        let currentAngle = 0;

        const handleMouseDown = (e) => {
            isDragging = true;
            startAngle = getAngle(e, knob);
            knob.style.cursor = 'grabbing';
        };

        const handleMouseMove = (e) => {
            if (!isDragging) return;
            const angle = getAngle(e, knob);
            const deltaAngle = angle - startAngle;
            currentAngle += deltaAngle;
            startAngle = angle;
            handle.style.transform = `translateX(-50%) rotate(${currentAngle}deg)`;
        };

        const handleMouseUp = () => {
            isDragging = false;
            knob.style.cursor = 'grab';
        };

        knob.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        /**
    * Calculates the angle of a mouse event relative to a given element's center.
    * 
    * @param {MouseEvent} e - The mouse event object.
    * @param {HTMLElement} knob - The HTML element to calculate the angle relative to.
    * @returns {number} The angle in degrees, ranging from -180 to 180.  Returns NaN if knob is not a valid HTMLElement.
    */


        function getAngle(e, knob) {
            const rect = knob.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;
            const x = e.clientX - centerX;
            const y = e.clientY - centerY;
            return Math.atan2(y, x) * (180 / Math.PI);
        }
    });

    // ===================== CONFIGURAZIONE DROPZONE INPUT =====================
    Dropzone.autoDiscover = false;
    const dropZonePreview = `
        <div id="player">
            <div id="progress-bar-container">
                <span id="song-title">Nome Brano</span>
                <div id="progress-bar-wrapper">
                    <div id="progress-bar"></div>
                </div>
            </div>
            <div id="time-container">
                <span id="current-song-time">0:00</span> / 
                <span id="total-song-duration">0:00</span>
            </div>
        </div>
    `;
    const songInputContainer = document.getElementById("song-input-container");
    const songInputDisplay = document.getElementById("song-input-display");

    const audioInput = new Dropzone(songInputContainer, {
        url: "#",
        paramName: "file",
        maxFiles: 1,
        acceptedFiles: "audio/*",
        previewTemplate: dropZonePreview,
        init: function () {
            this.on("addedfile", file => {
                songInputDisplay.style.display = "none";

                const reader = new FileReader();
                reader.onload = event => {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({
                            type: "new-audio",
                            name: file.name,
                            content: event.target.result.split(",")[1] // Rimuove il prefisso `data:audio/...;base64,`
                        }));
                    }
                };
                reader.readAsDataURL(file);
            });

            this.on("removedfile", () => {
                songInputDisplay.style.display = "block";
            });
        }
    });

    // ===================== CONFIGURAZIONE BOTTONE PER METTERE IN PAUSA IL BRANO =====================
    const pauseButton = document.getElementById("pause-current-song");
    let isPaused = false;

    /**
 * Event listener for the pause button click.  Handles pausing and resuming audio playback via a WebSocket connection.
 *
 * @param {Event} event - The click event triggered on the pause button.  (Implicit parameter, not explicitly defined in the code)
 * @returns {void}
 */

    pauseButton.addEventListener("click", () => {
        if (socket.readyState !== WebSocket.OPEN) {
            console.error("WebSocket non è connesso. Impossibile inviare il comando.");
            return;
        }

        isPaused = !isPaused;
        socket.send(JSON.stringify({ type: isPaused ? "pause-audio" : "resume-audio", content: "" }));

        pauseButton.innerHTML = `<i class="fa-solid ${isPaused ? "fa-play" : "fa-pause"} fa-xl"></i>`;
    });

    // ===================== CONFIGURAZIONE BOTTONE PER MUTARE IL BRANO IN RIPRODUZIONE =====================
    const muteButton = document.getElementById("mute-song");
    let isMuted = false;

    /**
 * Event listener for mute button click.  Handles toggling the mute state via a WebSocket connection.
 *
 * @function
 * @listens click
 */

    muteButton.addEventListener("click", () => {
        if (socket.readyState !== WebSocket.OPEN) return;

        socket.send(JSON.stringify({ type: "toggle-mute", content: "" }));

        isMuted = !isMuted;
        muteButton.innerHTML = `<i class="fa-solid ${isMuted ? "fa-volume-high" : "fa-volume-xmark"} fa-xl"></i>`;
    });

    // ===================== CONFIGURAZIONE BOTTONE PER METTEREI IL BRANO IN RIPRODUZIONE IN LOOP =====================
    const loopButton = document.getElementById("toggle-song-loop");
    let isLooping = false;

    loopButton.addEventListener("click", () => {
        if (socket.readyState !== WebSocket.OPEN) return;

        socket.send(JSON.stringify({ type: "toggle-loop", content: "" }));

        isLooping = !isLooping;
        const icon = loopButton.getElementsByTagName("i")[0]; // Seleziona il primo elemento <i>

        if (icon) {
            icon.style.color = isLooping ? "var(--text-color-tertiary)" : "";
        }
    });

    // ===================== CONFIGURAZIONE OROLOGIO ANALOGICO CHE SEGNA IL TEMPO ATTUALE =====================
    /**
    * Updates the position of clock hands on an analog clock visual.  This function calculates the degree of rotation for each hand based on the current time and applies the rotation via CSS transforms.
    *
    * @function updateClock
    * @returns {void}  Does not return a value; updates the DOM directly.
    */
    function updateClock() {
        const now = new Date();
        const hours = now.getHours();
        const minutes = now.getMinutes();
        const seconds = now.getSeconds();

        const hourDegrees = (hours / 12) * 360 + (minutes / 60) * 30 + 90;
        const minuteDegrees = (minutes / 60) * 360 + (seconds / 60) * 6 + 90;
        const secondDegrees = (seconds / 60) * 360 + 90;

        document.querySelector('.hour-hand').style.transform = `rotate(${hourDegrees}deg)`;
        document.querySelector('.minute-hand').style.transform = `rotate(${minuteDegrees}deg)`;
        document.querySelector('.second-hand').style.transform = `rotate(${secondDegrees}deg)`;
    }



    // getting al vertical slider in page
    const verticalSlider = document.querySelectorAll('.vertical-slider');
    verticalSlider.forEach((slider) => {
        noUiSlider.create(slider, {
            start: [20],
            orientation: 'vertical',
            direction: 'rtl',
            connect: [true, false],
            range: {
                min: 0,
                max: 100
            },
            tooltips: true,
            format: {
                to: value => `${Math.round(value)}%`,
                from: value => Number(value.replace('%', ''))
            }
        });
    });

    // iro.js initialization on color picker bar
    const pickr = Pickr.create({
        el: '#color-wheel',
        theme: 'nano', // Tema compatto
        default: '#ff0000', // Colore iniziale
        swatches: ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'],
        components: {
            preview: true,
            opacity: false, // Disabilita trasparenza se non necessaria
            hue: true,
            interaction: {
                input: true, // Abilita input manuale
                hex: true,
                rgba: false,
            }
        }
    });

    // switching background color on start button
    const legoStatusButton = document.getElementById("lego-power-button");
    legoStatusButton.addEventListener("click", () => {
        socket.send(JSON.stringify({ type: "toggle-motor-status", content: "" }));

        // Alterna tra "on" e "off"
        legoStatusButton.classList.toggle("on");
        legoStatusButton.classList.toggle("off");
    });

    // Image controls button
    const takePictureButton = document.getElementById("take-picture");
    takePictureButton.addEventListener("click", () => {
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "take-picture", content: "" }));
        } else {
            console.log("Can't take picture, socket is not connected");
            return;
        }
    });

    // video controls button
    const startButton = document.getElementById("start-recording");
    const stopButton = document.getElementById("stop-recording");

    startButton.addEventListener("click", () => {
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "start-recording", content: "" }));
            startButton.style.display = "none";
            stopButton.style.display = "block";
        } else {
            console.error("WebSocket connection is not open.");
        }
    });

    stopButton.addEventListener("click", () => {
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "stop-recording", content: "" }));
            stopButton.style.display = "none";
            startButton.style.display = "block";
        } else {
            console.error("WebSocket connection is not open.");
        }
    });


    // night mode toggling
    const nightModeInput = document.getElementById("night-mode-value");
    nightModeInput.addEventListener("change", () => {
        if (socket.readyState === WebSocket.OPEN) {
            const nightMode = nightModeInput.checked ? 1 : 0;
            console.log(nightMode);
            socket.send(JSON.stringify({ type: "toggle-night-mode", content: nightMode }));
        } else {
            console.error("WebSocket non aperto. Impossibile inviare il messaggio.");
        }
    });

    // Variables related to gear controller section
    const gearLever = document.getElementById("gearLever");
    const gearSlots = document.querySelectorAll(".gear-slot");
    let currentGear = "N";

    /**
    * Moves the gear lever to the specified gear position.
    * @param {string} gear - The gear to move the lever to.
    */
    function moveLever(gear) {
        const targetSlot = [...gearSlots].find(slot => slot.dataset.gear === gear);
        if (targetSlot) {
            const newTop = targetSlot.offsetTop + (targetSlot.offsetHeight / 4);
            gearLever.style.top = `${newTop}px`;
            gearLever.querySelector('.gear-text').textContent = gear;
            currentGear = gear;
            socket.send(JSON.stringify({ type: "switchgear", content: currentGear }));
        }
    }

    gearSlots.forEach(slot => {
        slot.addEventListener("click", () => {
            moveLever(slot.dataset.gear);
        });
    });

    moveLever(currentGear);

    // function to handle hand brake 
    const lever = document.querySelector('.lever');
    const status = document.querySelector('.status span');

    lever.addEventListener('click', () => {
        lever.classList.toggle('active');
        status.textContent = lever.classList.contains('active') ? '1' : '0';
        status.classList.toggle('active');
        status.classList.toggle('inactive');
    });

    // creating nouislider.js vertical bar to camera zoomer
    const zoomer = document.getElementById("camera-zoom-value");
    noUiSlider.create(zoomer, {
        start: [1],
        orientation: 'vertical',
        direction: 'rtl',
        connect: [true, false],
        range: {
            min: 0.5,
            max: 3
        },
        step: 0.1,
        tooltips: true,
        format: {
            to: function (value) {
                return value.toFixed(1) + 'X';
            },
            from: function (value) {
                return parseFloat(value);
            }
        }
    });

    // changing image zoom value when zoomer is updated
    zoomer.noUiSlider.on('update', function (values, handle) {
        const zoomFactor = parseFloat(values[0]);
        // notifying socket with new zoom value
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ "type": "set-zoom", "content": zoomFactor }));
        } else {
            return;
        }
    });


    updateClock();
    setInterval(updateClock, 1000);

});