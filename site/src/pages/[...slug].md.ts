import type { APIRoute, GetStaticPaths } from 'astro';
import { getCollection, type CollectionEntry } from 'astro:content';
import {
	markdownContentType,
	pageMarkdown,
	pageSlug,
	publishedEntries,
} from '../lib/page-markdown.ts';

// A markdown copy of every docs page, for AI agents: /reference/x/ is also served as
// /reference/x.md, and the home page (id `index`) as /index.md. See lib/page-markdown.ts.
export const getStaticPaths = (async () => {
	const docs = publishedEntries(await getCollection('docs'));
	return docs.map((entry) => ({ params: { slug: pageSlug(entry) }, props: { entry } }));
}) satisfies GetStaticPaths;

export const GET: APIRoute = ({ props }) => {
	const { entry } = props as { entry: CollectionEntry<'docs'> };
	return new Response(pageMarkdown(entry), { headers: { 'Content-Type': markdownContentType } });
};
