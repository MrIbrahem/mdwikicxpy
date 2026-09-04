/**
 * @external Contextualizer
 */

import sax from 'sax';
import Builder from './Builder.js';
import { is_transclusion as _is_transclusion, is_inline_empty_tag, is_math, is_reference, is_segment } from './Utils.js';

const block_tags = [
	'html', 'head', 'body', 'script',
	// head tags
	// In HTML5+RDFa, link/meta are actually allowed anywhere in the body, and are to be
	// treated as void flow content (like <br> and <img>).
	'title', 'style', 'meta', 'link', 'noscript', 'base',
	// non-visual content
	'audio', 'data', 'datagrid', 'datalist', 'dialog', 'eventsource', 'form',
	'iframe', 'main', 'menu', 'menuitem', 'optgroup', 'option',
	// paragraph
	'div', 'p',
	// tables
	'table', 'tbody', 'thead', 'tfoot', 'caption', 'th', 'tr', 'td',
	// lists
	'ul', 'ol', 'li', 'dl', 'dt', 'dd',
	// HTML5 heading content
	'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hgroup',
	// HTML5 sectioning content
	'article', 'aside', 'body', 'nav', 'section', 'footer', 'header', 'figure',
	'figcaption', 'fieldset', 'details', 'blockquote',
	// other
	'hr', 'button', 'canvas', 'center', 'col', 'colgroup', 'embed',
	'map', 'object', 'pre', 'progress', 'video',
	// non-annotation inline tags
	'img', 'br',
	'wiki-chart'
];

/**
 * Parser to read an HTML stream into a Doc
 *
 */
class Parser extends sax.SAXParser {
	/**
	 * @param {Contextualizer} contextualizer Tag contextualizer
	 * @param {Object} options Options
	 */
	constructor(contextualizer, options) {
		super(false, {
			lowercase: true
		});
		this.contextualizer = contextualizer;
		this.options = options || {};
	}

	init() {
		this.root_builder = new Builder();
		this.builder = this.root_builder;
		// Stack of tags currently open
		this.all_tags = [];
	}

	on_open_tag(tag) {
		if (
			// Check if this tag is a child tag of a removable tag
			this.contextualizer.get_context() === 'removable' ||
			// Check if the tag is removable. Note that it is not added to contextualizer yet.
			this.contextualizer.is_removable(tag)
		) {
			this.all_tags.push(tag);
			this.contextualizer.on_open_tag(tag);
			return;
		}

		if (this.options.isolate_segments && is_segment(tag)) {
			this.builder.push_block_tag({
				name: 'div',
				attributes: {
					class: 'cx-segment-block'
				}
			});
		}

		if (is_reference(tag) || is_math(tag)) {
			// Start a reference: create a child builder, and move into it
			this.builder = this.builder.create_child_builder(tag);
		} else if (is_inline_empty_tag(tag.name)) {
			this.builder.add_inline_content(
				tag, this.contextualizer.can_segment()
			);
		} else if (this.is_inline_annotation_tag(tag.name, _is_transclusion(tag))) {
			this.builder.push_inline_annotation_tag(tag);
		} else {
			this.builder.push_block_tag(tag);
		}

		this.all_tags.push(tag);
		this.contextualizer.on_open_tag(tag);
	}

	on_close_tag(tag_name) {
		const tag = this.all_tags.pop(),
			is_ann = this.is_inline_annotation_tag(tag_name, _is_transclusion(tag));

		if (this.contextualizer.is_removable(tag) || this.contextualizer.get_context() === 'removable') {
			this.contextualizer.on_close_tag(tag);
			return;
		}

		this.contextualizer.on_close_tag(tag);

		if (is_inline_empty_tag(tag_name)) {
			return;
		} else if (is_ann && this.builder.inline_annotation_tags.length > 0) {
			this.builder.pop_inline_annotation_tag(tag_name);
			if (this.options.isolate_segments && is_segment(tag)) {
				this.builder.pop_block_tag('div');
			}
		} else if (is_ann && this.builder.parent !== null) {
			// In a sub document: should be a span or sup that closes a reference
			if (tag_name !== 'span' && tag_name !== 'sup') {
				throw new Error('Expected close reference - span or sup tags, got "' + tag_name + '"');
			}
			this.builder.finish_text_block();
			this.builder.parent.add_inline_content(
				this.builder.doc, this.contextualizer.can_segment()
			);
			// Finished with child now. Move back to the parent builder
			this.builder = this.builder.parent;
		} else if (!is_ann) {
			// Block level tag close
			if (tag_name === 'p' && this.contextualizer.can_segment()) {
				// Add an empty textchunk before the closing block tag to flush segmentation contexts
				// For example, transclusion based references at the end of paragraphs
				this.builder.add_text_chunk('', this.contextualizer.can_segment());
			}
			this.builder.pop_block_tag(tag_name);
		} else {
			throw new Error('Unexpected close tag: ' + tag_name);
		}
	}

	ontext(text) {
		if (this.contextualizer.get_context() === 'removable') {
			return;
		}
		this.builder.add_text_chunk(text, this.contextualizer.can_segment());
	}

	onscript(text) {
		this.builder.add_text_chunk(text, this.contextualizer.can_segment());
	}

	/**
	 * Determine whether a tag is an inline annotation or not
	 *
	 * @param {string} tag_name Tag name in lowercase
	 * @param {boolean} is_transclusion If the tag is transclusion
	 * @return {boolean} Whether the tag is an inline annotation
	 */
	is_inline_annotation_tag(tag_name, is_transclusion) {
		const context = this.contextualizer.get_context();
		// <span> inside a media context acts like a block tag wrapping another block tag <video>
		// See https://www.mediawiki.org/wiki/Specs/HTML/1.7.0#Audio/Video
		if (tag_name === 'span' && context === 'media') {
			return false;
		}

		// Audio or Video are block tags. But in a media-inline context they are inline.
		if ((tag_name === 'audio' || tag_name === 'video') && context === 'media-inline') {
			return true;
		}

		// Styles are usually block tags, but sometimes style tags are used as transclusions
		// Example: T217585. In such cases treat styles as inline to avoid wrong segmentations.
		if (tag_name === 'style' && is_transclusion) {
			return true;
		}
		// All tags that are not block tags are inline annotation tags.
		return !block_tags.includes(tag_name);
	}
}

export default Parser;
