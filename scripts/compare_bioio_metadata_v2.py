import sys
import time

import numpy as np
import xarray as xr
from bioio import BioImage

# Use the same image
image_path = "datasets/FLUTE_FLIM_data_tif/Embryo.tif"

try:
    img = BioImage(image_path)
except Exception as e:
    print(f"Could not load {image_path}: {e}")
    sys.exit(1)

print("\n--- 1. Metadata Comparison ---")

def compare_attr(attr_name):
    wrapper_val = getattr(img, attr_name, "N/A")
    try:
        reader_val = getattr(img.reader, attr_name, "N/A")
    except Exception:
        reader_val = "Error accessing"
    
    # Handle huge metadata output
    wrapper_str = str(wrapper_val)
    if len(wrapper_str) > 100:
        wrapper_str = wrapper_str[:100] + "... [truncated]"
        
    reader_str = str(reader_val)
    if len(reader_str) > 100:
        reader_str = reader_str[:100] + "... [truncated]"
    
    print(f"\nProperty: {attr_name}")
    print(f"  BioImage wrapper: {wrapper_str}")
    print(f"  Reader object:    {reader_str}")
    
    # Check identity/equality if feasible
    try:
        print(f"  Same object?      {wrapper_val is reader_val}")
        # Equality might fail for arrays or complex objects
        if isinstance(wrapper_val, (np.ndarray, list, tuple)) or isinstance(reader_val, (np.ndarray, list, tuple)):
            print("  Equal value?      (Skipped for complex types)")
        else:
            print(f"  Equal value?      {wrapper_val == reader_val}")
    except:
        pass

attrs_to_check = [
    "physical_pixel_sizes",
    "channel_names",
    "dims",
    "shape",
    "dtype",
    # "metadata" # Skip printing this again, we saw it's huge
]

for attr in attrs_to_check:
    compare_attr(attr)

print("\n--- 2. Xarray Data ---")
if hasattr(img.reader, "xarray_data"):
    print("img.reader has xarray_data.")
    try:
        xr_data = img.reader.xarray_data
        print(f"  Type: {type(xr_data)}")
        if isinstance(xr_data, (xr.DataArray, xr.Dataset)):
            print(f"  Dims: {xr_data.dims}")
            print(f"  Coords: {xr_data.coords}")
    except Exception as e:
        print(f"  Error accessing xarray_data: {e}")
else:
    print("img.reader does NOT have xarray_data.")

if hasattr(img, "xarray_data"):
    print("img (BioImage) has xarray_data.")
else:
    print("img (BioImage) does NOT have xarray_data.")

print("\n--- 3. Unique Properties ---")
wrapper_dir = set(dir(img))
reader_dir = set(dir(img.reader))

only_wrapper = wrapper_dir - reader_dir
# Filter out private methods
only_wrapper_public = [x for x in only_wrapper if not x.startswith("_")]
print(f"Attributes only on BioImage wrapper (sample): {sorted(only_wrapper_public)[:10]}")

print("\n--- 4. Performance (Data Access) ---")

start_time = time.time()
d1 = img.data
wrapper_time = time.time() - start_time
print(f"img.data access time: {wrapper_time:.6f}s")
print(f"img.data shape: {d1.shape}")

# Resetting reader state isn't easily possible, but let's try accessing reader data
start_time = time.time()
d2 = img.reader.data
reader_time = time.time() - start_time
print(f"img.reader.data access time: {reader_time:.6f}s")
print(f"img.reader.data shape: {d2.shape}")

print(f"\nSpeedup/Slowdown factor (wrapper/reader): {wrapper_time/reader_time:.2f}x")

