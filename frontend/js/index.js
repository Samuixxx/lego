document.addEventListener("DOMContentLoaded", () => {

    // creating new websocket instance
    const socket = new WebSocket("ws://localhost:8765");

    socket.onopen = () => {
        console.log("Connected to the server");
    };

    socket.onclose = () => {
        console.log("Disconnected from the server");
    };

    // selecting window controls button
    const maximizeWindowButton = document.querySelector(".maximize-button");
    const minimizeWindowButton = document.querySelector(".minimize-button");
    const closeWindowButton = document.querySelector(".close-button");

    if (!maximizeWindowButton || !minimizeWindowButton || !closeWindowButton) {
        console.error("Window control buttons not found.");
        return;
    }

    const windowControls = {
        maximize: () => window.windowapi.send("maximize-window", {}),
        minimize: () => window.windowapi.send("minimize-window", {}),
        close: () => window.windowapi.send("close-window", {})
    };

    maximizeWindowButton.addEventListener("click", windowControls.maximize);
    minimizeWindowButton.addEventListener("click", windowControls.minimize);
    closeWindowButton.addEventListener("click", windowControls.close);

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

    Dropzone.autoDiscover = false;

    const songInputContainer = document.getElementById('song-input-container');
    const songInputDisplay = document.getElementById('song-input-display');

    const myDropzone = new Dropzone(songInputContainer, {
        url: "#",
        acceptedFiles: "audio/*",
        maxFiles: 1,
        autoProcessQueue: false,
        clickable: true,
        previewsContainer: false,
        createImageThumbnails: false,
        init: function () {
            this.on("addedfile", function (file) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    const audioData = event.target.result;
                };
                reader.readAsDataURL(file);
            });
        }
    });

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
    });

    // video controls button
    const startButton = document.getElementById("startRecording");
    const stopButton = document.getElementById("stopRecording");

    startButton.addEventListener("click", () => {
        startButton.style.display = "none";
        stopButton.style.display = "block";
        socket.send(JSON.stringify({ type: "start-video", content: "" }));
    });

    stopButton.addEventListener("click", () => {
        stopButton.style.display = "none";
        startButton.style.display = "block";
        socket.send(JSON.stringify({ type: "stop-video", content: "" }));
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
        start: [50],
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



    updateClock();
    setInterval(updateClock, 1000);

    socket.onmessage = function (event) {
        try {
            const response = JSON.parse(event.data);
            
            if (response.ok && response.motorStarted) {
                legoStatusButton.classList.remove("off");
                legoStatusButton.classList.add("on");
            } else if (response.ok && response.motorTurnedoff) {
                legoStatusButton.classList.remove("on");
                legoStatusButton.classList.add("off");
            }
        } catch (error) {
            console.error("Errore nella risposta WebSocket:", error);
        }
    };
    
});