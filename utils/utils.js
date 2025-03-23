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

module.exports = {
    maximizeWindow,
    minimizeWindow,
    closeWindow
};