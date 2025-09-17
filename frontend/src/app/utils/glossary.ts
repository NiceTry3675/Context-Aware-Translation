import { GlossaryTerm } from '../types/ui';

export interface GlossaryDownloadMetadata {
  job_id: number;
  job_filename?: string;
  generated_at: string;
  terms_count: number;
  format: 'glossary/v1';
}

export interface GlossaryDownloadPackage {
  metadata: GlossaryDownloadMetadata;
  terms: GlossaryTerm[];
  extracted_terms?: string[];
  dictionary?: Record<string, string>;
  source_snapshot?: unknown;
}

const SOURCE_KEYS = [
  'source',
  'term',
  'original',
  'source_term',
  'phrase',
  'key',
  'en',
  'english',
  'term_text',
];

const TARGET_KEYS = [
  'korean',
  'translation',
  'translated',
  'target',
  'value',
  'ko',
  'korean_translation',
  'translated_text',
  'korean_text',
];

const NESTED_VALUE_KEYS = ['text', 'value', 'korean', 'translation'];

function toStringValue(value: unknown): string | null {
  if (typeof value === 'string') {
    return value.trim();
  }
  if (value && typeof value === 'object') {
    for (const key of NESTED_VALUE_KEYS) {
      const nested = (value as Record<string, unknown>)[key];
      if (typeof nested === 'string') {
        return nested.trim();
      }
    }
  }
  return null;
}

function addEntry(store: Map<string, GlossaryTerm>, source?: string | null, korean?: string | null) {
  if (!source || !korean) return;
  const normalizedSource = source.trim();
  const normalizedKorean = korean.trim();
  if (!normalizedSource) return;
  store.set(normalizedSource, { source: normalizedSource, korean: normalizedKorean });
}

function extractFromObject(store: Map<string, GlossaryTerm>, obj: Record<string, unknown>) {
  const keys = Object.keys(obj);
  const hasKnownField = keys.some((key) => SOURCE_KEYS.includes(key) || TARGET_KEYS.includes(key));

  if (!hasKnownField && keys.length > 0 && keys.every((key) => typeof obj[key] === 'string')) {
    keys.forEach((key) => addEntry(store, key, obj[key] as string));
    return;
  }

  let source: string | null = null;
  for (const key of SOURCE_KEYS) {
    if (key in obj) {
      source = toStringValue(obj[key]);
      if (source) break;
    }
  }

  let korean: string | null = null;
  for (const key of TARGET_KEYS) {
    if (key in obj) {
      korean = toStringValue(obj[key]);
      if (korean) break;
    }
  }

  addEntry(store, source, korean);
}

function visitValue(store: Map<string, GlossaryTerm>, value: unknown, seen: Set<unknown>) {
  if (!value || seen.has(value)) return;
  if (Array.isArray(value)) {
    seen.add(value);
    value.forEach((item) => visitValue(store, item, seen));
    return;
  }
  if (typeof value === 'object') {
    seen.add(value);
    const obj = value as Record<string, unknown>;
    extractFromObject(store, obj);

    const nestedCandidates: unknown[] = [];
    if ('translated_terms' in obj) {
      const translatedTerms = obj['translated_terms'] as Record<string, unknown>;
      if (translatedTerms && typeof translatedTerms === 'object') {
        nestedCandidates.push((translatedTerms as Record<string, unknown>)['translations']);
      }
    }
    if ('glossary' in obj) nestedCandidates.push(obj['glossary']);
    if ('terms' in obj) nestedCandidates.push(obj['terms']);
    if ('translations' in obj) nestedCandidates.push(obj['translations']);
    if ('items' in obj) nestedCandidates.push(obj['items']);
    if ('entries' in obj) nestedCandidates.push(obj['entries']);
    if ('data' in obj) nestedCandidates.push(obj['data']);
    if ('values' in obj) nestedCandidates.push(obj['values']);

    nestedCandidates.forEach((candidate) => visitValue(store, candidate, seen));
  }
}

export function normalizeGlossaryData(raw: unknown): GlossaryTerm[] {
  const store = new Map<string, GlossaryTerm>();
  visitValue(store, raw, new Set());
  return Array.from(store.values());
}

export function mergeGlossaryTerms(base: GlossaryTerm[], incoming: GlossaryTerm[]): GlossaryTerm[] {
  const merged = new Map<string, GlossaryTerm>();
  base.forEach((term) => {
    if (!term?.source) return;
    merged.set(term.source.trim(), { ...term, source: term.source.trim(), korean: term.korean?.trim() || '' });
  });
  incoming.forEach((term) => {
    if (!term?.source) return;
    merged.set(term.source.trim(), { ...term, source: term.source.trim(), korean: term.korean?.trim() || '' });
  });
  return Array.from(merged.values());
}

export function createGlossaryDownloadPackage(params: {
  jobId: number;
  jobFilename?: string;
  terms: GlossaryTerm[];
  extractedTerms?: string[] | null;
  includeDictionary?: boolean;
  sourceSnapshot?: unknown;
}): GlossaryDownloadPackage {
  const uniqueTermsMap = new Map<string, GlossaryTerm>();
  params.terms.forEach((term) => {
    const source = term.source?.trim();
    const korean = term.korean?.trim();
    if (!source || !korean) return;

    if (!uniqueTermsMap.has(source)) {
      uniqueTermsMap.set(source, {
        source,
        korean,
        category: term.category,
        note: term.note,
      });
    }
  });

  const terms = Array.from(uniqueTermsMap.values()).sort((a, b) => a.source.localeCompare(b.source));

  let extractedTerms: string[] | undefined;
  if (params.extractedTerms && params.extractedTerms.length > 0) {
    extractedTerms = Array.from(new Set(
      params.extractedTerms.map((term) => term.trim()).filter(Boolean)
    ));
  }

  let dictionary: Record<string, string> | undefined;
  if (params.includeDictionary) {
    dictionary = terms.reduce<Record<string, string>>((acc, term) => {
      acc[term.source] = term.korean;
      return acc;
    }, {});
  }

  const pkg: GlossaryDownloadPackage = {
    metadata: {
      job_id: params.jobId,
      job_filename: params.jobFilename,
      generated_at: new Date().toISOString(),
      terms_count: terms.length,
      format: 'glossary/v1',
    },
    terms,
  };

  if (extractedTerms && extractedTerms.length > 0) {
    pkg.extracted_terms = extractedTerms;
  }

  if (dictionary) {
    pkg.dictionary = dictionary;
  }

  if (params.sourceSnapshot) {
    pkg.source_snapshot = params.sourceSnapshot;
  }

  return pkg;
}

export function serializeGlossaryDownloadPackage(pkg: GlossaryDownloadPackage): string {
  return JSON.stringify(pkg, null, 2);
}
