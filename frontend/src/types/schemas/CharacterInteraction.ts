/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * Name of the character the protagonist is speaking to
 */
export type CharacterName = string;
/**
 * Korean speech style used (반말 for informal, 해요체 for polite informal, 하십시오체 for formal)
 */
export type SpeechStyle = '반말' | '해요체' | '하십시오체';

/**
 * Single interaction between protagonist and another character.
 */
export interface CharacterInteraction {
  character_name: CharacterName;
  speech_style: SpeechStyle;
  [k: string]: unknown;
}
