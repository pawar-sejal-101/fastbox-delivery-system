"""Run the FastBox solution against every JSON input in data/."""
from pathlib import Path
from delivery_system import process_file

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"

for input_file in sorted(DATA.glob("*.json")):
    process_file(str(input_file), str(OUTPUTS))

print("All test cases completed successfully.")
