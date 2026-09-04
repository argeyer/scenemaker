# scenemaker

A scene creation toolkit written in Python.

## Requirements

- Python 3.10 or newer

## Installation

Create a virtual environment and install the project in editable mode with the
development extras:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
scenemaker --help
scenemaker --version
```

## Development

Run the test suite:

```bash
pytest
```

Lint and format:

```bash
ruff check .
ruff format .
```

## Project layout

```
src/scenemaker/   package source
tests/            test suite
pyproject.toml    build, dependency, and tool configuration
```

## License

MIT
