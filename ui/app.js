const tableRows = [
  { code: '600519', name: '贵州茅台', signal: '突破预警', time: '14:28:45', status: '已买入', badge: 'breakout', statusTone: 'buy' },
  { code: '000858', name: '五粮液', signal: '均线金叉', time: '14:15:20', status: '待确认', badge: 'ma', statusTone: 'pending' },
  { code: '300750', name: '宁德时代', signal: '卖出提醒', time: '13:58:12', status: '高风险', badge: 'sell', statusTone: 'risk' },
  { code: '000001', name: '平安银行', signal: '突破预警', time: '11:30:00', status: '监听中', badge: 'breakout', statusTone: 'buy' },
  { code: '601318', name: '中国平安', signal: '量能突增', time: '10:45:33', status: '持续观察', badge: 'volume', statusTone: 'watch' },
];

const monitorRows = [
  { code: '600519', name: '贵州茅台', price: '1745.00', change: '+1.25%', signal: 'MACD金叉买入', time: '14:32:05' },
  { code: '000858', name: '五粮液', price: '138.50', change: '+0.82%', signal: '底背离买入', time: '14:15:42' },
  { code: '300750', name: '宁德时代', price: '192.15', change: '-2.45%', signal: 'MACD死叉卖出', time: '13:58:11' },
  { code: '601318', name: '中国平安', price: '52.30', change: '-1.12%', signal: '顶背离卖出', time: '13:42:00' },
  { code: '000333', name: '美的集团', price: '71.25', change: '+0.45%', signal: 'MACD金叉买入', time: '11:20:15' },
];

const logs = [
  { time: '14:35:18', text: '监听服务已连接至本地策略引擎。' },
  { time: '14:34:50', text: '沪深自选池完成第 6 轮扫描。' },
  { time: '14:32:05', text: '贵州茅台触发 MACD 金叉买入信号。' },
  { time: '14:15:42', text: '五粮液触发底背离买入信号。' },
  { time: '13:58:11', text: '宁德时代触发 MACD 死叉卖出信号。' },
];

const app = document.getElementById('app');
const modalRoot = document.getElementById('modal-root');
const toast = document.getElementById('toast');
const floatingButton = document.getElementById('floating-button');
const floatingButtonLabel = document.getElementById('floating-button-label');
const navTabs = Array.from(document.querySelectorAll('.nav-tab'));
const pages = Array.from(document.querySelectorAll('.page'));
const topAddButton = document.getElementById('top-add-button');

let activePage = 'dashboard';
let toastTimer = 0;

function updateClock() {
  const element = document.getElementById('current-time');
  if (!element) return;
  element.textContent = new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function renderTable() {
  const body = document.getElementById('signal-table-body');
  body.innerHTML = tableRows.map((row) => `
    <tr>
      <td class="code-cell">${row.code}</td>
      <td class="name-cell">${row.name}</td>
      <td><span class="badge ${row.badge}">${row.signal}</span></td>
      <td>${row.time}</td>
      <td class="align-right"><span class="status-badge ${row.statusTone}">${row.status}</span></td>
    </tr>
  `).join('');
}

function renderMonitor() {
  const list = document.getElementById('monitor-list');
  list.innerHTML = monitorRows.map((row) => {
    const changeTone = row.change.startsWith('+') ? 'positive' : 'negative';
    const badgeTone = row.change.startsWith('+') ? 'breakout' : 'sell';
    return `
      <div class="monitor-row">
        <div class="mono code-cell">${row.code}</div>
        <div class="name-cell">${row.name}</div>
        <div class="mono">${row.price}</div>
        <div class="mono ${changeTone}">${row.change}</div>
        <div><span class="badge ${badgeTone}">${row.signal}</span></div>
        <div class="mono">${row.time}</div>
      </div>
    `;
  }).join('');
}

function renderLogs() {
  const list = document.getElementById('log-list');
  list.innerHTML = logs.map((log) => `
    <article class="log-item">
      <p>${log.text}</p>
      <time>${log.time}</time>
    </article>
  `).join('');
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 2200);
}

function openModal() {
  modalRoot.classList.remove('hidden');
  app.classList.add('is-modal-open');
}

function closeModal() {
  modalRoot.classList.add('hidden');
  app.classList.remove('is-modal-open');
}

function setPage(page) {
  activePage = page;
  navTabs.forEach((tab) => tab.classList.toggle('is-active', tab.dataset.page === page));
  pages.forEach((pageNode) => pageNode.classList.toggle('is-visible', pageNode.dataset.page === page));

  if (page === 'rules') {
    floatingButtonLabel.textContent = '保存';
  } else {
    floatingButtonLabel.textContent = '添加';
  }
}

function bindEvents() {
  navTabs.forEach((tab) => tab.addEventListener('click', () => setPage(tab.dataset.page)));

  topAddButton.addEventListener('click', openModal);
  floatingButton.addEventListener('click', () => {
    if (activePage === 'rules') {
      showToast('规则配置已保存。');
      logs.unshift({
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        text: '规则配置已保存：MACD 与背离策略参数已同步更新。',
      });
      renderLogs();
      return;
    }

    openModal();
  });

  document.getElementById('modal-close-button').addEventListener('click', closeModal);
  document.getElementById('modal-cancel-button').addEventListener('click', closeModal);
  modalRoot.querySelector('.modal-backdrop').addEventListener('click', closeModal);

  document.getElementById('modal-confirm-button').addEventListener('click', () => {
    const code = document.getElementById('stock-code-input').value.trim();
    const name = document.getElementById('stock-name-input').value.trim() || '未命名标的';
    const signal = document.getElementById('signal-type-input').value;
    const status = document.getElementById('stock-status-input').value;
    const now = new Date().toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    if (!code) {
      showToast('请先输入股票代码。');
      return;
    }

    const badgeMap = {
      '突破预警': 'breakout',
      '均线金叉': 'ma',
      '卖出提醒': 'sell',
      '量能突增': 'volume',
    };

    const statusMap = {
      '已买入': 'buy',
      '高风险': 'risk',
      '监听中': 'buy',
      '持续观察': 'watch',
      '待确认': 'pending',
    };

    tableRows.unshift({
      code,
      name,
      signal,
      time: now,
      status,
      badge: badgeMap[signal] || 'ma',
      statusTone: statusMap[status] || 'pending',
    });

    logs.unshift({ time: now, text: `${name}(${code}) 已加入监听池，当前信号为 ${signal}。` });
    renderTable();
    renderLogs();
    closeModal();
    showToast(`${name} 已成功添加。`);
  });

  document.getElementById('macd-range').addEventListener('input', (event) => {
    document.getElementById('macd-value').value = `> ${Number(event.target.value).toFixed(1)}`;
  });

  document.getElementById('macd-value').addEventListener('blur', (event) => {
    const parsed = parseFloat(event.target.value.replace('>', '').replace('%', '').trim());
    if (Number.isNaN(parsed)) {
      event.target.value = '> 5.0';
      document.getElementById('macd-range').value = '5';
      return;
    }
    const value = Math.max(0, Math.min(20, parsed));
    event.target.value = `> ${value.toFixed(1)}`;
    document.getElementById('macd-range').value = String(value);
  });

  Array.from(document.querySelectorAll('#period-switches button')).forEach((button) => {
    button.addEventListener('click', () => {
      Array.from(document.querySelectorAll('#period-switches button')).forEach((item) => item.classList.remove('is-active'));
      button.classList.add('is-active');
    });
  });
}

window.addEventListener('DOMContentLoaded', () => {
  updateClock();
  window.setInterval(updateClock, 1000);
  renderTable();
  renderMonitor();
  renderLogs();
  bindEvents();
  setPage('dashboard');
});
