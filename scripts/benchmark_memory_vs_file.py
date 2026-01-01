#!/usr/bin/env python3
"""Benchmark: Memory-backed vs File-backed Artifact Performance (T044).

Compares the performance of:
1. New mem:// artifacts with persistent workers
2. Legacy file-backed artifacts with disk I/O

Measures:
- Total execution time for multi-step workflows
- Disk I/O operations (if measurable)
- Memory usage patterns
"""

import time
import tempfile
import statistics
from pathlib import Path
import numpy as np

# Configuration
IMAGE_SIZES = [
    (1, 1, 1, 256, 256),  # Small 2D
    (1, 3, 1, 512, 512),  # Medium multi-channel
    (1, 1, 10, 512, 512),  # 3D stack
    (10, 3, 10, 256, 256),  # 5D time-lapse
]
ITERATIONS = 5  # Number of runs per test


def create_test_image(shape, tmp_dir):
    """Create a test OME-TIFF image."""
    from bioio.writers import OmeTiffWriter

    data = np.random.randint(0, 65535, size=shape, dtype=np.uint16)
    path = Path(tmp_dir) / f"test_{shape}.ome.tiff"
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")
    return path


def benchmark_file_backed_chain(image_path, num_operations=3):
    """Simulate legacy file-backed multi-step workflow.

    Each step:
    1. Read from disk
    2. Process in memory
    3. Write to disk
    """
    from bioio import BioImage
    from bioio.writers import OmeTiffWriter
    import xarray as xr

    start = time.perf_counter()
    current_path = image_path

    for i in range(num_operations):
        # Read
        img = BioImage(current_path)
        data = xr.DataArray(img.data, dims=list(img.dims.order))

        # Process (simulated operations)
        if i == 0:
            result = data  # Identity (simulated squeeze)
        elif i == 1:
            result = data.astype(np.float32) / 65535.0  # Normalize
        else:
            result = data  # Identity

        # Write to new file
        out_path = current_path.parent / f"step_{i}.ome.tiff"
        OmeTiffWriter.save(
            result.values if hasattr(result, "values") else result.data,
            str(out_path),
            dim_order=img.dims.order,
        )
        current_path = out_path

    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_memory_backed_chain(image_path, num_operations=3):
    """Simulate new memory-backed multi-step workflow.

    Steps:
    1. Read from disk once
    2. Process in memory (no intermediate I/O)
    3. Write to disk at the end only
    """
    from bioio import BioImage
    from bioio.writers import OmeTiffWriter
    import xarray as xr

    start = time.perf_counter()

    # Read once
    img = BioImage(image_path)
    data = xr.DataArray(img.data, dims=list(img.dims.order))

    # All operations in memory
    for i in range(num_operations):
        if i == 0:
            data = data  # Identity (simulated squeeze)
        elif i == 1:
            data = data.astype(np.float32) / 65535.0  # Normalize
        else:
            data = data  # Identity

    # Write once at the end
    out_path = image_path.parent / "final_output.ome.tiff"
    OmeTiffWriter.save(
        data.values if hasattr(data, "values") else data.data,
        str(out_path),
        dim_order=img.dims.order,
    )

    elapsed = time.perf_counter() - start
    return elapsed


def run_benchmarks():
    """Run all benchmarks and report results."""
    print("=" * 60)
    print("Memory vs File-Backed Artifact Performance Benchmark (T044)")
    print("=" * 60)
    print()

    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for shape in IMAGE_SIZES:
            size_mb = np.prod(shape) * 2 / (1024 * 1024)  # uint16
            print(f"Shape: {shape} ({size_mb:.1f} MB)")
            print("-" * 40)

            try:
                # Check dependencies
                import bioio
                import bioio_ome_tiff
                import xarray

                image_path = create_test_image(shape, tmpdir)
            except ImportError as e:
                print(f"  Skipping (missing dependency): {e}")
                continue
            except Exception as e:
                print(f"  Error creating test image: {e}")
                continue

            file_times = []
            mem_times = []

            for _ in range(ITERATIONS):
                file_times.append(benchmark_file_backed_chain(image_path))
                mem_times.append(benchmark_memory_backed_chain(image_path))

            file_avg = statistics.mean(file_times)
            mem_avg = statistics.mean(mem_times)
            speedup = file_avg / mem_avg if mem_avg > 0 else 0

            file_std = statistics.stdev(file_times) if len(file_times) > 1 else 0
            mem_std = statistics.stdev(mem_times) if len(mem_times) > 1 else 0

            print(f"  File-backed: {file_avg:.3f}s (±{file_std:.3f}s)")
            print(f"  Memory-backed: {mem_avg:.3f}s (±{mem_std:.3f}s)")
            print(f"  Speedup: {speedup:.2f}x")
            print()

            results.append(
                {
                    "shape": shape,
                    "size_mb": size_mb,
                    "file_avg": file_avg,
                    "mem_avg": mem_avg,
                    "speedup": speedup,
                }
            )

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if results:
        avg_speedup = statistics.mean([r["speedup"] for r in results])
        print(f"Average speedup: {avg_speedup:.2f}x")
        print()
        print("| Shape | Size | File (s) | Mem (s) | Speedup |")
        print("|-------|------|----------|---------|---------|")
        for r in results:
            print(
                f"| {r['shape']} | {r['size_mb']:.1f}MB | {r['file_avg']:.3f} | {r['mem_avg']:.3f} | {r['speedup']:.2f}x |"
            )

    return results


if __name__ == "__main__":
    run_benchmarks()
