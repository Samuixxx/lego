const path = require('path');
const { session } = require('electron');
const fs = require('fs');

/**
 * Attempts to maximize a given window object. If the window is already maximized,
 * it will attempt to unmaximize it and then set its dimensions and center it.
 *
 * @param {object} window - The window object to maximize.
 * @param {number} width - The desired width of the window if unmaximizing.
 * @param {number} height - The desired height of the window if unmaximizing.
 * @returns {void} Does not return a value. Logs an error message to the console if the window object is invalid or lacks the necessary methods.
 */
const maximizeWindow = (window, width, height) => {
    if (window && typeof window.isMaximized === 'function' && window.isMaximized()) {
        window.unmaximize();
        window.setBounds({ width, height });
        window.center();
    } else if (window && typeof window.maximize === 'function') {
        window.maximize();
    } else {
        console.error('Invalid window object or maximize/unmaximize method is not a function');
    }
};

/**
 * Minimizes a given window object.
 *
 * @function
 * @param {object} win - The window object to minimize. Must have a `hide()` method.
 * @returns {void} Does not return a value. Logs an error to the console if the window object is invalid or lacks a hide method.
 */
const minimizeWindow = (win) => {
    if (win && typeof win.minimize === 'function') {
        win.minimize();
    } else {
        console.error('Invalid window object or hide method is not a function');
    }
};

/**
 * Closes a given window object if it's valid and has a close method.
 *
 * @function closeWindow
 * @param {Window} win - The window object to be closed.
 * @returns {void} Does not return a value. Logs an error to the console if the window object is invalid or lacks a close method.
 */
const closeWindow = (win) => {
    if (win && typeof win.close === 'function') {
        win.close();
    } else {
        console.error('Invalid window object or close method is not a function');
    }
};

/**
 * Updates the SSL certificate verification process.
 * 
 * This function checks for the existence of an SSL certificate at a specified path.  If the certificate exists, it sets a custom verification procedure; otherwise, it logs an error message.  The verification procedure allows connections to `localhost` while rejecting others.
 * @param {string} __dirname - The directory path where the script is located.  Used to construct the certificate path.
 * @returns {void}
 */

const updateSslCert = (__dirname) => {
    const certPath = path.join(__dirname, 'certificate.crt');
    const keyPath = path.join(__dirname, 'private.key');  // Aggiungi il percorso della chiave privata

    // Controlla se il certificato esiste
    if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
        console.log("Certificato trovato:", certPath);

        // Verifica del certificato per 'localhost'
        const verifyProc = (request, callback) => {
            console.log('Verificando certificato per:', request.hostname);
            if (request.hostname === 'localhost') {
                console.log("Certificato valido per localhost");
                callback(0); 
            } else {
                console.log("Certificato non valido per:", request.hostname);
                callback(-3);  // -3 indica che il certificato non è valido
            }
        };

        // Imposta la procedura di verifica del certificato per la sessione
        session.defaultSession.setCertificateVerifyProc(verifyProc);
    } else {
        console.error('Il certificato SSL o la chiave non esistono:', certPath, keyPath);
    }
};


module.exports = {
    maximizeWindow,
    minimizeWindow,
    closeWindow,
    updateSslCert
};