// Pure helpers for the per-page markdown endpoint (src/pages/[...slug].md.ts), kept free
// of Astro imports so `node --test` can run them.

/** The parts of a docs collection entry the markdown copy needs. */
export interface PageEntry {
	id: string;
	body?: string;
	data: { title: string; draft?: boolean };
}

/** The path segment an entry is served under: its id, which has no base or extension. */
export function pageSlug(entry: PageEntry): string {
	return entry.id;
}

/** Entries that get a markdown copy: everything except drafts. */
export function publishedEntries<T extends PageEntry>(entries: T[]): T[] {
	return entries.filter((entry) => !entry.data.draft);
}

/** The served body: the title as a top-level heading, then the entry's raw source. */
export function pageMarkdown(entry: PageEntry): string {
	return `# ${entry.data.title}\n\n${(entry.body ?? '').trim()}\n`;
}

export const markdownContentType = 'text/markdown; charset=utf-8';
