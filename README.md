# FastBox Mystery Delivery System - Solution

## Files

- `delivery_system.py` - the main solution (parsing, assignment, simulation, report, bonuses)
- `bonus_demo.py` - demo of the random-delay and mid-day-new-agent bonus features
- `data/` - all provided input files (the assignment's `base_case.json` and the 10 `test_case_*.json` files)
- `outputs/` - generated results for every input file:
  - `<name>_report.json` - the required report (packages_delivered, total_distance, efficiency, best_agent)
  - `<name>_top_performer.csv` - bonus: CSV export of the top-performing agent's deliveries
  - `<name>_ascii_map.txt` - bonus: ASCII scatter-plot of warehouses / agents / destinations
  - `base_case_with_delays_report.json` - bonus: report including simulated random delivery delays
  - `base_case_midday_join_report.json` - bonus: report where a new agent joins mid-day

## How to run

```bash
# Single file -> writes report/csv/ascii-map into an output folder
python delivery_system.py data/base_case.json outputs

# Regenerate outputs for every provided test case
for f in data/*.json; do python delivery_system.py "$f" outputs; done

# See the extra bonus demos (delays + mid-day join)
python bonus_demo.py
```

## Approach

1. **Parsing** - `load_data`/`normalize_data` read the JSON with the built-in `json`
   module and normalize the two shapes seen across the provided files (dict-of-coords
   vs list-of-objects, `warehouse` vs `warehouse_id`) into one internal format.
2. **Distance** - a single `euclidean_distance(a, b)` helper is reused everywhere.
3. **Assignment** - each package is assigned to the agent whose *current* location is
   closest (Euclidean distance) to the package's *warehouse* - exactly as specified.
4. **Simulation** - each agent processes its assigned packages in order: it travels
   from wherever it currently is -> to the warehouse -> to the destination, and its
   position updates to the destination before the next package. This gives a
   realistic, continuous route rather than teleporting the agent back to its start
   point after every delivery.
5. **Report** -
   - `packages_delivered`: count of packages assigned to that agent
   - `total_distance`: total distance travelled, rounded to 2 decimals
   - `efficiency`: `total_distance / packages_delivered` (average distance per
     package - **lower is better**, since it means the agent covered less ground for
     each delivery)
   - `best_agent`: the agent with the lowest `efficiency` among agents who delivered
     at least one package
   - A sanity check asserts that packages delivered across all agents always equals
     the total number of input packages.
6. **Bonus extensions** (all implemented, see `delivery_system.py`):
   - Random delivery delays (`simulate_deliveries(..., delay_probability=...)`)
   - ASCII visualisation of the warehouse/agent/destination layout (`render_ascii_map`)
   - A new agent joining mid-day (`run_day_with_midday_join`)
   - Exporting the top performer's delivery breakdown to CSV (`export_top_performer_csv`)

## Notes

- Verified against all 10 provided test cases plus the assignment's `base_case.json` -
  every run passes the "total delivered == total packages" sanity check.
- The example numbers shown in the assignment PDF appear to be illustrative only (the
  PDF's embedded JSON sample itself is corrupted/duplicated by the PDF's text
  extraction), so exact figures were derived from the stated logic rather than
  reverse-engineered from that example.
