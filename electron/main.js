const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs/promises');
const path = require('path');

let dataService = null;
const runtimeDir = path.join(__dirname, '..', 'runtime');
const snapshotPath = path.join(runtimeDir, 'live_snapshot.json');
const watchlistPath = path.join(runtimeDir, 'watchlist.json');
const logPath = path.join(runtimeDir, 'desktop_debug.log');

async function readJson(filePath, fallback) {
  try {
    const raw = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

async function appendLog(message) {
  const line = `[${new Date().toISOString()}] ${message}\n`;
  await fs.mkdir(runtimeDir, { recursive: true });
  await fs.appendFile(logPath, line, 'utf-8');
}

function startDataService() {
  const scriptPath = path.join(__dirname, 'data_service.py');
  dataService = spawn('python', [scriptPath], {
    cwd: path.join(__dirname, '..'),
    stdio: 'ignore',
    windowsHide: true,
  });
}

ipcMain.handle('listener-assistant:add-stock', async (_event, payload) => {
  const code = `${payload?.code || ''}`.trim();
  const name = `${payload?.name || code}`.trim() || code;

  await appendLog(`add_stock invoked code=${code || '<empty>'} name=${name || '<empty>'}`);

  if (!code) {
    return { ok: false, message: '请输入股票代码' };
  }

  try {
    await fs.mkdir(runtimeDir, { recursive: true });
    const watchlist = await readJson(watchlistPath, []);
    const normalizedWatchlist = Array.isArray(watchlist) ? watchlist : [];
    const index = normalizedWatchlist.findIndex((item) => `${item?.code || ''}`.trim() === code);

    const nextItem = {
      code,
      name,
      status: 'loading',
      message: '正在抓取最近30个交易日分时数据',
      lastProcessedAt: null,
      updatedAt: new Date().toISOString(),
    };

    if (index >= 0) {
      normalizedWatchlist[index] = {
        ...normalizedWatchlist[index],
        ...nextItem,
      };
    } else {
      normalizedWatchlist.unshift(nextItem);
    }

    await fs.writeFile(watchlistPath, JSON.stringify(normalizedWatchlist, null, 2), 'utf-8');

    const snapshot = await readJson(snapshotPath, null);
    if (snapshot && Array.isArray(snapshot.dashboardRows)) {
      const loadingRow = {
        code,
        name,
        signal: '正在下载最近30个交易日分时数据',
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        status: '下载中',
        badge: 'neutral',
        tone: 'neutral',
        sortTime: new Date().toISOString(),
      };
      snapshot.dashboardRows = [
        loadingRow,
        ...snapshot.dashboardRows.filter((item) => `${item?.code || ''}`.trim() !== code),
      ];
      snapshot.logs = [
        {
          time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
          text: `${name}(${code}) 已加入监听，正在抓取最近30个交易日分时数据。`,
        },
        ...(Array.isArray(snapshot.logs) ? snapshot.logs : []),
      ].slice(0, 6);
      await fs.writeFile(snapshotPath, JSON.stringify(snapshot, null, 2), 'utf-8');
    }

    await appendLog(`add_stock persisted code=${code} name=${name}`);
    return { ok: true };
  } catch (error) {
    await appendLog(`add_stock_failed code=${code} error=${error?.message || error}`);
    return { ok: false, message: error?.message || '提交下载请求失败' };
  }
});

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1540,
    height: 980,
    minWidth: 1200,
    minHeight: 760,
    backgroundColor: '#f8f9fb',
    title: 'Stock Listener Assistant',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'react-ui', 'dist', 'index.html'));
}

app.whenReady().then(() => {
  appendLog('app_ready main process started').catch(() => {});
  startDataService();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (dataService) {
    dataService.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
