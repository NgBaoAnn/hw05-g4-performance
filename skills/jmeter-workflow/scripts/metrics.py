"""Summarize JMeter CSV samples by label in a half-open, start-time window."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def percentile(values, fraction=.95):
    return sorted(values)[math.ceil(len(values)*fraction)-1]


def read_http(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"timeStamp","elapsed","success","label","URL","threadName","allThreads","bytes"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("JTL must include "+", ".join(sorted(required)))
        return [row for row in reader if row["URL"].startswith(("http://","https://"))]


def summarize(rows, begin, end):
    if end <= begin:
        raise ValueError("End must be after start")
    selected = [r for r in rows if begin <= int(r["timeStamp"]) < end]
    if not selected:
        raise ValueError("No HTTP samples in this time window")
    groups = defaultdict(list)
    for r in selected:
        groups[r["label"]].append(r)
    def stats(samples):
        times = [int(r["elapsed"]) for r in samples]
        ok = sum(r["success"]=="true" for r in samples)
        return {"samples":len(times), "errors":len(times)-ok, "p95_ms":percentile(times),
                "success_rps":round(ok*1000/(end-begin),4),
                "max_bytes":max(int(r["bytes"]) for r in samples)}
    return {**stats(selected), "max_active":max(int(r["allThreads"]) for r in selected),
            "by_label":{k:stats(v) for k,v in groups.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jtl",type=Path)
    parser.add_argument("--start-ms",type=int)
    parser.add_argument("--end-ms",type=int)
    args=parser.parse_args()
    rows=read_http(args.jtl)
    if not rows:
        raise SystemExit("No HTTP samples in JTL")
    start = min(int(r["timeStamp"]) for r in rows) if args.start_ms is None else args.start_ms
    end = max(int(r["timeStamp"])+max(1,int(r["elapsed"])) for r in rows) if args.end_ms is None else args.end_ms
    print(json.dumps(summarize(rows,start,end),indent=2,ensure_ascii=False))
