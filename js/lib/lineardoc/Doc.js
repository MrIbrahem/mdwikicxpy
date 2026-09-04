/**
 * @external Text_block
 */

import { create_hash } from 'crypto';
import { clone_open_tag, get_close_tag_html, get_open_tag_html, is_gallery, is_math, is_non_translatable } from './Utils.js';
import { get_prop } from './../util.js';

/**
 * An HTML document in linear representation.
 *
 * The document is a list of items, where each items is
 * - a block open tag (e.g. <p>); or
 * - a block close tag (e.g. </p>); or
 * - a Text_block of annotated inline text; or
 * - "block whitespace" (a run of whitespace separating two block boundaries)
 *
 * Some types of HTML structure get normalized away. In particular:
 *
 * 1. Identical adjacent annotation tags are merged
 * 2. Inline annotations across block boundaries are split
 * 3. Annotations on block whitespace are stripped (except spans with 'data-mw')
 *
 * N.B. 2 can change semantics, e.g. identical adjacent links != single link
 *
 */
class Doc {
	/**
	 * @param {string} wrapper_tag open/close tags
	 */
	constructor(wrapper_tag) {
		this.items = [];
		this.wrapper_tag = wrapper_tag || null;
		this.categories = [];
	}

	/**
	 * Clone the Doc, modifying as we go
	 *
	 * @param {Function} callback The function to modify a node
	 * @return {Doc} clone with modifications
	 */
	clone(callback) {
		const new_doc = new Doc(this.wrapper_tag);
		for (let i = 0, len = this.items.length; i < len; i++) {
			const item = this.items[i];
			const new_item = callback(item);
			new_doc.add_item(new_item.type, new_item.item);
		}
		return new_doc;
	}

	/**
	 * Add an item to the document
	 *
	 * @param {string} type Type of item: open|close|blockspace|textblock
	 * @param {Object|string|Text_block} item Open/close tag, space or text block
	 * @return {this}
	 */
	add_item(type, item) {
		this.items.push({ type, item });
		return this;
	}

	/**
	 * Remove the top item from the linear array of items
	 */
	undo_add_item() {
		this.items.pop();
	}

	/**
	 * Get the top item in the linear array of items
	 *
	 * @return {Object}
	 */
	get_current_item() {
		return this.items[this.items.length - 1];
	}

	/**
	 * Get the root item in the doc. Since doc is a linear representation
	 * of DOM tree, the root item is the first item in the doc, skipping
	 * any blockspaces.
	 *
	 * @return {Object}
	 */
	get_root_item() {
		if (this.wrapper_tag) {
			return this.wrapper_tag;
		}
		for (let i = 0; i < this.items.length; i++) {
			// Ignore all blockspaces, loop till we see a tag opening
			if (this.items[i].type === 'open') {
				return this.items[i].item;
			}
		}
	}

	/**
	 * Segment the document into sentences
	 *
	 * @param {Function} get_boundaries Function taking plaintext, returning offset array
	 * @return {Doc} Segmented version of document TODO: warning: *shallow copied*.
	 */
	segment(get_boundaries) {
		const new_doc = new Doc();
		let next_section_id = 0,
			next_id = 0,
			section_number = 0;

		// TODO: return different counters depending on type
		function get_next_id(id_type, tag_name) {
			if (tag_name === 'section') {
				return String(`cx_source_section${next_section_id++}`);
			}
			if (id_type === 'segment' || id_type === 'link' || id_type === 'block') {
				return String(next_id++);
			} else {
				throw new Error(`Unknown ID type: ${id_type}`);
			}
		}

		let transclusion_context = null;
		for (let i = 0, len = this.items.length; i < len; i++) {
			const item = this.items[i];
			if (this.items[i].type === 'open') {
				const tag = clone_open_tag(item.item);
				if (tag.attributes.id) {
					// If the item is a header, we make it a fixed length id using hash of
					// the text content. Header ids are originally the header text to get
					// the URL fragments working, but for CX, it is irrelevant and we need
					// a fixed length id that can be used as DB key.
					// The text inside this 'open tag' is in the next item(i+1).
					if (['h1', 'h2', 'h3', 'h4', 'h5'].includes(tag.name) &&
						i + 1 < len &&
						this.items[i + 1].type === 'textblock'
					) {
						const hash = create_hash('sha256');
						hash.update(this.items[i + 1].item.get_plain_text());
						// 30 is the max length of ids we allow. We also prepend the sequence id
						// just to make sure the ids don't collide if the same text repeats.
						tag.attributes.id = hash.digest('hex').slice(0, 30);
					} else if (tag.attributes.id.length > 30) {
						// At any case, make sure that the section id never exceeds 30 bytes
						tag.attributes.id = tag.attributes.id.slice(0, 30);
					}
				} else {
					tag.attributes.id = get_next_id('block', tag.name);
					// Section headers (<h2> tags) mark the start of a new section
					if (i + 1 < len && this.items[i + 1].item.name === 'h2') {
						section_number++;
					}
				}
				if (tag.name === 'section') {
					tag.attributes['data-mw-section-number'] = section_number;
				}
				new_doc.add_item(item.type, tag);
				// Content of tags that are either mw:Transclusion or mw:Extension need not be segmented.
				const about = get_prop(['attributes', 'about'], tag);
				const type_of = get_prop(['attributes', 'typeof'], tag);
				if (about && type_of) {
					transclusion_context = about;
				}
			} else if (this.items[i].type === 'close') {
				const tag = item.item;
				const about = get_prop(['attributes', 'about'], tag);
				if (about && about === transclusion_context) {
					transclusion_context = null;
				}
				new_doc.add_item(item.type, item.item);
			} else if (this.items[i].type !== 'textblock') {
				new_doc.add_item(item.type, item.item);
			} else {
				const text_block = item.item;
				new_doc.add_item(
					'textblock',
					text_block.can_segment && !transclusion_context ?
						text_block.segment(get_boundaries, get_next_id) :
						text_block.set_link_ids(get_next_id)
				);
			}
		}
		return new_doc;
	}

	/**
	 * Dump an XML version of the linear representation, for debugging
	 *
	 * @return {string} XML version of the linear representation
	 */
	dump_xml() {
		return this.dump_xml_array('').join('\n');
	}

	/**
	 * Dump the document in HTML format
	 *
	 * @return {string} HTML document
	 */
	get_html() {
		const html = [];

		if (this.wrapper_tag) {
			html.push(get_open_tag_html(this.wrapper_tag));
		}
		for (let i = 0, len = this.items.length; i < len; i++) {
			const type = this.items[i].type;
			const item = this.items[i].item;

			if (item.attributes && item.attributes.class === 'cx-segment-block') {
				continue;
			}

			if (type === 'open') {
				const tag = item;
				html.push(get_open_tag_html(tag));
			} else if (type === 'close') {
				const tag = item;
				html.push(get_close_tag_html(tag));
			} else if (type === 'blockspace') {
				const space = item;
				html.push(space);
			} else if (type === 'textblock') {
				const textblock = item;
				// textblock html list may be quite long, so concatenate now
				html.push(textblock.get_html());
			} else {
				throw new Error(`Unknown item type: ${type}`);
			}
		}
		if (this.wrapper_tag) {
			html.push(get_close_tag_html(this.wrapper_tag));
		}
		return html.join('');
	}

	/**
	 * Wrap the content into sections
	 * See doc/Section_wrap.md for detailed documentaion.
	 *
	 * @return {string} HTML document
	 */
	wrap_sections() {
		const new_doc = new Doc();
		let in_body = false,
			prev_section = null,
			curr_section = null;

		// Copy the categories already collected.
		new_doc.categories = this.categories;

		/**
		 * For a given tag, get something that can be used to identify the tag.
		 * `about` attribute has more preference in our context since it connects
		 * template fragments. If `about` is not present, use id attribute.
		 * If no attributes, then it is tag name. In real wiki content, the case
		 * of no attributes is not found.
		 *
		 * @param {Object} tag
		 * @return {string}
		 */
		function get_tag_id(tag) {
			let id;
			if (tag.attributes) {
				id = tag.attributes.about || tag.attributes.id;
			}
			return id || tag.name;
		}

		function open_section(doc) {
			doc.add_item('open', { name: 'section', attributes: { rel: 'cx:Section' } });
		}

		function close_section(doc) {
			doc.add_item('close', { name: 'section' });
			prev_section = curr_section;
			curr_section = null;
		}

		function insert_to_prev_section(item, doc) {
			if (new_doc.get_current_item().item.name !== 'section') {
				throw new Error(`Sectionwrap: Attempting to remove a non-section tag: ${item.name}`);
			}
			// Undo last section close
			doc.undo_add_item();
			curr_section = prev_section;
			doc.add_item(item.type, item.item);
			close_section(new_doc);
		}

		const items_length = this.items.length;
		for (let i = 0; i < items_length; i++) {
			const item = this.items[i];
			const tag = item.item;
			const type = item.type;

			if (!in_body) {
				// Till we reach body, keep on adding items to new_doc.
				new_doc.add_item(type, tag);
				if (tag.name === 'body') {
					in_body = true;
				}
				continue;
			}
			if (type === 'open') {
				if (!curr_section) {
					if (prev_section === get_tag_id(tag)) {
						// This tag is connected to previous section. Can be a template fragment.
						// Undo last section close

						new_doc.undo_add_item();
						curr_section = prev_section;
					} else {
						open_section(new_doc);
						curr_section = get_tag_id(tag);
					}
				}

				new_doc.add_item(item.type, tag);
			} else if (type === 'close') {
				if (curr_section && tag.name === 'body') {
					close_section(new_doc);
					in_body = false;
				}

				new_doc.add_item(item.type, tag);
				if (get_tag_id(tag) === curr_section) {
					close_section(new_doc);
				}

			} else if (type === 'blockspace') {
				if (prev_section && new_doc.get_current_item().item.name === 'section') {
					insert_to_prev_section(item, new_doc);
				} else {
					new_doc.add_item(type, tag);
				}
			} else if (type === 'textblock') {
				const text_block = item.item;
				const tag_for_id = text_block.get_tag_for_id();

				if (!tag_for_id && !curr_section) {
					// Textblock with no tag identifier. Add it to the previous section
					if (prev_section && new_doc.get_current_item().item.name === 'section') {
						insert_to_prev_section(item, new_doc);
						continue;
					}
					// No previous section to attach to; fall through to open a new one
				}

				const is_connected = tag_for_id && !curr_section && prev_section === get_tag_id(tag_for_id);

				if (is_connected) {
					// This tag is connected to previous section. Can be a template fragment.
					insert_to_prev_section(item, new_doc);
					continue;
				}

				if (!curr_section) {
					open_section(new_doc);
					curr_section = get_tag_id(tag_for_id);
					if (!curr_section) {
						throw new Error(`No id for the opened section for tag ${tag_for_id.name}`);
					}
					new_doc.add_item(item.type, text_block);
					// There was no open sections. Close the section now itself. If this tag is a template
					// fragment, `is_connected` check above will insert the fragments to closed section.
					close_section(new_doc);
					continue;
				}

				new_doc.add_item(item.type, text_block);
			} else {
				throw new Error(`Unknown item type: ${type}`);
			}
		}

		return new_doc;
	}

	/**
	 * Dump an XML Array version of the linear representation, for debugging
	 *
	 * @param {string} pad
	 * @return {string[]} Array that will concatenate to an XML string representation
	 */
	dump_xml_array(pad) {
		const dump = [];

		if (this.wrapper_tag) {
			dump.push(`${pad}<cxwrapper>`);
		}
		for (let i = 0, len = this.items.length; i < len; i++) {
			const type = this.items[i].type;
			const item = this.items[i].item;
			if (type === 'open') {
				// open block tag
				const tag = item;
				dump.push(`${pad}<${tag.name}>`);
				if (tag.name === 'head') {
					// Add a few things for easy display
					dump.push(`${pad}<meta charset="UTF-8" />`);
					dump.push(`${pad}<style>cxtextblock { border: solid #88f 1px }`);
					dump.push(`${pad}cxtextchunk { border-right: solid #f88 1px }</style>`);
				}
			} else if (type === 'close') {
				// close block tag
				const tag = item;
				dump.push(`${pad}</${tag.name}>`);
			} else if (type === 'blockspace') {
				// Non-inline whitespace
				dump.push(`${pad}<cxblockspace/>`);
			} else if (type === 'textblock') {
				// Block of inline text
				const text_block = item;
				dump.push(`${pad}<cxtextblock>`);
				dump.push.apply(dump, text_block.dump_xml_array(pad + '  '));
				dump.push(`${pad}</cxtextblock>`);
			} else {
				throw new Error(`Unknown item type: ${type}`);
			}
		}
		if (this.wrapper_tag) {
			dump.push(`${pad}</cxwrapper>`);
		}
		return dump;
	}

	/**
	 * Extract the text segments from the document
	 *
	 * @return {string[]} balanced html fragments, one per segment
	 */
	get_segments() {
		const segments = [];

		for (let i = 0, len = this.items.length; i < len; i++) {
			if (this.items[i].type !== 'textblock') {
				continue;
			}
			const textblock = this.items[i].item;
			segments.push(textblock.get_html());
		}

		return segments;
	}

	/**
	 * Reduce the document size by removing all attributes except id.
	 * This is derives a smaller HTML content to use with machine
	 * translation engines that support HTML. Using the #expand method,
	 * the attributes can be re-applied again.
	 *
	 * If id attribute in the reduced document is a generated id based
	 * on a counter.
	 *
	 * We assume that the MT engine preserve the HTML structure and id
	 * attributes while translating.
	 *
	 * @param {Object} [id_counter] The id sequence start value to use for the attribute dump
	 * @return {Object} Object containing reduced_doc and extracted data that contains
	 *   attributes and content from original doc. This is required for #expand
	 */
	reduce(id_counter) {
		const reduced_doc = new Doc(this.wrapper_tag);
		let extracted_data = {};
		id_counter = id_counter || { value: 0 };

		// Check if the tag need to be translated by an MT service.
		// If not, the translation from MT service won't be accepted.
		let non_translatable_context = false;

		// Check if there are attributes other than id to save in attr_dump
		const has_attributes_to_save = (obj) => {
			const keys = obj.attributes && Object.keys(obj.attributes);
			if (!keys || keys.length === 0) {
				return false;
			}
			if (keys.length > 1) {
				return true;
			}
			if (keys[0] === 'id') {
				return false;
			}
			return true;
		};

		if (this.wrapper_tag && has_attributes_to_save(this.wrapper_tag)) {
			id_counter.value++;
			extracted_data[id_counter.value] = {
				attributes: Object.assign({}, this.wrapper_tag.attributes)
			};

			if (is_math(this.wrapper_tag)) {
				// Do not send inline mw:Extention/math content to MT engines
				// since they are known to mangle the content.
				// Save the (inline) document in extracted_data, return the document
				// wrapper tag alone.
				extracted_data[id_counter.value].document = this;
				this.wrapper_tag.attributes.id = id_counter.value;
				return { reduced_doc, extracted_data };
			}
			this.wrapper_tag.attributes = { id: id_counter.value };
		}
		for (let i = 0, i_len = this.items.length; i < i_len; i++) {
			const item = this.items[i];
			const tag = item.item;
			const type = item.type;

			if (type === 'open') {
				const has_attributes = has_attributes_to_save(tag);
				const has_non_translatable_content = is_non_translatable(tag);
				if (has_attributes || has_non_translatable_content) {
					id_counter.value++;

					if (has_attributes) {
						extracted_data[id_counter.value] = {
							attributes: Object.assign({}, tag.attributes) // Shallow copy
						};
					}

					const original_attrs = tag.attributes;
					tag.attributes = { id: id_counter.value };

					// Preserve rdfa attributes in the reduced doc so that when parsing
					// the output from MT systems, we don't remove spans with empty content
					// See Builder#pop_inline_annotation_tag
					if (original_attrs.typeof && original_attrs.about) {
						tag.attributes.typeof = original_attrs.typeof;
						tag.attributes.about = original_attrs.about;
					}
					// Set a flag to indicate that textblocks should be extracted out
					if (has_non_translatable_content) {
						non_translatable_context = true;
					}
				}
				reduced_doc.add_item(type, tag);
				continue;
			}

			if (type === 'close' || type === 'blockspace') {
				reduced_doc.add_item(type, tag);
				if (is_non_translatable(tag)) {
					non_translatable_context = false;
				}
				continue;
			}

			const textblock = tag;
			if (non_translatable_context) {
				extracted_data[id_counter.value] = Object.assign(
					extracted_data[id_counter.value] || {}, { content: textblock }
				);
				continue;
			}
			for (let j = 0, j_len = textblock.text_chunks.length; j < j_len; j++) {
				const chunk = textblock.text_chunks[j];

				if (chunk.tags) {
					for (let k = 0, k_len = chunk.tags.length; k < k_len; k++) {
						const chunk_tag = chunk.tags[k];
						if (!has_attributes_to_save(chunk_tag)) {
							continue;
						}
						id_counter.value++;
						const original_tag = Object.assign({}, chunk_tag);
						extracted_data[id_counter.value] = {
							attributes: Object.assign({}, chunk_tag.attributes)
						};
						chunk_tag.attributes = { id: id_counter.value };

						if (is_non_translatable(original_tag)) {
							extracted_data[id_counter.value] = Object.assign(
								extracted_data[id_counter.value] || {}, { content: chunk.text }
							);
						}
					}
				}

				if (chunk.inline_content) {
					if (chunk.inline_content.reduce) {
						// Using object wrapping to pass counter by reference in order to avoid
						// re-using already used IDs when this function continues processing.
						const inline_reduce_result = chunk.inline_content.reduce(id_counter);
						chunk.inline_content = inline_reduce_result.reduced_doc;
						extracted_data = Object.assign(extracted_data, inline_reduce_result.extracted_data);
					} else {
						if (!has_attributes_to_save(chunk.inline_content)) {
							continue;
						}
						id_counter.value++;
						extracted_data[id_counter.value] = {
							attributes: Object.assign({}, chunk.inline_content.attributes)
						};
						chunk.inline_content.attributes = { id: id_counter.value };
					}
				}
			}
			reduced_doc.add_item(type, tag);
		}

		return { reduced_doc, extracted_data };
	}

	/**
	 * Expand a document with the given attr_dump. The attributes based
	 * on the id of elements will be applied to the tags.
	 *
	 * @param {Object} extracted_data The extracted data in #reduce method
	 * @return {Doc} The expanded document.
	 */
	expand(extracted_data) {
		const expanded_doc = new Doc(this.wrapper_tag);
		let id = 0;

		const has_attributes = (obj) => obj.attributes && Object.keys(obj.attributes).length;
		if (this.wrapper_tag && has_attributes(this.wrapper_tag)) {
			id = this.wrapper_tag.attributes.id;
			if (extracted_data[id]) {
				if (extracted_data[id].document) {
					// The inline document is extracted as a whole. Return it.
					// This happens for mw:Extension/math.
					return extracted_data[id].document;
				}
				this.wrapper_tag.attributes = extracted_data[id].attributes;
			}
		}
		for (let i = 0, i_len = this.items.length; i < i_len; i++) {
			const item = this.items[i];
			const tag = item.item;
			const type = item.type;

			if (type === 'open') {
				if (has_attributes(tag)) {
					id = tag.attributes.id;
					if (extracted_data[id]) {
						tag.attributes = extracted_data[id].attributes;
					} else {
						// Restore the id attribute alone, if exists.
						tag.attributes = id ? { id } : {};
					}
				}
				expanded_doc.add_item(type, tag);
				if (extracted_data[id] && extracted_data[id].content) {
					// Make sure the content is a textblock object
					// before adding to the doc as a textblock
					if (typeof extracted_data[id].content === 'object') {
						expanded_doc.add_item('textblock', extracted_data[id].content);
						// Skip the next item in the loop since we replaced it with the content
						// from extracted data
						i++;
					}
				}
				continue;
			}

			if (type === 'close' || type === 'blockspace') {
				expanded_doc.add_item(type, tag);
				continue;
			}

			const textblock = tag;
			const expanded_ids = [];
			for (let j = 0, len = textblock.text_chunks.length; j < len; j++) {
				const chunk = textblock.text_chunks[j];

				if (chunk.tags) {
					for (let k = 0, k_len = chunk.tags.length; k < k_len; k++) {
						const chunk_tag = chunk.tags[k];
						if (!has_attributes(chunk_tag)) {
							continue;
						}
						id = chunk_tag.attributes.id;

						if (expanded_ids.includes(id)) {
							// This is a close tag. Ignore
							continue;
						}

						if (extracted_data[id]) {
							chunk_tag.attributes = extracted_data[id].attributes;
							if (extracted_data[id].content) {
								chunk.text = extracted_data[id].content;
							}
							// This loop will see the closing tag for this tag too.
							// So keep track of open tags.
							if (chunk_tag.attributes) {
								expanded_ids.push(chunk_tag.attributes.id);
							}
						} else {
							// Restore the id attribute alone, if exists.
							chunk_tag.attributes = id ? { id } : {};
						}
					}
				}
				if (chunk.inline_content) {
					if (chunk.inline_content.expand) {
						chunk.inline_content = chunk.inline_content.expand(extracted_data);
					} else {
						id = chunk.inline_content.attributes.id;
						if (extracted_data[id]) {
							chunk.inline_content.attributes = extracted_data[id].attributes;
						} else {
							chunk.inline_content.attributes = id ? { id } : {};
						}
					}
				}
			}
			expanded_doc.add_item(type, tag);
		}

		return expanded_doc;
	}

	/**
	 * Recursively adapt all nodes in the document.
	 *
	 * @param {Function} get_adapter Function taking a tag, returning adapted output
	 * @return {Doc} Adapted version of document TODO: warning: *shallow copied*.
	 */
	async adapt(get_adapter) {
		let adapter, new_doc = new Doc();

		if (this.wrapper_tag) {
			adapter = get_adapter(this.wrapper_tag);
			if (adapter) {
				new_doc = new Doc(await adapter.adapt());
			} else {
				new_doc = new Doc(this.wrapper_tag);
			}
		}
		let transclusion_context = null;
		for (let i = 0, len = this.items.length; i < len; i++) {
			const item = this.items[i];
			if (this.items[i].type === 'open') {
				const tag = clone_open_tag(item.item);
				if (i + 1 < len && this.items[i + 1].type === 'textblock') {
					tag.children = this.items[i + 1].item;
				}
				adapter = get_adapter(tag);
				if (adapter && !transclusion_context) {
					// Do not adapt translation units under a transclusion_context
					new_doc.add_item(item.type, await adapter.adapt());
				} else {
					new_doc.add_item(item.type, tag);
				}
				const about = get_prop(['attributes', 'about'], tag);
				if (about && !is_gallery(tag)) {
					// Presence of about attribute tells us that it is a transclusion or
					// transclusion fragment. The innerbody of the transclusion can be
					// skipped from adaption. Except in the case of Gallery with
					// typeof='mw:Extension/gallery' where we need to adapt captions
					transclusion_context = about;
				}
			} else if (this.items[i].type === 'close') {
				const tag = item.item;
				const about = get_prop(['attributes', 'about'], tag);
				if (about && about === transclusion_context) {
					transclusion_context = null;
				}
				new_doc.add_item(item.type, item.item);
			} else if (this.items[i].type !== 'textblock') {
				new_doc.add_item(item.type, item.item);
			} else {
				const text_block = item.item;
				if (!transclusion_context) {
					// Do not adapt translation units under a transclusion_context
					new_doc.add_item(
						'textblock',
						await text_block.adapt(get_adapter)
					);
				} else {
					new_doc.add_item(item.type, item.item);
				}
			}
		}

		return new_doc;
	}

	/**
	 * Reposition reference markers relative to sentence punctuation across the
	 * whole document, according to the target language convention.
	 *
	 * @param {Object} options
	 * @param {string} options.policy 'before' or 'after'
	 * @param {string[]} options.punctuation Punctuation marks to reposition around
	 * @return {Doc} This document, with references repositioned
	 */
	adapt_reference_punctuation(options) {
		for (let i = 0, len = this.items.length; i < len; i++) {
			if (this.items[i].type === 'textblock') {
				this.items[i].item = this.items[i].item.adapt_reference_punctuation(options);
			}
		}
		return this;
	}
}

export default Doc;
