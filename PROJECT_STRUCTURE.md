# Project Structure Documentation - Core HTML Processing Only

## Current JavaScript Structure (Simplified)

### Directory Tree
```
cxsever/
└── www/
    └── js/
        ├── server.js                    # Main Express server (only /textp endpoint)
        ├── package.json                 # Dependencies and scripts
        └── lib/                         # Core libraries
            ├── d/                       # Data/processing layer
            │   ├── u.js                 # HTML processing utilities (main logic)
            │   └── MWPageLoader.yaml    # Configuration file
            ├── lineardoc/               # Linear document processing
            │   ├── index.js             # Module exports
            │   ├── Parser.js            # HTML SAX parser
            │   ├── Builder.js           # Document builder
            │   ├── Doc.js               # Document model
            │   ├── TextBlock.js         # Text block representation
            │   ├── TextChunk.js         # Text chunk representation
            │   ├── utils.js             # Utility functions
            │   ├── Normalizer.js        # HTML normalizer
            │   ├── Contextualizer.js    # Base contextualizer
            │   ├── MwContextualizer.js  # MediaWiki contextualizer
            │   └── util.js              # Helper utilities
            └── segmentation/            # Segmentation for translation
                └── CXSegmenter.js       # Content segmentation
```

### Simplified Server (`server.js`)
```javascript
var express = require("express");
var cors = require('cors');
var bodyParser = require('body-parser');
var u = require('./lib/d/u.js');

var app = express();

app.use(cors());
app.use(bodyParser.json({ limit: '50mb' }));
app.use(bodyParser.urlencoded({ limit: '50mb', extended: false }));

// Main endpoint - Process HTML for translation
app.post("/textp", (req, res) => {
    const sourceHtml = req.body.html;

    if (!sourceHtml || sourceHtml.trim().length === 0) {
        res.send({
            result: 'Content for translate is not given or is empty'
        });
        res.status(500).end();
        return;
    }
    try {
        const processedText = u.tet(sourceHtml);
        res.send({ result: processedText });
    } catch (error) {
        console.error(error);
        res.send({
            result: error.message
        });
        res.status(500).end();
    }
});

app.listen(process.env.PORT || 8000, function () {
    console.log("Node.js app is listening on port " + (process.env.PORT || 8000));
});
```

### Core Processing (`lib/d/u.js`)
```javascript
'use strict';

const LinearDoc = require('../lineardoc')
const fs = require('fs'),
    yaml = require('js-yaml'),
    CXSegmenter = require('../segmentation/CXSegmenter');

const pageloaderConfig = yaml.load(fs.readFileSync(__dirname + '/MWPageLoader.yaml'));
const removableSections = pageloaderConfig.removableSections;

function tet(source_HTML) {
    // 1. Parse HTML with MediaWiki contextualization
    const parser = new LinearDoc.Parser(new LinearDoc.mw_contextualizer(
        { removableSections: removableSections }
    ), {
        wrapSections: true
    });

    parser.init();
    parser.write(source_HTML);

    // 2. Get and wrap sections
    let parsedDoc = parser.builder.doc;
    parsedDoc = parsedDoc.wrapSections();

    // 3. Segment for translation
    const segmentedDoc = new CXSegmenter().segment(parsedDoc, "en");

    // 4. Return processed HTML
    const result = segmentedDoc.get_html();
    return result;
}

module.exports = { tet };
```

---

## Python Structure (Simplified)

### Directory Tree
```
cxserver_py/
├── app.py                              # Main Flask/FastAPI application
├── requirements.txt                    # Python dependencies
├── config.py                           # Configuration management
├── run.py                              # Development server runner
├── wsgi.py                             # Production WSGI entry point (optional)
├── config/
│   └── MWPageLoader.yaml               # MediaWiki page loader config
├── lib/                                # Core libraries
│   ├── __init__.py
│   ├── processor.py                    # Main HTML processor (u.tet equivalent)
│   ├── lineardoc/                      # Linear document processing
│   │   ├── __init__.py
│   │   ├── parser.py                   # HTML parser (SAX-based)
│   │   ├── builder.py                  # Document builder
│   │   ├── doc.py                      # Document model
│   │   ├── text_block.py               # Text block representation
│   │   ├── text_chunk.py               # Text chunk representation
│   │   ├── utils.py                    # Utility functions
│   │   ├── normalizer.py               # HTML normalizer
│   │   ├── contextualizer.py           # Base contextualizer
│   │   ├── mw_contextualizer.py        # MediaWiki contextualizer
│   │   └── util.py                     # Helper utilities
│   └── segmentation/                   # Segmentation for translation
│       ├── __init__.py
│       └── cx_segmenter.py             # Content segmentation
└── tests/                              # Test suite
    ├── __init__.py
    ├── test_processor.py               # Test main processor
    ├── test_lineardoc.py               # Test lineardoc modules
    ├── test_segmentation.py            # Test segmentation
    └── fixtures/                       # Test data (before/after HTML)
        ├── input_1.html
        ├── expected_1.html
        ├── input_2.html
        └── expected_2.html
```

### Main Application (`app.py`)
```python
"""
CX Server - Content Translation HTML Processing
Main Flask application with single /textp endpoint
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from lib.processor import process_html
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Set max content length (50MB like Node.js version)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


@app.route('/textp', methods=['POST'])
def process_text():
    """
    Process HTML for translation

    Request:
        POST /textp
        Content-Type: application/json
        Body: {"html": "<p>Your HTML here</p>"}

    Response:
        Success: {"result": "<processed HTML>"}
        Error: {"result": "error message"}, 500
    """
    try:
        # Get JSON data
        data = request.get_json()

        if not data:
            return jsonify({
                'result': 'No JSON data provided'
            }), 400

        source_html = data.get('html', '')

        # Validate input
        if not source_html or source_html.strip() == '':
            return jsonify({
                'result': 'Content for translate is not given or is empty'
            }), 500

        # Process HTML
        logger.info(f"Processing HTML ({len(source_html)} characters)")
        processed_text = process_html(source_html)

        logger.info(f"Processing complete ({len(processed_text)} characters)")
        return jsonify({'result': processed_text})

    except Exception as error:
        logger.error(f"Error processing HTML: {error}", exc_info=True)
        return jsonify({
            'result': str(error)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    port = 8000
    logger.info(f"Starting CX Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
```

### Core Processor (`lib/processor.py`)
```python
"""
Main HTML processing module
Equivalent to lib/d/u.js - the tet() function
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any

from lib.lineardoc import Parser, mw_contextualizer
from lib.segmentation import CXSegmenter


def load_config() -> Dict[str, Any]:
    """
    Load configuration from MWPageLoader.yaml

    Returns:
        Configuration dictionary
    """
    config_path = Path(__file__).parent.parent / 'config' / 'MWPageLoader.yaml'

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


# Load config once at module import
_config = load_config()
_removable_sections = _config.get('removableSections', {})


def process_html(source_html: str) -> str:
    """
    Process HTML for translation
    Equivalent to u.tet() function in JavaScript

    Pipeline:
    1. Parse HTML with MediaWiki contextualization
    2. Wrap sections
    3. Segment content for translation
    4. Return processed HTML

    Args:
        source_html: Raw HTML content from MediaWiki

    Returns:
        Processed and segmented HTML ready for translation

    Raises:
        ValueError: If source_html is empty
        Exception: If processing fails
    """
    if not source_html or not source_html.strip():
        raise ValueError("Source HTML is empty")

    # 1. Parse HTML with MediaWiki contextualization
    parser = Parser(
        contextualizer=mw_contextualizer(removable_sections=_removable_sections),
        wrap_sections=True
    )

    parser.init()
    parser.write(source_html)

    # 2. Get parsed document and wrap sections
    parsed_doc = parser.builder.doc
    parsed_doc = parsed_doc.wrap_sections()

    # 3. Segment for translation
    segmenter = CXSegmenter()
    segmented_doc = segmenter.segment(parsed_doc, "en")

    # 4. Return processed HTML
    result = segmented_doc.get_html()

    return result
```

### Configuration (`config.py`)
```python
"""Application configuration"""
import os
from pathlib import Path


class Config:
    """Base configuration"""
    BASE_DIR = Path(__file__).parent
    CONFIG_DIR = BASE_DIR / 'config'

    # Server settings
    PORT = int(os.environ.get('PORT', 8000))
    HOST = os.environ.get('HOST', '0.0.0.0')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

    # Request limits (50MB like Node.js version)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
```

### Dependencies (`requirements.txt`)
```txt
# Web Framework
Flask==3.0.0
flask-cors==4.0.0

# Core dependencies
PyYAML==6.0.1           # For YAML config loading
lxml==5.1.0             # For HTML/XML parsing
pysbd==0.3.4            # Sentence boundary detection

# Development
pytest==8.0.0
pytest-cov==4.1.0

# Production server (optional)
gunicorn==21.2.0
```

### Module Structure

#### `lib/__init__.py`
```python
"""CX Server core library"""
from lib.processor import process_html

__all__ = ['process_html']
```

#### `lib/lineardoc/__init__.py`
```python
"""Linear document processing library"""
from lib.lineardoc.parser import Parser
from lib.lineardoc.builder import Builder
from lib.lineardoc.doc import Doc
from lib.lineardoc.text_block import text_block
from lib.lineardoc.text_chunk import text_chunk
from lib.lineardoc.normalizer import Normalizer
from lib.lineardoc.contextualizer import Contextualizer
from lib.lineardoc.mw_contextualizer import mw_contextualizer
from lib.lineardoc.utils import utils

__all__ = [
    'Parser',
    'Builder',
    'Doc',
    'text_block',
    'text_chunk',
    'Normalizer',
    'Contextualizer',
    'mw_contextualizer',
    'utils'
]
```

#### `lib/segmentation/__init__.py`
```python
"""Content segmentation for translation"""
from lib.segmentation.cx_segmenter import CXSegmenter

__all__ = ['CXSegmenter']
```

### Development Runner (`run.py`)
```python
"""Development server runner"""
from app import app
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True
    )
```

### Testing Structure (`tests/test_processor.py`)
```python
"""Test HTML processor"""
import pytest
from pathlib import Path
from lib.processor import process_html


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory"""
    return Path(__file__).parent / 'fixtures'


def test_process_html_with_fixture(fixtures_dir):
    """Test processing with real input/output examples"""
    # Load input
    input_file = fixtures_dir / 'input_1.html'
    expected_file = fixtures_dir / 'expected_1.html'

    with open(input_file, 'r', encoding='utf-8') as f:
        input_html = f.read()

    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_html = f.read()

    # Process
    result = process_html(input_html)

    # Compare
    assert result.strip() == expected_html.strip()


def test_process_empty_html():
    """Test that empty HTML raises error"""
    with pytest.raises(ValueError):
        process_html("")


def test_process_whitespace_only():
    """Test that whitespace-only HTML raises error"""
    with pytest.raises(ValueError):
        process_html("   \n  \t  ")
```

---

## File-by-File Mapping

| JavaScript | Python | Purpose |
|-----------|--------|---------|
| `server.js` | `app.py` | Main application server |
| `lib/d/u.js` | `lib/processor.py` | Core HTML processing |
| `lib/d/MWPageLoader.yaml` | `config/MWPageLoader.yaml` | Configuration |
| `lib/lineardoc/Parser.js` | `lib/lineardoc/parser.py` | HTML parser |
| `lib/lineardoc/Builder.js` | `lib/lineardoc/builder.py` | Document builder |
| `lib/lineardoc/Doc.js` | `lib/lineardoc/doc.py` | Document model |
| `lib/lineardoc/TextBlock.js` | `lib/lineardoc/text_block.py` | Text blocks |
| `lib/lineardoc/TextChunk.js` | `lib/lineardoc/text_chunk.py` | Text chunks |
| `lib/lineardoc/utils.js` | `lib/lineardoc/utils.py` | Utilities |
| `lib/lineardoc/Normalizer.js` | `lib/lineardoc/normalizer.py` | HTML normalizer |
| `lib/lineardoc/Contextualizer.js` | `lib/lineardoc/contextualizer.py` | Base contextualizer |
| `lib/lineardoc/MwContextualizer.js` | `lib/lineardoc/mw_contextualizer.py` | MW contextualizer |
| `lib/lineardoc/util.js` | `lib/lineardoc/util.py` | Helper utilities |
| `lib/segmentation/CXSegmenter.js` | `lib/segmentation/cx_segmenter.py` | Content segmenter |

---

## Quick Start

### Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Development Server
```bash
python run.py
# or
python app.py
```

### Test the Endpoint
```bash
curl -X POST http://localhost:8000/textp \
  -H "Content-Type: application/json" \
  -d '{"html": "<p>Hello world</p>"}'
```

### Run Tests
```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=lib --cov-report=html
```

---

## Next Steps

**Ready to proceed with implementation!**

Please provide:
1. **Input HTML examples** (before processing)
2. **Expected output HTML** (after processing)
3. **Content of `MWPageLoader.yaml`** configuration file

With these examples, I can:
- Create exact Python equivalents of all modules
- Ensure output matches JavaScript version 100%
- Build comprehensive test suite
- Verify the entire pipeline works correctly

🚀 Ready when you are!
