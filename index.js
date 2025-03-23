const { app, BrowserWindow, screen, ipcMain } = require('electron');
const RootPath = require('app-root-path');
const path = require('path');

// utils imports
const { maximizeWindow, minimizeWindow, closeWindow } = require('./utils/utils.js');

// getting root path
__dirname = RootPath.path;

function createWindow() {
    // getting user viewport dimension
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    // getting default page path
    const defaultFile = path.join(__dirname, 'frontend', 'html', 'index.html');

    let win = new BrowserWindow({
        width,
        height,
        show: false,
        frame: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            contentSecurityPolicy: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"
        }
    });

    win.maximize();
    win.show();

    win.loadFile(defaultFile);

    win.webContents.openDevTools();

    // Handle window close event
    win.on('closed', () => {
        win = null;
    });

    // ipcMain listener to real word (preload)
    ipcMain.on('maximize-window', () => {
        maximizeWindow(win, width, height);
    });

    ipcMain.on('minimize-window', () => {
        minimizeWindow(win);
    });

    ipcMain.on('close-window', () => {
        closeWindow(win);
    });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});