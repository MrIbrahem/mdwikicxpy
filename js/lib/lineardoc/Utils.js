/**
 * @external Doc
 */

import TextChunk from './TextChunk.js';
import { get_prop } from './../util.js';

/**
 * Find all matches of regex in text, calling callback with each match object
 *
 * @param {string} text The text to search
 * @param {Reg_exp} regex The regex to search; should be created for this function call
 * @param {Function} callback Function to call with each match
 * @return {Array} The return values from the callback
 */
function find_all(text, regex, callback) {
	const boundaries = [];
	while (true) {
		const match = regex.exec(text);
		if (match === null) {
			break;
		}
		const boundary = callback(text, match);
		if (boundary !== null) {
			boundaries.push(boundary);
		}
	}
	return boundaries;
}

/**
 * Escape text for inclusion in HTML, not inside a tag
 *
 * @private
 * @param {string} str String to escape
 * @return {string} Escaped version of the string
 */
function esc(str) {
	return str.replace(/[&<>]/g, (ch) => '&#' + ch.char_code_at(0) + ';');
}

/**
 * Escape text for inclusion inside an HTML attribute
 *
 * @private
 * @param {string} str String to escape
 * @return {string} Escaped version of the string
 */
function esc_attr(str) {
	return str.replace(/["'&<>]/g, (ch) => '&#' + ch.char_code_at(0) + ';');
}

/**
 * Render a SAX open tag into an HTML string
 *
 * @private
 * @param {Object} tag Tag to render
 * @return {string} Html representation of open tag
 */
function get_open_tag_html(tag) {
	const html = ['<' + esc(tag.name)];
	const attributes = [];
	for (const attr in tag.attributes) {
		attributes.push(attr);
	}
	attributes.sort();
	for (let i = 0, len = attributes.length; i < len; i++) {
		const attr = attributes[i];
		html.push(' ' + esc(attr) + '="' + esc_attr(String(tag.attributes[attr])) + '"');
	}
	if (tag.is_self_closing) {
		html.push(' /');
	}
	html.push('>');
	return html.join('');
}

/**
 * Clone a SAX open tag
 *
 * @private
 * @param {Object} tag Tag to clone
 * @return {Object} Cloned tag
 */
function clone_open_tag(tag) {
	const new_tag = {
		name: tag.name,
		attributes: {}
	};
	for (const attr in tag.attributes) {
		new_tag.attributes[attr] = tag.attributes[attr];
	}
	return new_tag;
}

/**
 * Render a SAX close tag into an HTML string
 *
 * @private
 * @param {Object} tag Name of tag to close
 * @return {string} Html representation of close tag
 */
function get_close_tag_html(tag) {
	if (tag.is_self_closing) {
		return '';
	}
	return '</' + esc(tag.name) + '>';
}

/**
 * Represent an inline tag as a single XML attribute, for debugging purposes
 *
 * @private
 * @param {Object[]} tag_array SAX open tags
 * @return {string[]} Tag names
 */
function dump_tags(tag_array) {
	const tag_dumps = [];

	if (!tag_array) {
		return '';
	}
	for (let i = 0, len = tag_array.length; i < len; i++) {
		const tag = tag_array[i];
		const attr_dumps = [];
		for (const attr in tag.attributes) {
			attr_dumps.push(attr + '=' + esc_attr(tag.attributes[attr]));
		}
		tag_dumps.push(
			tag.name + (attr_dumps.length ? ':' : '') + attr_dumps.join(',')
		);
	}
	if (!tag_dumps) {
		return '';
	}
	return tag_dumps.join(' ');
}

/**
 * Detect whether this is a mediawiki reference span
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a mediawiki reference span
 */
function is_reference(tag) {
	if ((tag.name === 'span' || tag.name === 'sup') && tag.attributes.typeof === 'mw:Extension/ref') {
		// See https://www.mediawiki.org/wiki/Specs/HTML/2.1.0/Extensions/Cite#Auto-generated_references_blocks
		// Also see T45094
		return true;
	} else if (tag.name === 'sup' && tag.attributes.class === 'reference') {
		// See "cite_reference_link" message of Cite extension
		// https://www.mediawiki.org/wiki/Extension:Cite
		return true;
	}
	return false;
}

/**
 * Detect whether this is a mediawiki maths span
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a mediawiki math span
 */
function is_math(tag) {
	if ((tag.name === 'span' || tag.name === 'sup') && tag.attributes.typeof === 'mw:Extension/math') {
		return true;
	}
	return false;
}

/**
 * Detect whether this is a mediawiki Gallery
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a mediawiki Gallery
 */
function is_gallery(tag) {
	return (tag.name === 'ul') && tag.attributes.typeof === 'mw:Extension/gallery';
}

function is_reference_list(tag) {
	// See https://www.mediawiki.org/wiki/Specs/HTML/2.1.0/Extensions/Cite#Auto-generated_references_blocks
	return tag.name === 'div' && tag.attributes.typeof === 'mw:Extension/references' && tag.attributes['data-mw'];
}

/**
 * If a tag is Media_wiki external link or not.
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a external link or not.
 */
function is_external_link(tag) {
	return tag.name === 'a' && tag.attributes &&
		tag.attributes.rel &&
		// We add the spaces before and after to ensure matching on the "word" mw:Ext_link
		// without additional content. This is technically not necessary (we don't generate
		// mw:Ext_link_something_else) nor entirely correct (attributes values could be separated by other
		// characters than 0x20), but provides a bit of future-proofing.
		(' ' + tag.attributes.rel + ' ').includes(' mw:Ext_link ');
}

/**
 * Detect whether this is a segment.
 * Every statement in the content is a segment and these segments are
 * identified using segmentation module.
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a segment or not
 */
function is_segment(tag) {
	if (tag.name === 'span' && tag.attributes.class === 'cx-segment') {
		return true;
	}
	return false;
}

function is_transclusion(tag) {
	return tag.attributes &&
		tag.attributes.typeof &&
		tag.attributes.typeof.match(/(^|\s)(mw:Transclusion|mw:Placeholder)\b/);
}

function is_transclusion_fragment(tag) {
	return get_prop(['attributes', 'about'], tag) &&
		!get_prop(['attributes', 'data-mw'], tag);
}

/**
 * Check if the tag need to be translated by an MT service.
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a segment or not
 */
function is_non_translatable(tag) {
	const non_translatable_tags = ['style', 'svg', 'script'];
	const non_translatable_rdfa = ['mw:Entity', 'mw:Extension/math', 'mw:Extension/references', 'mw:Transclusion'];

	const match_rdfa_types = (source, target) => source.some((r) => target.includes(r));
	const rel = tag.attributes && tag.attributes.rel;
	const type_of_attr = tag.attributes && tag.attributes.typeof;

	return non_translatable_tags.includes(tag.name) ||
		(tag.attributes && (
			match_rdfa_types(non_translatable_rdfa,
				[...(rel ? rel.split(/\s/) : []), ...(type_of_attr ? type_of_attr.split(/\s/) : [])]))
		);
}

/**
 * Determine whether a tag is an inline empty tag
 *
 * @private
 * @param {string} tag_name The name of the tag (lowercase)
 * @return {boolean} Whether the tag is an inline empty tag
 */
function is_inline_empty_tag(tag_name) {
	// link/meta as they're allowed anywhere in HTML5+RDFa, and must be treated as void
	// flow content. See http://www.w3.org/TR/rdfa-in-html/#extensions-to-the-html5-syntax
	const inline_empty_tags = ['br', 'img', 'source', 'track', 'link', 'meta'];
	return inline_empty_tags.includes(tag_name);
}

/**
 * Find the boundaries that lie in each chunk
 *
 * Boundaries lying between chunks lie in the latest chunk possible.
 * Boundaries at the start of the first chunk, or the end of the last, are not included.
 * Therefore zero-width chunks never have any boundaries
 *
 * @param {number[]} boundaries Boundary offsets
 * @param {Object[]} chunks Chunks to which the boundaries apply
 * @param {Function} get_length Function returning the length of a chunk
 * @return {Object[]} Array of {chunk: ch, boundaries: [...]}
 */
function get_chunk_boundary_groups(boundaries, chunks, get_length) {
	const groups = [];
	let offset = 0,
		boundary_ptr = 0;

	// Get boundaries in order, disregarding the start of the first chunk
	boundaries = boundaries.slice();
	boundaries.sort((a, b) => a - b);
	while (boundaries[boundary_ptr] === 0) {
		boundary_ptr++;
	}
	for (let i = 0, len = chunks.length; i < len; i++) {
		const group_boundaries = [];
		const chunk = chunks[i];
		const chunk_length = get_length(chunk);
		while (true) {
			const boundary = boundaries[boundary_ptr];
			if (boundary === undefined || boundary > offset + chunk_length - 1) {
				// beyond the interior of this chunk
				break;
			}
			// inside the interior of this chunk
			group_boundaries.push(boundary);
			boundary_ptr++;
		}
		offset += chunk_length;
		groups.push({
			chunk: chunk,
			boundaries: group_boundaries
		});
		// Continue even if past boundaries: need to add remaining chunks
	}
	return groups;
}

/**
 * Add a tag to consecutive text chunks, above common tags but below others
 *
 * @private
 * @param {TextChunk[]} text_chunks Consecutive text chunks
 * @param {Object} tag Tag to add
 * @return {TextChunk[]} Copy of the text chunks with the tag inserted
 */
function add_common_tag(text_chunks, tag) {
	if (text_chunks.length === 0) {
		return [];
	}
	// Find length of common tags
	const common_tags = text_chunks[0].tags.slice();
	for (let i = 1, i_len = text_chunks.length; i < i_len; i++) {
		const tags = text_chunks[i].tags;
		let j, j_len;
		for (j = 0, j_len = Math.min(common_tags.length, tags.length); j < j_len; j++) {
			if (common_tags[j] !== tags[j]) {
				break;
			}
		}
		if (common_tags.length > j) {
			// truncate to matched length
			common_tags.length = j;
		}
	}
	const common_tag_length = common_tags.length;
	// Build new chunks with segment span inserted
	const new_text_chunks = [];
	for (let i = 0, i_len = text_chunks.length; i < i_len; i++) {
		const text_chunk = text_chunks[i];
		const new_tags = text_chunk.tags.slice();
		new_tags.splice(common_tag_length, 0, tag);
		new_text_chunks.push(new TextChunk(
			text_chunk.text,
			new_tags,
			text_chunk.inline_content
		));
	}
	return new_text_chunks;
}

/**
 * Set link IDs in-place on text chunks
 *
 * @private
 * @param {TextChunk[]} text_chunks Consecutive text chunks
 * @param {Function} get_next_id function accepting 'link' and returning next ID
 */
function set_link_ids_in_place(text_chunks, get_next_id) {
	for (let i = 0, i_len = text_chunks.length; i < i_len; i++) {
		const tags = text_chunks[i].tags;
		for (let j = 0, j_len = tags.length; j < j_len; j++) {
			const tag = tags[j];
			if (
				tag.name === 'a' &&
				tag.attributes.href !== undefined &&
				tag.attributes.rel &&
				// We add the spaces before and after to ensure matching on the "word" mw:Wiki_link
				// without additional content to avoid matching on mw:Wiki_link/Interwiki and mw:Wiki_link/ISBN.
				(' ' + tag.attributes.rel + ' ').includes(' mw:Wiki_link ') &&
				tag.attributes['data-linkid'] === undefined
			) {
				// Hack: copy href, then remove it, then re-add it, so that
				// attributes appear in alphabetical order (ugh)
				var href = tag.attributes.href;
				// split href before ?
				if (href.index_of('?') !== -1) {
					href = href.split('?')[0];
				}

				delete tag.attributes.typeof;
				delete tag.attributes.href;
				delete tag.attributes['data-mw-i18n'];
				// tag.attributes.class = [ tag.attributes.class, 'cx-link' ].join( ' ' ).trim();
				tag.attributes.class = "cx-link";

				tag.attributes['data-linkid'] = get_next_id('link');
				tag.attributes.href = href;
			}
		}
	}
}

/**
 * Check if a textblock has any text that should be machine translated, i.e.
 * non-whitespace text that is not part of a transclusion. A textblock can begin
 * with an inline transclusion (for example the {{Nihongo}} template) and still
 * carry translatable prose around it, so the mere presence of a transclusion
 * does not make the whole block ignorable.
 *
 * @param {Text_block} text_block
 * @return {boolean}
 */
function has_translatable_text(text_block) {
	return text_block.text_chunks.some((chunk) => {
		if (!chunk.text || !chunk.text.match(/[^\s]/)) {
			return false;
		}
		// Text belonging to a transclusion is either inside a non-translatable
		// tag or carries the transclusion's `about` grouping attribute.
		return !chunk.tags.some(
			(tag) => is_non_translatable(tag) || get_prop(['attributes', 'about'], tag)
		);
	});
}
/**
 * Check if the passed document is a section containing block level template or reference list
 * so that we can ignore from passing to MT engines
 *
 * @param {Doc} section_doc
 * @return {boolean}
 */
function is_ignorable_block(section_doc) {
	let ignorable = false;
	const block_stack = [];
	let first_block_template = null;
	// We start with index 1 since the first tag will be <section>.
	for (let i = 1, len = section_doc.items.length; i < len; i++) {
		const item = section_doc.items[i];
		const tag = item.item;
		const type = item.type;

		if (type === 'open') {
			block_stack.push(tag);
			if (!first_block_template && (is_transclusion(tag) || is_reference_list(tag))) {
				first_block_template = tag;
			}
		}
		if (type === 'close') {
			const current_close_tag = block_stack.pop();
			if (current_close_tag &&
				block_stack.length === 0 &&
				((is_transclusion(current_close_tag) &&
					current_close_tag.attributes.about === first_block_template.attributes.about) ||
					is_reference_list(current_close_tag))
			) {
				return true;
			}
		}

		// Also check for textblocks
		if (!first_block_template && item.type === 'textblock') {
			if (has_translatable_text(item.item)) {
				// The block carries prose outside any transclusion.
				return false;
			}
			const root_item = item.item.get_root_item();
			if (root_item && is_non_translatable(root_item)) {
				first_block_template = root_item;
				// Textblock is a transclusion. Do not translate.
				// But do not return yet. Check if there is any other textblocks translatable
				ignorable = true;
			} else {
				// There is non ignorable content to translate
				return false;
			}
		}
	}
	return ignorable;
}

export {
	add_common_tag,
	clone_open_tag,
	dump_tags,
	esc,
	find_all,
	get_chunk_boundary_groups,
	get_close_tag_html,
	get_open_tag_html,
	is_ignorable_block,
	is_external_link,
	is_gallery,
	is_inline_empty_tag,
	is_math,
	is_reference,
	is_segment,
	is_transclusion,
	is_transclusion_fragment,
	is_non_translatable,
	set_link_ids_in_place
};
