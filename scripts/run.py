"""Run one scenario against a fresh disposable EShop checkout, capture JTL and process samples."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import signal
import socket
import subprocess as sp
import sys
import time
import urllib.request

from fixtures import ROOT, seed

WORK = ROOT / ".work"
BACKEND = WORK / "eshop/backend"
LOCAL = "http://127.0.0.1:3000"
DEFAULTS = {"Smoke": (1, 1, 90, 3), "Pilot": (5, 5, 120, -1), "Load": (10, 60, 360, -1),
            "Stress": (80, 30, 600, -1), "Spike": (50, 5, 365, -1), "Soak": (10, 1, 721, -1)}


def start_backend(log):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 3000))
    # Only run in a dedicated clone. Upstream drops its demo tables at every boot.
    assert (BACKEND.parent / ".git").exists()
    server = (BACKEND / "server.js").read_text()
    assert server.count("app.listen(PORT, () =>") == 1
    (BACKEND / "g4-local.cjs").write_text(server.replace("app.listen(PORT, () =>", "app.listen(PORT, '127.0.0.1', () =>"))
    proc = sp.Popen(["node", "g4-local.cjs"], cwd=BACKEND, stdout=log, stderr=log)
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError("Backend exited; inspect backend.log")
            try:
                with urllib.request.urlopen(LOCAL+"/api/products", timeout=1) as resp:
                    if len(json.load(resp)) == 5:
                        time.sleep(.2)
                        seed()
                        return proc
            except OSError:
                pass
            time.sleep(.1)
        raise TimeoutError("Seed initialization")
    except BaseException:
        proc.terminate()
        proc.wait()
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario", choices=DEFAULTS)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--vu", type=int, choices=range(1,81), metavar="1..80")
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    scenario = args.scenario
    n, ramp, duration, loops = DEFAULTS[scenario]
    if args.vu:
        assert scenario == "Soak", "--vu applies to soak only"
        n = args.vu
    profile = scenario if scenario in ("Stress","Spike") else "Load"
    plan, = (ROOT/"plans").glob(f"*_{profile}_*.jmx")
    if scenario == "Smoke":
        # JMeter's scheduler controls duration. Use an explicit finite-loop smoke plan.
        smoke = out/"smoke.jmx"
        smoke.write_text(plan.read_text().replace('${__P(loops,-1)}', '3').replace('name="ThreadGroup.scheduler">true', 'name="ThreadGroup.scheduler">false'))
        plan = smoke
    java = os.environ.get("JAVA", "java")
    jar = Path(os.environ.get("JMETER_HOME", WORK/"apache-jmeter-5.6.3"))/"bin/ApacheJMeter.jar"
    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + scenario
    cmd = [java, "-Xms128m", "-Xmx1g", "-Djava.awt.headless=true", "-jar", str(jar),
           "-n", "-t", str(plan), "-l", str(out/"samples.jtl"), "-j", str(out/"jmeter.log"),
           "-Jsummariser.interval=5", "-Jjmeterengine.nongui.port=0",
           "-Jjmeter.save.saveservice.assertion_results_failure_message=false",
           "-Jfixture="+str(ROOT/"data/admin-fixtures.csv"), "-JrunId="+run_id,
           f"-Jvu={n}", f"-Jramp={ramp}", f"-Jduration={duration}", f"-Jloops={loops}"]
    with (out/"backend.log").open("w") as bl, (out/"console.log").open("w") as jl, (out/"resources.csv").open("w") as rl:
        backend = start_backend(bl)
        try:
            meter = sp.Popen(cmd, cwd=ROOT, stdout=jl, stderr=jl)
            try:
                meta = dict(scenario=scenario, run_id=run_id, plan=plan.name, max_vu=n, ramp=ramp,
                            duration=duration, loops=loops, node_pid=backend.pid, java_pid=meter.pid)
                (out/"run.json").write_text(json.dumps(meta,indent=2))
                print(run_id, "started", flush=True)
                writer = csv.writer(rl)
                writer.writerow(["epoch","process","pid","cpu_pct","rss_kib"])
                while meter.poll() is None:
                    stamp=time.time()
                    rows=sp.check_output(["ps","-o","pid=,%cpu=,rss=","-p",f"{backend.pid},{meter.pid}"],text=True)
                    for row in rows.splitlines():
                        pid,cpu,rss=row.split()
                        writer.writerow([stamp,"node" if int(pid)==backend.pid else "java",pid,cpu,rss])
                    rl.flush()
                    time.sleep(1)
                if meter.returncode:
                    raise RuntimeError("JMeter failed: "+str(out/"console.log"))
            finally:
                if meter.poll() is None:
                    meter.terminate()
                    meter.wait()
        finally:
            backend.terminate()
            backend.wait()
    with (out/"samples.jtl").open() as jtl:
        rows = list(csv.DictReader(jtl))
    assert rows and all("elapsed" in r for r in rows)
    if scenario == "Smoke":
        assert len(rows)==30 and all(r["success"]=="true" for r in rows), "Smoke failed"
    if scenario in ("Load","Stress","Spike"):
        sp.run([java,"-Djava.awt.headless=true","-jar",str(jar),"-g",str(out/"samples.jtl"),
                "-o",str(out/"html"),"-j",str(out/"report.log")],check=True)
        assert (out/"html/index.html").is_file()
    print(run_id, "finished", len(rows), "samples", flush=True)


if __name__ == "__main__":
    main()
