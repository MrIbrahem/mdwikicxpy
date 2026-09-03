# 🚀 **REAL-WORLD AI IMPLEMENTATION PLAN**

## Converting JavaScript MediaWiki HTML Processor to Python

Based on actual code analysis of `WikiAr/mdwikicxpy`

---

## 📋 **EXECUTIVE SUMMARY**

### What POST /textp Does:

```
Input: MediaWiki HTML (Parsoid format)
     ↓
1. Parse HTML via SAX parser → Linear Document structure
2. Apply MediaWiki contextualization (remove unwanted sections)
3. Wrap sections with metadata
4. Segment text for translation (sentence boundaries)
5. Add tracking IDs (segments, links)
     ↓
Output: Processed HTML ready for Content Translation
```

### Core Pipeline (from `u.tet()`):

```javascript
Parser + mw_contextualizer → Doc → wrapSections() → CXSegmenter → HTML
```

---

## 🏗️ **ARCHITECTURE BREAKDOWN**

### **Phase 1: Understanding the Core Classes**

#### **1. LinearDoc System** (`lib/lineardoc/`)

**A. Parser.js** - SAX-based HTML stream processor

-   Uses `sax` library (Python equivalent: `xml.sax` or `lxml.etree.iterparse`)
-   Distinguishes block vs inline tags
-   Handles MediaWiki-specific structures (references, math, transclusions)
-   Key methods: `on_open_tag()`, `on_close_tag()`, `ontext()`

**B. Doc.js** - Linear document representation

-   Stores HTML as linear array of items:
    -   `{type: 'open', item: tag}`
    -   `{type: 'close', item: tag}`
    -   `{type: 'textblock', item: text_block}`
    -   `{type: 'blockspace', item: whitespace}`
-   Key methods: `segment()`, `wrapSections()`, `get_html()`

**C. TextBlock.js** - Annotated inline text container

-   Manages text chunks with tag annotations
-   Handles sentence segmentation
-   Key method: `segment(getBoundaries, getNextId)`
    -   Wraps sentences in `<span class="cx-segment" data-segmentid="X">`
    -   Adds link IDs: `<a data-linkid="Y">`

**D. MwContextualizer.js** - MediaWiki-specific logic

-   Removes sections based on config (MWPageLoader.yaml)
-   Tracks context (removable, media, transclusion)
-   Key method: `isRemovable(tag)`

**E. Builder.js** - Constructs Doc during parsing

-   Manages inline annotation tag stack
-   Creates nested TextBlocks

#### **2. Segmentation System** (`lib/segmentation/`)

**CXSegmenter.js** - Sentence boundary detection

-   Uses `sentencex` library (Python equivalent: `pySBD` or custom regex)
-   Creates segmenter function per language
-   Returns boundary offsets in plaintext

---

## 🎯 **PYTHON CONVERSION STRATEGY**

### **Technology Stack Recommendations:**

| Component          | JavaScript         | Python Equivalent                         |
| ------------------ | ------------------ | ----------------------------------------- |
| HTML Parser        | `sax` (SAX parser) | `lxml.etree.iterparse()` or `html.parser` |
| Sentence Segmenter | `sentencex`        | `pySBD` or `sentence-splitter`            |
| YAML Config        | `js-yaml`          | `PyYAML`                                  |
| Web Framework      | `express.js`       | `FastAPI` or `Flask`                      |
| Data Classes       | ES6 classes        | Python `dataclasses` or classes           |

---

## 📝 **DETAILED IMPLEMENTATION PLAN**

### **Step 1: Core Data Structures** (Week 1)

Create Python equivalents:

```python
# lib/lineardoc/text_chunk.py
@dataclass
class text_chunk:
    text: str
    tags: List[Tag]
    inline_content: Optional[Union[Doc, Tag]] = None
```

```python
# lib/lineardoc/text_block.py
class text_block:
    def __init__(self, text_chunks: List[text_chunk], can_segment: bool):
        self.text_chunks = text_chunks
        self.can_segment = can_segment
        self.offsets = self._calculate_offsets()

    def segment(self, get_boundaries: Callable, get_next_id: Callable) -> 'text_block':
        """
        Critical method - segments text into translation units
        Lines 347-409 in TextBlock.js
        """
        # TODO: Implement sentence boundary splitting
        # TODO: Wrap in <span class="cx-segment" data-segmentid="X">
        # TODO: Add link IDs
```

```python
# lib/lineardoc/doc.py
class Doc:
    def __init__(self, wrapper_tag=None):
        self.items: List[DocItem] = []
        self.wrapper_tag = wrapper_tag

    def segment(self, get_boundaries: Callable) -> 'Doc':
        """Lines 113-182 in Doc.js"""
        # TODO: Segment each text_block item

    def wrap_sections(self) -> 'Doc':
        """Lines 319-444 in Doc.js - CRITICAL"""
        # TODO: Wrap headings and content in <section> tags
        # TODO: Add rel="cx:Section", id="cxSourceSectionX"
```

---

### **Step 2: SAX Parser Implementation** (Week 2)

```python
# lib/lineardoc/parser.py
from lxml import etree

class Parser:
    BLOCK_TAGS = [
        'html', 'head', 'body', 'div', 'p', 'table',
        'h1', 'h2', 'h3', 'section', 'ul', 'ol', 'li',
        # ... (lines 11-36 in Parser.js)
    ]

    def __init__(self, contextualizer: mw_contextualizer, options: dict):
        self.contextualizer = contextualizer
        self.options = options
        self.builder = None
        self.all_tags = []

    def parse(self, html: str) -> Doc:
        """
        Stream-parse HTML using SAX-like approach
        See Parser.js lines 63-141
        """
        context = etree.iterparse(
            io.BytesIO(html.encode()),
            events=('start', 'end'),
            html=True
        )

        for event, elem in context:
            if event == 'start':
                self._on_open_tag(elem)
            elif event == 'end':
                self._on_close_tag(elem)

        return self.builder.doc

    def _on_open_tag(self, elem):
        """Lines 63-99 in Parser.js"""
        tag = self._elem_to_tag(elem)

        # Check removable
        if self.contextualizer.is_removable(tag):
            self.contextualizer.on_open_tag(tag)
            return

        # Handle references, math
        if utils.is_reference(tag) or utils.is_math(tag):
            self.builder = self.builder.create_child_builder(tag)
        elif self._is_inline_annotation_tag(tag.name):
            self.builder.push_inline_annotation_tag(tag)
        else:
            self.builder.push_block_tag(tag)
```

---

### **Step 3: MediaWiki Contextualizer** (Week 2)

```python
# lib/lineardoc/mw_contextualizer.py
import re
from typing import List, Dict

class mw_contextualizer:
    def __init__(self, config: dict):
        self.removable_sections = config['removableSections']
        self.context_stack = []

    def is_removable(self, tag: Tag) -> bool:
        """
        Check if tag should be removed
        Based on MWPageLoader.yaml config
        """
        # Check classes
        if 'class' in tag.attributes:
            classes = tag.attributes['class'].split()
            for cls in self.removable_sections['classes']:
                if cls in classes:
                    return True

        # Check RDFa typeof
        if 'typeof' in tag.attributes:
            typeof = tag.attributes['typeof']
            if typeof in self.removable_sections['rdfa']:
                return True

        # Check template names (data-mw attribute)
        if 'data-mw' in tag.attributes:
            # TODO: Parse JSON and check template names
            # See MWPageLoader.yaml lines 14-40
            pass

        return False
```

---

### **Step 4: Segmentation** (Week 3)

```python
# lib/segmentation/cx_segmenter.py
import pysbd

class CXSegmenter:
    def segment(self, parsed_doc: Doc, language: str) -> Doc:
        """
        Segment document into translation units
        See CXSegmenter.js lines 13-16
        """
        return parsed_doc.segment(self.get_segmenter(language))

    def get_segmenter(self, language: str) -> Callable:
        """Lines 24-33 in CXSegmenter.js"""
        def segmenter(text: str) -> List[int]:
            seg = pysbd.Segmenter(language=language, clean=False)
            sentences = seg.segment(text)

            boundaries = []
            for sentence in sentences:
                if sentence.strip():
                    boundaries.append(text.index(sentence))

            return boundaries

        return segmenter
```

---

### **Step 5: Main Processing Function** (Week 3)

```python
# lib/processor.py
import yaml
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent.parent / 'config' / 'MWPageLoader.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def process_html(source_html: str) -> str:
    """
    Main processing pipeline - equivalent to u.tet()
    See u.js lines 20-37
    """
    # 1. Create parser with MediaWiki contextualizer
    contextualizer = mw_contextualizer(
        {'removableSections': CONFIG['removableSections']}
    )
    parser = Parser(contextualizer, {'wrapSections': True})

    # 2. Parse HTML → Doc
    parser.init()
    parsed_doc = parser.parse(source_html)

    # 3. Wrap sections
    parsed_doc = parsed_doc.wrap_sections()

    # 4. Segment for translation
    segmenter = CXSegmenter()
    segmented_doc = segmenter.segment(parsed_doc, "en")

    # 5. Convert back to HTML
    result = segmented_doc.get_html()

    return result
```

---

### **Step 6: Web Server** (Week 4)

```python
# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lib.processor import process_html

app = FastAPI()

class HtmlRequest(BaseModel):
    html: str

@app.post("/textp")
async def process_text(request: HtmlRequest):
    """
    Equivalent to server.js lines 13-35
    """
    if not request.html or not request.html.strip():
        raise HTTPException(
            status_code=500,
            detail="Content for translate is not given or is empty"
        )

    try:
        processed_text = process_html(request.html)
        return {"result": processed_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## ⚠️ **CRITICAL IMPLEMENTATION DETAILS**

### **1. ID Assignment** (Doc.js `wrapSections()` lines 319-444)

```python
def wrap_sections(self):
    """
    CRITICAL: Assigns sequential IDs to ALL elements
    Wraps sections with metadata
    """
    id_counter = 0
    section_counter = 0

    for item in self.items:
        if item.type == 'open':
            # Assign id attribute
            if 'id' not in item.item.attributes:
                item.item.attributes['id'] = str(id_counter)
                id_counter += 1

            # Detect heading tags (h1-h6)
            if item.item.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Create section wrapper
                section_tag = {
                    'name': 'section',
                    'attributes': {
                        'rel': 'cx:Section',
                        'id': f'cxSourceSection{section_counter}',
                        'data-mw-section-number': str(section_counter)
                    }
                }
                section_counter += 1
```

### **2. Link ID Assignment** (utils.js `set_link_ids_in_place()`)

```python
def set_link_ids_in_place(text_chunks: List[text_chunk], get_next_id: Callable):
    """
    Add data-linkid to ALL links
    Add class="cx-link"
    """
    for chunk in text_chunks:
        for tag in chunk.tags:
            if tag.name == 'a' and 'href' in tag.attributes:
                # Add cx-link class
                classes = tag.attributes.get('class', '').split()
                if 'cx-link' not in classes:
                    classes.append('cx-link')
                    tag.attributes['class'] = ' '.join(classes)

                # Add data-linkid
                tag.attributes['data-linkid'] = str(get_next_id('link'))
```

### **3. HTML Attribute Encoding** (utils.js `esc_attr()`)

```python
def escape_attr(value: str) -> str:
    """
    Encode HTML attributes properly
    " → &#34;
    ' → &#39;
    """
    return (value
            .replace('&', '&amp;')
            .replace('"', '&#34;')
            .replace("'", '&#39;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))
```

---

## 🧪 **TESTING STRATEGY**

### **Test Cases:**

1. **Unit Tests** - Each class (Doc, text_block, Parser)
2. **Integration Tests** - Full pipeline with real MediaWiki HTML
3. **Comparison Tests** - Run JS and Python on same input, diff outputs

```python
# tests/test_processor.py
def test_full_pipeline():
    """Compare JS output vs Python output"""
    with open('fixtures/input.html') as f:
        input_html = f.read()

    with open('fixtures/expected_output.html') as f:
        expected = f.read()

    result = process_html(input_html)

    # Normalize whitespace
    assert normalize_html(result) == normalize_html(expected)
```

---

## 📦 **DEPENDENCIES**

```requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
lxml==4.9.3
pysbd==0.3.4
PyYAML==6.0.1
pydantic==2.5.0
```

---

## 🎯 **IMPLEMENTATION PRIORITIES**

### **MVP (Minimum Viable Product):**

1. ✅ Doc, text_block, text_chunk classes
2. ✅ Basic Parser (without all edge cases)
3. ✅ Simple segmentation (regex-based)
4. ✅ Basic wrapSections()
5. ✅ FastAPI endpoint

### **Full Feature Parity:**

1. Complete mw_contextualizer with all rules
2. Handle references, math, transclusions
3. Advanced sentence boundary detection
4. Full HTML escaping/encoding
5. Error handling matching JS behavior

---

## 🚨 **RISKS & MITIGATION**

| Risk                            | Mitigation                          |
| ------------------------------- | ----------------------------------- |
| SAX parsing differences         | Use comprehensive test fixtures     |
| Sentence segmentation accuracy  | Compare outputs with JS version     |
| MediaWiki edge cases            | Gradual rollout, A/B testing        |
| Performance (Python vs Node.js) | Profile and optimize critical paths |

---

## ✅ **SUCCESS CRITERIA**

1. **Functional**: 95%+ matching output with JS version
2. **Performance**: < 2x slower than Node.js version
3. **Maintainability**: Clean, documented Python code
4. **Test Coverage**: > 80% code coverage
