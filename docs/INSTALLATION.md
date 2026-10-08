# Clean offline installation

The runtime package has no dependencies. Building requires an already installed Python 3.11+ toolchain with setuptools 68+ and wheel. Do not download or upgrade a missing toolchain as part of the offline procedure.

A trusted build environment can create the wheel directly from this checkout:

```sh
python3 -c "from setuptools.build_meta import build_wheel; print(build_wheel('dist'))"
```

Create a fresh environment with its existing Python/pip toolchain, then install only that local artifact:

```sh
python3 -m venv /tmp/agent-replay-venv
/tmp/agent-replay-venv/bin/python -m pip install --no-index --no-deps dist/agent_replay_bench-0.1.0-py3-none-any.whl
```

Use fresh paths if those example directories already exist. Do not reuse or overwrite unrelated environments. Run the installed CLI from outside the checkout:

```sh
cd /tmp
/tmp/agent-replay-venv/bin/agent-replay-bench demo --format json
```

The demo's exit code is 1 because it deliberately demonstrates a divergence. To test installed behavior, copy only `tests/` and `examples/` into a fresh check directory, without the package source directory, and run the fresh environment's Python with isolated mode:

```sh
/tmp/agent-replay-venv/bin/python -I -m unittest discover -s /tmp/agent-replay-check/tests -v
```

Installed imports must resolve to the fresh environment's site-packages, not the checkout. Check both the module CLI and the console entry point. No evaluation batch is launched by these installation checks.

The admitted installation passed. Its [machine-readable facts](installation.json) and [verification summary](VERIFICATION.md) record the exact toolchain, source and wheel identities. The operational packaging limits are not a claim of hostile-code or arbitrary-descendant containment.
