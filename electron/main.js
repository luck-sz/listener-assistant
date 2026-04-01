const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const { spawn } = require('child_process');
const fsSync = require('fs');
const fs = require('fs/promises');
const path = require('path');

let dataService = null;
let mainWindow = null;
let notificationTimer = null;
let notificationSeeded = false;
const notifiedSignalKeys = new Set();

function getRuntimeDir() {
  return path.join(app.getPath('appData'), 'StockListenerAssistant', 'runtime');
}

function getLegacyRuntimeDirs() {
  const dirs = [];
  if (app.isPackaged) {
    dirs.push(path.join(process.resourcesPath, 'runtime'));
  }
  dirs.push(path.join(__dirname, '..', 'runtime'));
  return [...new Set(dirs.filter((dir) => dir !== getRuntimeDir()))];
}

function getSnapshotPath() {
  return path.join(getRuntimeDir(), 'live_snapshot.json');
}

function getWatchlistPath() {
  return path.join(getRuntimeDir(), 'watchlist.json');
}

function getLogPath() {
  return path.join(getRuntimeDir(), 'desktop_debug.log');
}

function getRulesConfigPath() {
  return path.join(getRuntimeDir(), 'rules_config.json');
}

function getDataServiceScriptPath() {
  if (!app.isPackaged) {
    return path.join(__dirname, 'data_service.py');
  }

  const candidates = [
    path.join(process.resourcesPath, 'python', 'data_service.py'),
    path.resolve(process.resourcesPath, '..', '..', '..', 'electron', 'data_service.py'),
    path.resolve(process.resourcesPath, '..', '..', 'electron', 'data_service.py'),
  ];

  return candidates.find((candidate) => fsSync.existsSync(candidate)) || null;
}

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
  const runtimeDir = getRuntimeDir();
  await fs.mkdir(runtimeDir, { recursive: true });
  await fs.appendFile(getLogPath(), line, 'utf-8');
}

async function ensureRuntimeMigrated() {
  const runtimeDir = getRuntimeDir();
  await fs.mkdir(runtimeDir, { recursive: true });

  for (const legacyDir of getLegacyRuntimeDirs()) {
    if (!fsSync.existsSync(legacyDir)) {
      continue;
    }

    for (const name of ['watchlist.json', 'rules_config.json', 'live_snapshot.json']) {
      const source = path.join(legacyDir, name);
      const target = path.join(runtimeDir, name);
      if (fsSync.existsSync(source) && !fsSync.existsSync(target)) {
        await fs.copyFile(source, target);
      }
    }
  }
}

function buildSignalKey(row) {
  return `${row?.code || ''}|${row?.signal || ''}|${row?.sortTime || row?.time || ''}`;
}

async function checkSignalNotifications() {
  const snapshot = await readJson(getSnapshotPath(), null);
  const rows = Array.isArray(snapshot?.dashboardRows) ? snapshot.dashboardRows : [];
  const signalRows = rows.filter((row) => row?.signal && !`${row.signal}`.includes('正在下载'));

  if (!notificationSeeded) {
    signalRows.forEach((row) => notifiedSignalKeys.add(buildSignalKey(row)));
    notificationSeeded = true;
    return;
  }

  for (const row of signalRows) {
    const key = buildSignalKey(row);
    if (notifiedSignalKeys.has(key)) {
      continue;
    }
    notifiedSignalKeys.add(key);

    if (Notification.isSupported()) {
      new Notification({
        title: `${row.name || row.code} 触发信号`,
        body: `${row.signal} | 触发价 ${row.price || '--'} | 涨幅 ${row.change || '--'} | ${row.time || ''}`,
        silent: false,
      }).show();
    }

    if (mainWindow && !mainWindow.isFocused()) {
      mainWindow.flashFrame(true);
    }
    await appendLog(`signal_notified key=${key}`);
  }
}

function startDataService() {
  const scriptPath = getDataServiceScriptPath();
  if (!scriptPath) {
    appendLog('skip_data_service no runnable python script found').catch(() => {});
    return;
  }
  appendLog(`start_data_service script=${scriptPath}`).catch(() => {});
  dataService = spawn('python', [scriptPath], {
    cwd: path.dirname(scriptPath),
    env: {
      ...process.env,
      LISTENER_RUNTIME_DIR: getRuntimeDir(),
    },
    stdio: 'ignore',
    windowsHide: true,
  });
  dataService.on('error', (error) => {
    appendLog(`data_service_spawn_error error=${error?.message || error}`).catch(() => {});
  });
  dataService.on('exit', (code) => {
    appendLog(`data_service_exit code=${code}`).catch(() => {});
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
    const runtimeDir = getRuntimeDir();
    const watchlistPath = getWatchlistPath();
    const snapshotPath = getSnapshotPath();

    await fs.mkdir(runtimeDir, { recursive: true });
    const watchlist = await readJson(watchlistPath, []);
    const normalizedWatchlist = Array.isArray(watchlist) ? watchlist : [];
    const snapshot = (await readJson(snapshotPath, null)) || { brand: '监听助手', updatedAt: new Date().toISOString(), dashboardRows: [], monitorRows: [], logs: [], errors: [] };
    const index = normalizedWatchlist.findIndex((item) => `${item?.code || ''}`.trim() === code);

    if (index >= 0) {
      await appendLog(`add_stock_duplicate code=${code}`);
      return { ok: false, message: '该股票已在监控列表中，请勿重复添加' };
    }

    const nextItem = {
      code,
      name,
      status: 'loading',
      message: '正在抓取最近7个交易日分时数据',
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

    if (snapshot && Array.isArray(snapshot.dashboardRows)) {
      const loadingRow = {
        code,
        name,
        signal: '正在下载最新7个交易日分时数据',
        price: '--',
        change: '--',
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
          text: `${name}(${code}) 已加入监听，正在抓取最近7个交易日分时数据。`,
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

ipcMain.handle('listener-assistant:save-rules', async (_event, payload) => {
  try {
    const runtimeDir = getRuntimeDir();
    await fs.mkdir(runtimeDir, { recursive: true });
    await fs.writeFile(getRulesConfigPath(), JSON.stringify(payload || {}, null, 2), 'utf-8');
    await appendLog('save_rules persisted');
    return { ok: true };
  } catch (error) {
    await appendLog(`save_rules_failed error=${error?.message || error}`);
    return { ok: false, message: error?.message || '保存规则配置失败' };
  }
});

ipcMain.handle('listener-assistant:read-rules', async () => {
  return readJson(getRulesConfigPath(), null);
});

ipcMain.handle('listener-assistant:regenerate-signals', async () => {
  try {
    const runtimeDir = getRuntimeDir();
    await fs.mkdir(runtimeDir, { recursive: true });
    const watchlist = await readJson(getWatchlistPath(), []);
    const normalizedWatchlist = Array.isArray(watchlist) ? watchlist : [];

    for (const item of normalizedWatchlist) {
      item.status = 'loading';
      item.message = '正在根据新周期重建信号列表';
      item.updatedAt = new Date().toISOString();
      item.lastProcessedAt = null;
    }

    await fs.writeFile(getWatchlistPath(), JSON.stringify(normalizedWatchlist, null, 2), 'utf-8');
    await appendLog('regenerate_signals queued all watchlist items');
    return { ok: true };
  } catch (error) {
    await appendLog(`regenerate_signals_failed error=${error?.message || error}`);
    return { ok: false, message: error?.message || '重新生成信号失败' };
  }
});

ipcMain.handle('listener-assistant:remove-stock', async (_event, payload) => {
  const code = `${payload?.code || ''}`.trim();

  await appendLog(`remove_stock invoked code=${code || '<empty>'}`);

  if (!code) {
    return { ok: false, message: '缺少股票代码' };
  }

  try {
    const runtimeDir = getRuntimeDir();
    const watchlistPath = getWatchlistPath();
    const snapshotPath = getSnapshotPath();

    await fs.mkdir(runtimeDir, { recursive: true });
    const watchlist = await readJson(watchlistPath, []);
    const normalizedWatchlist = Array.isArray(watchlist) ? watchlist : [];
    const nextWatchlist = normalizedWatchlist.filter((item) => `${item?.code || ''}`.trim() !== code);

    if (nextWatchlist.length === normalizedWatchlist.length) {
      return { ok: false, message: '该股票不在监听列表中' };
    }

    await fs.writeFile(watchlistPath, JSON.stringify(nextWatchlist, null, 2), 'utf-8');

    const snapshot = await readJson(snapshotPath, null);
    if (snapshot && typeof snapshot === 'object') {
      if (Array.isArray(snapshot.dashboardRows)) {
        snapshot.dashboardRows = snapshot.dashboardRows.filter((item) => `${item?.code || ''}`.trim() !== code);
      }
      if (Array.isArray(snapshot.monitorRows)) {
        snapshot.monitorRows = snapshot.monitorRows.filter((item) => `${item?.code || ''}`.trim() !== code);
      }
      snapshot.logs = [
        {
          time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
          text: `${code} 已从监听列表中移除。`,
        },
        ...(Array.isArray(snapshot.logs) ? snapshot.logs : []).filter((item) => item && typeof item === 'object'),
      ].slice(0, 6);
      await fs.writeFile(snapshotPath, JSON.stringify(snapshot, null, 2), 'utf-8');
    }

    for (const suffix of ['_intraday.csv', '_signals.csv', '_state.json']) {
      const target = path.join(runtimeDir, `${code}${suffix}`);
      if (fsSync.existsSync(target)) {
        await fs.unlink(target);
      }
    }

    await appendLog(`remove_stock persisted code=${code}`);
    return { ok: true };
  } catch (error) {
    await appendLog(`remove_stock_failed code=${code} error=${error?.message || error}`);
    return { ok: false, message: error?.message || '删除监听失败' };
  }
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1540,
    height: 980,
    minWidth: 1200,
    minHeight: 760,
    backgroundColor: '#f8f9fb',
    title: 'Stock Listener Assistant',
    autoHideMenuBar: true,
    webPreferences: {
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'react-ui', 'dist', 'index.html'));
  mainWindow.on('focus', () => mainWindow?.flashFrame(false));
}

app.whenReady().then(async () => {
  await ensureRuntimeMigrated();
  appendLog('app_ready main process started').catch(() => {});
  startDataService();
  createWindow();
  notificationTimer = setInterval(() => {
    checkSignalNotifications().catch(() => {});
  }, 5000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (notificationTimer) {
    clearInterval(notificationTimer);
  }
  if (dataService) {
    dataService.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
