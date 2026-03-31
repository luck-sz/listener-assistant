import { useEffect, useState } from 'react'
import './App.css'

const PAGE_SIZE = 10

function sortRowsByTime(rows) {
  return [...rows].sort((a, b) => `${b.sortTime || b.time || ''}`.localeCompare(`${a.sortTime || a.time || ''}`))
}

const signalRows = [
  { code: '600519', name: '贵州茅台', signal: '突破预警', time: '14:28:45', status: '已买入', badge: 'buy', tone: 'buy' },
  { code: '000858', name: '五粮液', signal: '均线金叉', time: '14:15:20', status: '待确认', badge: 'neutral', tone: 'neutral' },
  { code: '300750', name: '宁德时代', signal: '卖出提醒', time: '13:58:12', status: '高风险', badge: 'sell', tone: 'sell' },
  { code: '000001', name: '平安银行', signal: '突破预警', time: '11:30:00', status: '监听中', badge: 'buy', tone: 'buy' },
  { code: '601318', name: '中国平安', signal: '量能突增', time: '10:45:33', status: '持续观察', badge: 'neutral', tone: 'neutral' },
]

const monitorRows = [
  { code: '600519', name: '贵州茅台', price: '1745.00', change: '+1.25%', signal: 'MACD金叉买入', time: '14:32:05' },
  { code: '000858', name: '五粮液', price: '138.50', change: '+0.82%', signal: '底背离买入', time: '14:15:42' },
  { code: '300750', name: '宁德时代', price: '192.15', change: '-2.45%', signal: 'MACD死叉卖出', time: '13:58:11' },
  { code: '601318', name: '中国平安', price: '52.30', change: '-1.12%', signal: '顶背离卖出', time: '13:42:00' },
  { code: '000333', name: '美的集团', price: '71.25', change: '+0.45%', signal: 'MACD金叉买入', time: '11:20:15' },
]

const watchStats = [
  { label: '扫描轮次', value: '06', note: 'scan' },
  { label: '今日触发', value: '18', note: 'signals' },
  { label: '高优先级', value: '04', note: 'critical' },
  { label: '自动刷新', value: '30s', note: 'refresh' },
]

const topMeta = [
  { key: 'run', label: '运行中' },
  { key: 'network', label: '连接正常' },
  { key: 'time', label: 'time' },
]

const signalOptions = ['突破预警', '均线金叉', '卖出提醒', '量能突增']
const statusOptions = ['监听中', '待确认', '已买入', '高风险', '持续观察']
const periods = ['5分钟', '15分钟', '30分钟', '日线']

function timeNow() {
  return new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function App() {
  const [page, setPage] = useState('signals')
  const [tablePage, setTablePage] = useState(1)
  const [clock, setClock] = useState(timeNow())
  const [showModal, setShowModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [toast, setToast] = useState('')
  const [macdEnabled, setMacdEnabled] = useState(true)
  const [divergenceEnabled, setDivergenceEnabled] = useState(false)
  const [macdRange, setMacdRange] = useState(5)
  const [macdText, setMacdText] = useState('> 5.0')
  const [period, setPeriod] = useState('15分钟')
  const [limit, setLimit] = useState('')
  const [rows, setRows] = useState(signalRows)
  const [feedRows, setFeedRows] = useState(monitorRows)
  const [logs, setLogs] = useState([
    { time: '09:30:00', text: '监听服务已启动，等待实时分时数据。' },
  ])
  const [brand, setBrand] = useState('监听助手')
  const [form, setForm] = useState({
    code: '',
    name: '',
    signal: '突破预警',
    price: '',
    status: '监听中',
  })

  useEffect(() => {
    const timer = window.setInterval(() => setClock(timeNow()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let mounted = true

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

    loadSnapshot()
    const timer = window.setInterval(loadSnapshot, 15000)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(() => setToast(''), 2000)
    return () => window.clearTimeout(timer)
  }, [toast])

  const sortedRows = sortRowsByTime(rows)
  const totalPages = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE))
  const currentPage = Math.min(tablePage, totalPages)
  const visibleRows = sortedRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const closeModal = () => {
    if (isSubmitting) return
    setShowModal(false)
  }

  const syncRangeText = (value) => {
    setMacdRange(value)
    setMacdText(`> ${value.toFixed(1)}`)
  }

  const commitRangeText = () => {
    const parsed = Number.parseFloat(macdText.replace('>', '').replace('%', '').trim())
    const next = Number.isNaN(parsed) ? macdRange : Math.max(0, Math.min(20, parsed))
    syncRangeText(next)
  }

  const saveRules = () => {
    setToast('规则配置已保存')
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
      { code, name, signal: '正在下载最近30个交易日分时数据', time, status: '下载中', badge: 'neutral', tone: 'neutral', sortTime: new Date().toISOString() },
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

    const result = await window.listenerAssistant?.requestAddStock?.({ code, name })
    if (!result?.ok) {
      setIsSubmitting(false)
      setToast(result?.message ? `提交下载请求失败: ${result.message}` : '提交下载请求失败')
      return
    }

    setForm({ code: '', name: '', signal: '突破预警', price: '', status: '监听中' })
    setTablePage(1)
    setToast(`${name} 已开始下载30日分时数据`)
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
                  <p>高密度表格视图，聚焦代码、名称、信号类型和状态结果。</p>
                </div>
                <div className="signal-filters">
                  <button className="filter-btn active">全部信号</button>
                  <button className="filter-btn">仅查看预警</button>
                </div>
              </div>

              <div className="signal-card">
                <table className="signal-table">
                  <thead>
                    <tr>
                      <th>代码</th>
                      <th>名称</th>
                      <th>信号类型</th>
                      <th>触发时间</th>
                      <th className="right">当前状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row) => (
                      <tr key={`${row.code}-${row.time}`}>
                        <td className="code">{row.code}</td>
                        <td className="name">{row.name}</td>
                        <td>
                          <span className={`badge ${row.badge}`}>{row.signal}</span>
                        </td>
                        <td className="muted tabular">{row.time}</td>
                        <td className="right">
                          <span className={`status ${row.tone}`}>{row.status}</span>
                        </td>
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

              <div className="live-log-strip">
                {logs.map((log) => (
                  <article className="live-log-item" key={`${log.time}-${log.text}`}>
                    <p>{log.text}</p>
                    <time>{log.time}</time>
                  </article>
                ))}
              </div>
            </section>

            <footer className="technical-footer">
              <div className="security-row">
                <span>Security Level 4</span>
                <span>Low Latency Engine v2.4</span>
                <span>Encrypted Connection</span>
              </div>
              <p>© 2024 {brand} · 投资有风险，入市需谨慎</p>
            </footer>
          </section>
        ) : (
          <section className="page rules-page">
            <div className="title-block left-tight">
              <h1>策略配置</h1>
              <p>设置您的自动化监听规则，系统将在触发条件时实时推送通知。</p>
            </div>

            <section className="rule-panel elevated">
              <div className="rule-top">
                <div className="rule-title-wrap">
                  <div className="rule-icon primary">A</div>
                  <div>
                    <h2>MACD策略</h2>
                    <span>MACD Strategy</span>
                  </div>
                </div>

                <label className="toggle-row">
                  <input type="checkbox" checked={macdEnabled} onChange={(event) => setMacdEnabled(event.target.checked)} />
                  <span className="toggle-ui" />
                  <em>启用策略</em>
                </label>
              </div>

              <div className="rule-grid">
                <div className="field-block">
                  <label>当日涨幅阈值</label>
                  <div className="range-line">
                    <input type="range" min="0" max="20" step="0.5" value={macdRange} onChange={(event) => syncRangeText(Number(event.target.value))} />
                    <div className="suffix-input">
                      <input value={macdText} onChange={(event) => setMacdText(event.target.value)} onBlur={commitRangeText} />
                      <span>%</span>
                    </div>
                  </div>
                  <p>当个股当日涨幅超过此百分比时触发监控。</p>
                </div>

                <div className="field-block">
                  <label>零轴穿透模式</label>
                  <select defaultValue="从下方金叉穿过">
                    <option>从下方金叉穿过</option>
                    <option>零轴上方二次金叉</option>
                    <option>快速DIF回踩DEA</option>
                  </select>
                </div>
              </div>
            </section>

            <section className="rule-panel elevated">
              <div className="rule-top">
                <div className="rule-title-wrap">
                  <div className="rule-icon tertiary">D</div>
                  <div>
                    <h2>背离策略</h2>
                    <span>Divergence Strategy</span>
                  </div>
                </div>

                <label className="toggle-row">
                  <input type="checkbox" checked={divergenceEnabled} onChange={(event) => setDivergenceEnabled(event.target.checked)} />
                  <span className="toggle-ui" />
                  <em>启用策略</em>
                </label>
              </div>

              <div className="rule-stack">
                <div className="rule-grid">
                  <div className="field-block">
                    <label>背离周期确认</label>
                    <div className="period-row">
                      {periods.map((item) => (
                        <button type="button" key={item} className={period === item ? 'period active' : 'period'} onClick={() => setPeriod(item)}>{item}</button>
                      ))}
                    </div>
                  </div>

                  <div className="field-block">
                    <label>当日涨幅限制</label>
                    <div className="suffix-input wide">
                      <input value={limit} onChange={(event) => setLimit(event.target.value)} placeholder="输入限制百分比" />
                      <span>%</span>
                    </div>
                  </div>
                </div>

                <div className="metric-box-row">
                  <article className="metric-box green">
                    <span>价格指标</span>
                    <strong>Lower Low (新低)</strong>
                  </article>
                  <article className="metric-box blue">
                    <span>动量指标</span>
                    <strong>Higher Low (抬高)</strong>
                  </article>
                  <article className="metric-box red">
                    <span>偏离阈值</span>
                    <strong>12.5%</strong>
                  </article>
                </div>
              </div>
            </section>

            <div className="info-tip">
              <span>i</span>
              <p>提示：多条策略同时启用时，系统将并行监控并分别推送满足条件的标的。</p>
            </div>
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
                  <strong>正在抓取最近30个交易日分时数据</strong>
                  <p>系统正在下载最新分钟级数据并计算触发信号，请稍候...</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default App
