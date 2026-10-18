"""Arranca un servidor temporal, verifica HTTP local y lo detiene."""

from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = [sys.executable, "-m", "streamlit", "run", str(root / "app.py"),
               "--server.address=127.0.0.1", f"--server.port={port}",
               "--server.headless=true", "--browser.gatherUsageStats=false"]
    with subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as process:
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(process.stdout.read().decode("utf-8", errors="replace"))
                try:
                    with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as response:
                        assert response.status == 200
                        assert response.read() == b"ok"
                    with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                        assert response.status == 200
                        assert b"<html" in response.read().lower()
                    print("OK: servidor local, health=200, pagina=200. Servidor temporal detenido al finalizar.")
                    break
                except (URLError, TimeoutError):
                    time.sleep(0.25)
            else:
                raise RuntimeError("El servidor no respondió dentro de 40 segundos.")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
