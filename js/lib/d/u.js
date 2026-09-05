'use strict';

const Linear_doc = require('../lineardoc')

const fs = require('fs'),
	yaml = require('js-yaml'),
	CXSegmenter = require('../segmentation/CXSegmenter');

const pageloader_config = yaml.load(fs.readFileSync(__dirname + '/MWPage_loader.yaml'));

const removable_sections = pageloader_config.removable_sections;

function normalize(html) {
	const normalizer = new Linear_doc.Normalizer();
	normalizer.init();
	normalizer.write(html.replace(/[\t\r\n]+/g, ''));
	return normalizer.get_html();
}

function tet(source_HTML) {

	const parser = new Linear_doc.Parser(new Linear_doc.MwContextualizer(
		{ removable_sections: removable_sections }
	), {
		wrap_sections: true
	});

	parser.init();
	parser.write(source_HTML);
	let parsed_doc = parser.builder.doc;
	parsed_doc = parsed_doc.wrap_sections();

	const segmented_doc = new CXSegmenter().segment(parsed_doc, "en");

	const result = segmented_doc.get_html();

	return result;
}

module.exports = {
	tet
};
