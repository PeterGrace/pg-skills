import type { APIRoute, GetStaticPaths } from 'astro';
import { getCollection } from 'astro:content';

// A markdown copy of every docs page, for AI agents: /reference/x/ is also served as
// /reference/x.md. The entry id has no base or extension, and the home page's id is
// `index`, so it is served as /index.md.
export const getStaticPaths = (async () => {
	const docs = await getCollection('docs', ({ data }) => !data.draft);
	return docs.map((entry) => ({ params: { slug: entry.id }, props: { entry } }));
}) satisfies GetStaticPaths;

export const GET: APIRoute = ({ props }) => {
	const { entry } = props as { entry: Awaited<ReturnType<typeof getCollection<'docs'>>>[number] };
	const body = `# ${entry.data.title}\n\n${(entry.body ?? '').trim()}\n`;
	return new Response(body, { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });
};
