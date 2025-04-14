# Running Unit Tests Locally

## Important: Setting PYTHONPATH

Due to the project structure, particularly how Lambda functions are packaged (`lambda_pkg`), the Python interpreter needs help finding the source code modules (like `channel_processor`, `channel_router`) when running `pytest` from the project root directory locally.

If you run `pytest tests/unit/` directly, you will likely encounter `ModuleNotFoundError`.

**To fix this:** You must explicitly add the `src_dev` directory to your `PYTHONPATH` environment variable *before* running the tests in your current terminal session.

### Command

Execute the following command in your terminal from the project root directory:

```bash
export PYTHONPATH=$PYTHONPATH:./src_dev
```

### Running Tests

After setting the `PYTHONPATH`, you can then run the unit tests as usual:

```bash
p pytest tests/unit/
```

**Note:** You need to run the `export PYTHONPATH...` command **once per terminal session** before running the tests. This setting is automatically handled in the GitHub Actions CI environment. 