import subprocess
import sys

for script in ("scripts/smoke.py", "tests/e2e/browser.py"):
    subprocess.run([sys.executable, script], check=True)
