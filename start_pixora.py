"""Source/bundle bootstrap; does not install system services or modify Codex login."""
import hashlib
from pathlib import Path
import subprocess
import sys
import venv


def main():
    root = Path(__file__).resolve().parent
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11+ required / 请先安装 Python 3.11 或更新版本。')
    if not (root/'web/dist/index.html').is_file():
        raise SystemExit('Web build missing / 请使用含 Web 构建的交付包，或先运行 npm --prefix web ci 与 npm --prefix web run build。')
    directory = root/'.venv-local'
    python = directory/('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if not python.is_file():
        print('Preparing private Python environment / 正在准备独立 Python 环境…', flush=True)
        venv.create(directory, with_pip=True)
    fingerprint = hashlib.sha256((root/'requirements-lock.txt').read_bytes()+(root/'pyproject.toml').read_bytes()).hexdigest()
    marker = directory/'pixora-installed'
    if not marker.exists() or marker.read_text() != fingerprint:
        subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements-lock.txt')],cwd=root,check=True)
        marker.write_text(fingerprint)
    # Reinstall local source so application edits cannot leave a stale installed wheel.
    subprocess.run([str(python),'-m','pip','install','--no-deps',str(root)],cwd=root,check=True)
    raise SystemExit(subprocess.call([str(python),'-m','pixora.local','--web-dir',str(root/'web/dist'),*sys.argv[1:]],cwd=root))


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit('Startup failed: check Python, network and folder write access. / 启动失败，请检查 Python、网络与目录写权限。')
