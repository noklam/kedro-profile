# kedro-profile

Identify the bottleneck of your Kedro Pipeline quickly with `kedro-profile`

## Example

1. When pipeline runs successfully, you will see something similar to this when running the plugin with spaceflight project:

```
==========Node Summary==========
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Execution Order ┃ Node Name                     ┃ Loading Time(s) ┃ Node Compute Time(s) ┃ Saving Time(s) ┃ Total Time(s) ┃ Total Time ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 3               │ create_model_input_table_node │ 0.02            │ 0.01                 │ 0.0            │          0.03 │ a moment   │
│ 1               │ preprocess_shuttles_node      │ 0.0             │ 0.0                  │ 0.01           │          0.01 │ a moment   │
│ 2               │ preprocess_companies_node     │ 0.0             │ 0.0                  │ 0.0            │          0.01 │ a moment   │
│ 4               │ summarize_fleet_node          │ 0.0             │ 0.01                 │ 0.0            │          0.01 │ a moment   │
├─────────────────┼───────────────────────────────┼─────────────────┼──────────────────────┼────────────────┼───────────────┼────────────┤
│                 │ TOTAL                         │ 0.02            │ 0.02                 │ 0.01           │          0.06 │ a moment   │
├─────────────────┼───────────────────────────────┼─────────────────┼──────────────────────┼────────────────┼───────────────┼────────────┤
│                 │ Time Elapsed                  │                 │                      │                │          1.18 │ a second   │
└─────────────────┴───────────────────────────────┴─────────────────┴──────────────────────┴────────────────┴───────────────┴────────────┘

==========Dataset Summary==========
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Dataset Name                            ┃ Loading Time(s) ┃ Load Count ┃ Saving Time(s) ┃ Save Count ┃ Total Time(s) ┃ Total Time ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ preprocessed_shuttles                   │ 0.02            │ 1          │ 0.01           │ 1          │          0.03 │ a moment   │
│ preprocessed_companies                  │ 0.0             │ 1          │ 0.0            │ 1          │          0.01 │ a moment   │
│ companies                               │ 0.0             │ 1          │ nan            │ 0          │          0.00 │ a moment   │
│ shuttles                                │ 0.0             │ 1          │ nan            │ 0          │          0.00 │ a moment   │
│ model_input_table                       │ 0.0             │ 1          │ 0.0            │ 1          │          0.00 │ a moment   │
│ fleet_summary                           │ nan             │ 0          │ 0.0            │ 1          │          0.00 │ a moment   │
│ params:reporting.min_passenger_capacity │ 0.0             │ 1          │ nan            │ 0          │          0.00 │ a moment   │
├─────────────────────────────────────────┼─────────────────┼────────────┼────────────────┼────────────┼───────────────┼────────────┤
│ TOTAL                                   │ 0.02            │ 6          │ 0.01           │ 4          │          0.04 │ a moment   │
├─────────────────────────────────────────┼─────────────────┼────────────┼────────────────┼────────────┼───────────────┼────────────┤
│ Time Elapsed                            │                 │            │                │            │          1.18 │ a second   │
└─────────────────────────────────────────┴─────────────────┴────────────┴────────────────┴────────────┴───────────────┴────────────┘
```

and the tables will be saved to `data/08_reporting/profiling/` directory by default.

2. When the pipeline fails, the table will not be printed to the console, but the partial tables for nodes and datasets that have been run will still be saved to `data/08_reporting/profiling/` directory with a timestamp in the filename.

# Requirements

```
kedro>=0.18.5 # Minimal version for hook specifications
pandas>=1.0.0
humanize>=4.0.0
```

# Get Started

If you do not have kedro installed already, install kedro with:
`pip install kedro`

Then create an example project with this command:
`kedro new --example=yes --tools=none --name kedro-profile-example`

If you are cloning the repository, the project is already created [here](kedro-profile-example/)

This will create a new directory`kedro-profile-example` in your current directory.

## Enable the Profiling Hook

You will find this line in `settings.py`, update it as follow:

```python
from kedro_profile.hook import ProfileHook

HOOKS: tuple[ProfileHook] = (
    ProfileHook(
        save_file=True,  # Enable CSV file saving
        node_profile_path="data/08_reporting/profiling/node_profile.csv",
        dataset_profile_path="data/08_reporting/profiling/dataset_profile.csv",
    ),
)
```

### Configuration Options

- `save_file`: Boolean to enable/disable CSV file saving (default: False)
- `node_profile_path`: Path for node performance CSV file (default: "data/08_reporting/profiling/node_profile_{time.strftime('%Y%m%d_%H%M%S')}.csv")
- `dataset_profile_path`: Path for dataset performance CSV file (default: "data/08_reporting/profiling/dataset_profile_{time.strftime('%Y%m%d_%H%M%S')}.csv")
- `env`: Environment filter (default: "local")

### Example Configurations

**Save to custom directory:**

```python
HOOKS: tuple[ProfileHook] = (
    ProfileHook(
        save_file=True,
        node_profile_path="reports/node_performance.csv",
        dataset_profile_path="reports/dataset_performance.csv",
    ),
)
```

**Disable CSV saving (console output only):**

```python
HOOKS: tuple[ProfileHook] = (
    ProfileHook(save_file=False),
)
```

## Output

The plugin generates two CSV files when `save_file=True`:

1. **Node Profile**: Contains node execution times and performance metrics
2. **Dataset Profile**: Contains dataset loading/saving times and access counts

Both files include:

- Execution order (Node Profile)
- Load/Save counts (Dataset Profile)
- Loading/Saving times and node compute times
- Total time calculations in seconds and human-readable `Total Time`
- `TOTAL` and `Time Elapsed` (wall-clock duration) summary rows in console output (useful with `ThreadRunner`)
- Sorted by total time (descending)

## Environment Variables

- `KEDRO_PROFILE_DISABLE=1`: Disable profiling
- `KEDRO_PROFILE_RICH=0`: Disable rich console output
