# TTTR Test Datasets

Minimal subset of TTTR (Time-Tagged Time-Resolved) data files for testing the bioimage-mcp tttrlib integration.

## File Inventory

| File | Format | Size | Used By | Description |
|------|--------|------|---------|-------------|
| `bh/bh_spc132.spc` | SPC-130 | ~1MB | Smoke 8.1, 8.3 | Becker & Hickl SPC-132 FCS data |
| `imaging/leica/sp5/LSM_1.ptu` | PTU | ~5MB | Smoke 8.2 | Leica SP5 FLIM-CLSM scanning data |
| `hdf/1a_1b_Mix.hdf5` | Photon-HDF5 | ~2MB | Smoke 8.4 | Photon-HDF5 format sample |

## Provenance

These files are sourced from the [tttrlib test data repository](https://gitlab.peulen.xyz/skf/tttr-data).

- **Upstream Repository**: https://gitlab.peulen.xyz/skf/tttr-data
- **Pinned Commit**: To be updated when files are vendored
- **Last Updated**: 2025-01-15

## License

The tttrlib test data files are provided for testing purposes. Please refer to the upstream repository for license terms.

**Important**: Do not redistribute these files without verifying the license terms from the upstream source.

## Refreshing Datasets

To refresh the dataset subset from upstream:

1. Clone the upstream repository:
   ```bash
   git clone https://gitlab.peulen.xyz/skf/tttr-data.git /tmp/tttr-data
   ```

2. Copy required files:
   ```bash
   cp /tmp/tttr-data/bh/bh_spc132.spc datasets/tttr-data/bh/
   cp /tmp/tttr-data/imaging/leica/sp5/LSM_1.ptu datasets/tttr-data/imaging/leica/sp5/
   cp /tmp/tttr-data/photon-hdf5/1a_1b_Mix.hdf5 datasets/tttr-data/hdf/
   ```

3. Update the pinned commit hash in this README

## Git LFS

These binary files are tracked with Git LFS. To work with them:

```bash
git lfs install
git lfs pull
```
