#!/usr/bin/env python3
"""Export OpenAPI schema from FastAPI app without running the server."""

import json
import pathlib
import sys
from pathlib import Path

# Add the parent directory to sys.path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.main import app


def export_openapi():
    """Export the OpenAPI schema to a JSON file."""
    
    # Get the OpenAPI schema from the FastAPI app
    openapi_schema = app.openapi()
    
    # Define output path (root of the project)
    output_path = Path(__file__).parent.parent.parent / "openapi.json"
    
    # Write the schema to file
    output_path.write_text(
        json.dumps(openapi_schema, ensure_ascii=False, indent=2)
    )
    
    print(f"✅ OpenAPI schema exported to: {output_path.resolve()}")
    print(f"   Total endpoints: {len(openapi_schema.get('paths', {}))}")
    
    # Print some basic info about the schema
    if 'info' in openapi_schema:
        info = openapi_schema['info']
        print(f"   API Version: {info.get('version', 'N/A')}")
        print(f"   Title: {info.get('title', 'N/A')}")


if __name__ == "__main__":
    export_openapi()