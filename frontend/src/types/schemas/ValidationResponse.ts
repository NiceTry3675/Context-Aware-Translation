/* eslint-disable */
/**
 * This file was automatically generated from JSON Schema.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source Pydantic model
 * in core/schemas and regenerate this file.
 */

/**
 * 문제가 되는 현재 한국어 문장 (최대 1~2문장)
 */
export type CurrentKoreanSentence = string;
/**
 * 대응하는 원문 문장 (최대 1~2문장)
 */
export type ProblematicSourceSentence = string;
/**
 * 왜 문제인지
 */
export type Reason = string;
/**
 * 이슈 차원(카테고리)
 */
export type Dimension =
  | 'completeness'
  | 'accuracy'
  | 'addition'
  | 'name_consistency'
  | 'dialogue_style'
  | 'flow'
  | 'other';
/**
 * 이슈의 심각도. 1(사소함), 2(중대함), 3(치명적) 중 하나의 숫자로 표기.
 */
export type Severity = '1' | '2' | '3';
/**
 * 권장 수정 번역문
 */
export type RecommendKoreanSentence = string;
/**
 * 보조 라벨(예: terminology, formality, punctuation)
 */
export type Tags = string[];
/**
 * List of validation issues found. Empty list if no issues.
 */
export type Cases = ValidationCase[];

/**
 * Response model for validation results.
 */
export interface ValidationResponse {
  cases?: Cases;
  [k: string]: unknown;
}
/**
 * Individual validation issue found in translation.
 */
export interface ValidationCase {
  current_korean_sentence: CurrentKoreanSentence;
  problematic_source_sentence: ProblematicSourceSentence;
  reason: Reason;
  dimension: Dimension;
  severity: Severity;
  recommend_korean_sentence: RecommendKoreanSentence;
  tags?: Tags;
  [k: string]: unknown;
}
