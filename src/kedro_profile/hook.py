from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import humanize
import pandas as pd
from kedro.framework.hooks import hook_impl
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Mapping

    from kedro.io import DataCatalog
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node

LOAD_COUNT = "Load Count"
SAVE_COUNT = "Save Count"
LOAD_TIME = "Loading Time(s)"
SAVE_TIME = "Saving Time(s)"
NODE_RUN_TIME = "Node Compute Time(s)"
TOTAL_TIME = "Total Time(s)"
EXECUTION_ORDER = "Execution Order"


@dataclass()
class ProfileHook:
    """Kedro hook for profiling pipeline execution performance.

    This hook tracks and profiles the execution time of nodes and datasets
    in a Kedro pipeline, providing detailed performance metrics including
    loading time, computation time, and saving time.

    Attributes:
        env: Environment(s) to run in. Can be a single environment or list.
        save_file: Whether to save profiling results to CSV files.
        node_profile_path: Path where node profiling CSV will be saved.
        dataset_profile_path: Path where dataset profiling CSV will be saved.
    """

    env: str | list[str] = "local"
    save_file: bool = False
    node_profile_path: str | Path = field(
        default_factory=lambda: f"node_profile_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    )
    dataset_profile_path: str | Path = field(
        default_factory=lambda: f"dataset_profile_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    )

    def __post_init__(self) -> None:
        """Initialize profiling hook after dataclass initialization.

        Sets up internal state for profiling including:
        - Rich output formatting configuration
        - Enable/disable state based on environment variables
        - Per-key timing records for nodes and datasets
        - Pipeline start time tracking
        """
        if os.environ.get("KEDRO_PROFILE_RICH") == "0":
            self.rich_enabled = False
        else:
            self.rich_enabled = True

        if os.environ.get("KEDRO_PROFILE_DISABLE") == "1":
            self.disable = True
        else:
            self.disable = False

        self._reset_run_state()

    def _reset_run_state(self) -> None:
        """Clear all timing records so a new run starts fresh.

        Every record is stored under its own key and written by one thread
        only (a node runs once, in one thread), so no lock is needed. Totals
        are computed once at the end of the run in ``_collect_profiles``.
        """
        # node name -> epoch start time, and node name -> compute seconds
        self._node_starts: dict[str, float] = {}
        self._node_durations: dict[str, float] = {}
        # (dataset name, node name) -> epoch start time / seconds
        self._load_starts: dict[tuple[str, str], float] = {}
        self._load_durations: dict[tuple[str, str], float] = {}
        self._save_starts: dict[tuple[str, str], float] = {}
        self._save_durations: dict[tuple[str, str], float] = {}

        self._pipeline_start: float = time.time()

    def __hash__(self) -> int:
        """Return hash of the ProfileHook instance.

        Returns:
            Hash value based on instance id (dataclass has no hash method by default).
        """
        return id(self)

    def _save_to_csv(self, df: pd.DataFrame, file_path: str | Path) -> None:
        """Save DataFrame to CSV file, without the console-only Total Time text.

        Args:
            df: DataFrame containing profiling data to save.
            file_path: Path where CSV file should be saved.
        """
        try:
            # Ensure the directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            df.drop(columns=["Total Time"], errors="ignore").to_csv(
                file_path, index=False
            )
        except Exception as e:
            print(f"Failed to save profile data to {file_path}: {e}")

    def _print_path_saved(self, file_path: str | Path) -> None:
        """Print message indicating where profile data was saved.

        Args:
            file_path: Path where the profile data was saved.
        """
        print(f"Profile data saved to: {file_path}")

    def _collect_profiles(
        self,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Compute node and dataset profiles from the per-key timing records.

        Runs once at the end of a run (or when saving partial results), so it
        is the only place that sums durations or counts loads and saves.

        Returns:
            Tuple of (node profile, dataset profile) dictionaries keyed by name.
        """
        node_profile: dict[str, dict[str, Any]] = {}
        dataset_profile: dict[str, dict[str, Any]] = {}

        # list() snapshots the dicts: other threads may still be writing
        by_start = sorted(list(self._node_starts.items()), key=lambda item: item[1])
        for order, (node_name, _) in enumerate(by_start, start=1):
            node_profile[node_name] = {
                EXECUTION_ORDER: order,
                NODE_RUN_TIME: self._node_durations.get(node_name, float("nan")),
            }

        for durations, time_col, count_col in (
            (list(self._load_durations.items()), LOAD_TIME, LOAD_COUNT),
            (list(self._save_durations.items()), SAVE_TIME, SAVE_COUNT),
        ):
            for (dataset_name, node_name), duration in durations:
                for profile, name in (
                    (dataset_profile, dataset_name),
                    (node_profile, node_name),
                ):
                    entry = profile.setdefault(name, {})
                    entry[time_col] = entry.get(time_col, 0) + duration
                dataset_entry = dataset_profile[dataset_name]
                dataset_entry[count_col] = dataset_entry.get(count_col, 0) + 1

        return node_profile, dataset_profile

    def save_partial_results(self) -> None:
        """Save partial results to CSV files.

        This method is useful when pipelines fail, allowing you to save
        whatever profiling data has been collected up to the point of failure.
        """
        if self.disable or not self.save_file:
            return

        self._total_time = time.time() - self._pipeline_start

        # Build DataFrames for both node and dataset profiles
        node_profile, dataset_profile = self._collect_profiles()
        node_df = _build_node_table(node_profile, index_name="Node Name")
        dataset_df = _build_dataset_table(dataset_profile, index_name="Dataset Name")

        # Save to CSV files
        self._save_to_csv(node_df, self.node_profile_path)
        self._save_to_csv(dataset_df, self.dataset_profile_path)

        print("Partial profiling results saved due to pipeline failure.")

    # Node Profile
    @hook_impl
    def before_node_run(
        self, node: Node, catalog: DataCatalog, inputs: dict[str, Any]
    ) -> None:
        """Track node execution start time.

        Args:
            node: The Kedro node about to be executed.
            catalog: The data catalog containing datasets.
            inputs: Dictionary of input datasets for the node.
        """
        if self.disable:
            return

        self._node_starts[node.name] = time.time()

    @hook_impl
    def after_node_run(
        self, node: Node, catalog: DataCatalog, inputs: dict[str, Any]
    ) -> None:
        """Calculate node execution time after node completes.

        Args:
            node: The Kedro node that just finished executing.
            catalog: The data catalog containing datasets.
            inputs: Dictionary of input datasets for the node.
        """
        if self.disable:
            return
        self._node_durations[node.name] = time.time() - self._node_starts[node.name]

    @hook_impl
    def on_node_error(
        self,
        error: Exception,
        node: Node,
        catalog: DataCatalog,
        inputs: dict[str, Any],
        is_async: bool,
    ) -> None:
        """Handle node errors and save partial results.

        Args:
            error: The exception that was raised.
            node: The Kedro node that encountered an error.
            catalog: The data catalog containing datasets.
            inputs: Dictionary of input datasets for the node.
            is_async: Whether the node was running asynchronously.
        """
        if self.disable:
            return

        # Save partial results when a node fails
        self.save_partial_results()

    # Dataset profile
    @hook_impl
    def before_dataset_loaded(self, dataset_name: str, node: Node) -> None:
        """Track dataset loading start time.

        Args:
            dataset_name: Name of the dataset being loaded.
            node: The Kedro node loading the dataset.
        """
        if self.disable:
            return
        self._load_starts[(dataset_name, node.name)] = time.time()

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, node: Node) -> None:
        """Record the dataset loading time under its own key.

        Args:
            dataset_name: Name of the dataset that was loaded.
            node: The Kedro node that loaded the dataset.
        """
        if self.disable:
            return
        key = (dataset_name, node.name)
        self._load_durations[key] = time.time() - self._load_starts[key]

    @hook_impl
    def before_dataset_saved(self, dataset_name: str, node: Node) -> None:
        """Track dataset saving start time.

        Args:
            dataset_name: Name of the dataset being saved.
            node: The Kedro node saving the dataset.
        """
        if self.disable:
            return
        self._save_starts[(dataset_name, node.name)] = time.time()

    @hook_impl
    def after_dataset_saved(self, dataset_name: str, node: Node) -> None:
        """Record the dataset saving time under its own key.

        Args:
            dataset_name: Name of the dataset that was saved.
            node: The Kedro node that saved the dataset.
        """
        if self.disable:
            return
        key = (dataset_name, node.name)
        self._save_durations[key] = time.time() - self._save_starts[key]

    @hook_impl
    def before_pipeline_run(
        self,
        run_params: dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:
        """Initialize profiling at the start of pipeline execution.

        Args:
            run_params: Parameters passed to the pipeline run.
            pipeline: The Kedro pipeline being executed.
            catalog: The data catalog containing datasets.
        """
        if self.disable:
            return
        self._reset_run_state()
        self.run_env = run_params.get("env") if run_params.get("env") else "local"

    @hook_impl
    def on_pipeline_error(
        self,
        error: Exception,
        run_params: dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:
        """Handle pipeline errors and save partial results.

        Args:
            error: The exception that caused the pipeline to fail.
            run_params: Parameters passed to the pipeline run.
            pipeline: The Kedro pipeline that encountered an error.
            catalog: The data catalog containing datasets.
        """
        if self.disable:
            return

        print(f"Pipeline failed with error: {error}")
        # Save partial results when the entire pipeline fails
        self.save_partial_results()

    @hook_impl
    def after_pipeline_run(
        self,
        run_params: dict[str, Any],
        run_result: dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:
        """Generate and display profiling results after pipeline completes.

        Args:
            run_params: Parameters passed to the pipeline run.
            run_result: Results from the pipeline execution.
            pipeline: The Kedro pipeline that was executed.
            catalog: The data catalog containing datasets.
        """
        if self.disable:
            return

        self._total_time = time.time() - self._pipeline_start

        # Build DataFrames for both node and dataset profiles
        node_profile, dataset_profile = self._collect_profiles()
        node_df = _build_node_table(node_profile, index_name="Node Name")
        dataset_df = _build_dataset_table(dataset_profile, index_name="Dataset Name")

        # Save to CSV files if enabled
        if self.save_file:
            self._save_to_csv(node_df, self.node_profile_path)
            self._save_to_csv(dataset_df, self.dataset_profile_path)

        # Add total row for display tables
        node_df_display = _add_total_row(node_df.copy(), "Node Name")
        node_df_display = _add_wall_clock_row(
            node_df_display, "Node Name", self._total_time
        )
        dataset_df_display = _add_total_row(dataset_df.copy(), "Dataset Name")
        dataset_df_display = _add_wall_clock_row(
            dataset_df_display, "Dataset Name", self._total_time
        )

        # Display results
        if self.rich_enabled:
            print()
            print("=" * 10 + "Node Summary" + "=" * 10)
            node_summary = dataframe_to_rich_table(node_df_display)
            print_rich_table_to_console(node_summary)
            if self.save_file:
                self._print_path_saved(file_path=self.node_profile_path)

            print()
            print("=" * 10 + "Dataset Summary" + "=" * 10)
            dataset_summary = dataframe_to_rich_table(dataset_df_display)
            print_rich_table_to_console(dataset_summary)
            if self.save_file:
                self._print_path_saved(file_path=self.dataset_profile_path)

        else:
            print("Node Profile:")
            print(node_df_display)
            if self.save_file:
                self._print_path_saved(file_path=self.node_profile_path)

            print("\nDataset Profile:")
            print(dataset_df_display)
            if self.save_file:
                self._print_path_saved(file_path=self.dataset_profile_path)


# Format Table
def dataframe_to_rich_table(df: pd.DataFrame) -> Table:
    """Convert a pandas DataFrame to a Rich Table for console display.

    Automatically detects summary rows ("TOTAL" and
    "TOTAL Wall Clock") and adds a separator line before them for
    better visual distinction. Numeric columns are formatted with
    thousands separators and aligned on decimal places.

    Args:
        df: Pandas DataFrame to convert to a Rich table.

    Returns:
        Rich Table object ready for console printing.
    """
    table = Table(show_header=True, header_style="bold magenta")

    # Create a copy to avoid modifying the original DataFrame
    df_formatted = df.copy()

    # Format numeric columns with thousands separators and consistent decimal places
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            # Check if column is integer type
            is_integer_col = pd.api.types.is_integer_dtype(df[col])

            if is_integer_col:
                # Format integers with thousands separators, no decimal places
                df_formatted[col] = df_formatted[col].apply(
                    lambda x: f"{int(x):,}" if pd.notna(x) else ""
                )
            else:
                # Format floats with thousands separators and 2 decimal places
                df_formatted[col] = df_formatted[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) else ""
                )
            # Add column with right alignment for numeric columns
            table.add_column(col, justify="right")
        else:
            # Add column with left alignment for non-numeric columns
            table.add_column(col, justify="left")

    # Add rows
    rows = list(df_formatted.iterrows())
    for idx, (_, row) in enumerate(rows):
        is_total_row = any(str(cell) in ("TOTAL", "Time Elapsed") for cell in row)

        # Add separator before total rows
        if is_total_row and idx > 0:
            table.add_section()

        table.add_row(*[str(cell) for cell in row])

    return table


def print_rich_table_to_console(rich_table: Table) -> None:
    """Print a Rich Table to the console.

    Args:
        rich_table: Rich Table object to print.
    """
    console = Console()
    console.print(rich_table)


def _build_profile_table(
    dictionary: Mapping[str, dict[str, Any]],
    index_name: str,
    time_cols: list[str],
) -> pd.DataFrame:
    """Build a sorted, rounded profiling DataFrame from raw timing metrics."""
    df = pd.DataFrame.from_dict(dict(dictionary), orient="index")
    for col in time_cols:
        if col not in df.columns:
            df[col] = 0.0
    df[TOTAL_TIME] = df[time_cols].sum(axis=1, skipna=True)
    df["Total Time"] = df[TOTAL_TIME].apply(
        lambda x: humanize.naturaldelta(x, minimum_unit="seconds")
    )
    return (
        df.reset_index(names=index_name)
        .sort_values(TOTAL_TIME, ascending=False)
        .round(2)
    )


def _build_node_table(
    dictionary: Mapping[str, dict[str, Any]], index_name: str
) -> pd.DataFrame:
    """Build a formatted DataFrame from node profiling data."""
    df = _build_profile_table(
        dictionary=dictionary,
        index_name=index_name,
        time_cols=[LOAD_TIME, NODE_RUN_TIME, SAVE_TIME],
    )
    if EXECUTION_ORDER not in df.columns:
        df[EXECUTION_ORDER] = 0
    df[EXECUTION_ORDER] = df[EXECUTION_ORDER].fillna(0).astype("Int64")
    return df[
        [
            "Execution Order",
            "Node Name",
            "Loading Time(s)",
            "Node Compute Time(s)",
            "Saving Time(s)",
            "Total Time(s)",
            "Total Time",
        ]
    ]


def _build_dataset_table(
    dictionary: Mapping[str, dict[str, Any]], index_name: str
) -> pd.DataFrame:
    """Build a formatted DataFrame from dataset profiling data."""
    df = _build_profile_table(
        dictionary=dictionary,
        index_name=index_name,
        time_cols=[LOAD_TIME, SAVE_TIME],
    )
    if LOAD_COUNT in df.columns:
        df[LOAD_COUNT] = df[LOAD_COUNT].fillna(0).astype("Int64")
    if SAVE_COUNT in df.columns:
        df[SAVE_COUNT] = df[SAVE_COUNT].fillna(0).astype("Int64")
    return df


def _append_summary_row(
    df: pd.DataFrame,
    index_col_name: str,
    label: str,
    col_value_fn: Any,
) -> pd.DataFrame:
    """
    Append a single summary row to a profiling DataFrame.

    Iterates over columns, calling col_value_fn to determine each cell's
    value. Handles the empty-df guard and concat boilerplate in one place.

    Args:
        df: DataFrame containing profiling data.
        index_col_name: Name of the index column (receives the label).
        label: Text placed in the index column (e.g. "TOTAL").
        col_value_fn: Callable(col, df) -> value for each non-index column;
            None leaves the cell empty (NaN) so numeric columns stay numeric.

    Returns:
        New DataFrame with the summary row appended.
    """
    if df.empty:
        return df

    row: dict[str, Any] = {index_col_name: label}
    for col in df.columns:
        if col == index_col_name:
            continue
        row[col] = col_value_fn(col, df)

    row_df = pd.DataFrame([row], columns=df.columns)
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            row_df[col] = row_df[col].astype(df[col].dtype)
    return pd.concat([df, row_df], ignore_index=True)


def _add_total_row(df: pd.DataFrame, index_col_name: str) -> pd.DataFrame:
    """
    Add a total row summing all numeric columns.

    Creates a summary row labeled "TOTAL (sum of nodes)" that aggregates
    numeric values across all rows. Special handling for execution order
    (left empty) and human-readable time fields.

    Args:
        df: DataFrame containing profiling data.
        index_col_name: Name of the index column.

    Returns:
        New DataFrame with a total row appended at the end.
    """

    def _col_value(col: str, source_df: pd.DataFrame) -> Any:
        if col == EXECUTION_ORDER:
            return None
        if col == "Total Time":
            if TOTAL_TIME in source_df.columns:
                total_seconds = source_df[TOTAL_TIME].sum()
                return humanize.naturaldelta(total_seconds, minimum_unit="seconds")
            return None
        if pd.api.types.is_numeric_dtype(source_df[col]):
            return round(source_df[col].sum(), 2)
        return None

    return _append_summary_row(df, index_col_name, "TOTAL", _col_value)


def _add_wall_clock_row(
    df: pd.DataFrame, index_col_name: str, wall_clock_seconds: float
) -> pd.DataFrame:
    """
    Add a wall clock row showing actual elapsed pipeline time.

    When using ThreadRunner, nodes run concurrently so the sum of individual
    node times exceeds the actual wall-clock duration. This row shows the
    real elapsed time, making the parallelism benefit visible.

    Args:
        df: DataFrame with profiling data (should already have a TOTAL row).
        index_col_name: Name of the index column.
        wall_clock_seconds: Actual elapsed time in seconds.

    Returns:
        DataFrame with a wall clock row appended after the total row.
    """

    def _col_value(col: str, _source_df: pd.DataFrame) -> Any:
        if col == TOTAL_TIME:
            return round(wall_clock_seconds, 2)
        if col == "Total Time":
            return humanize.naturaldelta(wall_clock_seconds, minimum_unit="seconds")
        return None

    return _append_summary_row(df, index_col_name, "Time Elapsed", _col_value)
