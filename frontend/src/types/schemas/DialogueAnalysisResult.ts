/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * Name of the protagonist
 */
export type ProtagonistName = string;
/**
 * Name of the character the protagonist is speaking to
 */
export type CharacterName = string;
/**
 * Korean speech style used (반말 for informal, 해요체 for polite informal, 하십시오체 for formal)
 */
export type SpeechStyle = '반말' | '해요체' | '하십시오체';
/**
 * List of character interactions found in this segment
 */
export type Interactions = CharacterInteraction[];
/**
 * Whether the protagonist has any dialogue in this segment
 */
export type HasDialogue = boolean;

/**
 * Result of dialogue style analysis for a text segment.
 */
export interface DialogueAnalysisResult {
  protagonist_name: ProtagonistName;
  interactions?: Interactions;
  has_dialogue?: HasDialogue;
  [k: string]: unknown;
}
/**
 * Single interaction between protagonist and another character.
 */
export interface CharacterInteraction {
  character_name: CharacterName;
  speech_style: SpeechStyle;
  [k: string]: unknown;
}
