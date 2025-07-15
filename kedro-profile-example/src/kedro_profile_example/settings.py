"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/kedro_project_setup/settings.html.
"""

# Instantiated project hooks.
# For example, after creating a hooks.py and defining a ProjectHooks class there, do
# from kedro_profile_example.hooks import ProjectHooks

# Hooks are executed in a Last-In-First-Out (LIFO) order.
# HOOKS = (ProjectHooks(),)
from kedro_profile.hook import ProfileHook
import time

# Configure ProfileHook with CSV saving options
HOOKS: tuple[ProfileHook] = (
    ProfileHook(
        save_file=True,  # Enable CSV file saving
        node_profile_path=f"data/08_reporting/node_profile_{time.strftime('%Y%m%d_%H%M')}.csv",
        dataset_profile_path=f"data/08_reporting/dataset_profile_{time.strftime('%Y%m%d_%H%M')}.csv",
    ),
)

# Alternative configuration examples:
# HOOKS: tuple[ProfileHook] = (
#     ProfileHook(
#         save_file=True,
#         node_profile_path="reports/node_performance.csv",
#         dataset_profile_path="reports/dataset_performance.csv",
#     ),
# )

# HOOKS: tuple[ProfileHook] = (
#     ProfileHook(
#         save_file=False,  # Disable CSV saving, only console output
#     ),
# )

# Installed plugins for which to disable hook auto-registration.
# DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Class that manages storing KedroSession data.
# from kedro.framework.session.store import BaseSessionStore
# SESSION_STORE_CLASS = BaseSessionStore
# Keyword arguments to pass to the `SESSION_STORE_CLASS` constructor.
# SESSION_STORE_ARGS = {
#     "path": "./sessions"
# }

# Directory that holds configuration.
# CONF_SOURCE = "conf"

# Class that manages how configuration is loaded.
from kedro.config import OmegaConfigLoader  # noqa: E402

CONFIG_LOADER_CLASS = OmegaConfigLoader
# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    #       "config_patterns": {
    #           "spark" : ["spark*/"],
    #           "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    #       }
}

# Class that manages Kedro's library components.
# from kedro.framework.context import KedroContext
# CONTEXT_CLASS = KedroContext

# Class that manages the Data Catalog.
# from kedro.io import DataCatalog
# DATA_CATALOG_CLASS = DataCatalog
