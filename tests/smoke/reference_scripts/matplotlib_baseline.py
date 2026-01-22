from __future__ import annotations

import json
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path


def main():
    # Generate synthetic data
    x = np.linspace(0, 10, 100)
    y = np.sin(x)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x, y, label="Sine Wave")
    ax.set_title("Matplotlib Baseline")
    ax.legend()

    # Save to a temporary location if provided, else current dir
    output_dir = Path.cwd()
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])

    output_path = output_dir / "matplotlib_baseline.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(json.dumps({"plot_path": str(output_path.absolute())}))


if __name__ == "__main__":
    main()
