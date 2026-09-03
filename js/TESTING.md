# Running the JavaScript tests

This repository keeps the original Wikimedia Content Translation (cxserver)
JavaScript implementation under `js/`, together with a Node `node:test` test
suite for the segmentation pipeline under `tests/unit/segmentation/`
(notably `CXSegmenter.test.js`).

This document explains how to run those JS tests locally and in CI (on a new
pull request).

## Prerequisites

- **Node.js >= 18** (enforced by the `engines` field in `js/package.json`).
- **JS dependencies installed once** (installed into `js/node_modules`):

  ```bash
  cd js
  npm install          # or: npm ci   (uses the committed package-lock.json)
  ```

  This installs, among others, `sentencex`, `sax`, `js-yaml` and the
  `@wikimedia/language-data` package that `js/lib/lineardoc/util.js` requires.

## Run the segmentation test

From the **repository root**:

```bash
node --test tests/unit/segmentation/CXSegmenter.test.js
```

This uses Node's built-in test runner (no separate test framework needed). The
suite reads fixture HTML from `tests/unit/segmentation/data/`, compares the
segmented output against the expectations listed in
`tests/unit/segmentation/SegmentationTests.json`, and reports each case.

### How the test resolves the JS library

`CXSegmenter.test.js` imports the JS library with relative paths
(`../../lib/lineardoc`, `../../lib/segmentation/CXSegmenter`). Because the JS
sources live in `js/lib/` while the test lives in `tests/unit/segmentation/`,
the repo provides a symlink:

```
tests/lib  ->  ../js/lib
```

so the test's `../../lib/...` imports resolve to the real JS sources. (If you
prefer not to use the symlink, change the test's import paths to
`../../../js/lib/...` instead.)

## Running all JS tests

`js/package.json` defines the following scripts:

```json
"scripts": {
  "unittest": "node --test",
  "test": "npm run lint && npm run unittest",
  "lint": "eslint .",
  "coverage": "nyc --reporter=lcov node --test"
}
```

- `npm run unittest` discovers and runs every `*.test.js` under the current
  directory (Node auto-discovers a `test/` folder). From `js/`, run the suite
  with:

  ```bash
  cd js && node --test ../tests/unit/segmentation/CXSegmenter.test.js
  ```

- `npm test` runs ESLint **before** the tests. **Note:** `js/` currently has no
  ESLint configuration file, so `npm run lint` fails until one is added. To run
  the tests without linting, use `npm run unittest` (or the `node --test ...`
  command above) directly.

- `npm run coverage` produces an `lcov` coverage report via `nyc`.

## In CI (new pull requests)

A dedicated workflow, `.github/workflows/js-tests.yml`, runs the JS suite on
every pull request (and push) targeting the main branches, so the JS test
status is visible on each PR. The job:

1. Checks out the repo.
2. Sets up Node 20.
3. Installs JS dependencies with `npm ci` (in `js/`).
4. Runs `node --test ../tests/unit/segmentation/CXSegmenter.test.js`.

## Current status

The suite **passes**: all 40 cases in `tests/unit/segmentation/CXSegmenter.test.js`
(parse → contextualize → segment → serialize, including references, figures,
media and transclusion scenarios) run green both locally and in CI. Getting
there required fixing several porting defects in `js/lib` (see the git history of
this branch):

**Previous session**
- Wrong relative import `./../util.js` → `./util.js` in `Doc.js`,
  `text_block.js` and `mw_contextualizer.js`.
- Case-sensitive filenames: imports referenced `./utils.js`, `./TextBlock.js`
  and `./TextChunk.js` (valid on macOS, broken on Linux CI) → corrected to
  `Utils.js`, `text_block.js` and `text_chunk.js`.
- Missing npm dependency `@wikimedia/language-data` (now declared in
  `js/package.json`).
- A systemic **snake_case vs camelCase** naming mismatch between method/function
  definitions and their call sites; camelCase aliases were added where needed
  (e.g. `Contextualizer.getContext`/`get_context`, `text_block.getHtml`/
  `get_html`, and the `Utils` exports).

**This fix-up (to make the segmentation pipeline correct, not just loadable)**
- `text_block.js`: `setLinkIds()` now returns `this` (previously it returned the
  `undefined` result of `set_link_ids_in_place`, so segmented text blocks were
  added to the doc as `undefined` items and `Doc.getHtml()` crashed on
  `item.attributes`).
- `text_block.js`: the constructor stores the segmentability flag as
  `this.canSegment` (was `this.can_segment`), matching the `textBlock.canSegment`
  check used by `Doc.segment()` — otherwise text blocks were never actually
  segmented.
- `text_block.js`: fixed a variable that shadowed the `text_chunk` (TextChunk)
  class inside `segment()`, so splitting a chunk at a sentence boundary no longer
  tried to instantiate a chunk object.
- `text_block.js`: the inline-content branch now calls
  `text_chunk.inline_content.getHtml()` (was `.get_html()`), so sub-documents
  such as footnotes/references render correctly instead of being treated as empty
  tags (which threw on `tag.name`).
- `segmentation/CXSegmenter.js`: converted to an ES module (`export default` +
  `import segment from 'sentencex'`) to match upstream cxserver.

### Known limitations
- `npm test` still runs ESLint first, and `js/` has no ESLint config yet, so
  `npm run lint` (and therefore `npm test`) fails until a config is added. Use
  `npm run unittest` / `node --test ...` to run the tests directly.
- The JS under `js/lib` is a port of upstream cxserver; these tests cover the
  segmentation pipeline. Other cxserver behaviours are not exercised here.
