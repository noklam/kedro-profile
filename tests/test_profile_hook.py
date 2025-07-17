import pandas as pd
from kedro_profile.hook import ProfileHook


class DummyNode:
    def __init__(self, name):
        self.name = name


def test_partial_save_on_node_error(tmp_path):
    node_csv = tmp_path / "node_profile.csv"
    dataset_csv = tmp_path / "dataset_profile.csv"
    hook = ProfileHook(
        save_file=True,
        node_profile_path=node_csv,
        dataset_profile_path=dataset_csv,
    )
    node = DummyNode("test_node")
    hook.before_node_run(node, None, None)
    hook.on_node_error(Exception("fail!"), node, None, None, False, "dummy-session-id")
    assert node_csv.exists()
    assert dataset_csv.exists()
    assert not pd.read_csv(node_csv).empty


def test_partial_save_on_pipeline_error(tmp_path):
    node_csv = tmp_path / "node_profile.csv"
    dataset_csv = tmp_path / "dataset_profile.csv"
    hook = ProfileHook(
        save_file=True,
        node_profile_path=node_csv,
        dataset_profile_path=dataset_csv,
    )
    node = DummyNode("test_node")
    hook.before_node_run(node, None, None)
    hook.on_pipeline_error(Exception("pipeline fail!"), {}, None, None)
    assert node_csv.exists()
    assert dataset_csv.exists()
    assert not pd.read_csv(node_csv).empty


def test_multiple_nodes_mixed_success(tmp_path):
    node_csv = tmp_path / "node_profile.csv"
    dataset_csv = tmp_path / "dataset_profile.csv"
    hook = ProfileHook(
        save_file=True,
        node_profile_path=node_csv,
        dataset_profile_path=dataset_csv,
    )
    node1 = DummyNode("node1")
    node2 = DummyNode("node2")
    # Node 1 runs successfully
    hook.before_node_run(node1, None, None)
    hook.after_node_run(node1, None, None)
    # Node 2 starts but fails
    hook.before_node_run(node2, None, None)
    hook.on_node_error(Exception("fail!"), node2, None, None, False, "dummy-session-id")
    df = pd.read_csv(node_csv)
    assert "node1" in df["Node Name"].values
    assert "node2" in df["Node Name"].values


def test_no_nodes_run_pipeline_error(tmp_path):
    node_csv = tmp_path / "node_profile.csv"
    dataset_csv = tmp_path / "dataset_profile.csv"
    hook = ProfileHook(
        save_file=True,
        node_profile_path=node_csv,
        dataset_profile_path=dataset_csv,
    )
    # Only pipeline error, no nodes
    hook.on_pipeline_error(Exception("fail!"), {}, None, None)
    df = pd.read_csv(node_csv)
    # Should create files with only headers or empty
    assert df.empty or "Node Name" in df.columns


def test_all_nodes_success(tmp_path):
    node_csv = tmp_path / "node_profile.csv"
    dataset_csv = tmp_path / "dataset_profile.csv"
    hook = ProfileHook(
        save_file=True,
        node_profile_path=node_csv,
        dataset_profile_path=dataset_csv,
    )
    nodes = [DummyNode(f"node{i}") for i in range(3)]
    for node in nodes:
        hook.before_node_run(node, None, None)
        hook.after_node_run(node, None, None)
    hook.after_pipeline_run({}, {}, None, None)
    df = pd.read_csv(node_csv)
    for node in nodes:
        assert node.name in df["Node Name"].values


def test_dataset_load_save_counts(tmp_path):
    node_csv = tmp_path / "node_profile.csv"
    dataset_csv = tmp_path / "dataset_profile.csv"
    hook = ProfileHook(
        save_file=True,
        node_profile_path=node_csv,
        dataset_profile_path=dataset_csv,
    )
    node = DummyNode("node")
    # Simulate multiple loads/saves
    for _ in range(3):
        hook.before_dataset_loaded("mydata", node)
        hook.after_dataset_loaded("mydata", node)
    for _ in range(2):
        hook.before_dataset_saved("mydata", node)
        hook.after_dataset_saved("mydata", node)
    hook.after_pipeline_run({}, {}, None, None)
    df = pd.read_csv(dataset_csv)
    row = df[df["Dataset Name"] == "mydata"].iloc[0]
    assert row["Load Count"] == 3
    assert row["Save Count"] == 2
