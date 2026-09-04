'use strict';

// Compatibility shim for the upstream cxserver JS test harness.
// The segmentation test only relies on `assert.deep_equal` to compare
// normalized HTML strings, so re-exporting Node's built-in assert is enough.
module.exports = require( 'node:assert' );
