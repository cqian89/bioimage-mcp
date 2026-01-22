from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def main():
    if len(sys.argv) < 2:
        print("Usage: python pandas_baseline.py <csv_path>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    # 1. Read CSV - Standard read
    df = pd.read_csv(csv_path)

    # 2. Describe
    desc = df.describe()

    # 3. Groupby operation
    # In measurements.csv: label_id, area, mean_intensity, class_name
    if "class_name" in df.columns:
        gb = df.groupby("class_name").mean(numeric_only=True)
    else:
        # Fallback
        gb = df.iloc[:, :2].groupby(df.columns[0]).mean()

    # Combine results into a dict for JSON output
    result = {
        "describe": {
            **desc.to_dict(orient="split"),
            "index_names": list(desc.index.names),
        },
        "groupby": {
            **gb.to_dict(orient="split"),
            "index_names": list(gb.index.names),
        },
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
