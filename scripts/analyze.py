"""Match JTL rows and process telemetry to scheduled phases and select a soak level."""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"skills/jmeter-workflow/scripts"))
from metrics import read_http, summarize

PHASES = {"Load":[("steady",60,360)], "Stress":[(str(n),start,start+120) for n,start in zip((10,20,40,80),(30,180,330,480))],
          "Spike":[("before",5,120),("peak",125,185),("recovery",185,365)],
          "Soak":[("sustained",1,721)]}


def load(directory):
    meta = json.loads((directory/"run.json").read_text())
    text = (directory/"jmeter.log").read_text()
    match = re.search(r"^(.{23}) INFO .*Starting ThreadGroup: 1 :",text,re.M)
    origin = dt.datetime.strptime(match[1],"%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    start = round(origin.timestamp()*1000)
    samples = read_http(directory/"samples.jtl")
    with (directory/"resources.csv").open() as f:
        resources = list(csv.DictReader(f))
    def window(a,b):
        result = summarize(samples,start+a*1000,start+b*1000)
        result["start_ms"]=start+a*1000
        result["end_ms"]=start+b*1000
        for process in ("node","java"):
            data = [r for r in resources if r["process"]==process and a <= float(r["epoch"])-start/1000 < b]
            if data:
                rss=[int(r["rss_kib"])/1024 for r in data]
                result[process] = dict(peak_rss_mib=round(max(rss),1), first_rss_mib=round(rss[0],1),
                                       last_rss_mib=round(rss[-1],1), peak_cpu_pct=max(float(r["cpu_pct"]) for r in data))
        return result
    scenario = meta["scenario"]
    report={"meta":meta,"all":summarize(samples,min(int(r["timeStamp"]) for r in samples),
            max(int(r["timeStamp"])+max(1,int(r["elapsed"])) for r in samples)),
            "phases":{k:window(a,b) for k,a,b in PHASES.get(scenario,[])}}
    if scenario == "Soak":
        report["minutes"]=[window(i,i+60) for i in range(1,721,60)]
    if scenario == "Spike":
        report["recovery_windows"]=[window(i,i+30) for i in range(185,365,30)]
    return report


def violations(phase, baseline):
    issues = []
    if phase["errors"]/phase["samples"] >= .01:
        issues.append("error rate >= 1%")
    for label, stats in baseline["by_label"].items():
        p95 = phase["by_label"].get(label, {}).get("p95_ms")
        if p95 is None or p95 > 2*stats["p95_ms"]:
            issues.append(label)
    return issues


def choose_soak():
    baseline = load(ROOT/"evidence/Load")["phases"]["steady"]
    stress = load(ROOT/"evidence/Stress")["phases"]
    accepted=[int(key) for key,phase in stress.items() if not violations(phase,baseline)]
    return max(accepted,default=5)


if __name__=="__main__":
    if sys.argv[1:]==["--choose-soak"]:
        print(choose_soak())
    else:
        print(json.dumps(load(Path(sys.argv[1])),indent=2,ensure_ascii=False))
