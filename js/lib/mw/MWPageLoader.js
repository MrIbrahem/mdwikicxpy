/**
 * @external MTClient
 */

import { MwContextualizer, Parser } from '../lineardoc/index.js';
import CXSegmenter from '../segmentation/CXSegmenter.js';

const removableSections = {
	"classes": [
		"ambox",
		"hatnote",
		"metadata",
		"navbar",
		"navbox",
		"sisterproject",
		"sistersitebox",
		"vertical-navbox"
	],
	"rdfa": [
		"mw:Extension/indicator",
		"mw:Extension/templatestyles"
	],
	"templates": [
		"/^pp(-.*)?$/",
		"/^Articles (for|with|needing|containing).*$/",
		"/^Engvar[AB]$/",
		"/^Use[\\sa-z]+(English|spelling|referencing)$/",
		"/^Use [DMY]+ dates$/",
		"/^Wikipedia articles (for|with|needing|containing).*$/",
		"Anchor",
		"DEFAULTSORT",
		"Esborrany", // Stub category in es.wikipedia
		"Featured article",
		"FR",
		"Mdwiki revid",
		"mdwiki revid",
		"/^[Mm]dwiki[ _]revid$",
		"good article",
		"/^(.*-)?Stub$/",
		"Short description",
		"Void",
		"Italic title", // T216044
		"About",
		"See also", // T300958
		"Redirect", // T300958
		"Distinguish",
		"TOC limit",
		// - /^Redirect\-distinguish$/
		"/^#unlinkedwikibase:id=Q\\d+$/",
		"Other uses",
		"redirect" // T300958
	]
};

class MWPage_loader {

	get_page(content, wrap_sections) {
		let parsed_doc = this.get_parsed_doc(content);
		if (wrap_sections) {
			parsed_doc = parsed_doc.wrap_sections();
		}
		// Extract category tags from source document.
		const segmented_doc = new CXSegmenter().segment(parsed_doc, "en");

		return {
			content: segmented_doc.get_html(),
		};
	}

	get_parsed_doc(source_HTML) {
		const parser = new Parser(new MwContextualizer(
			{ removableSections: removableSections }
		), {
			wrapSections: true
		});

		parser.init();
		parser.write(source_HTML);
		return parser.builder.doc;
	}
}
export default MWPage_loader;
