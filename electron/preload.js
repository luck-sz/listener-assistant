const { contextBridge, ipcRenderer } = require('electron');
const fs = require('fs/promises');
const path = require('path');

function getRuntimeDir() {
  return path.join(process.env.APPDATA || path.join(__dirname, '..'), 'StockListenerAssistant', 'runtime');
}

function getSnapshotPath() {
  return path.join(getRuntimeDir(), 'live_snapshot.json');
}

function getWatchlistPath() {
  return path.join(getRuntimeDir(), 'watchlist.json');
}

function getPreloadLogPath() {
  return path.join(getRuntimeDir(), 'preload_debug.log');
}

function getRulesConfigPath() {
  return path.join(getRuntimeDir(), 'rules_config.json');
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
  await fs.appendFile(getPreloadLogPath(), line, 'utf-8');
}

appendLog('preload_loaded').catch(() => {});

async function persistAddStockLocally(code, name) {
  const watchlistPath = getWatchlistPath();
  const snapshotPath = getSnapshotPath();
  const watchlist = await readJson(watchlistPath, []);
  const normalizedWatchlist = Array.isArray(watchlist) ? watchlist : [];
  const index = normalizedWatchlist.findIndex((item) => `${item?.code || ''}`.trim() === code);

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

  const snapshot = await readJson(snapshotPath, null);
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
}

contextBridge.exposeInMainWorld('listenerAssistant', {
  readSnapshot: async () => readJson(getSnapshotPath(), null),
  readRulesConfig: async () => readJson(getRulesConfigPath(), null),
  saveRulesConfig: async (payload) => {
    await fs.mkdir(getRuntimeDir(), { recursive: true });
    await fs.writeFile(getRulesConfigPath(), JSON.stringify(payload || {}, null, 2), 'utf-8');
    return { ok: true };
  },
  requestAddStock: async (payload) => {
    const code = `${payload?.code || ''}`.trim();
    const name = `${payload?.name || code}`.trim() || code;

    try {
      await appendLog(`requestAddStock called code=${code || '<empty>'} name=${name || '<empty>'}`);
      const result = await ipcRenderer.invoke('listener-assistant:add-stock', payload);
      await appendLog(`requestAddStock ipc_result code=${code} ok=${Boolean(result?.ok)}`);
      return result;
    } catch (error) {
      await appendLog(`requestAddStock ipc_failed code=${code} error=${error?.message || error}`);
      try {
        await persistAddStockLocally(code, name);
        await appendLog(`requestAddStock fallback_persisted code=${code}`);
        return { ok: true, fallback: true };
      } catch (fallbackError) {
        await appendLog(`requestAddStock fallback_failed code=${code} error=${fallbackError?.message || fallbackError}`);
        return { ok: false, message: fallbackError?.message || error?.message || '提交下载请求失败' };
      }
    }
  },
  removeStock: async (payload) => {
    const code = `${payload?.code || ''}`.trim();

    try {
      await appendLog(`removeStock called code=${code || '<empty>'}`);
      const result = await ipcRenderer.invoke('listener-assistant:remove-stock', payload);
      await appendLog(`removeStock ipc_result code=${code} ok=${Boolean(result?.ok)}`);
      return result;
    } catch (error) {
      await appendLog(`removeStock ipc_failed code=${code} error=${error?.message || error}`);
      return { ok: false, message: error?.message || '删除监听失败' };
    }
  },
  regenerateSignals: async () => {
    try {
      await appendLog('regenerateSignals called');
      const result = await ipcRenderer.invoke('listener-assistant:regenerate-signals');
      await appendLog(`regenerateSignals ipc_result ok=${Boolean(result?.ok)}`);
      return result;
    } catch (error) {
      await appendLog(`regenerateSignals ipc_failed error=${error?.message || error}`);
      return { ok: false, message: error?.message || '重新生成信号失败' };
    }
  },
});
