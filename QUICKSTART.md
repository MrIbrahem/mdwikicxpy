# Quick Start Guide - CXServer Python

## Installation

```bash
# Clone the repository
git clone https://github.com/WikiAr/mdwikicxpy.git
cd mdwikicxpy

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

```bash
# Run integration test
python tests/test_processing.py

# Run comprehensive test suite
python tests/test_comprehensive.py
```

## Starting the Server

```bash
# Navigate to Python app directory
cd cxsever/www/python

# Run with Flask development server
python app.py

# Or run with Gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Server will start on `http://localhost:8000`

## Using the API

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

### Process HTML
```bash
curl -X POST http://localhost:8000/HtmltoSegments \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html><body><p>This is a test. Another sentence here.</p></body></html>"
  }'
```

Response:
```json
{
  "result": "<html id=\"0\">... processed HTML with sections, segments, and IDs ..."
}
```

## Using as a Library

```python
# Import the processor
from lib.processor import process_html

# Process MediaWiki HTML
source_html = """
<html>
<body>
<h2>Introduction</h2>
<p>This is a paragraph. It has multiple sentences.</p>
<p>Another paragraph with <a href="/wiki/Link" rel="mw:WikiLink">a link</a>.</p>
</body>
</html>
"""

result = process_html(source_html)
print(result)
```

The result will contain:
- ✅ Wrapped sections with `<section>` tags
- ✅ Segmented sentences with `<span class="cx-segment">`
- ✅ Segment IDs via `data-segmentid` attributes
- ✅ Link IDs via `data-linkid` attributes
- ✅ Section metadata

## What Gets Processed?

The pipeline performs these transformations:

1. **Parse HTML** - Convert to linear document structure
2. **Contextualize** - Apply MediaWiki rules, remove unwanted sections
3. **Wrap Sections** - Add section metadata
4. **Segment** - Break text into translatable sentences
5. **Add IDs** - Track segments and links with unique IDs

## Example Output

Input:
```html
<p>First sentence. Second sentence.</p>
```

Output:
```html
<section data-mw-section-number="0" id="cxSourceSection0" rel="cx:Section">
  <p id="1">
    <span class="cx-segment" data-segmentid="2">First sentence. </span>
    <span class="cx-segment" data-segmentid="3">Second sentence.</span>
  </p>
</section>
```

## Configuration

Configuration is loaded from `config/MWPageLoader.yaml`:

```yaml
removableSections:
  classes:
    - 'noprint'
    - 'metadata'
  rdfa:
    - 'mw:PageProp/toc'
  templates:
    - 'Template:Delete'
```

This controls which sections are removed during processing.

## Troubleshooting

### Import Errors
Make sure you're in the correct directory:
```bash
cd cxsever/www/python
python -c "from lib.processor import process_html; print('OK')"
```

### Empty Output
Check your HTML is valid:
```python
from lib.processor import process_html
result = process_html('<p>Test</p>')
print(len(result))  # Should be > 0
```

### Dependencies Missing
Reinstall requirements:
```bash
pip install -r requirements.txt --force-reinstall
```

## Next Steps

- Read the full [README](cxsever/www/python/README.md)
- Check [CONVERSION_SUMMARY.md](CONVERSION_SUMMARY.md) for technical details
- Review the [test suite](tests/) for usage examples
- Explore the [lib/lineardoc](cxsever/www/python/lib/lineardoc/) modules

## Support

For issues or questions:
- Check the test files for examples
- Review the comprehensive documentation
- Examine the original JavaScript code for reference
