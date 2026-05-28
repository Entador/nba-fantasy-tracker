/**
 * Get today's date in Eastern Time (America/New_York).
 * NBA schedule uses ET, so we align with it for consistent "tonight" behavior.
 */
export function getTodayET(): string {
  return new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/New_York',
  });
}

/** Convert a Date object to a YYYY-MM-DD string in local time. */
export function toDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
