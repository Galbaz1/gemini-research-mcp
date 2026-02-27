# Contributing to gemini-research-mcp

Thanks for your interest in contributing! This project is open source under the MIT license.

## Development Setup

```bash
# Clone and install
git clone https://github.com/Galbaz1/gemini-research-mcp
cd gemini-research-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run the installer locally (to test commands/skills/agents)
node bin/install.js --global
```

**Requirements**: Python >= 3.11, [uv](https://docs.astral.sh/uv/), Node.js >= 16

## Running Tests

```bash
# All tests (mocked, no API key needed)
uv run pytest tests/ -v

# Single file or test
uv run pytest tests/test_video_tools.py -v
uv run pytest tests/test_video_tools.py::test_name -v

# Lint
uv run ruff check src/ tests/
```

All tests mock the Gemini API via the `mock_gemini_client` fixture. No test should ever make a real API call.

## Code Style

- **Linter**: ruff (line-length=100, target py311)
- **Type hints**: use `Annotated[type, Field(...)]` for tool parameters
- **File size**: aim for ~300 lines of executable code per production file in `src/`
- **Error handling**: tools return `make_tool_error()` dicts, never raise exceptions
- **Models**: Pydantic v2, one file per domain in `models/`

## Making Changes

### Before You Start

1. Check [existing issues](https://github.com/Galbaz1/gemini-research-mcp/issues) to avoid duplicate work
2. For larger changes, open an issue first to discuss the approach

### Pull Request Process

1. Fork the repo and create a branch from `main`
2. Make your changes with clear, atomic commits
3. Add or update tests for new functionality
4. Ensure all tests pass: `uv run pytest tests/ -v`
5. Ensure lint passes: `uv run ruff check src/ tests/`
6. Open a PR against `main` with a clear description

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(video): add batch analysis for directories
fix(content): handle timeout on large PDFs
docs(readme): update installation instructions
test(research): add evidence assessment edge cases
refactor(client): extract retry logic to helper
```

## Architecture Overview

See [CLAUDE.md](CLAUDE.md) for detailed architecture, tool conventions, and testing patterns. Key points:

- **Composite FastMCP server** with 5 sub-servers (video, research, content, search, infra)
- **Instruction-driven tools**: accept free-text `instruction` parameter, return structured JSON
- **Structured output**: `GeminiClient.generate_structured(schema=PydanticModel)`
- **Shared types**: `Literal` types and `Annotated` aliases in `types.py`

## Adding a New Tool

1. Add the tool function to the appropriate `tools/*.py` sub-server
2. Add `ToolAnnotations` in the decorator
3. Use `Annotated` params with `Field` constraints
4. Add a Pydantic model in `models/` for structured output
5. Write tests using `mock_gemini_client`
6. Update CLAUDE.md tool table

## Questions?

Open an issue or reach out to [Fausto Albers](https://wonderwhy.ai).
