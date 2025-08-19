/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * Whether a style deviation was detected
 */
export type HasDeviation = boolean;
/**
 * The first few words of the deviating part
 */
export type StartsWith = string | null;
/**
 * Direct command for the translator regarding this deviation
 */
export type Instruction = string | null;

/**
 * Style deviation detected in a segment.
 */
export interface StyleDeviation {
  has_deviation: HasDeviation;
  starts_with?: StartsWith;
  instruction?: Instruction;
  [k: string]: unknown;
}
