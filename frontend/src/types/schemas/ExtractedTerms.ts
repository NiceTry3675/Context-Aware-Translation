/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * List of unique proper nouns found in the text. Empty list if none found.
 */
export type Terms = string[];

/**
 * Response model for proper noun extraction.
 */
export interface ExtractedTerms {
  terms?: Terms;
  [k: string]: unknown;
}
