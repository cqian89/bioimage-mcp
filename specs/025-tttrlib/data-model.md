# Data Model: tttrlib Integration

## Artifact Types

### TTTRRef

A dedicated artifact type for Time-Tagged Time-Resolved photon stream files.

```yaml
type: TTTRRef
fields:
  ref_id: string (UUID)
  uri: string (file:// path to TTTR file)
  type: "TTTRRef"
  format: string (PTU, HT3, SPC-130, SPC-630_256, SPC-630_4096, HDF, CZ-RAW, SM)
  storage_type: "file"
  metadata:
    n_valid_events: integer (optional) - Number of valid photon events
    used_routing_channels: array[integer] (optional) - Active detector channels
    macro_time_resolution_s: number (optional) - Macro time resolution in seconds
    micro_time_resolution_s: number (optional) - Micro time resolution in seconds
```

### ObjectRef (for CLSMImage)

Used to reference in-memory tttrlib objects like CLSMImage.

```yaml
type: ObjectRef
fields:
  ref_id: string (UUID)
  uri: string (obj://<session>/<env>/<id>)
  type: "ObjectRef"
  python_class: string (e.g., "tttrlib.CLSMImage")
  storage_type: "memory"
```

## Data Flow

```
TTTR File (SPC/PTU/HDF5)
    │
    ▼ tttrlib.TTTR()
TTTRRef ──────────────────────────────────────────┐
    │                                              │
    ├─▶ tttrlib.TTTR.header() ─▶ NativeOutputRef   │
    │                          (JSON metadata)     │
    ├─▶ tttrlib.Correlator() ─▶ TableRef           │
    │                         (tau, correlation)   │
    ├─▶ tttrlib.TTTR.get_time_window_ranges()      │
    │   ─▶ TableRef (burst ranges)                 │
    │                                              │
    └─▶ tttrlib.CLSMImage() ─▶ ObjectRef ──────────┤
                               (CLSMImage)         │
                                   │               │
                                   ▼               │
                    tttrlib.CLSMImage.compute_ics()│
                                   │               │
                                   ▼               │
                             BioImageRef           │
                           (ICS correlation map)   │
                                                   │
    tttrlib.TTTR.write() ◀─────────────────────────┘
           │
           ▼
    TTTRRef (new file)
```
