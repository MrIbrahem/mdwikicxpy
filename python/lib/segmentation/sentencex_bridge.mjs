/**
 * Node.js bridge that exposes the upstream `sentencex` sentence segmenter
 * (installed under js/node_modules) to the Python port of cxserver.
 *
 * The Python code (python/lib/segmentation/cx_segmenter.py) spawns this script
 * once per process and talks to it over stdin/stdout using a line-delimited
 * JSON request/response protocol:
 *
 *   request : {"lang": "<code>", "text": "<plain text>"}
 *   response: [<startOffset>, ...]   (sentence start offsets, like the JS CXSegmenter)
 *
 * The boundary computation mirrors js/lib/segmentation/CXSegmenter.js exactly:
 * sentencex returns the sentence *strings*, and we map each to its first index
 * in the original text via String.prototype.indexOf.
 */
// Resolve sentencex from js/node_modules regardless of where node is launched.
// import segment from '../../../js/node_modules/sentencex/dist/esm/index.js';
import segment from '../../../js/node_modules/sentencex/index.mjs';
// const { segment } = require('sentencex');
/**
 * Compute sentence start offsets for a piece of plain text.
 *
 * @param {string} lang Language code
 * @param {string} text Plain text to segment
 * @return {number[]} Sentence start offsets (matching the JS CXSegmenter output)
 */
function boundariesFor(lang, text) {
	const sentences = segment(lang, text);
	const boundaries = [];
	for (let i = 0; i < sentences.length; i++) {
		if (sentences[i].trim().length) {
			boundaries.push(text.indexOf(sentences[i]));
		}
	}
	return boundaries;
}

let buffer = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
	buffer += chunk;
	let newlineIndex;
	while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
		const line = buffer.slice(0, newlineIndex);
		buffer = buffer.slice(newlineIndex + 1);
		if (!line.trim()) {
			continue;
		}
		try {
			const request = JSON.parse(line);
			const result = boundariesFor(request.lang, request.text);
			process.stdout.write(JSON.stringify(result) + '\n');
		} catch (error) {
			process.stdout.write(JSON.stringify({ error: String(error) }) + '\n');
		}
	}
});
