import Text_chunk from './Text_chunk.js';
import { add_common_tag, dump_tags, esc, get_chunk_boundary_groups, get_close_tag_html, get_open_tag_html, is_transclusion, is_transclusion_fragment, set_link_ids_in_place } from './Utils.js';
import { get_prop } from './../util.js';

/**
 * A block of annotated inline text
 *
 * @class
 */
class Text_block {
	/**
	 * @constructor
	 *
	 * @param {string} text_chunks Annotated inline text
	 * @param {boolean} can_segment This is a block which can be segmented
	 */
	constructor(text_chunks, can_segment) {
		this.text_chunks = text_chunks;
		this.can_segment = can_segment;
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
		const text_block = this,
			common_tags = this.get_common_tags();
		return this.offsets.filter((offset, i) => {
			const text_chunk = text_block.text_chunks[i];
			return text_chunk.tags.length > common_tags.length && text_chunk.text.length > 0;
		});
	}

	/**
	 * Get the (last) text chunk at a given char offset
	 *
	 * @method
	 * @param {number} char_offset The char offset of the text_chunk
	 * @return {Text_chunk} The text chunk
	 */
	get_text_chunk_at(char_offset) {
		let i, len;
		// TODO: bisecting instead of linear search
		for (i = 0, len = this.text_chunks.length - 1; i < len; i++) {
			if (this.offsets[i + 1].start > char_offset) {
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
		const common_tags = this.text_chunks[0].tags.slice();
		for (let i = 0, i_len = this.text_chunks.length; i < i_len; i++) {
			const tags = this.text_chunks[i].tags;
			if (tags.length < common_tags.length) {
				common_tags.splice(tags.length);
			}
			for (let j = 0, j_len = common_tags.length; j < j_len; j++) {
				if (common_tags[j].name !== tags[j].name) {
					// truncate
					common_tags.splice(j);
					break;
				}
			}
		}
		return common_tags;
	}

	/**
	 * Create a new Text_block, applying our annotations to a translation
	 *
	 * @method
	 * @param {string} target_text Translated plain text
	 * @param {Object[]} range_mappings Array of source-target range index mappings
	 * @return {Text_block} Translated textblock with tags applied
	 */
	translate_tags(target_text, range_mappings) {
		// map of { offset: x, text_chunks: [...] }
		const empty_text_chunks = {};
		const empty_text_chunk_offsets = [];
		// list of { start: x, length: x, text_chunk: x }
		const text_chunks = [];

		function push_empty_text_chunks(offset, chunks) {
			for (let c = 0, c_len = chunks.length; c < c_len; c++) {
				text_chunks.push({
					start: offset,
					length: 0,
					text_chunk: chunks[c]
				});
			}
		}

		// Create map of empty text chunks, by offset
		for (let i = 0, i_len = this.text_chunks.length; i < i_len; i++) {
			const text_chunk = this.text_chunks[i];
			const offset = this.offsets[i].start;
			if (text_chunk.text.length > 0) {
				continue;
			}
			if (!empty_text_chunks[offset]) {
				empty_text_chunks[offset] = [];
			}
			empty_text_chunks[offset].push(text_chunk);
		}
		for (const offset in empty_text_chunks) {
			empty_text_chunk_offsets.push(offset);
		}
		empty_text_chunk_offsets.sort((a, b) => a - b);

		for (let i = 0, i_len = range_mappings.length; i < i_len; i++) {
			// Copy tags from source text start offset
			const range_mapping = range_mappings[i];
			const source_range_end = range_mapping.source.start + range_mapping.source.length;
			const target_range_end = range_mapping.target.start + range_mapping.target.length;
			const source_text_chunk = this.get_text_chunk_at(range_mapping.source.start);
			const text = target_text.slice(range_mapping.target.start, range_mapping.target.start + range_mapping.target.length);
			text_chunks.push({
				start: range_mapping.target.start,
				length: range_mapping.target.length,
				text_chunk: new Text_chunk(
					text, source_text_chunk.tags, source_text_chunk.inline_content
				)
			});

			// Empty source text chunks will not be represented in the target plaintext
			// (because they have no plaintext representation). Therefore we must clone each
			// one manually into the target rich text.

			// Iterate through all remaining empty_text_chunks
			for (let j = 0; j < empty_text_chunk_offsets.length; j++) {
				const offset = empty_text_chunk_offsets[j];
				// Check whether chunk is in range
				if (offset < range_mapping.source.start || offset > source_range_end) {
					continue;
				}
				// Push chunk into target text at the current point
				push_empty_text_chunks(target_range_end, empty_text_chunks[offset]);
				// Remove chunk from remaining list
				delete empty_text_chunks[offset];
				empty_text_chunk_offsets.splice(j, 1);
				// Decrement pointer to match removal
				j--;
			}
		}
		// Sort by start position
		text_chunks.sort((text_chunk1, text_chunk2) => text_chunk1.start - text_chunk2.start);
		// Fill in any text_chunk gaps using text with common_tags
		let pos = 0;
		const common_tags = this.get_common_tags();
		for (let i = 0, i_len = text_chunks.length; i < i_len; i++) {
			const text_chunk = text_chunks[i];
			if (text_chunk.start < pos) {
				throw new Error('Overlappping chunks at pos=' + pos + ', text_chunks=' + i + ' start=' + text_chunk.start);
			} else if (text_chunk.start > pos) {
				// Unmapped chunk: insert plaintext and adjust offset
				text_chunks.splice(i, 0, {
					start: pos,
					length: text_chunk.start - pos,
					text_chunk: new Text_chunk(
						target_text.slice(pos, text_chunk.start), common_tags
					)
				});
				i++;
				i_len++;
			}
			pos = text_chunk.start + text_chunk.length;
		}

		// Get trailing text and trailing whitespace
		let tail = target_text.slice(pos);
		const tail_space = tail.match(/\s*$/)[0];
		if (tail_space) {
			tail = tail.slice(0, tail.length - tail_space.length);
		}

		if (tail) {
			// Append tail as text with common_tags
			text_chunks.push({
				start: pos,
				length: tail.length,
				text_chunk: new Text_chunk(tail, common_tags)
			});
			pos += tail.length;
		}

		// Copy any remaining text_chunks that have no text
		for (let i = 0, i_len = empty_text_chunk_offsets.length; i < i_len; i++) {
			const offset = empty_text_chunk_offsets[i];
			push_empty_text_chunks(pos, empty_text_chunks[offset]);
		}
		if (tail_space) {
			// Append tail_space as text with common_tags
			text_chunks.push({
				start: pos,
				length: tail_space.length,
				text_chunk: new Text_chunk(tail_space, common_tags)
			});
			pos += tail.length;
		}
		return new Text_block(text_chunks.map((x) => x.text_chunk));
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
		let old_tags = [];
		for (let i = 0, i_len = this.text_chunks.length; i < i_len; i++) {
			const text_chunk = this.text_chunks[i];

			// Compare tag stacks; render close tags and open tags as necessary
			// Find the highest offset up to which the tags match on
			let match_top = -1;
			const min_length = Math.min(old_tags.length, text_chunk.tags.length);
			for (let j = 0, j_len = min_length; j < j_len; j++) {
				if (old_tags[j] === text_chunk.tags[j]) {
					match_top = j;
				} else {
					break;
				}
			}
			for (let j = old_tags.length - 1; j > match_top; j--) {
				html.push(get_close_tag_html(old_tags[j]));
			}
			for (let j = match_top + 1, j_len = text_chunk.tags.length; j < j_len; j++) {
				html.push(get_open_tag_html(text_chunk.tags[j]));
			}
			old_tags = text_chunk.tags;

			// Now add text and inline content
			html.push(esc(text_chunk.text));
			if (text_chunk.inline_content) {
				if (text_chunk.inline_content.get_html) {
					// a sub-doc
					html.push(text_chunk.inline_content.get_html());
				} else {
					// an empty inline tag
					html.push(get_open_tag_html(text_chunk.inline_content));
					html.push(get_close_tag_html(text_chunk.inline_content));
				}
			}
		}
		// Finally, close any remaining tags
		for (let j = old_tags.length - 1; j >= 0; j--) {
			html.push(get_close_tag_html(old_tags[j]));
		}
		return html.join('');
	}

	/**
	 * Get a root item in the textblock
	 *
	 * @return {Object}
	 */
	get_root_item() {
		for (let i = 0, i_len = this.text_chunks.length; i < i_len; i++) {
			const text_chunk = this.text_chunks[i];

			if (text_chunk.tags.length === 0 && text_chunk.text && text_chunk.text.match(/[^\s]/)) {
				// No tags in this textchunk. See if there is non whitespace text
				return null;
			}

			for (let j = 0, j_len = text_chunk.tags.length; j < j_len; j++) {
				if (text_chunk.tags[j]) {
					return text_chunk.tags[j];
				}
			}
			if (text_chunk.inline_content) {
				const inline_doc = text_chunk.inline_content;
				// Presence of inline_doc.get_root_item confirms that inline_doc is a Doc instance.
				if (inline_doc && inline_doc.get_root_item) {
					const root_item = inline_doc.get_root_item();
					return root_item || null;
				} else {
					return inline_doc;
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
	 * Doc#wrap_sections.
	 *
	 * @return {Object}
	 */
	get_tag_for_id() {
		return this.get_root_item();
	}

	/**
	 * Segment the text block into sentences
	 *
	 * @method
	 * @param {Function} get_boundaries Function taking plaintext, returning offset array
	 * @param {Function} get_next_id Function taking 'segment'|'link', returning next ID
	 * @return {Text_block} Segmented version, with added span tags
	 */
	segment(get_boundaries, get_next_id) {
		// Setup: current_text_chunks for current segment, and all_text_chunks for all segments
		const all_text_chunks = [];
		let current_text_chunks = [];
		function flush_chunks() {
			if (current_text_chunks.length === 0) {
				return;
			}
			const modified_text_chunks = add_common_tag(current_text_chunks, {
				name: 'span',
				attributes: {
					class: 'cx-segment',
					'data-segmentid': get_next_id('segment')
				}
			});
			set_link_ids_in_place(modified_text_chunks, get_next_id);
			all_text_chunks.push.apply(all_text_chunks, modified_text_chunks);
			current_text_chunks = [];
		}

		const root_item = this.get_root_item();
		if (root_item && is_transclusion(root_item)) {
			// Avoid segmenting inside transclusions.
			return this;
		}

		// for each chunk, split at any boundaries that occur inside the chunk
		const groups = get_chunk_boundary_groups(
			get_boundaries(this.get_plain_text()),
			this.text_chunks,
			(text_chunk) => text_chunk.text.length
		);
		let offset = 0;
		for (let i = 0, i_len = groups.length; i < i_len; i++) {
			const group = groups[i];
			let chunk = group.chunk;
			const boundaries = group.boundaries;
			for (let j = 0, j_len = boundaries.length; j < j_len; j++) {
				const rel_offset = boundaries[j] - offset;
				if (rel_offset === 0) {
					flush_chunks();
				} else {
					const left_part = new Text_chunk(
						chunk.text.slice(0, rel_offset), chunk.tags.slice()
					);
					const right_part = new Text_chunk(
						chunk.text.slice(rel_offset),
						chunk.tags.slice(),
						chunk.inline_content
					);
					current_text_chunks.push(left_part);
					offset += rel_offset;
					flush_chunks();
					chunk = right_part;
				}
			}
			// Even if the chunk is zero-width, it may have references
			current_text_chunks.push(chunk);
			offset += chunk.text.length;
		}
		flush_chunks();
		return new Text_block(all_text_chunks);
	}

	/**
	 * Set the link Ids for the links in all the textchunks in the textblock instance.
	 *
	 * @param {Function} get_next_id Function taking 'segment'|'link', returning next ID
	 * @return {Text_block} Segmented version, with added span tags
	 */
	set_link_ids(get_next_id) {
		set_link_ids_in_place(this.text_chunks, get_next_id);
		return this;
	}

	/**
	 * Adapt a text block.
	 *
	 * @param {Function} get_adapter A function that returns an adapter for the given node item
	 * @return {Promise} Promise that resolves the adapted Text_block instance
	 */
	adapt(get_adapter) {
		const text_chunk_promises = [];

		// Note that we are not using `await` for the better readable code here. `await` will pause
		// the execution till the `async` call is resolved. For us, while looping over these text
		// chunks and tags, this will create a problem. Adaptations often perform asynchrounous API
		// calls to a Media_wiki instance. If we do API calls for each and every item like a link
		// title, it is inefficient. The API accepts a batched list of titles. We do have a batched
		// API mechanism in cxserver, but that works by debouncing the incoming requests with a
		// timeout. Pausing execution here will cause that debounce handler to be called.
		// So we avoid that pausing by just using an array of promises.
		this.text_chunks.for_each((chunk) => {
			const tag_promises = [],
				tags = chunk.tags;
			tags.for_each((tag) => {
				const dataCX = get_prop(['attributes', 'data-cx'], tag);
				if (dataCX && Object.keys(JSON.parse(dataCX)).length) {
					// Already adapted
					return;
				}
				const adapter = get_adapter(tag);
				if (adapter && !is_transclusion_fragment(tag)) {
					// This loop get executed for open and close for the tag.
					// Use data-cx to mark this tag processed. The actual adaptation
					// process below will update this value.
					tag.attributes['data-cx'] = JSON.stringify({ adapted: false });
					tag_promises.push(adapter.adapt());
				}
			});
			text_chunk_promises.push(Promise.all(tag_promises));
			let adapt_promise;
			if (chunk.inline_content) {
				if (chunk.inline_content.adapt) {
					// Inline content is a sub document.
					adapt_promise = chunk.inline_content.adapt(get_adapter);
				} else {
					// Inline content is inline empty tag. Examples are link, meta etc.
					const adapter = get_adapter(chunk.inline_content);
					if (adapter && !is_transclusion_fragment(chunk.inline_content)) {
						adapt_promise = adapter.adapt();
					}
				}

				if (adapt_promise) {
					text_chunk_promises.push(((chk) => adapt_promise
						.then((adapted_inline_content) => {
							chk.inline_content = adapted_inline_content;
						}))(chunk));
				}
			}
		});

		return Promise.all(text_chunk_promises).then(() => this);
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
			const tags_dump = dump_tags(chunk.tags);
			const tags_attr = tags_dump ? ' tags="' + tags_dump + '"' : '';
			if (chunk.text) {
				dump.push(pad + '<cxtextchunk' + tags_attr + '>' +
					esc(chunk.text).replace(/\n/g, '&#10;') +
					'</cxtextchunk>');
			}
			if (chunk.inline_content) {
				dump.push(pad + '<cxinlineelement' + tags_attr + '>');
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

	// camel_case aliases for callers such as Doc
	get_html() {
		return this.get_html();
	}

	get_plain_text() {
		return this.get_plain_text();
	}

	set_link_ids(get_next_id) {
		set_link_ids_in_place(this.text_chunks, get_next_id);
		return this;
	}

}

export default Text_block;
