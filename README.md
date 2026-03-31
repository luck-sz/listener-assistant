# Listener Assistant

监听助手桌面应用源码仓库。

这是一个基于 `Electron + React` 的股票监听助手原型项目，目标是提供接近设计稿的桌面端界面，并接入最近 30 个交易日的分时数据抓取与信号分析逻辑。

## 当前状态

- 已完成桌面端基础壳：`Electron + React`
- 已完成主要页面：`信号监控`、`策略研究`、`添加股票监听` 弹窗
- 已接入参考项目的数据抓取与信号计算逻辑
- 已支持运行时快照文件：`runtime/live_snapshot.json`
- 已有桌面启动器源码：`launcher.py`

目前“添加股票监听 -> 下载 30 日分时 -> 自动回写列表”这条链路仍在继续排查和打磨，仓库已包含最新调试代码与日志入口。

## 目录结构

```text
electron/          Electron 主进程、preload、Python 数据服务
react-ui/          React 前端界面
ui/                早期静态页面资源
img/               设计参考图
launcher.py        启动器源码
main.py            早期桌面端入口
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

应用运行过程中会在运行目录下生成 `runtime/` 数据目录，常见文件包括：

- `runtime/live_snapshot.json`
- `runtime/watchlist.json`
- `runtime/desktop_debug.log`
- `runtime/preload_debug.log`

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

## 已知问题

- 添加股票监听链路仍在持续修复与验证
- 部分时间格式展示仍需要进一步清理
- Windows 打包链路目前以本地可运行目录和启动器方式为主，正式 portable 包流程还需要继续稳定

## 仓库说明

- 本仓库当前不包含 `dist/` 运行包
- 仅提交源码、素材和配置文件
