import { describe, it } from 'node:test';
import fs from 'fs';
import { fileURLTo_path } from 'url';
import assert from '../../utils/assert.js';
import * as Linear_doc from '../../lib/lineardoc/index.js';
import Segmenter from '../../lib/segmentation/CXSegmenter.js';

const __dirname = fileURLTo_path( new URL( '.', import.meta.url ) );

const all_tests = JSON.parse(
	fs.read_file_sync( new URL( './Segmentation_tests.json', import.meta.url ), 'utf8' )
);

function normalize( html ) {
	const normalizer = new Linear_doc.Normalizer();
	normalizer.init();
	normalizer.write( html.replace( /[\t\r\n]+/gm, '' ) );
	return normalizer.get_html();
}

function get_parsed_doc( content ) {
	const parser = new Linear_doc.Parser( new Linear_doc.Mw_contextualizer() );
	parser.init();
	parser.write( content );
	return parser.builder.doc;
}

function run_test( test, lang ) {
	const test_data = fs.read_file_sync( __dirname + '/data/' + test.source, 'utf8' );
	const parsed_doc = get_parsed_doc( test_data );
	const segmenter = new Segmenter();
	const segmented_linear_doc = segmenter.segment( parsed_doc, lang );
	const result = normalize( segmented_linear_doc.get_html() );
	const expected_result_data = normalize(
		fs.read_file_sync( __dirname + '/data/' + test.result, 'utf8' )
	);
	it( 'should not have any errors when: ' + test.desc, () => {
		assert.deep_equal( result, expected_result_data, test.source + ': ' + test.desc || '' );
	} );
}

for ( const lang in all_tests ) {
	describe( 'Segmentation tests for ' + lang, () => {
		const tests = all_tests[ lang ];
		const len = tests.length;
		for ( let i = 0; i < len; i++ ) {
			if ( tests[ i ].skip ) {
				continue;
			}
			run_test( tests[ i ], lang );
		}
	} );
}
