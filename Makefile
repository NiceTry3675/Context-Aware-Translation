# Makefile for Context-Aware Translation Codegen Pipeline
# This orchestrates the generation of schemas and types from the single source of truth

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make openapi       - Export OpenAPI schema from FastAPI"
	@echo "  make schemas       - Export JSON schemas from Pydantic models"
	@echo "  make fe-types      - Generate TypeScript types from OpenAPI"
	@echo "  make fe-schemas    - Generate TypeScript types from JSON schemas"
	@echo "  make codegen       - Run complete codegen pipeline"
	@echo "  make clean         - Clean generated files"
	@echo "  make verify        - Verify all generated files are up to date"

.PHONY: openapi
openapi:
	@echo "Exporting OpenAPI schema..."
	@python backend/scripts/export_openapi.py

.PHONY: schemas
schemas:
	@echo "Exporting JSON schemas from Pydantic models..."
	@python -m core.schemas.export_jsonschema

.PHONY: fe-types
fe-types:
	@echo "Generating TypeScript types from OpenAPI..."
	@cd frontend && npm run codegen:api

.PHONY: fe-schemas
fe-schemas:
	@echo "Generating TypeScript types from JSON schemas..."
	@cd frontend && npm run codegen:schemas

.PHONY: codegen
codegen: openapi schemas fe-types fe-schemas
	@echo "✅ Complete codegen pipeline executed successfully!"

.PHONY: clean
clean:
	@echo "Cleaning generated files..."
	@rm -f openapi.json
	@rm -rf core/schemas/jsonschema
	@rm -rf frontend/src/types/schemas
	@rm -f frontend/src/types/api.d.ts
	@echo "✅ Cleaned all generated files"

.PHONY: verify
verify: codegen
	@echo "Verifying generated files are up to date..."
	@git diff --quiet --exit-code || (echo "❌ Generated files are not up to date. Please commit the changes." && exit 1)
	@echo "✅ All generated files are up to date"