import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
	markdownContentType,
	pageMarkdown,
	pageSlug,
	publishedEntries,
	type PageEntry,
} from './page-markdown.ts';

const home: PageEntry = {
	id: 'index',
	data: { title: 'pg-skills' },
	body: "import { Card } from '@astrojs/starlight/components';\n\n<Card title=\"x\" />\n",
};
const nested: PageEntry = {
	id: 'reference/skills/github-issue-to-pr',
	data: { title: 'github-issue-to-pr' },
	body: '\nSource text\n',
};
const draft: PageEntry = { id: 'how-to/wip', data: { title: 'WIP', draft: true }, body: 'x' };

test('the home page keeps the id index', () => {
	assert.equal(pageSlug(home), 'index');
});

test('a nested id keeps its directories', () => {
	assert.equal(pageSlug(nested), 'reference/skills/github-issue-to-pr');
});

test('drafts get no route', () => {
	const slugs = publishedEntries([home, nested, draft]).map(pageSlug);
	assert.deepEqual(slugs, ['index', 'reference/skills/github-issue-to-pr']);
});

test('the body is the title heading, then the trimmed source', () => {
	assert.equal(pageMarkdown(nested), '# github-issue-to-pr\n\nSource text\n');
});

test('the home page is served as its raw MDX source', () => {
	const out = pageMarkdown(home);
	assert.ok(out.startsWith('# pg-skills\n\nimport { Card }'));
	assert.ok(out.includes('<Card title="x" />'));
});

test('an entry with no body still gets its heading', () => {
	assert.equal(pageMarkdown({ id: 'a', data: { title: 'A' } }), '# A\n\n\n');
});

test('the content type is markdown', () => {
	assert.equal(markdownContentType, 'text/markdown; charset=utf-8');
});
