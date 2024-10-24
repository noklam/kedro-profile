# kedro-profile
Identify the bottleneck of your Kedro Pipeline quickly with `kedro-profile`

## Example
You will see something similar to this when running the plugin with spaceflight project:

```
==========Node Summary==========
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Node Name                     ┃ Loading Time(s) ┃ Node Compute Time(s) ┃ Saving Time(s) ┃ Total Time(s) ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ preprocess_shuttles_node      │ 1.65            │ 0.01                 │ 0.01           │ 1.68          │
│ create_model_input_table_node │ 0.01            │ 0.03                 │ 0.02           │ 0.06          │
│ preprocess_companies_node     │ 0.01            │ 0.01                 │ 0.02           │ 0.03          │
└───────────────────────────────┴─────────────────┴──────────────────────┴────────────────┴───────────────┘

==========Dataset Summary==========
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Dataset Name           ┃ Loading Time(s) ┃ Load Count ┃ Saving Time(s) ┃ Save Count ┃ Total Time(s) ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ preprocessed_shuttles  │ 0.02            │ 1.0        │ 0.01           │ 1.0        │ 0.03          │
│ preprocessed_companies │ 0.0             │ 1.0        │ 0.02           │ 1.0        │ 0.02          │
│ companies              │ 0.01            │ 1.0        │ nan            │ nan        │ nan           │
│ shuttles               │ 1.65            │ 1.0        │ nan            │ nan        │ nan           │
│ reviews                │ 0.01            │ 1.0        │ nan            │ nan        │ nan           │
│ model_input_table      │ nan             │ nan        │ 0.02           │ 1.0        │ nan           │
└────────────────────────┴─────────────────┴────────────┴────────────────┴────────────┴───────────────┘
```

# Requirements
```
kedro>=0.18.5 # Minimal version for hook specifications
pandas>=1.0.0
```

# Get Started
If you do not have kedro installed already, install kedro with:
`pip install kedro`

Then create an example project with this command:
`kedro new --example=yes --tools=none --name kedro-profile-example`

If you are cloning the repository, the project is already created [here](kedro-profile-example/)

This will create a new directory` kedro-profile-example` in your current directory.

## Enable the Profiling Hook
You will find this line in `settings.py`, update it as follow:
```diff
- # HOOKS = (ProjectHooks(),)
+ from kedro_profile import ProfileHook
+ HOOKS = (ProfileHook(),)
```


# Example
There is an [example notebook](kedro-profile-example/notebooks/demo.ipynb) in the repository:


# How to extend & Contribute?
The implementation is in a [single hook](src/kedro_profile/hook.py), you can always copy this hook and modified it for your need.

## Kedro Hooks
Kedro use the concept of Hook for extension, you can find more details in [Introduction to Hools](https://docs.kedro.org/en/stable/hooks/introduction.html). To find out which arguments are supported for a specific hook, you can refer to the [Hook Specification](https://docs.kedro.org/en/stable/api/kedro.framework.hooks.specs.html#module-kedro.framework.hooks.specs)

## Contribution
PR & issue is very welcomed if you want to contribute the changes upstream.

## Limitations
Currently it doesn't support `ParallRunner` and `ThreadRunner` yet because it is not thread-safe.

## Versioning
Expect a not so stable release for the time being. If the plugin stablised it will be using semantic versioning. For now all the release will be `0.0.x`

## Environment variable
- `KEDRO_PROFILE_RICH`, the plugin try to detect `rich` automatically, if the value is set, it will print profiling result using `rich` for color console printing. Disable this either by uninstalling `rich` or set this to `0`.
- `KEDRO_PROFILE_DISABLE`, by default the value is not set. If you need to programatically disable the profiling hook, you can set this to "1".