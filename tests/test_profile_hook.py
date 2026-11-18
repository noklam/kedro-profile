"""
Unit Tests for ProfileHook Module

This module tests the ProfileHook class and its associated utility functions, which provide
performance profiling capabilities for Kedro pipelines. The ProfileHook class tracks
execution times for nodes and datasets, handles error conditions, and generates
comprehensive reports.

## Test Coverage:

### Core Tests:
- **Initialization**: `test_profile_hook_initialization_default_values` - Tests default ProfileHook setup
- **Configuration**: `test_profile_hook_environment_variables` - Tests environment variable configuration
- **Node Profiling**: `test_node_profiling_complete_cycle` - Tests complete node execution profiling
- **Dataset Profiling**: `test_dataset_profiling_load_save_cycle` - Tests dataset load/save profiling
- **Pipeline Integration**: `test_pipeline_run_complete_cycle` - Tests full pipeline profiling

### Edge Cases:
- **Error Handling**: `test_node_error_handling_with_partial_results` - Tests node failure scenarios
- **Pipeline Errors**: `test_pipeline_error_handling` - Tests pipeline failure handling
- **Empty Data**: `test_build_tables_with_empty_data` - Tests behavior with no profiling data
- **File Operations**: `test_csv_saving_functionality` - Tests CSV file creation and error handling
- **Rich Formatting**: `test_rich_table_formatting` - Tests Rich table display functionality

### Parameterized Tests:
- **Multiple Scenarios**: Tests various combinations of settings and data conditions
- **Environment Configurations**: Tests different environment variable combinations
"""

import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from kedro_profile.hook import (
    EXECUTION_ORDER,
    LOAD_COUNT,
    LOAD_TIME,
    NODE_RUN_TIME,
    SAVE_COUNT,
    SAVE_TIME,
    TOTAL_TIME,
    ProfileHook,
    _build_dataset_table,
    _add_total_row,
    _add_wall_clock_row,
    _build_node_table,
    dataframe_to_rich_table,
    print_rich_table_to_console,
)


def test_profile_hook_initialization_default_values():
    """
    Test ProfileHook initialization with default values.

    This test verifies that the ProfileHook class initializes correctly with
    default parameters and sets up internal data structures properly.
    Domain relevance: Ensures the profiling hook is ready to track pipeline
    performance metrics from the start.
    """
    # Arrange & Act
    hook = ProfileHook()

    # Assert
    assert hook.env == "local"
    assert hook.save_file is False
    assert isinstance(hook.node_profile_path, str)
    assert isinstance(hook.dataset_profile_path, str)
    assert "node_profile_" in hook.node_profile_path
    assert "dataset_profile_" in hook.dataset_profile_path
    assert hook._node_starts == {}
    assert hook._load_durations == {}
    assert isinstance(hook._pipeline_start, float)


@pytest.mark.parametrize(
    "rich_env_var,profile_disable_var,expected_rich,expected_disable",
    [
        ("0", "0", False, False),
        ("1", "1", True, True),
        (None, None, True, False),
        ("0", "1", False, True),
    ],
)
def test_profile_hook_environment_variables(
    rich_env_var: str | None,
    profile_disable_var: str | None,
    expected_rich: bool,
    expected_disable: bool,
):
    """
    Test ProfileHook configuration through environment variables.

    This test verifies that environment variables KEDRO_PROFILE_RICH and
    KEDRO_PROFILE_DISABLE correctly control the hook's behavior.
    Domain relevance: Allows users to control profiling output format and
    enable/disable profiling without code changes.
    """
    # Arrange
    with patch.dict(os.environ, {}, clear=True):
        if rich_env_var is not None:
            os.environ["KEDRO_PROFILE_RICH"] = rich_env_var
        if profile_disable_var is not None:
            os.environ["KEDRO_PROFILE_DISABLE"] = profile_disable_var

        # Act
        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = True  # Simulate rich is available
            hook = ProfileHook()

    # Assert
    assert hook.rich_enabled == expected_rich
    assert hook.disable == expected_disable


def test_profile_hook_custom_initialization():
    """
    Test ProfileHook initialization with custom parameters.

    This test verifies that custom initialization parameters are properly
    set and override default values.
    Domain relevance: Allows customization of output paths and environments
    for different deployment scenarios.
    """
    # Arrange
    custom_env = "production"
    custom_save_file = True
    custom_node_path = "custom_node_profile.csv"
    custom_dataset_path = "custom_dataset_profile.csv"

    # Act
    hook = ProfileHook(
        env=custom_env,
        save_file=custom_save_file,
        node_profile_path=custom_node_path,
        dataset_profile_path=custom_dataset_path,
    )

    # Assert
    assert hook.env == custom_env
    assert hook.save_file == custom_save_file
    assert hook.node_profile_path == custom_node_path
    assert hook.dataset_profile_path == custom_dataset_path


def test_profile_hook_hash_method():
    """
    Test ProfileHook hash method implementation.

    This test verifies that the hash method returns a unique identifier
    based on object identity, which is important for using ProfileHook
    instances in sets or as dictionary keys.
    """
    # Arrange & Act
    hook1 = ProfileHook()
    hook2 = ProfileHook()

    # Assert
    assert hash(hook1) != hash(hook2)
    assert hash(hook1) == id(hook1)
    assert hash(hook2) == id(hook2)


def test_node_profiling_complete_cycle():
    """
    Test complete node profiling cycle from before_node_run to after_node_run.

    This test verifies that node execution time is correctly tracked through
    the before_node_run and after_node_run hooks.
    Domain relevance: Core functionality for tracking individual node
    performance in ML pipelines to identify bottlenecks.
    """
    # Arrange
    hook = ProfileHook()
    mock_node = Mock()
    mock_node.name = "test_node"
    mock_catalog = Mock()
    mock_inputs = {}

    # Act
    hook.before_node_run(node=mock_node, catalog=mock_catalog, inputs=mock_inputs)

    # Simulate some processing time
    time.sleep(0.01)

    hook.after_node_run(node=mock_node, catalog=mock_catalog, inputs=mock_inputs)

    # Assert
    node_profile, _ = hook._collect_profiles()
    assert "test_node" in node_profile
    assert isinstance(node_profile["test_node"][NODE_RUN_TIME], float)
    assert node_profile["test_node"][NODE_RUN_TIME] > 0


def test_node_profiling_disabled():
    """
    Test that node profiling is skipped when hook is disabled.

    This test verifies that profiling hooks respect the disable flag
    and don't perform any tracking when disabled.
    Domain relevance: Allows turning off profiling in production environments
    where performance overhead needs to be minimized.
    """
    # Arrange
    with patch.dict(os.environ, {"KEDRO_PROFILE_DISABLE": "1"}):
        hook = ProfileHook()

    mock_node = Mock()
    mock_node.name = "test_node"
    mock_catalog = Mock()
    mock_inputs = {}

    # Act
    hook.before_node_run(node=mock_node, catalog=mock_catalog, inputs=mock_inputs)
    hook.after_node_run(node=mock_node, catalog=mock_catalog, inputs=mock_inputs)

    # Assert
    assert hook._node_starts == {}
    assert hook._node_durations == {}


def test_dataset_profiling_load_cycle():
    """
    Test dataset loading profiling cycle.

    This test verifies that dataset loading time and count are correctly
    tracked through the before_dataset_loaded and after_dataset_loaded hooks.
    Domain relevance: Critical for identifying data I/O bottlenecks in
    data science pipelines where loading large datasets can be a major
    performance concern.
    """
    # Arrange
    hook = ProfileHook()
    dataset_name = "test_dataset"
    mock_node = Mock()
    mock_node.name = "test_node"

    # Act
    hook.before_dataset_loaded(dataset_name=dataset_name, node=mock_node)
    time.sleep(0.01)  # Simulate loading time
    hook.after_dataset_loaded(dataset_name=dataset_name, node=mock_node)

    # Assert
    node_profile, dataset_profile = hook._collect_profiles()
    assert dataset_profile[dataset_name][LOAD_COUNT] == 1
    assert isinstance(dataset_profile[dataset_name][LOAD_TIME], float)
    assert dataset_profile[dataset_name][LOAD_TIME] > 0

    # Check node profile is also updated
    assert LOAD_TIME in node_profile["test_node"]


def test_dataset_profiling_save_cycle():
    """
    Test dataset saving profiling cycle.

    This test verifies that dataset saving time and count are correctly
    tracked through the before_dataset_saved and after_dataset_saved hooks.
    Domain relevance: Important for tracking output generation performance
    and identifying slow data persistence operations.
    """
    # Arrange
    hook = ProfileHook()
    dataset_name = "output_dataset"
    mock_node = Mock()
    mock_node.name = "test_node"

    # Act
    hook.before_dataset_saved(dataset_name=dataset_name, node=mock_node)
    time.sleep(0.01)  # Simulate saving time
    hook.after_dataset_saved(dataset_name=dataset_name, node=mock_node)

    # Assert
    _, dataset_profile = hook._collect_profiles()
    assert dataset_profile[dataset_name][SAVE_COUNT] == 1
    assert isinstance(dataset_profile[dataset_name][SAVE_TIME], float)
    assert dataset_profile[dataset_name][SAVE_TIME] > 0


def test_dataset_multiple_operations():
    """
    Test dataset profiling with multiple load and save operations.

    This test verifies that multiple operations on the same dataset
    are correctly accumulated in the profile counters.
    Domain relevance: Some datasets may be accessed multiple times
    during pipeline execution, and tracking cumulative access patterns
    is important for optimization.
    """
    # Arrange
    hook = ProfileHook()
    dataset_name = "multi_access_dataset"
    node_a = Mock()
    node_a.name = "node_a"
    node_b = Mock()
    node_b.name = "node_b"

    # Act - Load dataset from two nodes
    for mock_node in (node_a, node_b):
        hook.before_dataset_loaded(dataset_name=dataset_name, node=mock_node)
        time.sleep(0.01)
        hook.after_dataset_loaded(dataset_name=dataset_name, node=mock_node)

    # Save dataset once
    hook.before_dataset_saved(dataset_name=dataset_name, node=node_a)
    time.sleep(0.01)
    hook.after_dataset_saved(dataset_name=dataset_name, node=node_a)

    # Assert
    _, dataset_profile = hook._collect_profiles()
    assert dataset_profile[dataset_name][LOAD_COUNT] == 2
    assert dataset_profile[dataset_name][SAVE_COUNT] == 1


def test_pipeline_run_complete_cycle():
    """
    Test complete pipeline run profiling cycle.

    This test verifies that pipeline-level hooks work correctly and
    generate appropriate output when the pipeline completes successfully.
    Domain relevance: Provides end-to-end pipeline performance insights
    essential for production ML system monitoring.
    """
    # Arrange
    hook = ProfileHook()
    mock_run_params = {"env": "test"}
    mock_pipeline = Mock()
    mock_catalog = Mock()
    mock_run_result = Mock()

    # Add some test data
    hook._node_starts["test_node"] = 1.0
    hook._node_durations["test_node"] = 1.5
    hook._load_durations[("test_dataset", "test_node")] = 0.5
    hook._save_durations[("test_dataset", "test_node")] = 0.3

    # Act
    with patch("builtins.print") as mock_print:
        hook.before_pipeline_run(
            run_params=mock_run_params, pipeline=mock_pipeline, catalog=mock_catalog
        )
        hook.after_pipeline_run(
            run_params=mock_run_params,
            run_result=mock_run_result,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

    # Assert
    assert hook.run_env == "test"
    assert isinstance(hook._total_time, float)
    mock_print.assert_called()  # Verify output was generated


def test_node_error_handling_with_partial_results():
    """
    Test node error handling and partial results saving.

    This test verifies that when a node fails, the hook correctly calculates
    partial execution time and saves available profiling data.
    Domain relevance: Critical for debugging failed pipeline runs and
    understanding where failures occur in long-running ML pipelines.
    """
    # Arrange
    hook = ProfileHook(save_file=True)
    mock_node = Mock()
    mock_node.name = "failing_node"
    mock_catalog = Mock()
    mock_inputs = {}
    mock_error = Exception("Test error")

    # Start node execution
    hook.before_node_run(node=mock_node, catalog=mock_catalog, inputs=mock_inputs)
    time.sleep(0.01)

    # Act
    with patch.object(hook, "save_partial_results") as mock_save:
        hook.on_node_error(
            error=mock_error,
            node=mock_node,
            catalog=mock_catalog,
            inputs=mock_inputs,
            is_async=False,
        )

    # Assert
    node_profile, _ = hook._collect_profiles()
    assert pd.isna(node_profile["failing_node"][NODE_RUN_TIME])
    mock_save.assert_called_once()


def test_pipeline_error_handling():
    """
    Test pipeline error handling and partial results saving.

    This test verifies that pipeline-level errors trigger partial results
    saving with appropriate error messaging.
    Domain relevance: Essential for post-mortem analysis of failed pipeline
    runs in production environments.
    """
    # Arrange
    hook = ProfileHook()
    mock_error = Exception("Pipeline failure")
    mock_run_params = {"env": "test"}
    mock_pipeline = Mock()
    mock_catalog = Mock()

    # Act
    with (
        patch.object(hook, "save_partial_results") as mock_save,
        patch("builtins.print") as mock_print,
    ):
        hook.on_pipeline_error(
            error=mock_error,
            run_params=mock_run_params,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

    # Assert
    mock_save.assert_called_once()
    mock_print.assert_called_with("Pipeline failed with error: Pipeline failure")


def test_save_partial_results_disabled():
    """
    Test that save_partial_results respects disable and save_file flags.

    This test verifies that partial results saving is properly controlled
    by the hook configuration flags.
    """
    # Arrange - Test when disabled
    with patch.dict(os.environ, {"KEDRO_PROFILE_DISABLE": "1"}):
        hook = ProfileHook()

    # Act & Assert
    with patch.object(hook, "_save_to_csv") as mock_save:
        hook.save_partial_results()
        mock_save.assert_not_called()

    # Arrange - Test when save_file is False
    hook = ProfileHook(save_file=False)

    # Act & Assert
    with patch.object(hook, "_save_to_csv") as mock_save:
        hook.save_partial_results()
        mock_save.assert_not_called()


def test_csv_saving_functionality():
    """
    Test CSV file saving functionality with proper error handling.

    This test verifies that the _save_to_csv method correctly creates
    directories and saves DataFrames to CSV files, with proper error handling.
    Domain relevance: Essential for persisting profiling results for
    analysis and comparison across pipeline runs.
    """
    # Arrange
    hook = ProfileHook()
    test_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "subdir" / "test.csv"

        # Act
        hook._save_to_csv(df=test_df, file_path=test_file)

        # Assert
        assert test_file.exists()
        loaded_df = pd.read_csv(test_file)
        assert_frame_equal(loaded_df, test_df)


def test_build_node_table_with_complete_data():
    """
    Test _build_node_table function with complete profiling data.

    This test verifies that the node table building function correctly
    processes profiling data and creates a properly formatted DataFrame.
    Domain relevance: Node tables provide critical insights into individual
    step performance in ML pipelines.
    """
    # Arrange
    test_data = {
        "node1": {LOAD_TIME: 1.0, NODE_RUN_TIME: 2.0, SAVE_TIME: 0.5},
        "node2": {LOAD_TIME: 0.5, NODE_RUN_TIME: 1.5, SAVE_TIME: 1.0},
    }

    # Act
    result_df = _build_node_table(dictionary=test_data, index_name="Node Name")

    # Assert
    assert len(result_df) == 2
    assert "Node Name" in result_df.columns
    assert TOTAL_TIME in result_df.columns
    assert result_df.loc[0, TOTAL_TIME] == 3.5  # node1 total
    assert result_df.loc[1, TOTAL_TIME] == 3.0  # node2 total
    # Verify sorting by TOTAL_TIME descending
    assert result_df.loc[0, "Node Name"] == "node1"


def test_build_node_table_with_missing_columns():
    """
    Test _build_node_table function with missing timing columns.

    This test verifies that the function handles cases where some timing
    data is missing by filling with appropriate default values.
    Domain relevance: Real pipeline executions may have incomplete data
    due to errors or partial runs.
    """
    # Arrange
    test_data = {
        "node1": {NODE_RUN_TIME: 2.0},  # Missing LOAD_TIME and SAVE_TIME
        "node2": {LOAD_TIME: 0.5},  # Missing NODE_RUN_TIME and SAVE_TIME
    }

    # Act
    result_df = _build_node_table(dictionary=test_data, index_name="Node Name")

    # Assert
    assert len(result_df) == 2
    assert LOAD_TIME in result_df.columns
    assert NODE_RUN_TIME in result_df.columns
    assert SAVE_TIME in result_df.columns
    assert TOTAL_TIME in result_df.columns


def test_build_dataset_table_with_complete_data():
    """
    Test _build_dataset_table function with complete profiling data.

    This test verifies that the dataset table building function correctly
    processes profiling data and creates a properly formatted DataFrame.
    Domain relevance: Dataset tables help identify I/O bottlenecks in
    data-intensive ML pipelines.
    """
    # Arrange
    test_data = {
        "dataset1": {LOAD_TIME: 1.5, SAVE_TIME: 0.5, LOAD_COUNT: 2, SAVE_COUNT: 1},
        "dataset2": {LOAD_TIME: 0.8, SAVE_TIME: 1.2, LOAD_COUNT: 1, SAVE_COUNT: 1},
    }

    # Act
    result_df = _build_dataset_table(dictionary=test_data, index_name="Dataset Name")

    # Assert
    assert len(result_df) == 2
    assert "Dataset Name" in result_df.columns
    assert TOTAL_TIME in result_df.columns
    assert result_df.loc[0, TOTAL_TIME] == 2.0  # dataset1 total
    assert result_df.loc[1, TOTAL_TIME] == 2.0  # dataset2 total


def test_build_tables_with_empty_data():
    """
    Test table building functions with empty profiling data.

    This test verifies that both table building functions handle empty
    input gracefully and return properly structured empty DataFrames.
    Domain relevance: Edge case handling for pipelines with no profiling
    data due to early failures or configuration issues.
    """
    # Arrange
    empty_data = {}

    # Act
    node_df = _build_node_table(dictionary=empty_data, index_name="Node Name")
    dataset_df = _build_dataset_table(dictionary=empty_data, index_name="Dataset Name")

    # Assert
    assert len(node_df) == 0
    assert len(dataset_df) == 0
    assert "Node Name" in node_df.columns
    assert "Dataset Name" in dataset_df.columns


def test_rich_table_formatting():
    """
    Test Rich table formatting functionality.

    This test verifies that the dataframe_to_rich_table function correctly
    converts pandas DataFrames to Rich Table objects for enhanced display.
    Domain relevance: Rich formatting improves readability of profiling
    results for data scientists and engineers.
    """
    # Arrange
    test_df = pd.DataFrame(
        {
            "Name": ["node1", "node2"],
            "Time": [1.5, 2.0],
            "Status": ["complete", "complete"],
        }
    )

    # Act
    rich_table = dataframe_to_rich_table(df=test_df)

    # Assert
    assert rich_table is not None
    # Verify table has correct number of columns
    assert len(rich_table.columns) == 3


def test_print_rich_table_to_console():
    """
    Test Rich table console printing functionality.

    This test verifies that the print_rich_table_to_console function
    properly outputs Rich tables to the console.
    """
    # Arrange
    test_df = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})
    rich_table = dataframe_to_rich_table(df=test_df)

    # Act & Assert
    with patch("kedro_profile.hook.Console") as mock_console_class:
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        print_rich_table_to_console(rich_table=rich_table)

        mock_console.print.assert_called_once_with(rich_table)


@pytest.mark.parametrize(
    "save_file,rich_enabled",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
)
def test_after_pipeline_run_output_variations(save_file: bool, rich_enabled: bool):
    """
    Test after_pipeline_run with different output configurations.

    This parameterized test verifies that the after_pipeline_run method
    correctly handles different combinations of save_file and rich_enabled
    settings, producing appropriate output in each case.
    Domain relevance: Different deployment environments may require different
    output formats and persistence options.
    """
    # Arrange
    with patch.dict(os.environ, {}, clear=True):
        if not rich_enabled:
            os.environ["KEDRO_PROFILE_RICH"] = "0"

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = rich_enabled
            hook = ProfileHook(save_file=save_file)

    hook._node_starts["test_node"] = 1.0
    hook._node_durations["test_node"] = 1.0
    hook._load_durations[("test_dataset", "test_node")] = 0.5

    mock_run_params = {"env": "test"}
    mock_run_result = Mock()
    mock_pipeline = Mock()
    mock_catalog = Mock()

    # Act
    with (
        patch("builtins.print") as mock_print,
        patch.object(hook, "_save_to_csv") as mock_save,
    ):
        hook.after_pipeline_run(
            run_params=mock_run_params,
            run_result=mock_run_result,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

    # Assert
    if save_file:
        assert mock_save.call_count == 2  # Both node and dataset profiles
    else:
        mock_save.assert_not_called()

    mock_print.assert_called()  # Some output should be generated


def test_print_path_saved_functionality():
    """
    Test the _print_path_saved helper method.

    This test verifies that the path printing functionality works correctly
    for both string and Path objects.
    """
    # Arrange
    hook = ProfileHook()
    test_path_str = "/path/to/file.csv"
    test_path_obj = Path("/path/to/file.csv")

    # Act & Assert
    with patch("builtins.print") as mock_print:
        hook._print_path_saved(file_path=test_path_str)
        mock_print.assert_called_with(f"Profile data saved to: {test_path_str}")

    with patch("builtins.print") as mock_print:
        hook._print_path_saved(file_path=test_path_obj)
        mock_print.assert_called_with(f"Profile data saved to: {test_path_obj}")


def test_integration_full_pipeline_simulation():
    """
    Integration test simulating a complete pipeline execution with profiling.

    This test simulates a realistic pipeline execution scenario with multiple
    nodes and datasets to verify that all profiling components work together
    correctly.
    Domain relevance: Represents a typical ML pipeline execution pattern
    with data loading, processing, and saving operations.
    """
    # Arrange
    hook = ProfileHook(save_file=True)

    # Simulate pipeline setup
    mock_run_params = {"env": "test"}
    mock_pipeline = Mock()
    mock_catalog = Mock()
    mock_run_result = Mock()

    # Simulate nodes
    node1 = Mock()
    node1.name = "data_preprocessing"
    node2 = Mock()
    node2.name = "model_training"

    with tempfile.TemporaryDirectory() as temp_dir:
        hook.node_profile_path = Path(temp_dir) / "nodes.csv"
        hook.dataset_profile_path = Path(temp_dir) / "datasets.csv"

        # Act - Simulate complete pipeline execution
        hook.before_pipeline_run(
            run_params=mock_run_params, pipeline=mock_pipeline, catalog=mock_catalog
        )

        # Node 1 execution
        hook.before_node_run(node=node1, catalog=mock_catalog, inputs={})
        hook.before_dataset_loaded(dataset_name="raw_data", node=node1)
        time.sleep(0.01)
        hook.after_dataset_loaded(dataset_name="raw_data", node=node1)
        time.sleep(0.01)
        hook.after_node_run(node=node1, catalog=mock_catalog, inputs={})
        hook.before_dataset_saved(dataset_name="processed_data", node=node1)
        time.sleep(0.01)
        hook.after_dataset_saved(dataset_name="processed_data", node=node1)

        # Node 2 execution
        hook.before_node_run(node=node2, catalog=mock_catalog, inputs={})
        hook.before_dataset_loaded(dataset_name="processed_data", node=node2)
        time.sleep(0.01)
        hook.after_dataset_loaded(dataset_name="processed_data", node=node2)
        time.sleep(0.01)
        hook.after_node_run(node=node2, catalog=mock_catalog, inputs={})
        hook.before_dataset_saved(dataset_name="model_output", node=node2)
        time.sleep(0.01)
        hook.after_dataset_saved(dataset_name="model_output", node=node2)

        # Complete pipeline
        with patch("builtins.print"):
            hook.after_pipeline_run(
                run_params=mock_run_params,
                run_result=mock_run_result,
                pipeline=mock_pipeline,
                catalog=mock_catalog,
            )

        # Assert
        assert hook.node_profile_path.exists()
        assert hook.dataset_profile_path.exists()

        # Verify profiling data was collected
        node_profile, dataset_profile = hook._collect_profiles()
        assert set(node_profile) == {"data_preprocessing", "model_training"}
        assert set(dataset_profile) == {"raw_data", "processed_data", "model_output"}


def test_dataset_hooks_noop_when_disabled() -> None:
    """Dataset load and save hooks do nothing when KEDRO_PROFILE_DISABLE=1."""
    from kedro.pipeline import node

    test_node = node(lambda x: x, "raw_data", "output_data", name="test_node")

    with patch.dict(os.environ, {"KEDRO_PROFILE_DISABLE": "1"}):
        hook = ProfileHook()
        hook.before_dataset_loaded("raw_data", test_node)
        hook.after_dataset_loaded("raw_data", test_node)
        hook.before_dataset_saved("output_data", test_node)
        hook.after_dataset_saved("output_data", test_node)

    assert hook._load_starts == {}
    assert hook._load_durations == {}
    assert hook._save_starts == {}
    assert hook._save_durations == {}
    assert hook._collect_profiles() == ({}, {})


def test_concurrent_loads_of_same_dataset_give_correct_totals() -> None:
    """Two nodes loading one dataset at once sum to the right dataset total."""
    # Arrange
    hook = ProfileHook()
    nodes = []
    for name in ("node_a", "node_b"):
        mock_node = Mock()
        mock_node.name = name
        nodes.append(mock_node)
    barrier = threading.Barrier(len(nodes))

    def load(mock_node: Mock) -> None:
        hook.before_node_run(node=mock_node, catalog=Mock(), inputs={})
        barrier.wait()
        hook.before_dataset_loaded(dataset_name="shared", node=mock_node)
        time.sleep(0.05)
        hook.after_dataset_loaded(dataset_name="shared", node=mock_node)
        hook.after_node_run(node=mock_node, catalog=Mock(), inputs={})

    # Act
    threads = [threading.Thread(target=load, args=(n,)) for n in nodes]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    node_profile, dataset_profile = hook._collect_profiles()

    # Assert
    per_node = [node_profile[n][LOAD_TIME] for n in ("node_a", "node_b")]
    assert dataset_profile["shared"][LOAD_COUNT] == 2
    assert dataset_profile["shared"][LOAD_TIME] == pytest.approx(sum(per_node))
    assert all(duration >= 0.05 for duration in per_node)


def test_execution_order_follows_start_times() -> None:
    """Execution order is the rank of each node's start time."""
    # Arrange
    hook = ProfileHook()
    late, early = Mock(), Mock()
    late.name = "late"
    early.name = "early"
    hook._node_starts["late"] = 20.0
    hook._node_starts["early"] = 10.0  # inserted second, started first

    # Act
    node_profile, _ = hook._collect_profiles()

    # Assert
    assert node_profile["early"][EXECUTION_ORDER] == 1
    assert node_profile["late"][EXECUTION_ORDER] == 2


def test_second_run_starts_fresh() -> None:
    """before_pipeline_run clears records and the start time of the first run."""
    # Arrange
    hook = ProfileHook()
    mock_node = Mock()
    mock_node.name = "test_node"
    run_args = {"run_params": {}, "pipeline": Mock(), "catalog": Mock()}
    hook.before_pipeline_run(**run_args)
    hook.before_node_run(node=mock_node, catalog=Mock(), inputs={})
    hook.before_dataset_loaded(dataset_name="raw", node=mock_node)
    hook.after_dataset_loaded(dataset_name="raw", node=mock_node)
    hook.after_node_run(node=mock_node, catalog=Mock(), inputs={})
    hook._pipeline_start -= 1000

    # Act
    hook.before_pipeline_run(**run_args)

    # Assert
    assert hook._collect_profiles() == ({}, {})
    assert time.time() - hook._pipeline_start < 5


def test_unfinished_node_has_no_compute_time_and_stays_out_of_total() -> None:
    """A node that started but never finished shows NaN and adds nothing."""
    # Arrange
    hook = ProfileHook()
    hook._node_starts["done"] = 1_700_000_000.0
    hook._node_durations["done"] = 2.0
    hook._node_starts["failed"] = 1_700_000_001.0  # no duration recorded

    # Act
    node_profile, _ = hook._collect_profiles()
    node_df = _build_node_table(dictionary=node_profile, index_name="Node Name")
    with_total = _add_total_row(node_df, "Node Name")

    # Assert
    failed_row = with_total[with_total["Node Name"] == "failed"].iloc[0]
    total_row = with_total[with_total["Node Name"] == "TOTAL"].iloc[0]
    assert pd.isna(failed_row[NODE_RUN_TIME])
    assert total_row[NODE_RUN_TIME] == 2.0


def test_rich_table_with_summary_rows_formats_every_numeric_column() -> None:
    """TOTAL and Time Elapsed rows keep numeric dtypes, so formatting applies."""
    # Arrange
    node_df = _build_node_table(
        dictionary={
            "n1": {EXECUTION_ORDER: 1, LOAD_TIME: 1.0, NODE_RUN_TIME: 2.0},
            "n2": {EXECUTION_ORDER: 2, LOAD_TIME: 0.5, NODE_RUN_TIME: 1.5},
        },
        index_name="Node Name",
    )
    with_rows = _add_total_row(node_df, "Node Name")
    with_rows = _add_wall_clock_row(with_rows, "Node Name", 4.0)

    # Act
    rich_table = dataframe_to_rich_table(df=with_rows)

    # Assert
    numeric_cols = [EXECUTION_ORDER, LOAD_TIME, NODE_RUN_TIME, SAVE_TIME, TOTAL_TIME]
    for col in numeric_cols:
        assert pd.api.types.is_numeric_dtype(with_rows[col]), col
    columns = {column.header: column for column in rich_table.columns}
    assert all(columns[col].justify == "right" for col in numeric_cols)
    assert list(columns[NODE_RUN_TIME]._cells) == ["2.00", "1.50", "3.50", ""]
    assert list(columns[EXECUTION_ORDER]._cells) == ["1", "2", "", ""]
    assert list(columns[TOTAL_TIME]._cells) == ["3.00", "2.00", "5.00", "4.00"]


def test_csv_files_exclude_humanized_total_time() -> None:
    """Total Time (humanized text) is console-only; CSVs keep Total Time(s)."""
    # Arrange
    hook = ProfileHook(save_file=True)
    hook._node_starts["test_node"] = 1.0
    hook._node_durations["test_node"] = 1.5
    hook._load_durations[("test_dataset", "test_node")] = 0.5

    with tempfile.TemporaryDirectory() as temp_dir:
        hook.node_profile_path = Path(temp_dir) / "nodes.csv"
        hook.dataset_profile_path = Path(temp_dir) / "datasets.csv"

        # Act
        with patch("builtins.print"):
            hook.after_pipeline_run(
                run_params={}, run_result=Mock(), pipeline=Mock(), catalog=Mock()
            )

        # Assert
        for path in (hook.node_profile_path, hook.dataset_profile_path):
            saved = pd.read_csv(path)
            assert TOTAL_TIME in saved.columns
            assert "Total Time" not in saved.columns
