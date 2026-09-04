/**
 * Contextualizer for HTML - tracks the segmentation context of the currently open node
 */
class Contextualizer {
	/**
	 * @param {Object} config
	 */
	constructor(config) {
		this.contexts = [];
		this.config = config || {};
	}

	/**
	 * Get the context for a new tag being opened
	 *
	 * @param {Object} open_tag
	 * @param {string} open_tag.name HTML tag name
	 * @param {Object} open_tag.attributes HTML attributes as a string map
	 * @return {string|undefined} The new context
	 */
	get_child_context(open_tag) {
		// Change to 'media' context inside figure
		if (open_tag.name === 'figure') {
			return 'media';
		}

		// Exception: return to undefined context inside figure//figcaption
		if (open_tag.name === 'figcaption') {
			return undefined;
		}

		// No change: same as parent context
		return this.get_context();
	}

	/**
	 * Get the current context
	 *
	 * @return {string|undefined} The current context
	 */
	get_context() {
		return this.contexts[this.contexts.length - 1];
	}

	/**
	 * Call when a tag opens
	 *
	 * @param {Object} open_tag
	 * @param {string} open_tag.name HTML tag name
	 * @param {Object} open_tag.attributes HTML attributes as a string map
	 */
	on_open_tag(open_tag) {
		this.contexts.push(this.get_child_context(open_tag));
	}

	/**
	 * Call when a tag closes (or just after an empty tag opens)
	 */
	on_close_tag() {
		this.contexts.pop();
	}

	/**
	 * Determine whether sentences can be segmented into spans in this context
	 *
	 * @return {boolean} Whether sentences can be segmented into spans in this context
	 */
	can_segment() {
		return this.get_context() === undefined;
	}

	// camel_case aliases for callers such as Parser
	get_context() {
		return this.get_context();
	}

	on_open_tag(open_tag) {
		return this.on_open_tag(open_tag);
	}

	on_close_tag() {
		return this.on_close_tag();
	}

	can_segment() {
		return this.can_segment();
	}

}

export default Contextualizer;
