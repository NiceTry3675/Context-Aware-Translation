/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * Brief description of the narrator's voice (e.g., 'A neutral, third-person observer's voice')
 */
export type Description = string;
/**
 * Korean sentence ending style for narration (almost always 해라체)
 */
export type EndingStyle = string;

/**
 * Narration style details.
 */
export interface NarrationStyle {
  description: Description;
  ending_style?: EndingStyle;
  [k: string]: unknown;
}
