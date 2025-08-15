# Refactoring Log

## 2025-08-15: Structured Output Implementation

### Overview
Migrated glossary, character style, and narrative analysis from text-based parsing to Gemini Structured Output API for deterministic JSON responses.

### Changes
- **New**: `core/schemas/` - Centralized Pydantic models and JSON schema builders
  - `glossary.py` - Term extraction and translation schemas
  - `character_style.py` - Dialogue style analysis schemas  
  - `narrative_style.py` - Style definition and deviation schemas
  - `validation.py` - Re-exports existing validation schemas

- **Updated**: Core managers with dual-mode support (structured/text)
  - `GlossaryManager` - Structured term extraction and translation
  - `CharacterStyleManager` - Structured dialogue analysis
  - `DynamicConfigBuilder` - Structured style deviation detection

### Configuration
- Environment variable: `USE_STRUCTURED_OUTPUT=true` (default)
- Backward compatible - legacy text mode still available

### Benefits
- Eliminates regex parsing errors
- Deterministic JSON responses
- Better error handling via schema validation
- Improved frontend data consistency

### Testing
- `tests/test_structured_output.py` - Comprehensive test coverage
- All components tested and working