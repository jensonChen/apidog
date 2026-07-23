# ApiDog Desktop EXE Phase A — Implementation Plan

> **For agentic workers:** Execute task-by-task. Checkbox tracking.

**Goal:** 将 ApiDog 打成自带运行时的 Windows 安装包，双击打开独立窗口，数据在 `%AppData%\ApiDog`。

**Architecture:** pywebview 壳 + 线程内 uvicorn + 现有 Vue/FastAPI；PyInstaller onedir + Inno Setup。

**Tech Stack:** Python 3.10+、FastAPI、pywebview、PyInstaller、Inno Setup、Vue3 既有前端。

## Global Constraints

- 业务 API 不改语义；空白工作区；无自动更新；无旧 data 自动迁移
- 函数 ≤ 85 行；禁止吞异常假成功；路径/端口等用常量模块
- 冻结 EXE 用 AppData；开发 BS 默认仓库 `data/`

---

### Task 1: 路径与空白工作区

**Files:** `backend/app_constants.py`, `backend/config_loader.py`, `backend/storage.py`, `backend/main.py`

- [ ] 常量：应用名、默认端口、健康路径、环境变量名
- [ ] `resolve_data_dir` / `resolve_frontend_dist`（支持 frozen + `APIDOG_DATA_DIR`）
- [ ] `ensure_data_layout` 改为空项目 + 默认空环境
- [ ] 验证：本地 import / 简单脚本检查目录解析

### Task 2: 桌面启动器

**Files:** `backend/desktop_launcher.py`

- [ ] 单实例锁、起 uvicorn、健康检查、pywebview、关闭时退出
- [ ] 失败弹窗（Windows MessageBox），禁止假成功

### Task 3: 打包与安装

**Files:** `packaging/apidog.spec`, `packaging/inno/ApiDog.iss`, `scripts/build_desktop.ps1`, `backend/requirements.txt`, `.gitignore`

- [ ] PyInstaller onedir，入口 `desktop_launcher.py`，打入 `frontend/dist`
- [ ] Inno：选目录、开始菜单、不删 AppData
- [ ] build 脚本：前端 build → pyinstaller →（可选）iscc

### Task 4: 验证与 Tag

- [ ] 开发模式 `start.bat` 仍可用
- [ ] 桌面模式可启动窗口（本机）
- [ ] 提交并打 `v2.1.0-desktop`
