from __future__ import annotations

import argparse
import json
import os
import tempfile

import pandas as pd
from scipy import stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table-a", required=True)
    parser.add_argument("--table-b", required=True)
    parser.add_argument("--column", required=True)
    parser.add_argument("--equal-var", type=str, default="true")
    args = parser.parse_args()

    equal_var = args.equal_var.lower() == "true"

    # Load tables
    df_a = pd.read_csv(args.table_a)
    df_b = pd.read_csv(args.table_b)

    # Extract columns
    a = df_a[args.column].values
    b = df_b[args.column].values

    # Run t-test
    result = stats.ttest_ind(
        a, b, equal_var=equal_var, nan_policy="propagate", alternative="two-sided"
    )

    # Prepare stable output
    output = {
        "statistic": float(result.statistic),
        "pvalue": float(result.pvalue),
        "equal_var": equal_var,
        "column": args.column,
        "n_a": int(len(a)),
        "n_b": int(len(b)),
    }

    # Save to JSON
    fd, output_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    with open(output_path, "w") as f:
        json.dump(output, f)

    # Print contract
    print(json.dumps({"status": "success", "output_path": output_path}))


if __name__ == "__main__":
    main()
