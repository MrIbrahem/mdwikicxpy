# CXServer to Python Conversion Plan

## Project Overview

**Source Project**: CXServer (Content Translation Server)
**Purpose**: HTML processing pipeline for MediaWiki content translation
**Current Stack**: Node.js/JavaScript with Express
**Target Stack**: Python with Flask/FastAPI

### Core Functionality
The system takes HTML input, processes it through a pipeline that:
1. Normalizes HTML structure
2. Parses HTML into a linear document representation
3. Contextualizes content (identifies removable sections)
4. Wraps content into sections
5. Segments text into translatable units
6. Returns processed HTML with segmentation IDs

---

## Architecture Analysis

### Current JavaScript Architecture

```
HTTP Server (Express)
    ↓
Main Endpoint (/HtmltoSegments)
    ↓
u.HtmltoSegments() function
    ↓
LinearDoc Pipeline:
    1. Parser (SAX-based)
    2. MwContextualizer
    3. Builder
    4. Doc (linear representation)
    5. Section Wrapper
    6. CXSegmenter (sentencex)
    ↓
HTML Output
```

### Key Components

1. **Server Layer** (`server.js`)
   - Express HTTP server
   - POST /HtmltoSegments endpoint
   - Body parsing (JSON, up to 50mb)
   - CORS enabled

2. **Core Processing** (`lib/d/segments_main.js`)
   - Main entry point: `HtmltoSegments()` function
   - Orchestrates the pipeline

3. **LinearDoc Library** (`lib/lineardoc/`)
   - **Parser**: SAX-based HTML parser
   - **MwContextualizer**: MediaWiki-specific context handling
   - **Contextualizer**: Base context manager
   - **Builder**: Constructs linear document from parsed HTML
   - **Doc**: Linear document representation
   - **TextBlock**: Block of annotated text
   - **TextChunk**: Individual text segment with tags
   - **Normalizer**: HTML normalization
   - **Utils**: Utility functions

4. **Segmentation** (`lib/segmentation/CXSegmenter.js`)
   - Uses `sentencex` library for sentence boundary detection
   - Language-aware segmentation

5. **Configuration** (`lib/d/MWPageLoader.yaml`)
   - Removable sections configuration
   - Class names, RDFa types, templates

---

## Conversion Strategy

### Phase 1: Foundation (Priority: HIGH)

#### 1.1 Project Setup
- **Task**: Create Python project structure
- **Actions**:
  ```
  cxserver-python/
  ├── app.py                    # Main Flask/FastAPI application
  ├── requirements.txt          # Dependencies
  ├── config/
  │   └── page_loader.yaml     # Configuration
  ├── cxserver/
  │   ├── __init__.py
  │   ├── api/
  │   │   └── routes.py        # API endpoints
  │   ├── core/
  │   │   └── pipeline.py      # Main processing logic
  │   ├── lineardoc/
  │   │   ├── __init__.py
  │   │   ├── parser.py
  │   │   ├── builder.py
  │   │   ├── doc.py
  │   │   ├── text_block.py
  │   │   ├── text_chunk.py
  │   │   ├── contextualizer.py
  │   │   ├── mw_contextualizer.py
  │   │   ├── normalizer.py
  │   │   └── utils.py
  │   ├── segmentation/
  │   │   └── cx_segmenter.py
  │   └── utils/
  │       └── helpers.py
  └── tests/
      ├── __init__.py
      ├── test_parser.py
      ├── test_segmenter.py
      └── test_integration.py
      └── fixtures/                       # Test data (before/after HTML)
        ├── input_1.html
        ├── expected_1.html
        ├── input_2.html
        └── expected_2.html
  ```

#### 1.2 Dependencies Mapping
| JavaScript Package | Python Alternative | Purpose |
|-------------------|-------------------|---------|
| `express` | `flask` or `fastapi` | Web framework |
| `sax` | `lxml.etree.iterparse()` or `html.parser` | HTML parsing |
| `js-yaml` | `pyyaml` | YAML config loading |
| `sentencex` | `pysbd` or `spacy` | Sentence segmentation |
| `body-parser` | Built into Flask/FastAPI | Request parsing |
| `cors` | `flask-cors` | CORS handling |

**Recommended Dependencies**:
```txt
flask==3.0.0
flask-cors==4.0.0
pyyaml==6.0.1
lxml==5.1.0
pysbd==0.3.4
beautifulsoup4==4.12.0
```

---

### Phase 2: Core Components (Priority: HIGH)

#### 2.1 Data Structures

**Python Equivalents**:

```python
# TextChunk class
@dataclass
class TextChunk:
    text: str
    tags: List[Dict]
    inline_content: Optional[Any] = None

# TextBlock class
@dataclass
class TextBlock:
    text_chunks: List[TextChunk]
    can_segment: bool
    offsets: List[Dict] = field(default_factory=list)

# Doc class
class Doc:
    def __init__(self, wrapper_tag=None):
        self.items = []
        self.wrapper_tag = wrapper_tag
        self.categories = []

    def add_item(self, item_type: str, item: Any):
        self.items.append({'type': item_type, 'item': item})
        return self
```

#### 2.2 HTML Parser

**Key Considerations**:
- JavaScript uses SAX (streaming) parser
- Python options:
  - **lxml.etree.iterparse()**: Streaming, memory-efficient
  - **html.parser + custom state machine**: More control
  - **BeautifulSoup**: Simpler but loads entire DOM

**Recommended Approach**: Use `lxml` with custom SAX-style event handler

```python
from lxml import etree

class Parser:
    def __init__(self, contextualizer, options=None):
        self.contextualizer = contextualizer
        self.options = options or {}
        self.builder = None
        self.root_builder = None
        self.all_tags = []

    def parse(self, html_string):
        # Implement streaming parse with event callbacks
        # Similar to onopentag, onclosetag, ontext
        pass
```

#### 2.3 Contextualizer

**Translation Notes**:
- Manages parsing context (removable sections, media, etc.)
- Tracks tag hierarchy
- Determines if content is translatable

```python
class Contextualizer:
    def __init__(self):
        self.context_stack = []

    def on_open_tag(self, tag):
        # Update context based on tag
        pass

    def on_close_tag(self, tag):
        # Pop context
        pass

    def can_segment(self):
        # Check if current context allows segmentation
        return 'removable' not in self.context_stack
```

#### 2.4 MwContextualizer

**MediaWiki-specific logic**:
- Load YAML configuration
- Check against removable sections (classes, RDFa, templates)
- Handle transclusions, references, media

```python
import yaml
import re

class MwContextualizer(Contextualizer):
    def __init__(self, config):
        super().__init__()
        self.removable_sections = config.get('removableSections', {})
        self.compile_patterns()

    def is_removable(self, tag):
        # Check classes
        # Check RDFa typeof
        # Check template names
        pass
```

---

### Phase 3: Segmentation (Priority: HIGH)

#### 3.1 Sentence Segmenter

**Options**:
1. **pysbd** (Python Sentence Boundary Disambiguation)
   - Direct replacement for sentencex
   - Language-aware
   - Fast

2. **spaCy**
   - More accurate
   - Heavier (needs language models)
   - Overkill for this use case

**Recommended**: Use `pysbd`

```python
from pysbd import Segmenter

class CXSegmenter:
    def segment(self, parsed_doc, language):
        return parsed_doc.segment(self.get_segmenter(language))

    def get_segmenter(self, language):
        segmenter = Segmenter(language=language, clean=False)

        def boundary_function(text):
            sentences = segmenter.segment(text)
            boundaries = []
            for sentence in sentences:
                if sentence.strip():
                    boundaries.append(text.index(sentence))
            return boundaries

        return boundary_function
```

---

### Phase 4: HTTP Server (Priority: MEDIUM)

#### 4.1 API Layer

**FastAPI Approach** (Recommended):
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextProcessRequest(BaseModel):
    html: str

@app.post("/HtmltoSegments")
async def process_text(request: TextProcessRequest):
    if not request.html or not request.html.strip():
        raise HTTPException(
            status_code=500,
            detail="Content for translate is not given or is empty"
        )

    try:
        from cxserver.core.pipeline import process_html
        result = process_html(request.html)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Flask Approach** (Alternative):
```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/HtmltoSegments', methods=['POST'])
def process_text():
    data = request.get_json()
    source_html = data.get('html', '')

    if not source_html or not source_html.strip():
        return jsonify({'result': 'Content for translate is not given or is empty'}), 500

    try:
        from cxserver.core.pipeline import process_html
        result = process_html(source_html)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'result': str(e)}), 500
```

---

### Phase 5: Testing Strategy (Priority: HIGH)

#### 5.1 Test Data Collection
1. **Export test cases from JS project**:
   - Create test inputs (various HTML samples)
   - Run through JS version
   - Save outputs as reference

2. **Test categories**:
   - Simple paragraphs
   - Complex nested structures
   - MediaWiki-specific elements (references, transclusions)
   - Edge cases (malformed HTML, empty content)

#### 5.2 Unit Tests

```python
# tests/test_parser.py
import pytest
from cxserver.lineardoc.parser import Parser

def test_simple_paragraph():
    html = "<p>Hello world</p>"
    parser = Parser(contextualizer=None)
    doc = parser.parse(html)
    assert doc is not None

def test_nested_tags():
    html = "<p>Hello <b>bold</b> world</p>"
    # ... assertions
```

#### 5.3 Integration Tests

```python
# tests/test_integration.py
def test_full_pipeline():
    input_html = """
    <html>
    <body>
    <p>This is a test paragraph.</p>
    </body>
    </html>
    """

    from cxserver.core.pipeline import process_html
    output = process_html(input_html)

    # Verify segmentation IDs are present
    assert 'data-segmentid' in output or 'id=' in output
```

#### 5.4 Regression Tests

**Strategy**: Compare Python output vs JavaScript output
```python
def test_regression_against_js():
    # Load test cases from JSON/YAML
    test_cases = load_test_cases('test_data.json')

    for case in test_cases:
        py_output = process_html(case['input'])
        js_output = case['expected_output']

        # Compare (may need normalization)
        assert normalize(py_output) == normalize(js_output)
```

---

## Implementation Roadmap

### Sprint 1 (Week 1): Foundation
- [ ] Set up Python project structure
- [ ] Install and configure dependencies
- [ ] Implement basic data classes (TextChunk, TextBlock, Doc)
- [ ] Port utility functions
- [ ] Load YAML configuration

### Sprint 2 (Week 2): Core Parsing
- [ ] Implement Parser class with lxml
- [ ] Port Contextualizer base class
- [ ] Port MwContextualizer
- [ ] Implement Builder class
- [ ] Test basic HTML parsing

### Sprint 3 (Week 3): Document Processing
- [ ] Complete Doc class implementation
- [ ] Implement section wrapping logic
- [ ] Port Normalizer
- [ ] Add ID generation and management
- [ ] Test document operations

### Sprint 4 (Week 4): Segmentation
- [ ] Implement CXSegmenter with pysbd
- [ ] Test sentence boundary detection
- [ ] Integrate segmentation into pipeline
- [ ] Handle multiple languages

### Sprint 5 (Week 5): API & Integration
- [ ] Create Flask/FastAPI server
- [ ] Implement /HtmltoSegments endpoint
- [ ] Add error handling
- [ ] Configure CORS
- [ ] End-to-end testing

### Sprint 6 (Week 6): Testing & Validation
- [ ] Create comprehensive test suite
- [ ] Run regression tests against JS version
- [ ] Fix discrepancies
- [ ] Performance optimization
- [ ] Documentation

---

## Critical Challenges & Solutions

### Challenge 1: SAX Parser Differences
**Issue**: JavaScript uses streaming SAX parser; Python's html.parser works differently

**Solution**:
- Use `lxml.etree.iterparse()` in streaming mode
- OR implement custom state machine with BeautifulSoup events
- Maintain tag stack manually to replicate SAX behavior

### Challenge 2: JavaScript Object Model
**Issue**: JavaScript's loose typing and object manipulation vs Python's stricter approach

**Solution**:
- Use `dataclasses` or `pydantic` models for structure
- Use `typing` module for type hints
- Careful handling of `None` vs empty objects

### Challenge 3: Regular Expression Differences
**Issue**: JavaScript regex syntax differs from Python

**Solution**:
- Review all regex patterns in MWPageLoader.yaml
- Test pattern matching carefully
- Use `re.compile()` for efficiency

### Challenge 4: Sentence Segmentation Library
**Issue**: `sentencex` (JS) vs `pysbd` (Python) may have different behavior

**Solution**:
- Create test corpus
- Compare outputs
- Adjust parameters or post-process if needed
- Consider creating wrapper for consistent behavior

### Challenge 5: Asynchronous Processing
**Issue**: JavaScript's event loop vs Python's async/await

**Solution**:
- Most of this pipeline is synchronous, so not a major issue
- Use `asyncio` only if needed for I/O operations
- FastAPI natively supports async endpoints

---

## Testing & Validation Strategy

### Validation Criteria
1. **Functional Equivalence**: Python output matches JavaScript output for same input
2. **Performance**: Processing time within 2x of JavaScript version
3. **Memory**: No memory leaks, efficient handling of large documents
4. **Edge Cases**: Handles malformed HTML, empty content, special characters

### Test Data Sources
1. Sample MediaWiki articles (various languages)
2. Edge case HTML snippets
3. Malformed HTML
4. Large documents (stress testing)

### Metrics to Track
- Processing time per 1000 chars
- Memory usage
- Segmentation accuracy
- Output size vs input size

---

## Deployment Considerations

### Development Environment
```bash
# requirements.txt
flask==3.0.0
flask-cors==4.0.0
fastapi==0.109.0
uvicorn==0.27.0
pyyaml==6.0.1
lxml==5.1.0
pysbd==0.3.4
beautifulsoup4==4.12.0
pytest==7.4.0
```

### Production Environment
- **Web Server**: Gunicorn (for Flask) or Uvicorn (for FastAPI)
- **Reverse Proxy**: Nginx
- **Process Manager**: Supervisor or systemd
- **Monitoring**: Prometheus + Grafana

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Migration Path

### Parallel Running Strategy
1. Deploy Python version alongside JavaScript version
2. Route small percentage of traffic to Python
3. Compare outputs in production
4. Gradually increase traffic to Python version
5. Monitor for issues
6. Full cutover when validated

### Rollback Plan
- Keep JavaScript version running
- Feature flag for routing
- Quick switch back if issues detected

---

## AI Agent Instructions

### For Automated Conversion

**Phase-by-Phase Instructions**:

#### Phase 1: Setup
```
1. Create project structure as outlined in Phase 1.1
2. Generate requirements.txt with dependencies from Phase 1.2
3. Create empty __init__.py files in all packages
4. Copy MWPageLoader.yaml to config/ directory
```

#### Phase 2: Data Classes
```
1. Convert TextChunk (TextChunk.js → text_chunk.py)
   - Use @dataclass decorator
   - Maintain same properties: text, tags, inline_content

2. Convert TextBlock (TextBlock.js → text_block.py)
   - Port all methods
   - Pay attention to offset calculations

3. Convert Doc (Doc.js → doc.py)
   - Port linear representation logic
   - Maintain items array structure
   - Port all transformation methods
```

#### Phase 3: Parser
```
1. Port Utils first (Utils.js → utils.py)
   - Port all tag checking functions (isReference, is_math, etc.)
   - Port tag cloning functions

2. Port Contextualizer (Contextualizer.js → contextualizer.py)
   - Maintain context stack
   - Port tag tracking logic

3. Port MwContextualizer (MwContextualizer.js → mw_contextualizer.py)
   - Load YAML config
   - Compile regex patterns
   - Port removable section detection

4. Port Parser (Parser.js → parser.py)
   - Implement using lxml.etree.iterparse()
   - Maintain event-driven architecture
   - Port block tag definitions
```

#### Phase 4: Builder
```
1. Port Builder class (Builder.js → builder.py)
   - Maintain tag stacks
   - Port block tag push/pop logic
   - Port inline annotation handling
   - Port text chunk assembly
```

#### Phase 5: Segmentation
```
1. Port CXSegmenter (CXSegmenter.js → cx_segmenter.py)
   - Replace sentencex with pysbd
   - Maintain same interface
   - Port boundary detection logic
```

#### Phase 6: Pipeline Integration
```
1. Create main pipeline (pipeline.py)
   - Port u.HtmltoSegments() function
   - Wire all components together
   - Add error handling

2. Create API endpoints (routes.py, app.py)
   - Implement /HtmltoSegments POST endpoint
   - Add CORS configuration
   - Add request validation
```

#### Phase 7: Testing
```
1. Generate test cases from JavaScript version
   - Run JS version with various inputs
   - Save outputs as expected results

2. Create unit tests for each component
3. Create integration tests
4. Run regression tests
```

### Conversion Rules

**Variable Naming**:
- `camelCase` (JS) → `snake_case` (Python)
- Class names remain `PascalCase`

**Type Conversions**:
- `{}` → `{}`
- `[]` → `[]`
- `null` → `None`
- `undefined` → `None`
- `const/let/var` → type annotations

**Function Conversions**:
- `function name() {}` → `def name():`
- Arrow functions → lambda or def
- `this.` → `self.`
- `module.exports` → class/function definition

**Array Methods**:
- `.push()` → `.append()`
- `.pop()` → `.pop()`
- `.splice()` → list slicing
- `.filter()` → list comprehension or `filter()`
- `.map()` → list comprehension or `map()`
- `.includes()` → `in` operator

**String Methods**:
- `.trim()` → `.strip()`
- `.replace()` → `.replace()`
- `.match()` → `re.search()` or `re.match()`

---

## Success Criteria

### Functional Requirements
- ✅ Accepts HTML via POST /HtmltoSegments endpoint
- ✅ Returns segmented HTML with IDs
- ✅ Handles MediaWiki-specific elements
- ✅ Removes configured sections
- ✅ Maintains HTML structure integrity

### Performance Requirements
- ✅ Processes 10KB HTML in < 500ms
- ✅ Handles 1MB HTML without memory issues
- ✅ Concurrent request handling (50+ requests/sec)

### Quality Requirements
- ✅ 95%+ output equivalence with JS version
- ✅ 80%+ test coverage
- ✅ No critical bugs in production
- ✅ Proper error handling and logging

---

## Maintenance & Future Enhancements

### Potential Optimizations
1. **Caching**: Cache parsed documents for repeat requests
2. **Parallelization**: Process multiple sections in parallel
3. **Lazy Loading**: Stream output instead of building entire doc in memory
4. **C Extensions**: Use Cython for hot paths

### Feature Additions
1. **More Languages**: Extend segmentation support
2. **Custom Rules**: User-definable removable sections
3. **Analytics**: Track processing metrics
4. **Webhooks**: Async processing for large documents

---

## Appendix

### Key File Mapping

| JavaScript File | Python File | Priority |
|----------------|-------------|----------|
| `server.js` | `app.py` | HIGH |
| `lib/d/segments_main.js` | `core/pipeline.py` | HIGH |
| `lib/lineardoc/Parser.js` | `lineardoc/parser.py` | HIGH |
| `lib/lineardoc/Builder.js` | `lineardoc/builder.py` | HIGH |
| `lib/lineardoc/Doc.js` | `lineardoc/doc.py` | HIGH |
| `lib/lineardoc/TextBlock.js` | `lineardoc/text_block.py` | HIGH |
| `lib/lineardoc/TextChunk.js` | `lineardoc/text_chunk.py` | HIGH |
| `lib/lineardoc/Contextualizer.js` | `lineardoc/contextualizer.py` | HIGH |
| `lib/lineardoc/MwContextualizer.js` | `lineardoc/mw_contextualizer.py` | HIGH |
| `lib/lineardoc/Utils.js` | `lineardoc/utils.py` | HIGH |
| `lib/lineardoc/Normalizer.js` | `lineardoc/normalizer.py` | MEDIUM |
| `lib/segmentation/CXSegmenter.js` | `segmentation/cx_segmenter.py` | HIGH |

### Estimated Effort

| Component | Complexity | Estimated Hours |
|-----------|-----------|----------------|
| Project Setup | Low | 4 |
| Data Classes | Low | 8 |
| Utils & Config | Low | 4 |
| Parser | High | 16 |
| Contextualizer | Medium | 8 |
| MwContextualizer | Medium | 8 |
| Builder | Medium | 12 |
| Doc | High | 16 |
| TextBlock | Medium | 8 |
| Segmenter | Low | 4 |
| API Layer | Low | 8 |
| Testing | High | 24 |
| Documentation | Medium | 8 |
| **TOTAL** | | **128 hours** |

### References
- Original repo: https://phabricator.wikimedia.org/diffusion/GCXS/cxserver.git
- MediaWiki CX docs: https://mediawiki.org/wiki/CX
- pysbd: https://github.com/nipunsadvilkar/pySBD
- lxml: https://lxml.de/

---

## Conclusion

This plan provides a comprehensive roadmap for converting the CXServer JavaScript pipeline to Python. The conversion is estimated at **128 hours** of development work, broken into 6 sprints of approximately 1 week each.

**Key Success Factors**:
1. Thorough understanding of the original JavaScript code
2. Careful selection of Python libraries
3. Comprehensive testing at each phase
4. Regression testing against original outputs
5. Incremental deployment with validation

The modular structure of the original code makes it amenable to systematic conversion, with clear boundaries between components that can be tested independently before integration.
