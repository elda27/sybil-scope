# Sibyl Scope Viewer

A simple Streamlit UI to explore your Sibyl Scope traces. This guide shows how to launch the viewer, load data, and use its panels.

## Requirements

- Python 3.10+
- Install the optional viewer extras:

```bash
pip install sibyl-scope[viewer]
```

If you are working from this repo, ensure dependencies are installed (uv/pip supported).

## Launching the Viewer

You can start the viewer in a few ways from the repository root:

- Using the package module entrypoint:
```bash
python -m sybil_scope.viewer
```

- Using the helper script:
```bash
python run_viewer.py
```

The viewer runs on http://localhost:8501 by default.

## Getting Trace Data

- Generate sample traces provided by the repo:
```bash
python examples/generate_sample_traces.py
```
This writes a JSONL file under the `traces/` folder, e.g. `traces/traces_YYYYMMDD_HHMMSS.jsonl`.

- Or use any JSONL file produced by `FileBackend` in your app.

By default, `FileBackend` writes to `traces/` with an auto-named file. You can customize via config:
```python
from sybil_scope.config import set_option, ConfigKey

set_option(ConfigKey.TRACING_FILE_PREFIX, "myrun")
# set_option(ConfigKey.TRACING_FILE_PATH, "custom/path/file.jsonl")  # optional
```

## Loading Data in the UI

In the left sidebar you can:
- Upload a JSONL file directly, or
- Enter a file path and click "Load File"

Once loaded, you’ll see a summary with the number of events and time range.

## Views and Features

The viewer offers several panes you can toggle in the sidebar:

- Statistics: Event counts, type/action distributions, and basic performance metrics
- Hierarchical: Parent/child tree of events (agent spans shown as single units)
- Timeline: Duration-oriented plots by type/action
- Flow Diagram: Graph-style view of event relationships
- Table View: Flat and expandable tables with quick filters

Use the Event Inspector (sidebar) to enter an event ID and drill into its details.

## Tips

- Large files: Loading very large JSONL files can be slow in a browser environment. Consider filtering data in your app or generating separate runs.
- Data shape: The viewer expects events emitted by Sibyl Scope’s `TraceEvent` model (one JSON object per line).
- Port conflicts: If 8501 is in use, set a different port via Streamlit env vars, or run the module and let Streamlit choose an open port.

## Troubleshooting

- No file found: Double-check the path you enter in the sidebar. Relative paths are relative to the viewer process CWD.
- Blank page: Ensure `pip install sibyl-scope[viewer]` completed and you’re using a Python with access to those packages.
- Windows PowerShell: If launching from PowerShell, prefer the module form (`python -m sybil_scope.viewer`).

## Alternative: Embed in Your App

You can also load and visualize events programmatically using the components in `sybil_scope.viewer.*` if you wish to integrate parts into your own Streamlit app.
