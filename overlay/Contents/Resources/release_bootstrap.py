#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""桌面包启动引导；必须在导入 eazybot 前加载发布环境。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _load_release_environment() -> Path:
    """加载安装包内经过白名单过滤的环境文件。"""
    env_path = Path(__file__).resolve().with_name("release.env")
    if not env_path.is_file():
        raise FileNotFoundError(f"桌面运行时配置不存在: {env_path}")
    from dotenv import load_dotenv

    load_dotenv(env_path, override=True)
    os.environ["EAZYBOT_RELEASE_ENV_FILE"] = str(env_path)
    os.environ["EAZYBOT_DESKTOP_APP"] = "1"
    os.environ["PYTHONNOUSERSITE"] = "1"

    # 国内镜像默认值：MCP 子进程 npx/uvx 按需下载包时走国内源，
    # 避免 registry.npmjs.org / pypi.org 不可达导致 15s 连接超时。
    # setdefault 保证用户显式配置的 env 优先级更高：
    # StdIOStatefulClient 用 {**os.environ, **(env or {})} 合并环境。
    os.environ.setdefault(
        "NPM_CONFIG_REGISTRY",
        "https://registry.npmmirror.com",
    )
    os.environ.setdefault(
        "UV_DEFAULT_INDEX",
        "https://mirrors.aliyun.com/pypi/simple/",
    )
    os.environ.setdefault(
        "PIP_INDEX_URL",
        "https://mirrors.aliyun.com/pypi/simple/",
    )
    app_root = os.environ.get("EAZYBOT_WORKING_DIR", "").strip()
    if app_root:
        os.environ["EAZYBOT_APP_ROOT"] = app_root
    try:
        import certifi

        certificate = certifi.where()
        os.environ["SSL_CERT_FILE"] = certificate
        os.environ["REQUESTS_CA_BUNDLE"] = certificate
        os.environ["CURL_CA_BUNDLE"] = certificate
    except (ImportError, OSError):
        pass
    return env_path


def _working_dir() -> Path:
    configured = os.environ.get("EAZYBOT_WORKING_DIR", "").strip()
    return Path(configured or "~/.eazybot").expanduser().resolve()


def _seed_working_data() -> None:
    """桌面包内置数据播种：全新工作目录时铺入预置智能体与技能。

    只在 WORKING_DIR 尚无 config.json / profiles.json（全新机器）时执行，
    绝不覆盖既有用户数据。
    """
    seed_dir = Path(__file__).resolve().with_name("seed") / "eazybot-data"
    if not seed_dir.is_dir():
        return
    working_dir = _working_dir()
    if (working_dir / "config.json").is_file() or (
        working_dir / "profiles.json"
    ).is_file():
        return
    import shutil

    print("首次启动，正在铺入预置智能体与技能...", flush=True)
    shutil.copytree(seed_dir, working_dir, dirs_exist_ok=True)


def _ensure_initialized(arguments: list[str]) -> None:
    """桌面启动时首次创建配置，其它 CLI 命令保持无副作用。"""
    if not arguments or arguments[0] != "desktop":
        return
    if (_working_dir() / "config.json").is_file():
        return
    print("首次启动，正在初始化桌面配置...", flush=True)
    subprocess.run(
        [
            sys.executable,
            "-u",
            "-m",
            "eazybot",
            "init",
            "--defaults",
            "--accept-security",
        ],
        check=True,
        env=os.environ.copy(),
    )


def _desktop_subprocess(
    args: list[str],
) -> tuple[list[str], dict[str, int]] | None:
    """Windows 桌面命令需要进程组隔离；其余场景返回 None。

    根因：隐藏控制台启动时 CTRL_C_EVENT 会连带中断桌面壳，
    pywebview 窗口尚未稳定即退出（退出码 0xC000013A）。修复：
    新进程组隔离 Ctrl+C，并避免多余控制台窗口。
    """
    if os.name != "nt":
        return None
    if not args or args[0] != "desktop":
        return None
    # pythonw.exe 跑 pywebview 桌面壳约十余秒后以 0 退出，
    # webview 无法稳定驻留；必须改用 python.exe。
    executable = sys.executable
    exe_dir = os.path.dirname(executable)
    if os.path.basename(executable).lower() == "pythonw.exe":
        candidate = os.path.join(exe_dir, "python.exe")
        if os.path.isfile(candidate):
            executable = candidate
    creationflags = getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    debug_console = os.environ.get("EAZYBOT_DESKTOP_CONSOLE") in (
        "1",
        "true",
        "yes",
    )
    if not debug_console:
        creationflags |= getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    return [executable, "-u", "-m", "eazybot", *args], {
        "creationflags": creationflags,
    }


def main(arguments: list[str] | None = None) -> int:
    """加载发布配置后替换为真正的 EazyBot CLI 进程。"""
    args = list(sys.argv[1:] if arguments is None else arguments)
    _load_release_environment()
    _seed_working_data()
    _ensure_initialized(args)
    desktop = _desktop_subprocess(args)
    if desktop is not None:
        command, kwargs = desktop
    else:
        # argv[0] 用应用名：让系统把进程显示为 EazyBot-jiangnan 而非 python
        command = ["EazyBot-jiangnan", "-u", "-m", "eazybot", *args]
        kwargs = {}
    if sys.platform == "darwin" and desktop is None:
        # macOS 桌面应用由 LaunchServices 关联到当前 PID。若再用
        # subprocess.call 派生 Shell，pywebview 会把子 Python 注册成一个
        # 通用 exec 应用。直接替换可保留外层 .app 身份。
        # LaunchServices 只把 Contents/MacOS/ 下的可执行文件归属到 .app；
        # __PYVENV_LAUNCHER__ 会把 sys.executable 指回 venv 内的 python，
        # 因此最终 exec 必须回到启动器指定的 MacOS 副本，否则 Dock 会
        # 出现第二个独立图标。
        target = os.environ.get("EAZYBOT_MACOS_PYTHON", "").strip() or sys.executable
        child_env = os.environ.copy()
        # CPython 读取 __PYVENV_LAUNCHER__ 后会把它从 os.environ 弹掉；
        # 二次 exec 时必须补回，否则 MacOS 副本解析不到 pyvenv.cfg。
        child_env.setdefault(
            "__PYVENV_LAUNCHER__",
            str(Path(sys.prefix) / "bin" / "EazyBot-jiangnan"),
        )
        os.execve(target, command, child_env)
        raise RuntimeError("替换 EazyBot CLI 进程失败")
    sys.exit(
        subprocess.call(
            command, env=os.environ.copy(), **kwargs
        )
    )


if __name__ == "__main__":
    sys.exit(main())
