import Doc from './Doc.js';
import { is_external_link, is_reference, is_transclusion } from './Utils.js';
import Text_block from './TextBlock.js';
import Text_chunk from './TextChunk.js';

/**
 * A document builder
 *
 */
class Builder {
	/**
	 * @param {Builder} [parent] Parent document builder
	 * @param {Object} [wrapper_tag] tag that wraps document (if there is a parent)
	 */
	constructor(parent, wrapper_tag) {
		this.block_tags = [];
		// Stack of annotation tags
		this.inline_annotation_tags = [];
		// The height of the annotation tags that have been used, minus one
		this.inline_annotation_tags_used = 0;
		this.doc = new Doc(wrapper_tag || null);
		this.text_chunks = [];
		this.is_block_segmentable = true;
		this.parent = parent || null;
	}

	create_child_builder(wrapper_tag) {
		return new Builder(this, wrapper_tag);
	}

	push_block_tag(tag) {
		this.finish_text_block();
		this.block_tags.push(tag);
		if (this.is_ignored_tag(tag)) {
			return;
		}
		if (tag.name === 'figure') {
			tag.attributes.rel = 'cx:Figure';
		}
		this.doc.add_item('open', tag);
	}

	is_section(tag) {
		return tag.name === 'section' && tag.attributes['data-mw-section-id'];
	}

	is_ignored_tag(tag) {
		return this.is_section(tag) || this.is_category(tag);
	}

	is_category(tag) {
		return tag.name === 'link' && tag.attributes.rel &&
			// We add the spaces before and after to ensure matching on the "word" mw:Page_prop/Category
			// without additional content. This is technically not necessary (we don't generate
			// mw:Page_prop/Category/Something_else) nor entirely correct (attributes values could be separated by other
			// characters than 0x20), but provides a bit of future-proofing.
			(' ' + tag.attributes.rel + ' ').includes(' mw:Page_prop/Category ') && !tag.attributes.about;
	}

	pop_block_tag(tag_name) {
		const tag = this.block_tags.pop();
		if (!tag || tag.name !== tag_name) {
			throw new Error(
				'Mismatched block tags: open=' + (tag && tag.name) + ', close=' + tag_name
			);
		}
		this.finish_text_block();

		if (!this.is_ignored_tag(tag)) {
			this.doc.add_item('close', tag);
		}

		return tag;
	}

	push_inline_annotation_tag(tag) {
		this.inline_annotation_tags.push(tag);
	}

	pop_inline_annotation_tag(tag_name) {
		let i;
		const tag = this.inline_annotation_tags.pop();
		if (this.inline_annotation_tags_used === this.inline_annotation_tags.length) {
			this.inline_annotation_tags_used--;
		}
		if (!tag || tag.name !== tag_name) {
			throw new Error(
				'Mismatched inline tags: open=' + (tag && tag.name) + ', close=' + tag_name
			);
		}

		if (!Object.keys(tag.attributes).length) {
			// Skip tags which have attributes, content or both from further check to
			// see if we want to keep inline content. Else we assume that, if this tag has
			// whitespace or empty content, it is ok to remove it from resulting document.
			// But if it has attributes, we make sure that there are inline content blocks to
			// avoid them missing in resulting document.
			// See T104539
			return;
		}
		// Check for empty/whitespace-only data tags. Replace as inline content
		let replace = true;
		const whitespace = [];
		for (i = this.text_chunks.length - 1; i >= 0; i--) {
			const text_chunk = this.text_chunks[i];
			const chunk_tag = text_chunk.tags[text_chunk.tags.length - 1];
			if (!chunk_tag) {
				break;
			}
			if (text_chunk.text.match(/\S/) || text_chunk.inline_content || chunk_tag !== tag) {
				// text_chunk has non whitespace content, Or it has child tags.
				replace = false;
				break;
			}
			whitespace.push(text_chunk.text);
		}

		// Allow empty external links because REST API v1 can output links with
		// no link text (which then get a CSS generated content numbered reference).
		if (replace && (is_reference(tag) || is_external_link(tag) || is_transclusion(tag))) {
			// truncate list and add data span as new sub-Doc.
			this.text_chunks.length = i + 1;
			whitespace.reverse();
			this.add_inline_content(
				new Doc()
					.add_item('open', tag)
					.add_item('textblock', new Text_block(
						[new Text_chunk(whitespace.join(''), [])]
					))
					.add_item('close', tag)
			);
		}
		return;
	}

	add_text_chunk(text, can_segment) {
		this.text_chunks.push(new Text_chunk(text, this.inline_annotation_tags.slice()));
		this.inline_annotation_tags_used = this.inline_annotation_tags.length;
		// Inside a textblock, if a textchunk becomes segmentable, unlike inline tags,
		// the textblock becomes segmentable. See T195768
		this.is_block_segmentable = can_segment;
	}

	/**
	 * Add content that doesn't need linearizing, to appear inline
	 *
	 * @param {Object} content Sub-document or empty SAX tag
	 * @param {boolean} can_segment
	 */
	add_inline_content(content, can_segment) {
		// If the content is a category tag, capture it separately and don't add to doc.
		if (this.is_category(content)) {
			this.doc.categories.push(content);
			return;
		}
		this.text_chunks.push(new Text_chunk('', this.inline_annotation_tags.slice(), content));
		if (!can_segment) {
			this.is_block_segmentable = false;
		}
		this.inline_annotation_tags_used = this.inline_annotation_tags.length;
	}

	finish_text_block() {
		let whitespace = [], whitespace_only = true;

		if (this.text_chunks.length === 0) {
			return;
		}
		for (let i = 0, len = this.text_chunks.length; i < len; i++) {
			const text_chunk = this.text_chunks[i];
			if (text_chunk.inline_content || text_chunk.text.match(/\S/)) {
				whitespace_only = false;
				whitespace = undefined;
				break;
			} else {
				whitespace.push(this.text_chunks[i].text);
			}
		}
		if (whitespace_only) {
			this.doc.add_item('blockspace', whitespace.join(''));
		} else {
			this.doc.add_item('textblock', new Text_block(this.text_chunks, this.is_block_segmentable));
		}
		this.text_chunks = [];
		this.is_block_segmentable = true;
	}

}

export default Builder;
