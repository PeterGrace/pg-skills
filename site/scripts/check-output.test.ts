// Asserts the built site's agent-facing files. Run after `npm run build`.
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { test } from 'node:test';

const dist = new URL('../dist/', import.meta.url);
const read = (path: string) => readFileSync(new URL(path, dist), 'utf8');

test('llms files exist', () => {
	for (const f of ['llms.txt', 'llms-full.txt', 'llms-small.txt']) {
		assert.ok(existsSync(new URL(f, dist)), f);
	}
});

test('llms-full.txt includes the home page and a generated reference page', () => {
	const full = read('llms-full.txt');
	assert.ok(full.includes('These are the skills I use with Claude Code every day'));
	assert.ok(full.includes('End-to-end workflow that turns a GitHub issue'));
});

test('per-page markdown exists for the home page and a nested page', () => {
	assert.ok(read('index.md').startsWith('# pg-skills\n'));
	assert.ok(
		read('reference/skills/github-issue-to-pr.md').startsWith('# github-issue-to-pr\n'),
	);
});
