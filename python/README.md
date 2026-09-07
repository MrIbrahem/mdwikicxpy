# MediaWiki CXServer - Python Port

This is a Python port of the MediaWiki Content Translation (CX) Server HTML processing pipeline.

## Overview

The CX server processes MediaWiki HTML through a pipeline that:

1. **Parses HTML** via SAX-style parser into a linear document structure
2. **Applies MediaWiki contextualization** - removes unwanted sections based on YAML config
3. **Wraps sections** with metadata
4. **Segments text** for translation (sentence boundaries)
5. **Adds tracking IDs** for segments and links

## Architecture

### Core Data Classes
- `text_chunk` - A chunk of uniformly-annotated inline text
- `text_block` - A block of annotated inline text
- `Doc` - An HTML document in linear representation

### Processing Modules
- `Parser` - SAX-style HTML parser using lxml
- `Builder` - Document builder for creating linear documents
- `Contextualizer` - Base contextualizer for HTML
- `mw_contextualizer` - MediaWiki-specific contextualizer
- `CXSegmenter` - Sentence boundary detection using pysbd

### Utilities
- `utils` - HTML processing and tag manipulation utilities
- `Normalizer` - XML/HTML normalizer

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### As a Library

```python
from lib.processor import process_html

# Process HTML
result = process_html(source_html)
```

### As a Web Service

```bash
# Run the Flask app
python app.py

# Or with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### API Endpoint

**POST /HtmltoSegments**

Request body:
```json
{
  "html": "<html>...</html>"
}
```

Response:
```json
{
  "result": "processed HTML with segments and IDs"
}
```

## Testing

```bash
python tests/test_processing.py
```

## Configuration

Configuration is loaded from `config/MWPageLoader.yaml` which specifies:
- Removable sections (classes, RDFa types, templates)
- Section wrapping rules

## Implementation Notes

### Differences from JavaScript Version

1. **Parser**: Uses lxml instead of SAX for XML/HTML parsing
2. **Segmentation**: Uses pysbd instead of sentencex for sentence boundary detection
3. **Data Structures**: Uses Python dictionaries instead of JavaScript objects

### Key Design Decisions

- Linear document representation simplifies processing
- Tag contextualizer pattern allows flexible section handling
- Separation of parsing, contextualization, and segmentation

## Project Structure

```
cxsever/www/python/
├── app.py                          # Flask application
├── lib/
│   ├── __init__.py
│   ├── processor.py                # Main processing pipeline
│   ├── lineardoc/
│   │   ├── __init__.py
│   │   ├── text_chunk.py          # text_chunk class
│   │   ├── text_block.py          # text_block class
│   │   ├── doc.py                 # Doc class
│   │   ├── utils.py               # Utility functions
│   │   ├── util.py                # Helper utilities
│   │   ├── normalizer.py          # HTML normalizer
│   │   ├── contextualizer.py      # Base contextualizer
│   │   ├── mw_contextualizer.py   # MW contextualizer
│   │   ├── builder.py             # Document builder
│   │   └── parser.py              # HTML parser
│   └── segmentation/
│       ├── __init__.py
│       └── cx_segmenter.py        # Sentence segmenter
└── config/
    └── MWPageLoader.yaml           # Configuration

tests/
└── test_processing.py              # Integration test
```

## License

This is a port of the MediaWiki Content Translation server.
Original JavaScript version: https://www.mediawiki.org/wiki/Content_translation
