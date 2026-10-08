# BOAND* performance experiments

## Round 1: journal smoke suite

The fixed suite contains 14 instances in the 11 ICAPS domains. Comparisons use
`PYTHONHASHSEED=0`, four workers, 6,000,000 KB of virtual memory per planner,
and the campaign's unchanged BOAND bw configuration. Each unprofiled revision
is measured three times, extended to five if needed. Successful runs require
14 completed searches, 12 solved instances, matching Pareto costs and policy
replay. Profiled runs are excluded from timing comparisons.

Raw measurements and profiling scripts are retained in
`outputs/performance/round1/`; planner provenance remains in
`runs/journal_development/`. Per-instance search times are summarized by their
median; aggregate speedups use the geometric mean of baseline/candidate ratios.
Peak planner RSS is sampled from Linux `/proc` high-water marks and is a lower
bound when a process exits between samples. Virtual memory remains capped by
the campaign. Total suite times include execution and validation; external
elapsed times additionally include interpreter startup and measurement overhead.

Baseline and attempt records will be added as measurements complete.
