"""Run local fallback acceptance while Docker images download; processes are cleaned up."""
import os
import subprocess
import sys
import socket
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = dict(os.environ, DOMAIN_URL="http://127.0.0.1:8080", PYTHON_URL="http://127.0.0.1:8082")
python = str(root / ".venv/Scripts/python.exe") if os.name == "nt" else sys.executable
commands = [
    ([python, "-m", "uvicorn", "app.main:app", "--app-dir", "services/ai-service", "--host", "127.0.0.1", "--port", "8082", "--no-access-log"], 8082),
    (["java", "-jar", "services/domain-api/target/domain-api-0.1.0.jar"], 8080),
    (["node", "apps/bff/src/server.js"], 8081),
    (["node", "node_modules/vite/bin/vite.js", "apps/web", "--host", "127.0.0.1", "--port", "3000"], 3000),
]
processes = []
try:
    for command, port in commands:
        process = subprocess.Popen(command, cwd=root, env=env)
        processes.append(process)
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError(f"Service {port} exited: {process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError(f"Service {port} did not become ready")
    subprocess.run([python, "scripts/local_checks.py"], cwd=root, env=env, check=True)
finally:
    for process in reversed(processes):
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
