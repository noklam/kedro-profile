# Kedro Profile

A Kedro plugin for profiling pipeline performance and saving results to CSV files.

## Features

- **Pipeline Performance Profiling**: Tracks node execution times, dataset loading/saving times, and counts
- **Rich Console Output**: Beautiful formatted tables when rich is installed
- **CSV Export**: Save profiling results to CSV files for further analysis
- **Configurable Paths**: Customize where CSV files are saved
- **Environment Support**: Works with different Kedro environments

## Installation

```bash
pip install kedro-profile
```

## Usage

### Basic Configuration

In your `settings.py`:

```python
from kedro_profile.hook import ProfileHook

HOOKS: tuple[ProfileHook] = (
    ProfileHook(
        save_file=True,  # Enable CSV file saving
        node_profile_path="data/08_reporting/node_profile.csv",
        dataset_profile_path="data/08_reporting/dataset_profile.csv",
    ),
)
```

### Configuration Options

- `save_file`: Boolean to enable/disable CSV file saving (default: False)
- `node_profile_path`: Path for node performance CSV file (default: "node_profile.csv")
- `dataset_profile_path`: Path for dataset performance CSV file (default: "dataset_profile.csv")
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

- Load/Save counts
- Loading/Saving times
- Total time calculations
- Sorted by total time (descending)

## Environment Variables

- `KEDRO_PROFILE_DISABLE=1`: Disable profiling
- `KEDRO_PROFILE_RICH=0`: Disable rich console output
