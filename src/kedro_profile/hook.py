import importlib
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


import pandas as pd
import time
from kedro.framework.hooks import hook_impl

LOAD_COUNT = "load_count"
SAVE_COUNT = "save_count"
LOAD_TIME = "load_time"
SAVE_TIME = "save_time"
NODE_RUN_TIME = "Node Compute Time"


@dataclass()
class ProfileHook:
    env: str | list[str] = "local"
    save_file: bool = False
    save_path: str | Path = "kedro_pipeline_profile.csv"

    def __post_init__(self):
        if os.environ.get("KEDRO_PROFILE_RICH") == "0":
            self.rich_enabled = False
        # Rich not installed
        elif importlib.import_module("rich"):
            self.rich_enabled = True
        else:
            self.rich_enabled = False

        if os.environ.get("KEDRO_PROFILE_DISABLE") == "1":
            self.disable = True
        else:
            self.disable = False

        self._dataset_profile = defaultdict(lambda: {})
        self._node_profile = defaultdict(lambda: {})

        self._pipeline_start = time.time()

    def __hash__(self):
        # dataclass has not hash method by default
        return id(self)

    # Node Profile
    @hook_impl
    def before_node_run(self, node, catalog, inputs):
        if self.disable:
            return

        self._node_profile[node.name][NODE_RUN_TIME] = time.time()

    @hook_impl
    def after_node_run(self, node, catalog, inputs):
        if self.disable:
            return
        self._node_profile[node.name][NODE_RUN_TIME] = (
            time.time() - self._node_profile[node.name][NODE_RUN_TIME]
        )
        print("=======" * 20)
        print("node_run")

    # Dataset profile
    @hook_impl
    def before_dataset_loaded(self, dataset_name: str, node):
        curr = time.time()
        self._dataset_profile[dataset_name][LOAD_TIME] = curr
        self._node_profile[node.name][LOAD_TIME] = curr

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, node):
        self._dataset_profile[dataset_name][LOAD_TIME] = (
            time.time() - self._dataset_profile[dataset_name][LOAD_TIME]
        )
        self._node_profile[node.name][LOAD_TIME] = (
            time.time() - self._node_profile[node.name][LOAD_TIME]
        )
        self._dataset_profile[dataset_name][LOAD_COUNT] = (
            self._dataset_profile[dataset_name].get(LOAD_COUNT, 0) + 1
        )

    @hook_impl
    def before_dataset_saved(self, dataset_name: str, node):
        curr = time.time()
        self._dataset_profile[dataset_name][SAVE_TIME] = curr
        self._node_profile[node.name][SAVE_TIME] = curr

    @hook_impl
    def after_dataset_saved(self, dataset_name: str, node):
        self._dataset_profile[dataset_name][SAVE_TIME] = (
            time.time() - self._dataset_profile[dataset_name][SAVE_TIME]
        )
        self._node_profile[node.name][SAVE_TIME] = (
            time.time() - self._node_profile[node.name][SAVE_TIME]
        )
        self._dataset_profile[dataset_name][SAVE_COUNT] = (
            self._dataset_profile[dataset_name].get(SAVE_COUNT, 0) + 1
        )

    @hook_impl
    def before_pipeline_run(self, run_params, pipeline, catalog):
        if self.disable:
            return
        self.run_env = run_params.get("env") if run_params.get("env") else "local"

    @hook_impl
    def after_pipeline_run(self, run_params, run_result, pipeline, catalog):
        if self.disable:
            return

        self._total_time = time.time() - self._pipeline_start

        if self.rich_enabled:
            self._node_profile = dict_to_df(self._node_profile, index_name="Node Name")
            self._dataset_profile = dict_to_df(
                self._dataset_profile, index_name="Dataset Name"
            )
            node_summary = dataframe_to_rich_table(self._node_profile)
            print_rich_table_to_console(node_summary)
            dataset_summary = dataframe_to_rich_table(
                self._dataset_profile,
            )
            print_rich_table_to_console(dataset_summary)
        else:
            print(self._dataset_profile)


# Format Table
# Function to convert DataFrame to Rich table
def dataframe_to_rich_table(df: pd.DataFrame):
    from rich.table import Table

    table = Table(show_header=True, header_style="bold magenta")

    # Add columns
    for col in df.columns:
        table.add_column(col)

    # Add rows
    for _, row in df.iterrows():
        table.add_row(*[str(cell) for cell in row])

    return table


def print_rich_table_to_console(rich_table) -> None:
    from rich.console import Console

    console = Console()
    console.print(rich_table)


def dict_to_df(dictionary, index_name):
    df = pd.DataFrame.from_dict(dictionary, orient="index").reset_index(
        names=index_name
    )
    return df
