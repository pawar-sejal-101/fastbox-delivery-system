"""
=====================================================================
 FastBox Mystery Delivery System - Logistics Simulator
=====================================================================
Scenario
--------
FastBox runs several warehouses, delivery agents, and packages.
This program:
  1. Reads and parses the input JSON file manually (no pandas / no
     third-party JSON helpers - just Python's built-in `json` module
     plus our own normalisation logic, since real-world input files
     are rarely in one single consistent shape).
  2. Assigns every package to the delivery agent that is closest
     (Euclidean distance) to the package's warehouse.
  3. Simulates the day: each agent travels from wherever it
     currently is -> to the warehouse -> to the destination, for
     every package it was assigned (in the order the packages
     appear in the input file). Total distance travelled is
     accumulated per agent.
  4. Produces a report (per-agent packages delivered, total
     distance, "efficiency" = average distance per package - lower
     is better) and writes it to report.json.

Bonus extras implemented
-------------------------
  * Random delivery delays               -> simulate_deliveries(..., delay_probability=...)
  * ASCII visualisation of routes        -> render_ascii_map()
  * Mid-day new agent joining            -> run_day_with_midday_join()
  * Export of the top performer to CSV   -> export_top_performer_csv()

Usage
-----
    python delivery_system.py <input_data.json> [output_directory]

If no arguments are given, it defaults to data.json -> current dir.
=====================================================================
"""

import json
import math
import random
import csv
import os
import sys


# ---------------------------------------------------------------------------
# 1. LOADING & PARSING THE JSON FILE
# ---------------------------------------------------------------------------
def load_data(filepath):
    """
    Read the JSON file from disk and hand it to `normalize_data`.

    The assignment brief shows warehouses/agents as a dict of
    {id: [x, y]}. Some of the real test files instead use a list of
    {"id": ..., "location": [x, y]} objects, and packages sometimes
    use the key "warehouse" and sometimes "warehouse_id". We support
    both shapes so the same script works on every provided test case.
    """
    with open(filepath, "r") as f:
        raw = json.load(f)
    return normalize_data(raw)


def normalize_data(raw):
    """Convert whichever JSON shape we were given into a single,
    predictable internal representation:
        warehouses -> {warehouse_id: (x, y)}
        agents     -> {agent_id: (x, y)}
        packages   -> [{"id":.., "warehouse":.., "destination": (x, y)}, ...]
    """
    warehouses = {}
    raw_warehouses = raw.get("warehouses", {})
    if isinstance(raw_warehouses, dict):
        for wid, loc in raw_warehouses.items():
            warehouses[wid] = (float(loc[0]), float(loc[1]))
    else:  # list-of-objects shape
        for w in raw_warehouses:
            warehouses[w["id"]] = (float(w["location"][0]), float(w["location"][1]))

    agents = {}
    raw_agents = raw.get("agents", {})
    if isinstance(raw_agents, dict):
        for aid, loc in raw_agents.items():
            agents[aid] = (float(loc[0]), float(loc[1]))
    else:
        for a in raw_agents:
            agents[a["id"]] = (float(a["location"][0]), float(a["location"][1]))

    packages = []
    for p in raw.get("packages", []):
        wh_id = p.get("warehouse", p.get("warehouse_id"))
        dest = p["destination"]
        packages.append({
            "id": p["id"],
            "warehouse": wh_id,
            "destination": (float(dest[0]), float(dest[1])),
        })

    return warehouses, agents, packages


# ---------------------------------------------------------------------------
# 2. DISTANCE CALCULATION
# ---------------------------------------------------------------------------
def euclidean_distance(point_a, point_b):
    """Straight-line distance between two (x, y) points."""
    return math.sqrt((point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2)


# ---------------------------------------------------------------------------
# 3. NEAREST-AGENT ASSIGNMENT
# ---------------------------------------------------------------------------
def assign_packages(warehouses, agents, packages):
    """For every package, find the agent whose current location is
    closest (Euclidean distance) to the package's warehouse, and
    assign the package to that agent.

    Returns: {agent_id: [package, package, ...]}
    """
    assignment = {agent_id: [] for agent_id in agents}

    for pkg in packages:
        wh_location = warehouses[pkg["warehouse"]]
        nearest_agent = min(
            agents,
            key=lambda agent_id: euclidean_distance(agents[agent_id], wh_location),
        )
        assignment[nearest_agent].append(pkg)

    return assignment


# ---------------------------------------------------------------------------
# 4. SIMULATION + REPORT GENERATION
# ---------------------------------------------------------------------------
def simulate_deliveries(warehouses, agents, assignment, delay_probability=0.0, seed=None):
    """
    Simulate one day of deliveries.

    For each agent, we walk through its assigned packages IN ORDER:
        current_position -> warehouse -> destination
    and add both legs to that agent's running total distance. The
    agent's "current position" then becomes the delivery destination,
    ready for the next package (this mirrors how a real courier
    actually moves through their day, instead of unrealistically
    teleporting back to their starting point after every drop-off).

    delay_probability (bonus): if > 0, each delivery has that chance
    of picking up a random delay (in minutes), which is logged but
    does not affect distance.

    Returns:
        report -> dict matching the format requested in the brief
        routes -> {agent_id: [(x, y), (x, y), ...]} - full path each
                  agent walked, used later for the ASCII visualisation
    """
    rng = random.Random(seed)
    report = {}
    routes = {}

    for agent_id, pkgs in assignment.items():
        current_pos = agents[agent_id]
        total_distance = 0.0
        total_delay_minutes = 0
        path = [current_pos]

        for pkg in pkgs:
            wh_location = warehouses[pkg["warehouse"]]
            dest_location = pkg["destination"]

            # Leg 1: travel to the warehouse to pick up the package
            total_distance += euclidean_distance(current_pos, wh_location)
            # Leg 2: travel from warehouse to the delivery destination
            total_distance += euclidean_distance(wh_location, dest_location)

            path.append(wh_location)
            path.append(dest_location)
            current_pos = dest_location

            if delay_probability > 0 and rng.random() < delay_probability:
                total_delay_minutes += rng.randint(1, 15)

        routes[agent_id] = path
        packages_delivered = len(pkgs)
        # "efficiency" = average distance travelled per package delivered.
        # Lower is better (the agent covered less ground per delivery).
        efficiency = round(total_distance / packages_delivered, 2) if packages_delivered else 0.0

        report[agent_id] = {
            "packages_delivered": packages_delivered,
            "total_distance": round(total_distance, 2),
            "efficiency": efficiency,
        }
        if delay_probability > 0:
            report[agent_id]["total_delay_minutes"] = total_delay_minutes

    # Best agent = the one with the lowest efficiency score (least
    # distance per package) among agents who actually delivered
    # something.
    active_agents = {a: r for a, r in report.items() if r["packages_delivered"] > 0}
    report["best_agent"] = min(active_agents, key=lambda a: active_agents[a]["efficiency"]) if active_agents else None

    return report, routes


def run_simulation(input_path, delay_probability=0.0, seed=None):
    """Convenience wrapper: load data -> assign -> simulate -> report."""
    warehouses, agents, packages = load_data(input_path)
    assignment = assign_packages(warehouses, agents, packages)
    report, routes = simulate_deliveries(warehouses, agents, assignment, delay_probability, seed)

    total_delivered = sum(r["packages_delivered"] for a, r in report.items() if a != "best_agent")
    assert total_delivered == len(packages), "Sanity check failed: not all packages were delivered!"

    return warehouses, agents, packages, assignment, report, routes


def save_report(report, output_path):
    """Task 5: save the report to report.json."""
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# BONUS 1: mid-day new agent joining
# ---------------------------------------------------------------------------
def run_day_with_midday_join(warehouses, agents, packages, new_agent_id, new_agent_location,
                              join_after_fraction=0.5, delay_probability=0.0, seed=None):
    """
    Simulate a day where a brand-new agent shows up partway through.

    The package list is split into an "early" batch and a "late"
    batch (by position in the list, as a stand-in for time-of-day).
    The early batch is assigned/simulated with the original roster
    of agents. Then the new agent is added to the roster (using
    agents' current, post-delivery positions) and the late batch is
    assigned/simulated with the expanded roster. The two partial
    reports are finally merged into one full-day report.
    """
    split_index = int(len(packages) * join_after_fraction)
    early_packages, late_packages = packages[:split_index], packages[split_index:]

    # --- Morning shift: original agents only ---
    early_assignment = assign_packages(warehouses, agents, early_packages)
    early_report, early_routes = simulate_deliveries(warehouses, agents, early_assignment, delay_probability, seed)

    # Agents' end-of-morning positions become their new starting points
    updated_agents = dict(agents)
    for agent_id, path in early_routes.items():
        if len(path) > 1:
            updated_agents[agent_id] = path[-1]
    updated_agents[new_agent_id] = new_agent_location  # the newcomer clocks in

    # --- Afternoon shift: full roster, including the new agent ---
    late_assignment = assign_packages(warehouses, updated_agents, late_packages)
    late_report, late_routes = simulate_deliveries(warehouses, updated_agents, late_assignment, delay_probability, seed)

    # --- Merge morning + afternoon into one full-day report ---
    all_agent_ids = set(early_report) | set(late_report)
    all_agent_ids.discard("best_agent")
    merged_report = {}
    merged_routes = {}
    for agent_id in all_agent_ids:
        morning = early_report.get(agent_id, {"packages_delivered": 0, "total_distance": 0.0})
        afternoon = late_report.get(agent_id, {"packages_delivered": 0, "total_distance": 0.0})
        delivered = morning["packages_delivered"] + afternoon["packages_delivered"]
        distance = round(morning["total_distance"] + afternoon["total_distance"], 2)
        merged_report[agent_id] = {
            "packages_delivered": delivered,
            "total_distance": distance,
            "efficiency": round(distance / delivered, 2) if delivered else 0.0,
        }
        merged_routes[agent_id] = early_routes.get(agent_id, [agents.get(agent_id, new_agent_location)]) + \
            late_routes.get(agent_id, [])[1:]

    active = {a: r for a, r in merged_report.items() if r["packages_delivered"] > 0}
    merged_report["best_agent"] = min(active, key=lambda a: active[a]["efficiency"]) if active else None

    return merged_report, merged_routes


# ---------------------------------------------------------------------------
# BONUS 2: ASCII route visualisation
# ---------------------------------------------------------------------------
def render_ascii_map(warehouses, agents, packages, width=70, height=28):
    """
    Draw a simple ASCII scatter-plot of the whole map:
        W = warehouse, A = agent start position, . = package destination

    Coordinates are scaled to fit inside `width` x `height` characters.
    This is a lightweight "birds-eye view" - not a routed path drawing,
    since real coordinates can overlap/collide at ASCII resolution.
    """
    all_points = list(warehouses.values()) + list(agents.values()) + [p["destination"] for p in packages]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = (max_x - min_x) or 1
    span_y = (max_y - min_y) or 1

    grid = [[" " for _ in range(width)] for _ in range(height)]

    def place(point, symbol):
        col = int((point[0] - min_x) / span_x * (width - 1))
        row = int((max_y - point[1]) / span_y * (height - 1))  # flip Y so north is up
        grid[row][col] = symbol

    for dest_point in [p["destination"] for p in packages]:
        place(dest_point, ".")
    for wh_point in warehouses.values():
        place(wh_point, "W")
    for ag_point in agents.values():
        place(ag_point, "A")

    lines = ["".join(row) for row in grid]
    legend = "Legend: W = warehouse   A = agent start   . = package destination"
    return "\n".join(lines) + "\n" + legend


# ---------------------------------------------------------------------------
# BONUS 3: export top performer to CSV
# ---------------------------------------------------------------------------
def export_top_performer_csv(report, assignment, warehouses, output_path):
    """Write a CSV breaking down every package delivered by the
    top-performing (best_agent) agent, plus their summary stats."""
    best_agent = report.get("best_agent")
    if not best_agent:
        return None

    pkgs = assignment.get(best_agent, [])
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency"])
        writer.writerow([
            best_agent,
            report[best_agent]["packages_delivered"],
            report[best_agent]["total_distance"],
            report[best_agent]["efficiency"],
        ])
        writer.writerow([])
        writer.writerow(["package_id", "warehouse", "warehouse_location", "destination"])
        for pkg in pkgs:
            writer.writerow([pkg["id"], pkg["warehouse"], warehouses[pkg["warehouse"]], pkg["destination"]])

    return output_path


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
def process_file(input_path, output_dir, delay_probability=0.0, seed=42):
    """Run the full pipeline for one input file and write all outputs
    (report.json, top_performer.csv, routes.txt) into output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    warehouses, agents, packages, assignment, report, routes = run_simulation(
        input_path, delay_probability=delay_probability, seed=seed
    )

    report_path = os.path.join(output_dir, f"{base_name}_report.json")
    save_report(report, report_path)

    csv_path = os.path.join(output_dir, f"{base_name}_top_performer.csv")
    export_top_performer_csv(report, assignment, warehouses, csv_path)

    ascii_map = render_ascii_map(warehouses, agents, packages)
    ascii_path = os.path.join(output_dir, f"{base_name}_ascii_map.txt")
    with open(ascii_path, "w") as f:
        f.write(ascii_map)

    print(f"[{base_name}] packages={len(packages)} agents={len(agents)} "
          f"warehouses={len(warehouses)} best_agent={report['best_agent']}")

    return report


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    process_file(input_file, out_dir)
