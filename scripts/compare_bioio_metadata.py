import sys
import time

import xarray as xr
from bioio import BioImage

# Use a sample image that is likely to exist and have metadata
# Using one from datasets/FLUTE_FLIM_data_tif/Embryo.tif as seen in the file list
# Or synthetic if that's safer. Let's try Embryo.tif first.
image_path = "datasets/FLUTE_FLIM_data_tif/Embryo.tif"

try:
    print(f"Loading {image_path}...")
    img = BioImage(image_path)
except Exception as e:
    print(f"Could not load {image_path}: {e}")
    # Fallback to creating a dummy image if needed, but bioio works best with files
    # Let's try another path if that fails, or just exit.
    sys.exit(1)

print("\n--- 1. Metadata Comparison ---")

def compare_attr(attr_name):
    wrapper_val = getattr(img, attr_name, "N/A")
    try:
        reader_val = getattr(img.reader, attr_name, "N/A")
    except Exception:
        reader_val = "Error accessing"
    
    print(f"\nProperty: {attr_name}")
    print(f"  BioImage wrapper: {wrapper_val}")
    print(f"  Reader object:    {reader_val}")
    print(f"  Same object?      {wrapper_val is reader_val}")
    print(f"  Equal value?      {wrapper_val == reader_val}")

attrs_to_check = [
    "physical_pixel_sizes",
    "channel_names",
    "dims",
    "shape",
    "dtype",
    "metadata"
]

for attr in attrs_to_check:
    compare_attr(attr)

print("\n--- 2. Xarray Data ---")
if hasattr(img.reader, "xarray_data"):
    print("img.reader has xarray_data.")
    xr_data = img.reader.xarray_data
    print(f"  Type: {type(xr_data)}")
    if isinstance(xr_data, (xr.DataArray, xr.Dataset)):
        print(f"  Dims: {xr_data.dims}")
        print(f"  Coords: {xr_data.coords}")
else:
    print("img.reader does NOT have xarray_data.")

# Check if BioImage wrapper exposes xarray_data directly
if hasattr(img, "xarray_data"):
    print("img (BioImage) has xarray_data.")
else:
    print("img (BioImage) does NOT have xarray_data.")
    

print("\n--- 3. Unique Properties ---")
wrapper_dir = set(dir(img))
reader_dir = set(dir(img.reader))

only_wrapper = wrapper_dir - reader_dir
print(f"Attributes only on BioImage wrapper (sample): {list(only_wrapper)[:10]}")

print("\n--- 4. Performance (Data Access) ---")

start_time = time.time()
_ = img.data
wrapper_time = time.time() - start_time
print(f"img.data access time: {wrapper_time:.6f}s")
print(f"img.data shape: {img.data.shape}")

# Resetting or reloading might be needed if caching is involved, 
# but we are just comparing access overhead for now.
# Note: BioImage usually converts to standard TCZYX, reader might be raw.

start_time = time.time()
_ = img.reader.data
reader_time = time.time() - start_time
print(f"img.reader.data access time: {reader_time:.6f}s")
print(f"img.reader.data shape: {img.reader.data.shape}")

