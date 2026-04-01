# Listener Assistant

一个基于 `Electron + React + Python` 的桌面股票监听工具，用来管理监听股票、生成分时级别 MACD / 背离信号，并在桌面端集中查看信号列表。

## 项目特性

- 桌面端实时信号监控界面，支持股票筛选与日期筛选
- 支持 `1分钟` / `5分钟` 周期切换，并在切换后重新生成信号列表
- 支持监听股票本地持久化，重启应用后自动恢复
- 支持监听列表管理，可直接删除不再需要的监听项
- 支持策略配置：启用/关闭不同信号类型、设置涨幅限制
- 使用本地运行时目录保存快照、监听列表、调试日志和信号缓存

## 当前页面

- `信号监控`
  - 查看信号列表
  - 按股票筛选
  - 按日期筛选
  - 查看价格、涨幅、触发时间和信号类型
- `策略研究`
  - 启用或关闭具体信号策略
  - 切换 `1分钟 / 5分钟` 周期
  - 保存规则后自动重建信号列表
- `监听列表`
  - 查看当前已监听股票
  - 删除监听股票

## 技术栈

- Electron
- React
- Vite
- Python
- pytdx

## 项目结构

```text
electron/          Electron 主进程、preload、Python 数据服务
react-ui/          React 前端页面
package.json       Electron 项目配置与构建脚本
requirements.txt   Python 依赖说明
README.md          项目说明
```

## 本地开发

### 1. 安装 Node.js 依赖

```bash
npm install
npm install --prefix react-ui
```

### 2. 安装 Python 依赖

```bash
python -m pip install -r requirements.txt
```

### 3. 启动桌面应用

```bash
npm run start
```

这个命令会先构建 `react-ui`，然后启动 Electron 桌面应用。

## 构建 Windows 可执行文件

```bash
npm run build
```

构建完成后，输出文件位于：

```text
release/StockListenerAssistant 1.0.0.exe
```

## 运行时目录

应用运行时会在当前用户目录下生成本地运行数据：

```text
C:\Users\<用户名>\AppData\Roaming\StockListenerAssistant\runtime
```

常见文件包括：

- `live_snapshot.json`：前端读取的实时快照
- `watchlist.json`：当前监听股票列表
- `rules_config.json`：策略配置与周期设置
- `desktop_debug.log`：主进程日志
- `preload_debug.log`：preload 日志
- `*_1m_signals.csv` / `*_5m_signals.csv`：按周期生成的信号文件

## 使用流程

1. 打开桌面应用
2. 点击右上角 `添加监控`
3. 输入股票代码，等待最近 7 个交易日分时数据下载完成
4. 在 `策略研究` 页面选择周期和启用的信号类型
5. 返回 `信号监控` 页面查看结果
6. 如需清理监听股票，可在 `监听列表` 页面删除

## 说明

- 当前仓库提交的是源码，不建议提交 `release/`、`build/`、`runtime/`、`node_modules/` 等运行产物
- 项目已经配置 `.gitignore`，适合直接托管到 GitHub
- 当前主链路是 `Electron + React`，旧的静态页面和 PyInstaller 链路已经清理

## 参考

数据抓取与信号逻辑参考自本地 Python 项目：

- `E:\PythonProject\stock_intraday_fetch`

如果你准备继续把这个仓库公开化，下一步建议补充：

- 项目截图
- LICENSE
- Roadmap / TODO
