# Context-Aware Translation Tests

This directory contains tests for the Context-Aware Translation system.

## Test Files

- `test_translation_overall.py` - Unit tests with mocked API calls
- `test_integration.py` - Integration tests with actual Gemini API
- `run_tests.py` - Test runner script

## Running Tests

### Unit Tests (No API Key Required)

Run unit tests with mocked API responses:

```bash
# From project root
python -m tests.test_translation_overall

# Or using the test runner
python tests/run_tests.py --unit
```

### Integration Tests (API Key Required)

Run integration tests with actual Gemini API:

```bash
# Set your API key
export GEMINI_API_KEY='your-gemini-api-key'

# Run integration tests
python tests/run_tests.py --integration
```

### Run All Tests

```bash
export GEMINI_API_KEY='your-gemini-api-key'
python tests/run_tests.py --all
```

## Test Coverage

### Unit Tests (`test_translation_overall.py`)
- Tests translation of first 20,000 characters from "The Catcher in the Rye"
- Mocks Gemini API responses
- Verifies:
  - Segment creation
  - Translation pipeline execution
  - Glossary building
  - Output file generation
  - API key validation

### Integration Tests (`test_integration.py`)
- **Small Sample Test**: Translates 1,000 characters with real API
- **Full Test**: Translates 20,000 characters with real API (optional, uses more API calls)
- Verifies:
  - Actual Korean translation output
  - API connectivity
  - End-to-end translation process
  - Performance metrics

## Test Output

Test outputs are saved in the `test_outputs/` directory:
- Translated files
- Statistics files
- Debug logs

## Requirements

- Python 3.8+
- All project dependencies (`pip install -r requirements.txt`)
- Gemini API key (for integration tests only)

## Notes

- Unit tests use mocked responses and don't consume API quota
- Integration tests make actual API calls and will use your quota
- The full integration test (20k chars) will make multiple API calls