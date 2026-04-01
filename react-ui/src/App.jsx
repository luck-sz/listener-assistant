import { useEffect, useState } from 'react'
import './App.css'

const PAGE_SIZE = 10
const RULES_STORAGE_KEY = 'listener-assistant-rules'
const SIGNAL_TYPES = ['顶背离卖出', '底背离买入', 'MACD金叉买入', 'MACD死叉卖出']
const DEFAULT_RULES = {
  signals: {
    '顶背离卖出': true,
    '底背离买入': true,
    'MACD金叉买入': true,
    'MACD死叉卖出': true,
  },
  period: '5分钟',
  limit: '',
}

function sortRowsByTime(rows) {
  return [...rows].sort((a, b) => `${b.sortTime || b.time || ''}`.localeCompare(`${a.sortTime || a.time || ''}`))
}

const signalRows = []

const monitorRows = []

const topMeta = [
  { key: 'run', label: '运行中' },
  { key: 'network', label: '连接正常' },
  { key: 'time', label: 'time' },
]

function loadSavedRules() {
  try {
    const raw = window.localStorage.getItem(RULES_STORAGE_KEY)
    if (!raw) {
      return DEFAULT_RULES
    }

    const parsed = JSON.parse(raw)
    return {
      signals: {
        ...DEFAULT_RULES.signals,
        ...(parsed.signals || {}),
      },
      limit: parsed.limit || DEFAULT_RULES.limit,
    }
  } catch {
    return DEFAULT_RULES
  }
}

function timeNow() {
  return new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function dateToday() {
  return new Date().toLocaleDateString('sv-SE')
}

function App() {
  const initialRules = loadSavedRules()
  const [page, setPage] = useState('signals')
  const [tablePage, setTablePage] = useState(1)
  const [clock, setClock] = useState(timeNow())
  const [showModal, setShowModal] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [toast, setToast] = useState('')
  const [ruleSignals, setRuleSignals] = useState(initialRules.signals)
  const [period, setPeriod] = useState(initialRules.period || '1分钟')
  const [limit, setLimit] = useState(initialRules.limit)
  const [selectedCode, setSelectedCode] = useState('all')
  const [selectedDate, setSelectedDate] = useState(dateToday())
  const [rows, setRows] = useState(signalRows)
  const [feedRows, setFeedRows] = useState(monitorRows)
  const [logs, setLogs] = useState([
    { time: '09:30:00', text: '监听服务已启动，等待实时分时数据。' },
  ])
  const [brand, setBrand] = useState('监听助手')
  const [form, setForm] = useState({
    code: '',
    name: '',
    signal: 'MACD金叉买入',
    price: '',
  })

  useEffect(() => {
    const timer = window.setInterval(() => setClock(timeNow()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let mounted = true

    const loadRules = async () => {
      const runtimeRules = await window.listenerAssistant?.readRulesConfig?.()
      if (!mounted || !runtimeRules) {
        return
      }

      if (runtimeRules.signals) {
        setRuleSignals((current) => ({ ...current, ...runtimeRules.signals }))
      }
      if (typeof runtimeRules.limit === 'string') {
        setLimit(runtimeRules.limit)
      }
      if (typeof runtimeRules.period === 'string') {
        setPeriod(runtimeRules.period)
      }
    }

    const loadSnapshot = async () => {
      if (!window.listenerAssistant?.readSnapshot) {
        return
      }

      const snapshot = await window.listenerAssistant.readSnapshot()
      if (!mounted || !snapshot) {
        return
      }

      if (snapshot.brand) {
        setBrand(snapshot.brand)
      }
      if (Array.isArray(snapshot.dashboardRows) && snapshot.dashboardRows.length) {
        setRows(snapshot.dashboardRows)
      }
      if (Array.isArray(snapshot.monitorRows) && snapshot.monitorRows.length) {
        setFeedRows(snapshot.monitorRows)
      }
      if (Array.isArray(snapshot.logs) && snapshot.logs.length) {
        setLogs(snapshot.logs)
      }
    }

    loadRules()
    loadSnapshot()
    const refreshInterval = rows.some((row) => row.signal === '正在下载最新7个交易日分时数据') ? 3000 : 30000
    const timer = window.setInterval(loadSnapshot, refreshInterval)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [rows])

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(() => setToast(''), 2000)
    return () => window.clearTimeout(timer)
  }, [toast])

  const enabledSignals = SIGNAL_TYPES.filter((signalName) => ruleSignals[signalName])
  const stockOptions = [{ code: 'all', name: '全部监听股票' }, ...feedRows.map((row) => ({ code: row.code, name: row.name || row.code }))]
  const dateOptions = ['all', ...Array.from(new Set(rows.map((row) => `${row.time || ''}`.slice(0, 10)).filter(Boolean))).sort((a, b) => b.localeCompare(a))]
  const availableCodes = new Set(stockOptions.map((item) => item.code))
  const activeCode = availableCodes.has(selectedCode) ? selectedCode : 'all'
  const activeDate = dateOptions.includes(selectedDate) ? selectedDate : (dateOptions.includes(dateToday()) ? dateToday() : 'all')
  const sortedRows = sortRowsByTime(
    rows.filter((row) => {
      const signalAllowed = row.signal === '正在下载最新7个交易日分时数据' || enabledSignals.includes(row.signal)
      const stockAllowed = activeCode === 'all' || row.code === activeCode
      const dateAllowed = activeDate === 'all' || `${row.time || ''}`.startsWith(activeDate)
      return signalAllowed && stockAllowed && dateAllowed
    }),
  )
  const watchStats = [
    { label: '监控股票', value: `${feedRows.length}`.padStart(2, '0'), note: 'scan' },
    { label: '今日触发', value: `${sortedRows.filter((row) => enabledSignals.includes(row.signal)).length}`.padStart(2, '0'), note: 'signals' },
    { label: '卖出信号', value: `${sortedRows.filter((row) => row.signal.includes('卖出')).length}`.padStart(2, '0'), note: 'critical' },
    { label: '自动刷新', value: '30s', note: 'refresh' },
  ]
  const totalPages = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE))
  const currentPage = Math.min(tablePage, totalPages)
  const visibleRows = sortedRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const closeModal = () => {
    if (isSubmitting) return
    setShowModal(false)
  }

  const closeDeleteModal = () => {
    if (isSubmitting) return
    setPendingDelete(null)
  }

  const saveRules = async () => {
    const payload = { signals: ruleSignals, period, limit }
    window.localStorage.setItem(RULES_STORAGE_KEY, JSON.stringify(payload))
    const result = await window.listenerAssistant?.saveRulesConfig?.(payload)
    if (result && result.ok === false) {
      setToast(result.message || '规则配置保存失败')
      return
    }
    const regenerateResult = await window.listenerAssistant?.regenerateSignals?.()
    if (regenerateResult && regenerateResult.ok === false) {
      setToast(regenerateResult.message || '信号重建失败')
      return
    }
    setToast('规则配置已保存')
  }

  const toggleRuleSignal = (signalName) => {
    setRuleSignals((current) => ({
      ...current,
      [signalName]: !current[signalName],
    }))
  }

  const addStock = async () => {
    if (!form.code.trim()) {
      setToast('请输入股票代码')
      return
    }

    const code = form.code.trim()
    const time = timeNow()
    const name = code

    setIsSubmitting(true)
    setShowModal(false)

    setRows((current) => sortRowsByTime([
      { code, name, signal: '正在下载最新7个交易日分时数据', price: '--', change: '--', time, badge: 'neutral', tone: 'neutral', sortTime: new Date().toISOString() },
      ...current.filter((row) => row.code !== code),
    ]))

    setFeedRows((current) => [
      {
        code,
        name,
        price: '0.00',
        change: '+0.00%',
        signal: '数据下载中',
        time,
      },
      ...current.filter((row) => row.code !== code),
    ])

    const requestAddStock = window.listenerAssistant?.requestAddStock
    const result = requestAddStock
      ? await requestAddStock({ code, name })
      : { ok: true, fallback: true }

    if (!result?.ok) {
      setIsSubmitting(false)
      setToast(result?.message ? `提交下载请求失败: ${result.message}` : '提交下载请求失败')
      return
    }

    setForm({ code: '', name: '', signal: 'MACD金叉买入', price: '' })
    setTablePage(1)
    setToast(`${name} 已开始下载7日分时数据`)
    const snapshot = await window.listenerAssistant?.readSnapshot?.()
    if (snapshot?.dashboardRows) {
      setRows(snapshot.dashboardRows)
    }
    if (snapshot?.monitorRows) {
      setFeedRows(snapshot.monitorRows)
    }
    if (snapshot?.logs) {
      setLogs(snapshot.logs)
    }
    setIsSubmitting(false)
  }

  const removeStock = async () => {
    if (!pendingDelete?.code) {
      return
    }

    setIsSubmitting(true)
    const result = await window.listenerAssistant?.removeStock?.({ code: pendingDelete.code })

    if (!result?.ok) {
      setIsSubmitting(false)
      setToast(result?.message || '删除监听失败')
      return
    }

    const nextRows = rows.filter((row) => row.code !== pendingDelete.code)
    const nextFeedRows = feedRows.filter((row) => row.code !== pendingDelete.code)
    setRows(nextRows)
    setFeedRows(nextFeedRows)
    if (selectedCode === pendingDelete.code) {
      setSelectedCode('all')
    }
    setPendingDelete(null)
    setTablePage(1)
    setToast(`${pendingDelete.name || pendingDelete.code} 已删除监听`)

    const snapshot = await window.listenerAssistant?.readSnapshot?.()
    if (snapshot?.dashboardRows) {
      setRows(snapshot.dashboardRows)
    }
    if (snapshot?.monitorRows) {
      setFeedRows(snapshot.monitorRows)
    }
    if (snapshot?.logs) {
      setLogs(snapshot.logs)
    }
    setIsSubmitting(false)
  }

  return (
    <div className={`app ${showModal ? 'modal-open' : ''}`}>
      <div className="bg-orb bg-orb-right" />
      <div className="bg-orb bg-orb-left" />

      <header className="topbar">
        <div className="topbar-left">
          <span className="brand">{brand}</span>
          <nav className="nav">
            <button className={`nav-link ${page === 'signals' ? 'active' : ''}`} onClick={() => setPage('signals')}>信号监控</button>
            <button className={`nav-link ${page === 'rules' ? 'active' : ''}`} onClick={() => setPage('rules')}>策略研究</button>
            <button className={`nav-link ${page === 'watchlist' ? 'active' : ''}`} onClick={() => setPage('watchlist')}>监听列表</button>
          </nav>
        </div>

          <div className="topbar-right">
            <div className="status-cluster">
              {topMeta.map((item) => (
                <div key={item.key} className={`meta-pill ${item.key}`}>
                  {item.key === 'run' ? <span className="run-dot" /> : null}
                  <span>{item.key === 'time' ? clock : item.label}</span>
                </div>
              ))}
            </div>
            <button className="primary-mini" onClick={() => setShowModal(true)}>添加监控</button>
            <div className="avatar" />
          </div>
        </header>

      <main className="main-shell">
        {page === 'signals' ? (
          <section className="page signals-page">
            <section className="signal-section">
              <div className="signal-overview-strip">
                <div className="overview-card overview-card-primary">
                  <div>
                    <span className="overview-eyebrow">Live Monitor</span>
                    <h2>{brand}</h2>
                    <p>实时监控市场动态，精准捕获多维度交易信号，强化更贴近设计稿的信息密度与版式秩序。</p>
                  </div>
                </div>

                <div className="overview-metrics">
                  {watchStats.map((item) => (
                    <article key={item.label} className={`overview-stat overview-stat-${item.note}`}>
                      <span>{item.label}</span>
                      <strong>{item.value}</strong>
                    </article>
                  ))}
                </div>
              </div>

              <div className="signal-header">
                <div className="signal-heading-block">
                  <h2>实时信号列表</h2>
                  <p>高密度表格视图，聚焦代码、名称、信号类型、触发价与涨幅。</p>
                </div>
                <div className="signal-filters">
                  <label className="stock-filter-shell">
                    <span>股票筛选</span>
                    <select value={activeCode} onChange={(event) => { setSelectedCode(event.target.value); setTablePage(1) }}>
                      {stockOptions.map((item) => (
                        <option key={item.code} value={item.code}>{item.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="stock-filter-shell date-filter-shell">
                    <span>日期筛选</span>
                    <select value={activeDate} onChange={(event) => { setSelectedDate(event.target.value); setTablePage(1) }}>
                      <option value="all">全部日期</option>
                      {dateOptions.filter((item) => item !== 'all').map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>

              <div className="signal-card">
                <table className="signal-table">
                  <thead>
                    <tr>
                      <th className="equal-col center">代码</th>
                      <th className="equal-col center">名称</th>
                      <th className="equal-col center">信号类型</th>
                      <th className="equal-col center">触发价</th>
                      <th className="equal-col center">涨幅</th>
                      <th className="equal-col center">触发时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row) => (
                      <tr key={`${row.code}-${row.time}`}>
                        <td className="code center">{row.code}</td>
                        <td className="name center">{row.name}</td>
                        <td className="center">
                          <span className={`badge ${row.badge}`}>{row.signal}</span>
                        </td>
                        <td className="center">
                          <span className="tabular">{row.price || '--'}</span>
                        </td>
                        <td className={`center tabular ${`${row.change || ''}`.startsWith('-') ? 'negative' : 'positive'}`}>{row.change || '--'}</td>
                        <td className="muted tabular center">{row.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="table-pagination">
                <button className="page-btn" onClick={() => setTablePage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>上一页</button>
                <span className="page-indicator">第 {currentPage} / {totalPages} 页</span>
                <button className="page-btn" onClick={() => setTablePage((value) => Math.min(totalPages, value + 1))} disabled={currentPage === totalPages}>下一页</button>
              </div>

            </section>

            <footer className="technical-footer">
              <div className="security-row">
                <span>Security Level 4</span>
                <span>Low Latency Engine v2.4</span>
                <span>Encrypted Connection</span>
              </div>
              <p>© 2026 {brand} · 投资有风险，入市需谨慎</p>
            </footer>
          </section>
        ) : page === 'rules' ? (
          <section className="page rules-page">
            <div className="title-block left-tight">
              <h1>策略配置</h1>
              <p>添加股票后会先下载最近7个交易日分时数据，只有这里启用的策略才会出现在实时信号列表。</p>
            </div>

            <section className="rule-panel elevated">
              <div className="rule-top">
                <div className="rule-title-wrap">
                  <div className="rule-icon primary">S</div>
                  <div>
                    <h2>信号策略</h2>
                    <span>Signal Strategy</span>
                  </div>
                </div>
              </div>

              <div className="rule-grid">
                {SIGNAL_TYPES.map((signalName) => (
                  <label className="toggle-row" key={signalName}>
                    <input
                      type="checkbox"
                      checked={Boolean(ruleSignals[signalName])}
                      onChange={() => toggleRuleSignal(signalName)}
                    />
                    <span className="toggle-ui" />
                    <em>{signalName}</em>
                  </label>
                ))}
              </div>
            </section>

            <section className="rule-panel elevated">
              <div className="rule-top">
                <div className="rule-title-wrap">
                  <div className="rule-icon tertiary">D</div>
                  <div>
                    <h2>下载与过滤</h2>
                    <span>Download and Filter</span>
                  </div>
                </div>
              </div>

              <div className="rule-stack">
                <div className="rule-grid">
                  <div className="field-block">
                    <label>涨幅限制</label>
                    <div className="suffix-input wide">
                      <input value={limit} onChange={(event) => setLimit(event.target.value)} placeholder="输入限制百分比" />
                      <span>%</span>
                    </div>
                  </div>
                </div>

                <div className="metric-box-row">
                  <article className="metric-box green">
                    <span>下载窗口</span>
                    <strong>最近 7 个交易日</strong>
                  </article>
                  <article className="metric-box blue">
                    <span>信号周期</span>
                    <strong>{period}</strong>
                  </article>
                  <article className="metric-box red">
                    <span>过滤条件</span>
                    <strong>{limit || '未设置'}</strong>
                  </article>
                </div>

                <div className="rule-grid">
                  <div className="field-block">
                    <label>MACD 计算周期</label>
                    <div className="period-row">
                      {['1分钟', '5分钟'].map((item) => (
                        <button key={item} type="button" className={`period ${period === item ? 'active' : ''}`} onClick={() => setPeriod(item)}>{item}</button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <div className="info-tip">
              <span>i</span>
              <p>提示：保存后的策略会写入本地，下次打开应用时自动恢复，并用于过滤实时信号列表。</p>
            </div>
          </section>
        ) : (
          <section className="page rules-page">
            <div className="title-block left-tight">
              <h1>监听列表</h1>
              <p>管理当前已经加入监听的股票，可在此快速删除不再需要的监听项。</p>
            </div>

            <section className="rule-panel elevated">
              <div className="rule-top">
                <div className="rule-title-wrap">
                  <div className="rule-icon red">L</div>
                  <div>
                    <h2>已监听股票</h2>
                    <span>Watchlist Manager</span>
                  </div>
                </div>
              </div>

              <div className="watchlist-stack">
                {feedRows.length ? feedRows.map((row) => (
                  <article className="watchlist-item" key={row.code}>
                    <div className="watchlist-main">
                      <div className="watchlist-title-row">
                        <strong>{row.name || row.code}</strong>
                        <span>{row.code}</span>
                      </div>
                      <p>{row.signal || '监控中'} | 价格 {row.price || '--'} | 涨幅 {row.change || '--'}</p>
                    </div>
                    <button className="danger-btn" onClick={() => setPendingDelete({ code: row.code, name: row.name || row.code })}>删除监听</button>
                  </article>
                )) : (
                  <div className="empty-watchlist">当前还没有已监听的股票。</div>
                )}
              </div>
            </section>
          </section>
        )}
      </main>

      {page === 'rules' ? (
        <button className="fab" onClick={saveRules}>
          <span>保存规则配置</span>
        </button>
      ) : null}

      <div className={toast ? 'toast visible' : 'toast'}>{toast}</div>

      {showModal ? (
        <div className="modal-root">
          <div className="modal-mask" onClick={closeModal} />
          <div className="modal-card">
            <div className="modal-header">
              <h3>添加股票监听</h3>
              <button className="close-btn" onClick={closeModal} disabled={isSubmitting}>×</button>
            </div>

            <div className="modal-content">
              <div className="field-block tight modal-code-block">
                <label>股票代码</label>
                <div className="search-shell">
                  <span className="search-icon">⌕</span>
                  <input
                    value={form.code}
                    onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))}
                    placeholder="请输入股票代码 (例如: 600519)"
                    autoFocus
                    disabled={isSubmitting}
                  />
                </div>
                <p>请输入沪深/港股/美股代码。系统将自动识别市场并加载实时 K 线数据及预警算法。</p>
              </div>

            </div>

            <div className="modal-actions">
              <button className="cancel-btn" onClick={closeModal} disabled={isSubmitting}>取消</button>
              <button className="confirm-btn" onClick={addStock} disabled={isSubmitting}>{isSubmitting ? '下载中...' : '确认添加'}</button>
            </div>

            {isSubmitting ? (
              <div className="modal-loading-overlay">
                <div className="modal-loading-card">
                  <span className="modal-spinner large" />
                  <strong>正在抓取最近7个交易日分时数据</strong>
                  <p>系统正在下载最新分钟级数据并计算触发信号，请稍候...</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {pendingDelete ? (
        <div className="modal-root">
          <div className="modal-mask" onClick={closeDeleteModal} />
          <div className="modal-card confirm-card">
            <div className="modal-header">
              <h3>确认删除监听</h3>
              <button className="close-btn" onClick={closeDeleteModal} disabled={isSubmitting}>×</button>
            </div>

            <div className="modal-content confirm-content">
              <p>确定要删除 `{pendingDelete.name}` 的监听吗？删除后该股票将不再继续监控，且本地缓存信号数据也会一并移除。</p>
            </div>

            <div className="modal-actions">
              <button className="cancel-btn" onClick={closeDeleteModal} disabled={isSubmitting}>取消</button>
              <button className="danger-btn solid" onClick={removeStock} disabled={isSubmitting}>{isSubmitting ? '删除中...' : '确定删除'}</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default App
