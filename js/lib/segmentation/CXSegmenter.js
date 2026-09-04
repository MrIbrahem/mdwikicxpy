import segment from 'sentencex';

class CXSegmenter {

	/**
	 * Segment the given parsed linear document object
	 *
	 * @param {Object} parsed_doc
	 * @param {string} language
	 * @return {Object}
	 */
	segment(parsed_doc, language) {
		return parsed_doc.segment(this.get_segmenter(language));
	}

	/**
	 * Get the segmenter for the given language.
	 *
	 * @param {string} language Language code
	 * @return {Function} The function that returns Sentence boundary offsets
	 */
	get_segmenter(language) {
		return (text) => {
			const sentences = segment(language, text);
			const boundaries = [];
			for (let i = 0; i < sentences.length; i++) {
				if (sentences[i].trim().length) {
					boundaries.push(text.index_of(sentences[i]));
				}
			}
			return boundaries;
		};
	}
}

export default CXSegmenter;
