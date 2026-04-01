# Listener Assistant

监听助手桌面应用源码仓库。

这是一个基于 `Electron + React` 的股票监听助手项目，目标是提供桌面端信号监控、策略配置和监听管理能力，并接入分时数据抓取与信号分析逻辑。

## 当前状态

- 已完成桌面端基础壳：`Electron + React`
- 已完成主要页面：`信号监控`、`策略研究`、`监听列表`、`添加股票监听` 弹窗
- 已接入参考项目的数据抓取与信号计算逻辑
- 已支持运行时快照与本地持久化运行目录

目前已支持 `1分钟 / 5分钟` 周期切换，并可在切换后重新生成信号列表。

## 目录结构

```text
electron/          Electron 主进程、preload、Python 数据服务
react-ui/          React 前端界面
package.json       根级 Electron 项目配置
requirements.txt   Python 依赖
```

## 技术栈

- Electron
- React
- Vite
- Python
- pytdx

## 本地开发

### 1. 安装前端依赖

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

这个命令会先构建 `react-ui`，再用 Electron 启动桌面端。

## 构建

```bash
npm run build
```

默认构建目标在 `package.json` 中配置为 Windows portable 包，输出目录为 `release/`。

## 运行时文件

应用运行过程中会在本地目录 `C:\Users\<用户名>\AppData\Roaming\StockListenerAssistant\runtime` 生成运行时文件，常见文件包括：

- `live_snapshot.json`
- `watchlist.json`
- `desktop_debug.log`
- `preload_debug.log`

这些文件主要用于：

- 前端读取实时快照
- 记录监控股票列表
- 排查主进程 / preload 层的请求问题

## 参考项目

数据抓取与信号逻辑参考：

- `E:\PythonProject\stock_intraday_fetch`

核心参考文件包括：

- `fetch_tdx_intraday_30d.py`
- `live_divergence_incremental.py`
- `web_app.py`

## 仓库说明

- 本仓库建议仅提交源码与必要配置文件
- `release/`、`build/`、`runtime/`、`node_modules/` 等目录已加入忽略规则，不建议提交到 GitHub
