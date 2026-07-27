# ApiDog

**面向内网与离线场景的本地 API 工作台。**

不登录、不上云、不强制外网。打开就能用——把浏览器 F12 里的请求整段粘进来，或粘贴 curl，一键解析、发送、归档。

[下载 Windows 安装包](https://github.com/jensonChen/apidog/releases/tag/v2.1.6-desktop) · [更新日志](https://github.com/jensonChen/apidog/releases) · [问题反馈](https://github.com/jensonChen/apidog/issues)

---

## 为什么做 ApiDog

日常做接口联调时，最常用的工具往往是 Postman、Apifox。它们功能很强，但在不少真实工作环境里会碰到同样的痛：

| 痛点 | 实际情况 |
|------|----------|
| **必须登录账号** | 隔一段时间就要重新登录，切换网络不方便且笨重 |
| **依赖外网** | 内网机房、隔离网、客户现场经常切不出去网，否则打不开软件 |
| **复制成本高** | 从 Chrome F12 里一个个抄 URL、Header、Cookie、Body，又慢又容易漏 |

ApiDog 的出发点很简单：

> **接口工具应该像记事本一样——本机打开就能干活，数据留在自己电脑上。**

因此我们做了这些取舍：

- **本地优先**：请求集合、环境变量、历史记录全部落在本机，不经过第三方账号体系
- **内网友好**：不强制连接公网鉴权服务；能访问目标接口即可工作
- **按开发者习惯设计**：支持整页粘贴 Chrome 网络面板内容，以及 curl 互转，减少机械劳动

如果你也经常在内网写接口、改 Cookie、对响应，ApiDog 就是为这种场景准备的。

---

## 特性

### 抓包即用

- **Chrome 粘贴**：从 DevTools Network 复制请求相关信息（标头 / 参数等），整段粘贴后自动解析为可发送请求
- **Curl 模式**：粘贴 curl 命令即可还原请求；也可把表单请求导出为 curl，方便分享给同事
- **表单模式**：方法、URL、Headers、Body 可视化编辑，适合精细调整

### 本地工作区

- **项目 / 模块 / 接口树**：按业务整理集合，支持拖拽调整结构
- **环境变量**：如 `{{baseUrl}}`，切换环境不用改每个 URL
- **请求历史**：本地记录近期发送结果，便于回溯
- **多标签会话**：同时编辑多个请求，互不干扰

### 导入与导出

- 导入 **Postman Collection**（`.json`）
- 导入 **ApiDog 项目文件** 或 **本软件导出的 zip 工作区**
- 导出整个工作区（桌面版支持另存为选目录）

### 桌面端一键使用

- 提供 Windows 安装包（`ApiDog-Setup-*.exe`）
- **无需安装 Python / Node**，双击安装即可用
- 用户数据默认在 `%AppData%\ApiDog`，覆盖安装不丢数据

---

## 快速开始

### 方式一：直接安装（推荐）

1. 打开 [Releases · ApiDog 2.1.6 Desktop](https://github.com/jensonChen/apidog/releases/tag/v2.1.6-desktop)
2. 下载 **`ApiDog-Setup-2.1.6.exe`**
3. 安装并启动（Windows 10 / 11）
4. 在左侧「新建」项目，或「导入」已有集合，开始发请求

### 方式二：从源码运行（开发者）

环境要求：Python 3.10+、Node.js 18+（仅构建前端时需要）。

```bat
git clone https://github.com/jensonChen/apidog.git
cd apidog
start.bat
```

脚本会准备后端虚拟环境、必要时构建前端，并在本机打开工作台（默认 `http://127.0.0.1:19527`）。

桌面窗口模式（开发）：

```bat
start_desktop.bat
```

打包 Windows 安装包：

```bat
build_desktop.bat
```

产物位于 `packaging\output\`。

---

## 典型工作流

```text
Chrome F12 → 复制请求信息
        ↓
  ApiDog「Chrome 粘贴」整段粘贴 → 解析预览
        ↓
     发送 / 保存到集合
        ↓
   （可选）导出 curl 给同事，或导出工作区备份
```

也可以：

```text
同事发来 curl → 粘贴到「Curl 模式」→ 解析 → 改参数 → 发送 → 保存
```

---

## 架构一览

```text
┌─────────────────────────────────────────┐
│  前端  Vue 3 + TypeScript + Element Plus │
│  请求编辑 · 集合树 · 响应 / 历史面板      │
└──────────────────┬──────────────────────┘
                   │  HTTP (本机)
┌──────────────────▼──────────────────────┐
│  后端  FastAPI + httpx                   │
│  解析 Chrome / curl · 执行请求 · 存档     │
│  数据：JSON 文件（项目 / 环境 / 历史）    │
└─────────────────────────────────────────┘
                   │
        桌面壳：独立窗口（Windows）
        数据目录：%AppData%\ApiDog
```

设计原则：**职责清晰、本地可运行、配置与数据可落地、不绑架云账号。**

---

## 目录结构

```text
apidog/
├── backend/          # FastAPI 服务、解析器、存储与桌面启动器
├── frontend/         # Vue 3 工作台界面
├── scripts/          # 启动、停止、构建脚本

```

---

## 与常见工具的对比（定位）

| | Postman / Apifox | ApiDog |
|--|------------------|--------|
| 账号登录 | 通常需要 | **不需要** |
| 外网依赖 | 偏强（账号 / 云同步） | **本机可用，面向内网** |
| F12 整段粘贴解析 | 一般需手动拆字段 | **按工作习惯整段解析** |
| curl | 支持 | 支持解析与互转 |
| 团队云协作 | 强 | 当前聚焦单机；可用导入导出交接 |

ApiDog **不是**要替代所有云端协作能力，而是把**内网里最顺手的那一段**做扎实。

---

## 路线图（方向）

- 持续打磨 Chrome / curl 解析边界情况
- 更完善的工作区备份与迁移体验
- 桌面体验与安装包稳定性（当前主推 Windows）
- 按真实内网反馈迭代，而不是堆云端功能

欢迎通过 [Issues](https://github.com/jensonChen/apidog/issues) 提出场景与缺陷。

---

## 贡献

欢迎 Issue 与 Pull Request。提交前请尽量：

1. 说明复现环境（Windows 版本、安装包版本或源码分支）
2. 附上最小复现步骤（可打码敏感 Header / Cookie）
3. 若改动解析逻辑，补充对应用例

开发分支以仓库实际协作为准；桌面安装包以 [Releases](https://github.com/jensonChen/apidog/releases) 为准。

---

## 许可证

本仓库若未单独声明许可证文件，使用前请以仓库内后续补充的 `LICENSE` 为准。若你计划商用或二次分发，建议先在 Issue 中确认授权意向。

---

## 致谢

感谢所有在内网环境里仍坚持把接口联调做扎实的工程师。  
ApiDog 希望成为你们工具箱里「打开就能用」的那一把。

---

<p align="center">
  <b>ApiDog</b> — 本地 API 工作台 · 为内网而生
</p>
