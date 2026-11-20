---
name: jmeter-workflow
description: Design and run a CSV-driven JMeter business workflow on a local test system and audit throughput, p95 and failures from its raw HTTP JTL. Use for endpoint groups, step loads, spikes and soak comparisons.
---

Map each operation to a measured HTTP request, the data it consumes and an observable business assertion. Confirm the base URL and use disposable records for writes. Pin the SUT revision and keep fixture size and initial database state comparable across runs.

Assign each virtual user a stable input row. Extract the login token per iteration and verify the role. Read back an independent record after a write. For a dashboard, inspect the calls made by the actual client before choosing labels and think time.

Prove one complete iteration at 1 VU before increasing load. Capture the active thread count, run clock and backend resource samples. Keep console output and original JTL. Save one report view appropriate to the question.

Run `python3 scripts/metrics.py <path-to-jtl>` from this skill directory. For a plateau use `--start-ms` and `--end-ms` with epoch milliseconds from the run log. Output gives HTTP sample count, business assertion failures, nearest-rank p95 of elapsed milliseconds and successful requests per wall-clock second, globally and per label. Filters out non-HTTP rows using the URL column. Confirm synthetic transaction samples lack URLs before counting.

For a workflow rate, match completions by thread and iteration. If the plan skips to the next loop on any error and the final sampler is unique, its successful count is a completion counter. Keep interrupted iterations out of this count. Compare p95 for the same label and load window. Audit resource claims against backend PID samples. Record the exact window and sample count with every suspected regression.
