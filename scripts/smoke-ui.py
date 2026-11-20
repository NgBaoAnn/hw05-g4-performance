"""Check CRUD and real CSV upload in a fresh local EShop instance. Install Playwright before running."""
import json
import os
import subprocess as sp
import sys
import time
import urllib.request
from pathlib import Path
from run import BACKEND, ROOT, start_backend

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
with (out/"backend.log").open("w") as backend_log, (out/"vite.log").open("w") as frontend_log:
    backend = start_backend(backend_log)
    try:
        frontend_dir = BACKEND.parent/"frontend-admin"
        vite = sp.Popen([str(frontend_dir/"node_modules/.bin/vite"),"--host","127.0.0.1"],cwd=frontend_dir,stdout=frontend_log,stderr=frontend_log)
        try:
            for _ in range(100):
                if vite.poll() is not None:
                    raise RuntimeError("Vite exited: see vite.log")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:5174",timeout=1):
                        break
                except OSError:
                    time.sleep(.12)
            sp.run(["node","scripts/smoke-admin.cjs",str(out)],cwd=ROOT,check=True)
        finally:
            vite.terminate()
            vite.wait()
    finally:
        backend.terminate()
        backend.wait()
