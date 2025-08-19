/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * Source term in the source language
 */
export type Source = string;
/**
 * Korean translation
 */
export type Korean = string;

/**
 * Single term translation pair.
 */
export interface TranslatedTerm {
  source: Source;
  korean: Korean;
  [k: string]: unknown;
}
