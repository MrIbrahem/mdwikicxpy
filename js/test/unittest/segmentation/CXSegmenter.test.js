import { describe, it } from 'node:test';
import { readFileSync } from 'fs';
import { deepEqual } from '../utils/assert.js';
import {
	MwContextualizer,
	Normalizer,
	Parser
} from '../../../../js/lib/lineardoc/index.js';
import Segmenter from '../../../../js/lib/segmentation/CXSegmenter.js';
import allTests from './SegmentationTests.json' with { type: 'json' };

import { fileURLToPath } from 'url';
import path from 'path';

// Convert file URL to a valid path compatible with Windows
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function normalize(html) {
	const normalizer = new Normalizer();
	normalizer.init();
	normalizer.write(html.replace(/[\t\r\n]+/gm, ''));
	return normalizer.getHtml();
}

function getParsedDoc(content) {
	const parser = new Parser(new MwContextualizer());
	parser.init();
	parser.write(content);
	return parser.builder.doc;
}

function runTest(test, lang) {
	const sourcePath = path.join(__dirname, 'data', test.source);
	const resultPath = path.join(__dirname, 'data', test.result);

	const testData = readFileSync(sourcePath, 'utf8');
	const parsedDoc = getParsedDoc(testData);
	const segmenter = new Segmenter();
	const segmentedLinearDoc = segmenter.segment(parsedDoc, lang);
	const result = normalize(segmentedLinearDoc.getHtml());
	const expectedResultData = normalize(
		readFileSync(resultPath, 'utf8')
	);
	it('should not have any errors when: ' + test.desc, () => {
		deepEqual(result, expectedResultData, test.source + ': ' + test.desc || '');
	});
}

for (const lang in allTests) {
	describe('Segmentation tests for ' + lang, () => {
		const tests = allTests[lang];
		const len = tests.length;
		for (let i = 0; i < len; i++) {
			if (tests[i].skip) {
				continue;
			}
			runTest(tests[i], lang);
		}
	});
}
