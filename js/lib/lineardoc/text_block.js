import text_chunk from './text_chunk.js';
import { add_common_tag, dump_tags, esc, get_chunk_boundary_groups, get_close_tag_html, get_open_tag_html, is_transclusion, is_transclusion_fragment, set_link_ids_in_place } from './Utils.js';
import { getProp } from './util.js';

/**
 * A block of annotated inline text
 *
 * @class
 */
class text_block {
	/**
	 * @constructor
	 *
	 * @param {string} text_chunks Annotated inline text
	 * @param {boolean} canSegment This is a block which can be segmented
	 */
	constructor(text_chunks, canSegment) {
		this.text_chunks = text_chunks;
		this.canSegment = canSegment;
		this.offsets = [];
		let cursor = 0;
		for (let i = 0, len = this.text_chunks.length; i < len; i++) {
			this.offsets[i] = {
				start: cursor,
				length: this.text_chunks[i].text.length,
				tags: this.text_chunks[i].tags
			};
			cursor += this.offsets[i].length;
		}
	}

	/**
	 * Get the start and length of each non-common annotation
	 *
	 * @return {Object[]}
	 * @return {number} [i].start {number} Position of each text chunk
	 * @return {number} [i].length {number} Length of each text chunk
	 */
	get_tag_offsets() {
		const textBlock = this,
			commonTags = this.get_common_tags();
		return this.offsets.filter((offset, i) => {
			const text_chunk = textBlock.text_chunks[i];
			return text_chunk.tags.length > commonTags.length && text_chunk.text.length > 0;
		});
	}

	/**
	 * Get the (last) text chunk at a given char offset
	 *
	 * @method
	 * @param {number} charOffset The char offset of the text_chunk
	 * @return {text_chunk} The text chunk
	 */
	get_text_chunk_at(charOffset) {
		let i, len;
		// TODO: bisecting instead of linear search
		for (i = 0, len = this.text_chunks.length - 1; i < len; i++) {
			if (this.offsets[i + 1].start > charOffset) {
				break;
			}
		}
		return this.text_chunks[i];
	}

	/**
	 * Returns the list of SAX tags that apply to the whole text block
	 *
	 * @return {Object[]} List of common SAX tags
	 */
	get_common_tags() {
		if (this.text_chunks.length === 0) {
			return [];
		}
		const commonTags = this.text_chunks[0].tags.slice();
		for (let i = 0, iLen = this.text_chunks.length; i < iLen; i++) {
			const tags = this.text_chunks[i].tags;
			if (tags.length < commonTags.length) {
				commonTags.splice(tags.length);
			}
			for (let j = 0, jLen = commonTags.length; j < jLen; j++) {
				if (commonTags[j].name !== tags[j].name) {
					// truncate
					commonTags.splice(j);
					break;
				}
			}
		}
		return commonTags;
	}

	/**
	 * Create a new text_block, applying our annotations to a translation
	 *
	 * @method
	 * @param {string} targetText Translated plain text
	 * @param {Object[]} rangeMappings Array of source-target range index mappings
	 * @return {text_block} Translated textblock with tags applied
	 */
	translate_tags(targetText, rangeMappings) {
		// map of { offset: x, text_chunks: [...] }
		const emptyTextChunks = {};
		const emptyTextChunkOffsets = [];
		// list of { start: x, length: x, text_chunk: x }
		const text_chunks = [];

		function pushEmptyTextChunks(offset, chunks) {
			for (let c = 0, cLen = chunks.length; c < cLen; c++) {
				text_chunks.push({
					start: offset,
					length: 0,
					text_chunk: chunks[c]
				});
			}
		}

		// Create map of empty text chunks, by offset
		for (let i = 0, iLen = this.text_chunks.length; i < iLen; i++) {
			const text_chunk = this.text_chunks[i];
			const offset = this.offsets[i].start;
			if (text_chunk.text.length > 0) {
				continue;
			}
			if (!emptyTextChunks[offset]) {
				emptyTextChunks[offset] = [];
			}
			emptyTextChunks[offset].push(text_chunk);
		}
		for (const offset in emptyTextChunks) {
			emptyTextChunkOffsets.push(offset);
		}
		emptyTextChunkOffsets.sort((a, b) => a - b);

		for (let i = 0, iLen = rangeMappings.length; i < iLen; i++) {
			// Copy tags from source text start offset
			const rangeMapping = rangeMappings[i];
			const sourceRangeEnd = rangeMapping.source.start + rangeMapping.source.length;
			const targetRangeEnd = rangeMapping.target.start + rangeMapping.target.length;
			const sourceTextChunk = this.get_text_chunk_at(rangeMapping.source.start);
			const text = targetText.slice(rangeMapping.target.start, rangeMapping.target.start + rangeMapping.target.length);
			text_chunks.push({
				start: rangeMapping.target.start,
				length: rangeMapping.target.length,
				text_chunk: new text_chunk(
					text, sourceTextChunk.tags, sourceTextChunk.inline_content
				)
			});

			// Empty source text chunks will not be represented in the target plaintext
			// (because they have no plaintext representation). Therefore we must clone each
			// one manually into the target rich text.

			// Iterate through all remaining emptyTextChunks
			for (let j = 0; j < emptyTextChunkOffsets.length; j++) {
				const offset = emptyTextChunkOffsets[j];
				// Check whether chunk is in range
				if (offset < rangeMapping.source.start || offset > sourceRangeEnd) {
					continue;
				}
				// Push chunk into target text at the current point
				pushEmptyTextChunks(targetRangeEnd, emptyTextChunks[offset]);
				// Remove chunk from remaining list
				delete emptyTextChunks[offset];
				emptyTextChunkOffsets.splice(j, 1);
				// Decrement pointer to match removal
				j--;
			}
		}
		// Sort by start position
		text_chunks.sort((textChunk1, textChunk2) => textChunk1.start - textChunk2.start);
		// Fill in any text_chunk gaps using text with commonTags
		let pos = 0;
		const commonTags = this.get_common_tags();
		for (let i = 0, iLen = text_chunks.length; i < iLen; i++) {
			const text_chunk = text_chunks[i];
			if (text_chunk.start < pos) {
				throw new Error('Overlappping chunks at pos=' + pos + ', text_chunks=' + i + ' start=' + text_chunk.start);
			} else if (text_chunk.start > pos) {
				// Unmapped chunk: insert plaintext and adjust offset
				text_chunks.splice(i, 0, {
					start: pos,
					length: text_chunk.start - pos,
					text_chunk: new text_chunk(
						targetText.slice(pos, text_chunk.start), commonTags
					)
				});
				i++;
				iLen++;
			}
			pos = text_chunk.start + text_chunk.length;
		}

		// Get trailing text and trailing whitespace
		let tail = targetText.slice(pos);
		const tailSpace = tail.match(/\s*$/)[0];
		if (tailSpace) {
			tail = tail.slice(0, tail.length - tailSpace.length);
		}

		if (tail) {
			// Append tail as text with commonTags
			text_chunks.push({
				start: pos,
				length: tail.length,
				text_chunk: new text_chunk(tail, commonTags)
			});
			pos += tail.length;
		}

		// Copy any remaining text_chunks that have no text
		for (let i = 0, iLen = emptyTextChunkOffsets.length; i < iLen; i++) {
			const offset = emptyTextChunkOffsets[i];
			pushEmptyTextChunks(pos, emptyTextChunks[offset]);
		}
		if (tailSpace) {
			// Append tailSpace as text with commonTags
			text_chunks.push({
				start: pos,
				length: tailSpace.length,
				text_chunk: new text_chunk(tailSpace, commonTags)
			});
			pos += tail.length;
		}
		return new text_block(text_chunks.map((x) => x.text_chunk));
	}

	/**
	 * Return plain text representation of the text block
	 *
	 * @return {string} Plain text representation
	 */
	get_plain_text() {
		const text = [];
		for (let i = 0, len = this.text_chunks.length; i < len; i++) {
			text.push(this.text_chunks[i].text);
		}
		return text.join('');
	}

	/**
	 * Return HTML representation of the text block
	 *
	 * @return {string} Plain text representation
	 */
	get_html() {
		const html = [];
		// Start with no tags open
		let oldTags = [];
		for (let i = 0, iLen = this.text_chunks.length; i < iLen; i++) {
			const text_chunk = this.text_chunks[i];

			// Compare tag stacks; render close tags and open tags as necessary
			// Find the highest offset up to which the tags match on
			let matchTop = -1;
			const minLength = Math.min(oldTags.length, text_chunk.tags.length);
			for (let j = 0, jLen = minLength; j < jLen; j++) {
				if (oldTags[j] === text_chunk.tags[j]) {
					matchTop = j;
				} else {
					break;
				}
			}
			for (let j = oldTags.length - 1; j > matchTop; j--) {
				html.push(get_close_tag_html(oldTags[j]));
			}
			for (let j = matchTop + 1, jLen = text_chunk.tags.length; j < jLen; j++) {
				html.push(get_open_tag_html(text_chunk.tags[j]));
			}
			oldTags = text_chunk.tags;

			// Now add text and inline content
			html.push(esc(text_chunk.text));
			if (text_chunk.inline_content) {
				if (text_chunk.inline_content.getHtml) {
					// a sub-doc
					html.push(text_chunk.inline_content.getHtml());
				} else {
					// an empty inline tag
					html.push(get_open_tag_html(text_chunk.inline_content));
					html.push(get_close_tag_html(text_chunk.inline_content));
				}
			}
		}
		// Finally, close any remaining tags
		for (let j = oldTags.length - 1; j >= 0; j--) {
			html.push(get_close_tag_html(oldTags[j]));
		}
		return html.join('');
	}

	/**
	 * Get a root item in the textblock
	 *
	 * @return {Object}
	 */
	getRootItem() {
		for (let i = 0, iLen = this.text_chunks.length; i < iLen; i++) {
			const text_chunk = this.text_chunks[i];

			if (text_chunk.tags.length === 0 && text_chunk.text && text_chunk.text.match(/[^\s]/)) {
				// No tags in this textchunk. See if there is non whitespace text
				return null;
			}

			for (let j = 0, jLen = text_chunk.tags.length; j < jLen; j++) {
				if (text_chunk.tags[j]) {
					return text_chunk.tags[j];
				}
			}
			if (text_chunk.inline_content) {
				const inlineDoc = text_chunk.inline_content;
				// Presence of inlineDoc.getRootItem confirms that inlineDoc is a Doc instance.
				if (inlineDoc && inlineDoc.getRootItem) {
					const rootItem = inlineDoc.getRootItem();
					return rootItem || null;
				} else {
					return inlineDoc;
				}
			}
		}
		return null;
	}

	/**
	 * Get a tag that can represent this textblock.
	 * Textblock can have multiple tags. The first tag is returned.
	 * If there is no tags, but inline_content present, then that is returned.
	 * This is used to extract a unique identifier for the textblock at
	 * Doc#wrapSections.
	 *
	 * @return {Object}
	 */
	getTagForId() {
		return this.getRootItem();
	}

	/**
	 * Segment the text block into sentences
	 *
	 * @method
	 * @param {Function} getBoundaries Function taking plaintext, returning offset array
	 * @param {Function} getNextId Function taking 'segment'|'link', returning next ID
	 * @return {text_block} Segmented version, with added span tags
	 */
	segment(getBoundaries, getNextId) {
		// Setup: currentTextChunks for current segment, and allTextChunks for all segments
		const allTextChunks = [];
		let currentTextChunks = [];
		function flushChunks() {
			if (currentTextChunks.length === 0) {
				return;
			}
			const modifiedTextChunks = add_common_tag(currentTextChunks, {
				name: 'span',
				attributes: {
					class: 'cx-segment',
					'data-segmentid': getNextId('segment')
				}
			});
			set_link_ids_in_place(modifiedTextChunks, getNextId);
			allTextChunks.push.apply(allTextChunks, modifiedTextChunks);
			currentTextChunks = [];
		}

		const rootItem = this.getRootItem();
		if (rootItem && is_transclusion(rootItem)) {
			// Avoid segmenting inside transclusions.
			return this;
		}

		// for each chunk, split at any boundaries that occur inside the chunk
		const groups = get_chunk_boundary_groups(
			getBoundaries(this.get_plain_text()),
			this.text_chunks,
			(text_chunk) => text_chunk.text.length
		);
		let offset = 0;
		for (let i = 0, iLen = groups.length; i < iLen; i++) {
			const group = groups[i];
			let chunk = group.chunk;
			const boundaries = group.boundaries;
			for (let j = 0, jLen = boundaries.length; j < jLen; j++) {
				const relOffset = boundaries[j] - offset;
				if (relOffset === 0) {
					flushChunks();
				} else {
					const leftPart = new text_chunk(
						chunk.text.slice(0, relOffset), chunk.tags.slice()
					);
					const rightPart = new text_chunk(
						chunk.text.slice(relOffset),
						chunk.tags.slice(),
						chunk.inline_content
					);
					currentTextChunks.push(leftPart);
					offset += relOffset;
					flushChunks();
					chunk = rightPart;
				}
			}
			// Even if the chunk is zero-width, it may have references
			currentTextChunks.push(chunk);
			offset += chunk.text.length;
		}
		flushChunks();
		return new text_block(allTextChunks);
	}

	/**
	 * Set the link Ids for the links in all the textchunks in the textblock instance.
	 *
	 * @param {Function} getNextId Function taking 'segment'|'link', returning next ID
	 * @return {text_block} Segmented version, with added span tags
	 */
	setLinkIds(getNextId) {
		set_link_ids_in_place(this.text_chunks, getNextId);
		return this;
	}

	/**
	 * Adapt a text block.
	 *
	 * @param {Function} getAdapter A function that returns an adapter for the given node item
	 * @return {Promise} Promise that resolves the adapted text_block instance
	 */
	adapt(getAdapter) {
		const textChunkPromises = [];

		// Note that we are not using `await` for the better readable code here. `await` will pause
		// the execution till the `async` call is resolved. For us, while looping over these text
		// chunks and tags, this will create a problem. Adaptations often perform asynchrounous API
		// calls to a MediaWiki instance. If we do API calls for each and every item like a link
		// title, it is inefficient. The API accepts a batched list of titles. We do have a batched
		// API mechanism in cxserver, but that works by debouncing the incoming requests with a
		// timeout. Pausing execution here will cause that debounce handler to be called.
		// So we avoid that pausing by just using an array of promises.
		this.text_chunks.forEach((chunk) => {
			const tagPromises = [],
				tags = chunk.tags;
			tags.forEach((tag) => {
				const dataCX = getProp(['attributes', 'data-cx'], tag);
				if (dataCX && Object.keys(JSON.parse(dataCX)).length) {
					// Already adapted
					return;
				}
				const adapter = getAdapter(tag);
				if (adapter && !is_transclusion_fragment(tag)) {
					// This loop get executed for open and close for the tag.
					// Use data-cx to mark this tag processed. The actual adaptation
					// process below will update this value.
					tag.attributes['data-cx'] = JSON.stringify({ adapted: false });
					tagPromises.push(adapter.adapt());
				}
			});
			textChunkPromises.push(Promise.all(tagPromises));
			let adaptPromise;
			if (chunk.inline_content) {
				if (chunk.inline_content.adapt) {
					// Inline content is a sub document.
					adaptPromise = chunk.inline_content.adapt(getAdapter);
				} else {
					// Inline content is inline empty tag. Examples are link, meta etc.
					const adapter = getAdapter(chunk.inline_content);
					if (adapter && !is_transclusion_fragment(chunk.inline_content)) {
						adaptPromise = adapter.adapt();
					}
				}

				if (adaptPromise) {
					textChunkPromises.push(((chk) => adaptPromise
						.then((adaptedInlineContent) => {
							chk.inline_content = adaptedInlineContent;
						}))(chunk));
				}
			}
		});

		return Promise.all(textChunkPromises).then(() => this);
	}

	/**
	 * Dump an XML Array version of the linear representation, for debugging
	 *
	 * @method
	 * @param {string} pad Whitespace to indent XML elements
	 * @return {string[]} Array that will concatenate to an XML string representation
	 */
	dump_xml_array(pad) {
		const dump = [];
		for (let i = 0, len = this.text_chunks.length; i < len; i++) {
			const chunk = this.text_chunks[i];
			const tagsDump = dump_tags(chunk.tags);
			const tagsAttr = tagsDump ? ' tags="' + tagsDump + '"' : '';
			if (chunk.text) {
				dump.push(pad + '<cxtextchunk' + tagsAttr + '>' +
					esc(chunk.text).replace(/\n/g, '&#10;') +
					'</cxtextchunk>');
			}
			if (chunk.inline_content) {
				dump.push(pad + '<cxinlineelement' + tagsAttr + '>');
				if (chunk.inline_content.dump_xml_array) {
					// sub-doc: concatenate
					dump.push.apply(dump, chunk.inline_content.dump_xml_array(pad + '  '));
				} else {
					dump.push(pad + '  <' + chunk.inline_content.name + '/>');
				}
				dump.push(pad + '</cxinlineelement>');
			}
		}
		return dump;
	}

	// camelCase aliases for callers such as Doc
	getHtml() {
		return this.get_html();
	}

	getPlainText() {
		return this.get_plain_text();
	}

	setLinkIds(getNextId) {
		set_link_ids_in_place(this.text_chunks, getNextId);
		return this;
	}

}

export default text_block;
