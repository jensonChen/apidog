# ApiDog 桌面 EXE（Phase A）设计 / PRD

> 状态：已确认  
> 日期：2026-07-23  
> 基线 Tag：`v2.0.0-bs`（BS 浏览器启动形态）  
> 分支：`feat/desktop-exe-phase-a`  
> 产品 Tag（完成后）：`v2.1.0-desktop`

## 1. 背景与目标

ApiDog 当前为本机 BS：`start.bat` 启动 FastAPI，再用浏览器打开。目标用户含不懂技术的同事，需要：

- 安装向导安装，开始菜单可打开
- 双击后出现**独立窗口**（非浏览器标签页）
- **零依赖**：不要求安装 Python / Node
- 用户数据在 `%AppData%\ApiDog\`，覆盖安装不丢数据
- 首次为**空白工作区**，不自动迁移旧 `data/`；需要时用现有「导入 Postman」等能力手动带入

Phase A 验证「双击即用」；Phase B（后续）用 Tauri 替换窗口壳，业务层尽量不动。

## 2. 非目标（本阶段不做）

- 自动更新 / 静默更新
- 旧项目 `data/` 自动迁移
- 多用户账号、云同步、团队协作
- 系统托盘、复杂原生菜单（留给 Phase B）
- macOS / Linux 安装包

## 3. 成功标准

1. 同事在干净 Win10/11 机器上运行安装包，无需额外开发环境即可打开 ApiDog 窗口并发送请求。
2. 集合 / 环境 / 历史写入 `%AppData%\ApiDog\`；卸载或覆盖安装后数据仍在（卸载默认不删 AppData）。
3. 开发者仍可用原 BS 方式（`start.bat` / `python main.py`）调试，数据默认仍在仓库 `data/`。
4. 打包产物可复现：脚本能产出安装包或至少可运行的 onedir 程序目录。

## 4. 架构

```
安装目录 (Program Files\ApiDog)
  ApiDog.exe          # 入口：启后端 + pywebview 窗口
  _internal/          # PyInstaller 运行时、依赖、frontend/dist
  ...

%AppData%\ApiDog\
  config.json
  workspace.json
  collections/
  environments/
  history/
```

运行时：

1. EXE 启动 → 解析数据目录为 `%AppData%\ApiDog`
2. 后台线程启动 uvicorn（127.0.0.1 + 配置端口）
3. 健康检查通过后，pywebview（WebView2）加载 `http://127.0.0.1:<port>/`
4. 窗口关闭 → 停止服务进程/线程并退出

前后端业务（Vue + FastAPI API）保持不变；仅增加桌面入口、路径解析与打包。

## 5. 数据与空白工作区

| 模式 | 数据目录 | 首次内容 |
|------|----------|----------|
| 桌面 / 冻结 EXE | `%AppData%\ApiDog` | 空项目列表 + 默认空环境 |
| 开发 BS | `<repo>/data` | 同上（不再植入演示项目） |
| 覆盖 | `APIDOG_DATA_DIR` 环境变量 | 按该路径 |

- 不自动拷贝仓库旁旧 `data/`
- 覆盖安装只替换程序文件，不清理 AppData

## 6. 分发

- **打包**：PyInstaller `onedir`（启动更快、排错更容易）
- **安装包**：Inno Setup（选目录、开始菜单快捷方式、可选桌面图标）
  - 构建机需安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)；未安装时 `build_desktop.ps1` 仍产出可运行的 `packaging/dist/ApiDog/`
- **更新**：发新安装包覆盖安装；不做在线检查
- **同事临时分发**：可将整个 `packaging/dist/ApiDog` 目录拷贝使用（绿色版）；正式场景用 Inno 安装包

## 7. 错误处理

- 端口被占用：启动失败并弹窗明确提示（含端口号），不静默假成功
- WebView2 缺失：提示安装 Edge WebView2 Runtime
- 后端健康检查超时：弹窗失败原因，退出码非 0
- 单实例：第二次启动聚焦已有窗口或提示已在运行（避免多实例抢端口）

## 8. Phase B 预留

- 保持「HTTP API + 静态前端」边界清晰
- 启动逻辑集中在桌面入口模块，便于日后换成 Tauri sidecar
- 数据目录约定不变（仍 AppData）

## 9. 风险

| 风险 | 缓解 |
|------|------|
| 杀软误报 PyInstaller | 使用 onedir、公司内网分发、必要时签名（后续） |
| WebView2 未装 | 安装包说明 / 检测并提示下载 |
| 体积偏大（自带 Python） | Phase A 可接受；Phase B Tauri 可再优化壳层 |

## 10. 验收清单

- [ ] 干净机安装后可从开始菜单打开独立窗口
- [ ] 新建项目、发请求、历史写入 AppData
- [ ] 覆盖安装后原集合仍在
- [ ] `start.bat` 开发路径仍可用
- [ ] Tag：`v2.0.0-bs`（改造前）与 `v2.1.0-desktop`（改造后）
