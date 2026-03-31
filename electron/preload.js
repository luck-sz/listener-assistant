const { contextBridge, ipcRenderer } = require('electron');
const fs = require('fs/promises');
const path = require('path');

const runtimeDir = path.join(__dirname, '..', 'runtime');
const snapshotPath = path.join(runtimeDir, 'live_snapshot.json');
const watchlistPath = path.join(runtimeDir, 'watchlist.json');
const preloadLogPath = path.join(runtimeDir, 'preload_debug.log');

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
  await fs.appendFile(preloadLogPath, line, 'utf-8');
}

async function persistAddStockLocally(code, name) {
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
}

contextBridge.exposeInMainWorld('listenerAssistant', {
  readSnapshot: async () => readJson(snapshotPath, null),
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
});
