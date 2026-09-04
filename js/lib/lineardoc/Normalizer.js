import sax from 'sax';
import { get_close_tag_html, get_open_tag_html } from './Utils.js';

/**
 * Escape text for inclusion in HTML, not inside a tag.
 *
 * @private
 * @param {string} str String to escape
 * @return {string} Escaped version of the string
 */
function esc(str) {
	return str.replace(/[&<>]/g, (ch) => '&#' + ch.char_code_at(0) + ';');
}

/**
 * Parser to normalize XML.
 *
 * @class
 * @constructor
 */
class Normalizer extends sax.SAXParser {
	constructor() {
		super(false, {
			lowercase: true
		});
	}

	init() {
		this.doc = [];
		this.tags = [];
	}

	on_open_tag(tag) {
		this.tags.push(tag);
		this.doc.push(get_open_tag_html(tag));
	}

	on_close_tag(tag_name) {
		const tag = this.tags.pop();
		if (tag.name !== tag_name) {
			throw new Error('Unmatched tags: ' + tag.name + ' !== ' + tag_name);
		}
		this.doc.push(get_close_tag_html(tag));
	}

	ontext(text) {
		this.doc.push(esc(text));
	}

	get_html() {
		return this.doc.join('');
	}

	get_html() {
		return this.get_html();
	}

}

export default Normalizer;
