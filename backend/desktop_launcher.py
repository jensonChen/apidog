"""Desktop entry: FastAPI subprocess + pywebview window."""

from __future__ import annotations

import multiprocessing
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Must run before backend modules resolve data paths.
os.environ.setdefault("APIDOG_USE_APPDATA", "1")
os.environ.setdefault("APIDOG_DESKTOP_SHELL", "1")

from app_constants import (
    APP_DISPLAY_NAME,
    DEFAULT_HOST,
    HEALTH_PATH,
    HEALTH_WAIT_ATTEMPTS,
    HEALTH_WAIT_INTERVAL_SECONDS,
    SINGLE_INSTANCE_MUTEX_NAME,
    WIN_ERROR_ALREADY_EXISTS,
    WIN_MB_ICONERROR,
    WINDOW_BACKGROUND_COLOR,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from config_loader import load_config, resolve_data_dir, resolve_frontend_dist
from workspace_export import build_workspace_export_zip


class DesktopWindowApi:
    """Bridge for custom title-bar controls and native dialogs."""

    def __init__(self) -> None:
        self.window: Any = None
        self._is_maximized = False

    def minimize(self) -> None:
        if self.window is None:
            raise RuntimeError("窗口未就绪")
        self.window.minimize()

    def toggle_maximize(self) -> None:
        if self.window is None:
            raise RuntimeError("窗口未就绪")
        if self._is_maximized:
            self.window.restore()
            self._is_maximized = False
            return
        self.window.maximize()
        self._is_maximized = True

    def close(self) -> None:
        if self.window is None:
            raise RuntimeError("窗口未就绪")
        self.window.destroy()

    def export_workspace(self) -> dict[str, Any]:
        if self.window is None:
            raise RuntimeError("窗口未就绪")
        import webview

        payload, filename = build_workspace_export_zip()
        desktop = Path.home() / "Desktop"
        start_dir = str(desktop if desktop.exists() else Path.home())
        selected = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=start_dir,
            save_filename=filename,
            file_types=("Zip Files (*.zip)", "All files (*.*)"),
        )
        if not selected:
            return {"ok": False, "cancelled": True, "path": ""}
        target = Path(selected[0] if isinstance(selected, (list, tuple)) else selected)
        if target.suffix.lower() != ".zip":
            target = target.with_suffix(".zip")
        target.write_bytes(payload)
        return {"ok": True, "cancelled": False, "path": str(target)}


def _startup_log_path() -> Path:
    return resolve_data_dir() / "desktop-startup.log"


def _append_startup_log(message: str) -> None:
    path = _startup_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(message.rstrip() + "\n")


def _show_error(message: str) -> None:
    _append_startup_log(f"ERROR: {message}")
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, APP_DISPLAY_NAME, WIN_MB_ICONERROR)
        return
    print(message, file=sys.stderr)


def _acquire_single_instance() -> Any | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    if kernel32.GetLastError() == WIN_ERROR_ALREADY_EXISTS:
        return None
    return handle


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _wait_until_healthy(base_url: str) -> None:
    health_url = f"{base_url}{HEALTH_PATH}"
    last_error = ""
    for _ in range(HEALTH_WAIT_ATTEMPTS):
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(HEALTH_WAIT_INTERVAL_SECONDS)
    raise RuntimeError(f"后端健康检查失败: {last_error}")


def _ensure_stdio() -> None:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _start_server_process(host: str, port: int) -> subprocess.Popen[Any]:
    """
    必须用独立进程跑 uvicorn。
    同进程线程 + WebView2 加载本机 HTTP 会在 Windows 上把整进程卡成「未响应」。
    """
    env = os.environ.copy()
    env["APIDOG_USE_APPDATA"] = "1"
    env["APIDOG_DESKTOP_SHELL"] = "1"
    env.setdefault("APIDOG_DATA_DIR", str(resolve_data_dir()))

    if getattr(sys, "frozen", False):
        # PyInstaller onedir: 子进程带 --apidog-server 进入仅服务模式
        command = [sys.executable, "--apidog-server", host, str(port)]
        cwd = str(Path(sys.executable).resolve().parent)
    else:
        command = [
            sys.executable,
            "-c",
            (
                "import uvicorn; from main import app; "
                f"uvicorn.run(app, host={host!r}, port={port}, "
                "log_level='warning', log_config=None)"
            ),
        ]
        cwd = str(Path(__file__).resolve().parent)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _append_startup_log(f"server subprocess pid={proc.pid} cmd={command}")
    return proc


def _stop_server_process(proc: subprocess.Popen[Any] | None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def run_server_mode(host: str, port: int) -> int:
    """Child-process entry: only serve FastAPI."""
    _ensure_stdio()
    try:
        import uvicorn
        from main import app

        _append_startup_log(f"server-mode uvicorn {host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="warning", log_config=None)
        return 0
    except Exception:
        _append_startup_log("server-mode crashed:\n" + traceback.format_exc())
        return 1


def run() -> int:
    multiprocessing.freeze_support()
    _ensure_stdio()

    # Frozen child: ApiDog.exe --apidog-server 127.0.0.1 19527
    if len(sys.argv) >= 4 and sys.argv[1] == "--apidog-server":
        return run_server_mode(sys.argv[2], int(sys.argv[3]))

    mutex_handle = _acquire_single_instance()
    if sys.platform == "win32" and mutex_handle is None:
        _show_error(f"{APP_DISPLAY_NAME} 已在运行。")
        return 1

    server_proc: subprocess.Popen[Any] | None = None
    try:
        data_dir = resolve_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        _append_startup_log(f"--- start frozen={getattr(sys, 'frozen', False)} data={data_dir}")

        config = load_config()
        host = DEFAULT_HOST
        port = int(config["port"])
        frontend_dist = resolve_frontend_dist()
        _append_startup_log(f"frontend_dist={frontend_dist} exists={frontend_dist.exists()}")

        if not frontend_dist.exists():
            raise RuntimeError(f"未找到前端资源目录: {frontend_dist}")

        if not _port_is_free(host, port):
            raise RuntimeError(
                f"端口 {port} 已被占用。请关闭占用程序后重试，或修改 {data_dir / 'config.json'} 中的 port。"
            )

        server_proc = _start_server_process(host, port)
        base_url = f"http://{host}:{port}"
        _wait_until_healthy(base_url)
        _append_startup_log(f"healthy {base_url}")

        import webview

        window_api = DesktopWindowApi()
        window = webview.create_window(
            APP_DISPLAY_NAME,
            url=base_url,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT),
            frameless=False,
            easy_drag=False,
            shadow=False,
            background_color=WINDOW_BACKGROUND_COLOR,
        )
        window_api.window = window

        def _on_loaded() -> None:
            try:
                # 禁止在 create_window(js_api=...) 时注入：冻结包下会卡成「未响应」
                window.expose(window_api.export_workspace)
                _append_startup_log("export_workspace exposed after loaded")
            except Exception as exc:
                _append_startup_log(f"expose api failed: {exc}")

        window.events.loaded += _on_loaded
        webview.start()
        _append_startup_log("window closed")
        return 0
    except Exception as exc:
        _show_error(f"{APP_DISPLAY_NAME} 启动失败:\n{exc}")
        return 1
    finally:
        _stop_server_process(server_proc)


if __name__ == "__main__":
    sys.exit(run())
