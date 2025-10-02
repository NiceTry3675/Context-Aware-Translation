/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * The single most central character's name. If unclear, 'Protagonist'
 */
export type ProtagonistName = string;
/**
 * Brief description of the narrator's voice (e.g., 'A neutral, third-person observer's voice')
 */
export type Description = string;
/**
 * Korean sentence ending style for narration (almost always 해라체)
 */
export type EndingStyle = string;
/**
 * 3-5 keywords describing the overall mood (Korean)
 *
 * @minItems 1
 * @maxItems 5
 */
export type CoreToneKeywords =
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string];
/**
 * Overarching rule for the novel's feel and rhythm
 */
export type GoldenRule = string;

/**
 * Core narrative style definition for the entire work.
 */
export interface NarrativeStyleDefinition {
  protagonist_name: ProtagonistName;
  narration_style: NarrationStyle;
  core_tone_keywords: CoreToneKeywords;
  golden_rule: GoldenRule;
  [k: string]: unknown;
}
/**
 * Style and endings for narrative text
 */
export interface NarrationStyle {
  description: Description;
  ending_style?: EndingStyle;
  [k: string]: unknown;
}
