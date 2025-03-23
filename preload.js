const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("windowapi", {
    send: (channel, data) => {
        if (typeof channel !== 'string') {
            console.error(`Invalid channel type: ${typeof channel}. Expected string.`);
            return;
        }
        if (typeof data !== 'object') {
            console.error(`Invalid data type for channel '${channel}': ${typeof data}. Expected object.`);
            return;
        }
        ipcRenderer.send(channel, data);
    },
    on: (channel, callback) => {
        if (typeof channel !== 'string') {
            console.error(`Invalid channel type: ${typeof channel}. Expected string.`);
            return;
        }
        if (typeof callback !== 'function') {
            console.error(`Invalid callback type for channel '${channel}': ${typeof callback}. Expected function.`);
            return;
        }
        ipcRenderer.on(channel, (event, data) => callback(data));
    },
    removeAllListeners: (channel) => {
        if (typeof channel !== 'string') {
            console.error(`Invalid channel type: ${typeof channel}. Expected string.`);
            return;
        }
        ipcRenderer.removeAllListeners(channel);
    }
});