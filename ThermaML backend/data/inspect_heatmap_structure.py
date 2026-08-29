import json
from pathlib import Path


HEATMAP_FILE = Path(
    "data/phoenix/raw/heatmaps/phoenix_2023-07-15_60m_tcm.json"
)

print("=" * 70)
print("HEATMAP FILE INSPECTION")
print("=" * 70)

print("Current working directory:")
print(Path.cwd())

print("\nExpected file:")
print(HEATMAP_FILE)

print("\nAbsolute path:")
print(HEATMAP_FILE.resolve())

print("\nFile exists:")
print(HEATMAP_FILE.exists())

if not HEATMAP_FILE.exists():
    print("\nERROR: Heatmap file was not found.")
    raise SystemExit

print("\nFile size:")
print(HEATMAP_FILE.stat().st_size, "bytes")


print("\nReading file...")

with open(HEATMAP_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

print("Characters read:", len(raw))

print("\nFirst 500 characters:")
print("-" * 70)
print(raw[:500])
print("-" * 70)


print("\nAttempting JSON parsing...")

try:
    data = json.loads(raw)
except Exception as e:
    print("JSON parsing FAILED:")
    print(type(e).__name__, str(e))
    raise SystemExit

print("JSON parsing successful.")

print("\nPython type:")
print(type(data).__name__)


if isinstance(data, dict):

    print("\nTop-level dictionary keys:")
    print(list(data.keys()))

    for key, value in data.items():

        print("\n" + "=" * 50)
        print("KEY:", key)
        print("TYPE:", type(value).__name__)

        if isinstance(value, list):

            print("LIST LENGTH:", len(value))

            if len(value) > 0:
                print("\nFIRST ITEM TYPE:")
                print(type(value[0]).__name__)

                print("\nFIRST ITEM:")
                print(value[0])

        elif isinstance(value, dict):

            print("DICTIONARY KEYS:")
            print(list(value.keys()))

elif isinstance(data, list):

    print("\nLIST LENGTH:")
    print(len(data))

    if len(data) > 0:

        print("\nFIRST ITEM TYPE:")
        print(type(data[0]).__name__)

        print("\nFIRST ITEM:")
        print(data[0])


print("\n" + "=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)