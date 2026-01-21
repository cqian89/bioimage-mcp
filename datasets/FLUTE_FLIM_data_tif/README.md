# FLUTE FLIM Data

This directory contains the primary validation dataset for live workflow tests. The dataset contains TIFF files used to validate real tool execution, I/O handling, and artifact workflows.

## Provenance
- Source: [FLUTE: a Python GUI for interactive phasor analysis of FLIM data](https://zenodo.org/records/8324901)
- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode)
- Attribution: Gottlieb, D., Asadipour, B., Kostina, P., Ung, T., & Stringari, C. (2023). FLUTE: A Python GUI for interactive phasor analysis of FLIM data. Biological Imaging, 1-22. doi:10.1017/S2633903X23000211
- Retrieved: 2023 (via Zenodo record 8324901)

Provenance for this dataset should be maintained alongside the original source metadata. If additional datasets are added in the future, list them here with the same provenance details.

## Acquisition Parameters
All files have been acquired with the following parameters:
- temporal bin number = 56
- laser repetition rates = 80 MHz
- bin width = 0.223ns

## File Descriptions

| Filename | Description | Calibration File |
|----------|-------------|------------------|
| `Embryo.tif` | Fluorescence intensity decay of a zebrafish embryo at 3 days post fertilisation. | `Fluorescein_Embryo.tif` |
| `Fluorescein_Embryo.tif` | Fluorescence intensity decay of fluorescein solution with a known lifetime of 4ns. | N/A (Calibration Source) |
| `Fluorescein_hMSC.tif` | Fluorescence intensity decay of fluorescein solution with a known lifetime of 4ns. | N/A (Calibration Source) |
| `hMSC-ZOOM.tif` | Fluorescence intensity decay of mesenchymal stromal cells in control condition. | `Fluorescein_hMSC.tif` |
| `hMSC control.tif` | Fluorescence intensity decay of mesenchymal stromal cells in control condition. | `Fluorescein_hMSC.tif` |
| `hMSC_rotenone.tif` | Fluorescence intensity decay of mesenchymal stromal cells treated with rotenone. | `Fluorescein_hMSC.tif` |
| `starch SHG-IRF.tif` | Measurement of the SHG signal from starch, with a known lifetime of 0ns. | N/A (Calibration Source) |
| `ZF-1100_noEF.tif` | Fluorescence intensity decay of the zebrafish embryo at 5 days post fertilization acquired without emission. | `starch SHG-IRF.tif` |
| `ZF-1100_607-70_filter.tif` | Fluorescence intensity decay of the zebrafish embryo at 5 days post fertilization acquired with an emission filter a 607/70 nm. | `starch SHG-IRF.tif` |
| `ZF-1100_550-49_filter.tif` | Fluorescence intensity decay of the zebrafish embryo at 5 days post fertilization acquired with an emission filter of 549/50 nm. | `starch SHG-IRF.tif` |
