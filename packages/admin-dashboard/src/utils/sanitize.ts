import DOMPurify from 'dompurify'

/**
 * Sanitize a string value from an API response to prevent XSS.
 * Strips all HTML tags and attributes — API data should be plain text.
 */
export function sanitizeText(dirty: string): string {
  return DOMPurify.sanitize(dirty, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
}

/**
 * Recursively sanitize all string values in an object.
 * Returns a new object (no mutation).
 */
export function sanitizeRecord<T>(obj: T): T {
  if (typeof obj === 'string') {
    return sanitizeText(obj) as unknown as T
  }
  if (Array.isArray(obj)) {
    return obj.map(sanitizeRecord) as unknown as T
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, value]) => [
        key,
        sanitizeRecord(value),
      ]),
    ) as T
  }
  return obj
}
