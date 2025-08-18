#!/usr/bin/env node
/**
 * Generate TypeScript types from JSON schemas exported by core Python models.
 * This creates typed interfaces for structured outputs like validation reports
 * and glossary data that are used directly in the UI.
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileFromFile } from 'json-schema-to-typescript';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Schema mappings - which schemas to generate and their source files
const SCHEMAS = [
  // Validation schemas
  ['ValidationResponse', '../core/schemas/jsonschema/ValidationResponse.schema.json'],
  ['ValidationCase', '../core/schemas/jsonschema/ValidationCase.schema.json'],
  
  // Glossary schemas
  ['ExtractedTerms', '../core/schemas/jsonschema/ExtractedTerms.schema.json'],
  ['TranslatedTerms', '../core/schemas/jsonschema/TranslatedTerms.schema.json'],
  ['TranslatedTerm', '../core/schemas/jsonschema/TranslatedTerm.schema.json'],
  
  // Character style schemas
  ['CharacterInteraction', '../core/schemas/jsonschema/CharacterInteraction.schema.json'],
  ['DialogueAnalysisResult', '../core/schemas/jsonschema/DialogueAnalysisResult.schema.json'],
  
  // Narrative style schemas
  ['NarrativeStyleDefinition', '../core/schemas/jsonschema/NarrativeStyleDefinition.schema.json'],
  ['NarrationStyle', '../core/schemas/jsonschema/NarrationStyle.schema.json'],
  ['StyleDeviation', '../core/schemas/jsonschema/StyleDeviation.schema.json'],
];

// Output directory for generated TypeScript types
const OUTPUT_DIR = path.join(__dirname, '..', 'src', 'types', 'schemas');

async function ensureOutputDir() {
  try {
    await fs.mkdir(OUTPUT_DIR, { recursive: true });
    console.log(`✓ Output directory ensured: ${OUTPUT_DIR}`);
  } catch (error) {
    console.error(`Failed to create output directory: ${error.message}`);
    process.exit(1);
  }
}

async function generateTypeForSchema(name, schemaPath) {
  const fullPath = path.join(__dirname, '..', schemaPath);
  
  try {
    // Check if schema file exists
    await fs.access(fullPath);
    
    // Generate TypeScript from JSON Schema
    const ts = await compileFromFile(fullPath, {
      bannerComment: `/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */`,
      style: {
        semi: true,
        singleQuote: true,
      },
    });
    
    // Write to output file
    const outputPath = path.join(OUTPUT_DIR, `${name}.ts`);
    await fs.writeFile(outputPath, ts);
    
    console.log(`✓ Generated ${name}.ts`);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.warn(`⚠ Schema file not found: ${fullPath}`);
      console.warn(`  Run 'python -m core.schemas.export_jsonschema' to generate schemas`);
    } else {
      console.error(`✗ Failed to generate ${name}: ${error.message}`);
    }
    return false;
  }
}

async function createIndexFile() {
  // Create an index.ts file that re-exports all generated types
  const exports = SCHEMAS.map(([name]) => 
    `export type { ${name} } from './${name}';`
  ).join('\n');
  
  const indexContent = `/* eslint-disable */
/**
 * This file was automatically generated.
 * DO NOT MODIFY IT BY HAND. Instead, regenerate using npm run codegen:schemas
 */

${exports}
`;
  
  const indexPath = path.join(OUTPUT_DIR, 'index.ts');
  await fs.writeFile(indexPath, indexContent);
  console.log('✓ Generated index.ts');
}

async function main() {
  console.log('Generating TypeScript types from JSON schemas...\n');
  
  // Ensure output directory exists
  await ensureOutputDir();
  
  // Generate types for each schema
  let successCount = 0;
  for (const [name, schemaPath] of SCHEMAS) {
    const success = await generateTypeForSchema(name, schemaPath);
    if (success) successCount++;
  }
  
  // Create index file
  await createIndexFile();
  
  console.log(`\n✅ Successfully generated ${successCount}/${SCHEMAS.length} type definitions`);
  
  if (successCount < SCHEMAS.length) {
    console.log('\n⚠ Some schemas were not found. Make sure to run:');
    console.log('  python -m core.schemas.export_jsonschema');
    console.log('  before running this script.');
  }
  
  console.log('\nNext steps:');
  console.log('  1. Import types from "@/types/schemas" in your components');
  console.log('  2. Replace local type definitions with generated ones');
}

// Run the script
main().catch(error => {
  console.error('Script failed:', error);
  process.exit(1);
});