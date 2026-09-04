import Text_chunk from './TextChunk.js';
import { add_common_tag, dump_tags, esc, get_chunk_boundary_groups, get_close_tag_html, get_open_tag_html, is_transclusion, is_transclusion_fragment, set_link_ids_in_place } from './Utils.js';
import { get_prop } from './../util.js';

/**
 * Whether the text chunk represents a reference marker.
 *
 * @param {Text_chunk} chunk
 * @return {boolean}
 */
function is_reference_chunk(chunk) {
	const inline = chunk.inline_content;
	if (inline && inline.wrapper_tag && inline.wrapper_tag.attributes &&
		is_reference(inline.wrapper_tag)) {
		return true;
	}
	return chunk.tags.some((tag) => tag.attributes && is_reference(tag));
}

// Placeholder characters used when a text block is flattened to a plain
// string. These are Unicode noncharacters (U+FDD0 and U+FDD1), guaranteed
// absent from interchanged text.
const REF_CHAR = '\uFDD0';
const INLINE_CHAR = '\uFDD1';

/**
 * Flatten chunks into one item per string position. Reference markers and
 * other inline content become a single placeholder item; text chunks
 * contribute one item per code unit, each remembering its source chunk.
 * The concatenated chars form the plain text of the block, so rules matched
 * against it do not depend on how the text is split into chunks.
 *
 * @param {Text_chunk[]} chunks
 * @return {Object[]} Items of shape { char, chunk, atomic }
 */
function to_char_items(chunks) {
	const items = [];
	for (const chunk of chunks) {
		if (is_reference_chunk(chunk)) {
			items.push({ char: REF_CHAR, chunk, atomic: true });
		} else if (chunk.inline_content) {
			items.push({ char: INLINE_CHAR, chunk, atomic: true });
		} else {
			for (let i = 0; i < chunk.text.length; i++) {
				items.push({ char: chunk.text[i], chunk });
			}
		}
	}
	return items;
}

/**
 * Rebuild a chunk list from (reordered) flattened items. Atomic items emit
 * their original chunk; consecutive characters from the same source chunk
 * merge back into a single chunk. Source tags arrays are reused by
 * reference, which keeps the serialized markup of untouched regions
 * byte-identical.
 *
 * @param {Object[]} items Items produced by to_char_items
 * @return {Text_chunk[]} New chunk list
 */
function to_chunks(items) {
	const chunks = [];
	let text = '';
	let source = null;
	const flush = () => {
		if (text !== '') {
			chunks.push(new Text_chunk(text, source.tags));
			text = '';
		}
	};
	for (const item of items) {
		if (item.atomic) {
			flush();
			source = null;
			chunks.push(item.chunk);
		} else if (item.chunk === source) {
			text += item.char;
		} else {
			flush();
			source = item.chunk;
			text = item.char;
		}
	}
	flush();
	return chunks;
}

/**
 * Escape a character for use inside a regex character class.
 *
 * @param {string} char
 * @return {string}
 */
function escape_for_char_class(char) {
	return char.replace(/[\\\]^-]/g, '\\$&');
}

/**
 * Move sentence punctuation across reference runs to the side preferred by
 * the target language. The block is flattened to a plain string in which
 * every reference marker is a single placeholder character, so the rule is
 * one regex over the visible text, independent of chunk boundaries. The
 * whitespace that separated the word, punctuation and references is dropped
 * so that the three stay glued together; whitespace between the references
 * of a run is preserved.
 *
 * @param {Text_chunk[]} chunks
 * @param {string} policy 'before' or 'after'
 * @param {string[]} punctuation Punctuation marks to reposition around
 * @return {Text_chunk[]} New chunk list
 */
function move_punctuation_across_references(chunks, policy, punctuation) {
	const items = to_char_items(chunks);
	const text = items.map((item) => item.char).join('');
	const punct = '([' + punctuation.map(escape_for_char_class).join('') + '])';
	const run = `(${REF_CHAR}(?:\\s*${REF_CHAR})*)`;
	const pattern = policy === 'before' ?
		new Reg_exp(`${punct}\\s*${run}`, 'gd') :
		new Reg_exp(`\\s*${run}\\s*${punct}`, 'gd');

	const reordered = [];
	let position = 0;
	for (const match of text.match_all(pattern)) {
		const [run_start, run_end] = match.indices[policy === 'before' ? 2 : 1];
		const run_items = items.slice(run_start, run_end);
		// The moved punctuation inherits the reference tags (e.g. the segment
		// span) so it stays inside the same markup as the reference run.
		const punct_item = {
			char: match[policy === 'before' ? 1 : 2],
			chunk: { tags: run_items[run_items.length - 1].chunk.tags }
		};
		reordered.push(...items.slice(position, match.index));
		if (policy === 'before') {
			reordered.push(...run_items, punct_item);
		} else {
			reordered.push(punct_item, ...run_items);
		}
		position = match.index + match[0].length;
	}
	reordered.push(...items.slice(position));
	return to_chunks(reordered);
}

/**
 * Get the values of the "about" attribute of a text chunk.
 *
 * The values come from the annotation tags of the chunk and from its
 * inline content. Inline content is not always a tag: for references it
 * is a sub-document with no attributes property. Read attributes only
 * when they are present.
 *
 * @param {Text_chunk} chunk
 * @return {string[]} The about values; can be empty
 */
function get_chunk_about_values(chunk) {
	const values = [];
	for (let i = 0, len = chunk.tags.length; i < len; i++) {
		const attributes = chunk.tags[i].attributes;
		if (attributes && attributes.about) {
			values.push(attributes.about);
		}
	}
	const inline = chunk.inline_content;
	if (inline && inline.attributes && inline.attributes.about) {
		values.push(inline.attributes.about);
	}
	return values;
}

/**
 * Remove sentence boundaries that fall inside a transclusion about-group.
 *
 * Parsoid puts an inline transclusion into sibling elements that share one
 * "about" attribute. These siblings must stay together. A sentence boundary
 * between them would put the fragments into different segments and thus
 * into different parent elements (T213262). A boundary is inside a group
 * when the chunks on the two sides of it share an about value. The run
 * before the boundary includes zero-width chunks, such as category links.
 *
 * @param {number[]} boundaries Sentence boundary offsets
 * @param {Text_chunk[]} text_chunks The chunks of the text block
 * @return {number[]} The boundaries that do not break an about-group
 */
function suppress_about_group_boundaries(boundaries, text_chunks) {
	const starts = [];
	let offset = 0;
	for (let i = 0, len = text_chunks.length; i < len; i++) {
		starts.push(offset);
		offset += text_chunks[i].text.length;
	}
	return boundaries.filter((boundary) => {
		// Find the first chunk with content at or after the boundary.
		// Zero-width chunks at the boundary belong to the run before it.
		let i = 0;
		while (i < text_chunks.length &&
			starts[i] + text_chunks[i].text.length <= boundary) {
			i++;
		}
		if (i === text_chunks.length) {
			return true;
		}
		const after_abouts = get_chunk_about_values(text_chunks[i]);
		if (after_abouts.length === 0) {
			return true;
		}
		if (starts[i] < boundary) {
			// The boundary is in the interior of a chunk that carries an
			// about value: the two sides share it.
			return false;
		}
		const before_abouts = [];
		for (let j = i - 1; j >= 0; j--) {
			before_abouts.push(...get_chunk_about_values(text_chunks[j]));
			if (text_chunks[j].text.length > 0) {
				break;
			}
		}
		return !after_abouts.some((about) => before_abouts.includes(about));
	});
}

/**
 * A block of annotated inline text
 *
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
	 * @return {Object[]} Array of text chunk information objects with start and length properties
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
	 * @param {number} char_offset The char offset of the Text_chunk
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
		const valid_boundaries = suppress_about_group_boundaries(
			get_boundaries(this.get_plain_text()), this.text_chunks
		);
		const groups = get_chunk_boundary_groups(
			valid_boundaries,
			this.text_chunks,
			(text_chunk) => text_chunk.text.length
		);
		let offset = 0;
		for (let i = 0, i_len = groups.length; i < i_len; i++) {
			const group = groups[i];
			let text_chunk = group.chunk;
			const boundaries = group.boundaries;
			for (let j = 0, j_len = boundaries.length; j < j_len; j++) {
				const rel_offset = boundaries[j] - offset;
				if (rel_offset === 0) {
					flush_chunks();
				} else {
					const left_part = new Text_chunk(
						text_chunk.text.slice(0, rel_offset), text_chunk.tags.slice()
					);
					const right_part = new Text_chunk(
						text_chunk.text.slice(rel_offset),
						text_chunk.tags.slice(),
						text_chunk.inline_content
					);
					current_text_chunks.push(left_part);
					offset += rel_offset;
					flush_chunks();
					text_chunk = right_part;
				}
			}
			// Even if the text_chunk is zero-width, it may have references
			current_text_chunks.push(text_chunk);
			offset += text_chunk.text.length;
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
}

export default Text_block;
