"""
Small demo script that exercises the two bonus features that aren't
part of the default pipeline in delivery_system.py:

  1. Random delivery delays (delay_probability > 0)
  2. A new agent joining partway through the day

Run:  python bonus_demo.py
"""
import json
from delivery_system import (
    load_data, assign_packages, simulate_deliveries,
    run_day_with_midday_join,
)

warehouses, agents, packages = load_data("data/base_case.json")

# --- Bonus: random delivery delays -----------------------------------
assignment = assign_packages(warehouses, agents, packages)
report_with_delays, _ = simulate_deliveries(
    warehouses, agents, assignment, delay_probability=0.4, seed=7
)
print("=== Report with random delivery delays (40% chance per drop-off) ===")
print(json.dumps(report_with_delays, indent=2))

# --- Bonus: a new agent (A4) joins mid-day ----------------------------
merged_report, _ = run_day_with_midday_join(
    warehouses, agents, packages,
    new_agent_id="A4", new_agent_location=(80, 10),
    join_after_fraction=0.5, seed=7,
)
print("\n=== Report where agent A4 joins halfway through the day ===")
print(json.dumps(merged_report, indent=2))

with open("outputs/base_case_with_delays_report.json", "w") as f:
    json.dump(report_with_delays, f, indent=2)
with open("outputs/base_case_midday_join_report.json", "w") as f:
    json.dump(merged_report, f, indent=2)
