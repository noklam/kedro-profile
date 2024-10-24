# kedro-profile
Identify the bottleneck of your Kedro Pipeline quickly with `kedro-profile`

# Requirements
```
kedro>=0.18
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