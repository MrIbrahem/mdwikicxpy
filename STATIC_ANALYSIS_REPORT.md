# Static Analysis Report - mdwikicxpy

**Analysis Date:** 2026-02-14
**Codebase:** mdwikicxpy - MediaWiki Content Translation Python Port

## Executive Summary

This report documents findings from a comprehensive static analysis of the mdwikicxpy codebase, covering logical errors, security vulnerabilities, performance bottlenecks, architectural anti-patterns, and documentation gaps.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Security | 1 | 2 | 1 | 0 |
| Logic | 0 | 2 | 3 | 2 |
| Performance | 0 | 1 | 3 | 1 |
| Architecture | 0 | 2 | 4 | 2 |
| Documentation | 0 | 1 | 5 | 3 |

---

## 1. Security Issues

### 1.1 [CRITICAL] Missing Input Size Validation (app.py:28-35)

**Location:** `python/app.py:28-35`

**Issue:** The Flask endpoint accepts HTML input without size limits, potentially allowing DoS attacks via large payloads.

**Risk:** Memory exhaustion, service unavailability.

**Recommendation:** Add maximum content length validation:

```python
MAX_HTML_SIZE = 10 * 1024 * 1024  # 10MB

if len(source_html) > MAX_HTML_SIZE:
    return jsonify({"result": "Content exceeds maximum allowed size"}), 413
```

### 1.2 [HIGH] Verbose Error Exposure (app.py:38-43)

**Location:** `python/app.py:38-43`

**Issue:** Exception traceback is printed and raw error messages are returned to clients, exposing internal implementation details.

**Risk:** Information disclosure, assists attackers in reconnaissance.

**Recommendation:** Log errors internally, return generic error messages:

```python
except Exception as error:
    app.logger.error(f"Error processing HTML: {error}", exc_info=True)
    return jsonify({"result": "Internal processing error"}), 500
```

### 1.3 [HIGH] Missing Content-Type Validation (app.py:29)

**Location:** `python/app.py:29`

**Issue:** `request.get_json()` is called without validation that the request is JSON.

**Risk:** Unexpected input types may cause unhandled exceptions.

**Recommendation:** Validate content type:

```python
if not request.is_json:
    return jsonify({"result": "Content-Type must be application/json"}), 415
```

### 1.4 [MEDIUM] No Rate Limiting

**Location:** `python/app.py`

**Issue:** The API lacks rate limiting, allowing abuse.

**Recommendation:** Implement rate limiting via Flask-Limiter or similar.

---

## 2. Logical Errors & Edge Cases

### 2.1 [HIGH] Potential IndexError in get_tag_offsets (text_block.py:48-62)

**Location:** `python/lib/lineardoc/text_block.py:58-62`

**Issue:** The loop variable `i` may not be properly set if `text_chunks` is empty.

```python
def get_text_chunk_at(self, char_offset):
    i = 0
    for i in range(len(self.text_chunks) - 1):  # If empty, loop doesn't execute
        if self.offsets[i + 1]["start"] > char_offset:
            break
    return self.text_chunks[i]  # IndexError if text_chunks is empty
```

**Recommendation:** Add guard clause:

```python
if not self.text_chunks:
    raise ValueError("No text chunks available")
```

### 2.2 [HIGH] Non-Atomic Tag Stack Operations (parser.py:183-186)

**Location:** `python/lib/lineardoc/parser.py:183-186`

**Issue:** `self.all_tags.pop()` is called before checking if the stack is empty, but the check only verifies truthiness.

```python
if not self.all_tags:
    return
tag = self.all_tags.pop()  # Safe after check, but...
```

The subsequent logic may leave the stack in inconsistent state on errors.

### 2.3 [MEDIUM] Exception Swallowing (parser.py:93-100)

**Location:** `python/lib/lineardoc/parser.py:93-100`

**Issue:** General exception catching loses error context.

```python
except Exception:
    try:
        tree = etree.fromstring(f"<div>{html}</div>".encode(), parser)
        ...
    except Exception as e:
        raise Exception(f"Failed to parse HTML: {e}")  # Original error lost
```

### 2.4 [MEDIUM] Silent Failure in JSON Parsing (mw_contextualizer.py:147-150)

**Location:** `python/lib/lineardoc/mw_contextualizer.py:147-150`

**Issue:** JSON decode errors are silently caught, returning False. This may mask data corruption issues.

```python
try:
    mw_data = json.loads(data_mw)
except (json.JSONDecodeError, ValueError):
    return False  # Should log warning
```

### 2.5 [MEDIUM] Off-by-One in get_chunk_boundary_groups (utils.py:295)

**Location:** `python/lib/lineardoc/utils.py:295`

**Issue:** The condition `boundary > offset + chunk_length - 1` may skip valid boundaries at chunk boundaries.

### 2.6 [LOW] Unused Variable in segment (doc.py:104)

**Location:** `python/lib/lineardoc/doc.py:104`

**Issue:** `section_number` is declared but the increment logic at line 145 may not execute as expected.

### 2.7 [LOW] Duplicate Import (text_block.py:174)

**Location:** `python/lib/lineardoc/text_block.py:174`

**Issue:** `import re` appears at module level (line 7) and again inside a function (line 174).

---

## 3. Performance Issues

### 3.1 [HIGH] Repeated Regex Compilation (cx_segmenter.py:36-53)

**Location:** `python/lib/segmentation/cx_segmenter.py:36-53`

**Issue:** Each call creates a new `pysbd.Segmenter` instance. For high-volume processing, this is expensive.

**Recommendation:** Cache segmenters by language:

```python
_segmenter_cache: Dict[str, pysbd.Segmenter] = {}

def get_segmenter(self, language: str) -> BoundaryDetector:
    if language not in self._segmenter_cache:
        self._segmenter_cache[language] = pysbd.Segmenter(language=language, clean=False)
    # ... return cached segmenter
```

### 3.2 [MEDIUM] String Concatenation in HTML Generation (doc.py:197-223)

**Location:** `python/lib/lineardoc/doc.py:197-223`

**Issue:** While the code uses list joining (good), the repeated calls to `utils.get_open_tag_html()` create intermediate strings.

**Optimization:** Consider pre-computing attribute strings for tags that don't change.

### 3.3 [MEDIUM] O(n) Search in Boundary Detection (cx_segmenter.py:47)

**Location:** `python/lib/segmentation/cx_segmenter.py:47`

**Issue:** `text.find(sentence, current_pos)` is O(n) per sentence, making overall complexity O(n*m).

### 3.4 [MEDIUM] Repeated Dictionary Access (doc.py:125-138)

**Location:** `python/lib/lineardoc/doc.py:125-138`

**Issue:** Multiple `.get("attributes", {})` calls on the same tag object. Cache the result.

```python
# Current
if tag.get("attributes", {}).get("id"):
    ...
    tag["attributes"]["id"] = ...

# Better
attrs = tag.get("attributes", {})
if attrs.get("id"):
    attrs["id"] = ...
```

### 3.5 [LOW] List Copy in add_common_tag (utils.py:323)

**Location:** `python/lib/lineardoc/utils.py:323`

**Issue:** Creates unnecessary copies of tag lists when the common tag length is 0.

---

## 4. Architectural Anti-Patterns

### 4.1 [HIGH] Code Duplication in Segmenters (cx_segmenter.py)

**Location:** `python/lib/segmentation/cx_segmenter.py`

**Issue:** `CXSegmenter` and `CXSegmenterNew` share identical structure, differing only in the segmentation library used.

**Recommendation:** Extract common logic to base class:

```python
class BaseSegmenter(ABC):
    @abstractmethod
    def _get_sentences(self, text: str, language: str) -> List[str]:
        ...

    def segment(self, parsed_doc: Doc, language: str) -> Doc:
        return parsed_doc.segment(self.get_segmenter(language))

    def get_segmenter(self, language: str) -> BoundaryDetector:
        def segmenter(text: str) -> BoundaryList:
            sentences = self._get_sentences(text, language)
            return self._find_boundaries(text, sentences)
        return segmenter
```

### 4.2 [HIGH] Mutable Module State (processor.py:11-16)

**Location:** `python/lib/processor.py:11-16`

**Issue:** Configuration is loaded at module import time, making testing difficult and preventing runtime configuration.

```python
# Loaded at import - cannot be mocked easily
with open(config_path, "r", encoding="utf-8") as f:
    pageloader_config = yaml.safe_load(f)
```

**Recommendation:** Use dependency injection or lazy loading:

```python
_config: Optional[Dict] = None

def get_config() -> Dict:
    global _config
    if _config is None:
        with open(config_path, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    return _config
```

### 4.3 [MEDIUM] God Class - Doc (doc.py)

**Location:** `python/lib/lineardoc/doc.py`

**Issue:** The `Doc` class handles too many responsibilities:
- Document item management
- HTML serialization
- Section wrapping
- Segmentation
- XML debugging output

**Recommendation:** Consider separating concerns into:
- `Doc` - core document model
- `DocSerializer` - HTML/XML output
- `SectionWrapper` - section handling
- `DocSegmenter` - segmentation coordination

### 4.4 [MEDIUM] Primitive Obsession (types.py)

**Location:** `python/lib/lineardoc/types.py`

**Issue:** Using `Dict[str, Any]` for `TagDict` instead of proper dataclasses or TypedDict loses type safety.

**Current:**
```python
class TagDict(Dict[str, Any]):
    name: str
    attributes: AttributeDict
```

**Better:**
```python
from typing import TypedDict

class TagDict(TypedDict, total=False):
    name: str
    attributes: Dict[str, str]
    isSelfClosing: bool
```

### 4.5 [MEDIUM] Missing Abstraction for ID Generation (doc.py:107-118)

**Location:** `python/lib/lineardoc/doc.py:107-118`

**Issue:** ID generation logic is embedded in the `segment` method, making it difficult to customize or test.

### 4.6 [MEDIUM] Tight Coupling to lxml (parser.py, normalizer.py)

**Location:** `python/lib/lineardoc/parser.py`, `python/lib/lineardoc/normalizer.py`

**Issue:** Direct dependency on lxml makes it difficult to swap parsers or mock for testing.

### 4.7 [LOW] Inconsistent Naming Convention

**Location:** Multiple files

**Issue:** Class `TextBlock` vs file `text_block.py` follows Python convention, but `TextChunk` class uses camelCase method `has_inline_content()` while `TextBlock` uses snake_case `get_plain_text()`.

### 4.8 [LOW] Commented-Out Code (multiple files)

**Location:** Various files contain `# reviewed from js?` markers and commented-out code blocks.

---

## 5. Documentation Gaps

### 5.1 [HIGH] Missing Module-Level Documentation (parser.py, builder.py, utils.py)

**Location:** `python/lib/lineardoc/parser.py`, `builder.py`, `utils.py`

**Issue:** Module docstrings exist but lack comprehensive descriptions of:
- Module purpose and role in pipeline
- Key algorithms
- Dependencies and their rationale

### 5.2 [MEDIUM] Missing Exception Documentation

**Location:** All modules

**Issue:** Most docstrings lack `Raises:` sections documenting exceptions.

### 5.3 [MEDIUM] Incomplete Type Annotations

**Location:** `doc.py`, `text_block.py`, `parser.py`, `builder.py`, `utils.py`

**Issue:** Many functions lack return type annotations:

```python
# Current
def get_html(self):
    ...

# Should be
def get_html(self) -> str:
    ...
```

### 5.4 [MEDIUM] Missing Parameter Constraints Documentation

**Location:** Various

**Issue:** Docstrings don't document valid ranges or constraints for parameters.

### 5.5 [MEDIUM] No Architecture Documentation

**Location:** Project root

**Issue:** Missing high-level architecture documentation explaining:
- Data flow between modules
- Design patterns used
- Extension points

### 5.6 [LOW] Inconsistent Docstring Style

**Location:** Multiple files

**Issue:** Mix of Google-style and NumPy-style docstrings. Should standardize on one.

---

## 6. Type Safety Issues

### 6.1 Missing Type Annotations Summary

| File | Missing Annotations | Incomplete Types |
|------|---------------------|------------------|
| doc.py | 12 functions | 5 |
| text_block.py | 14 functions | 4 |
| parser.py | 8 functions | 3 |
| builder.py | 11 functions | 4 |
| utils.py | 15 functions | 6 |
| contextualizer.py | 6 functions | 2 |
| mw_contextualizer.py | 4 functions | 2 |
| normalizer.py | 6 functions | 2 |
| cx_segmenter.py | 4 functions | 2 |
| processor.py | 4 functions | 1 |
| app.py | 2 functions | 1 |

### 6.2 TypedDict Not Properly Utilized

The `types.py` file defines `TagDict` as `Dict[str, Any]` subclass, which provides no static type checking. Should use `TypedDict` or `dataclass`.

---

## 7. Recommendations Summary

### Immediate Actions (Security & Critical)

1. Add input size validation in Flask app
2. Remove verbose error exposure
3. Add content-type validation
4. Implement rate limiting

### Short-Term (High Priority)

1. Fix potential IndexError in `get_text_chunk_at`
2. Extract common segmenter logic to base class
3. Make configuration lazily loaded
4. Add comprehensive type annotations

### Medium-Term

1. Consider refactoring `Doc` class
2. Add proper TypedDict definitions
3. Create architecture documentation
4. Add exception documentation to all functions

### Long-Term

1. Consider parser abstraction layer
2. Implement performance monitoring
3. Add comprehensive logging
4. Create migration guide for TypedDict usage

---

## 8. Files Requiring Updates

Based on this analysis, the following files should be updated with improved type annotations, documentation, and bug fixes:

1. `python/app.py` - Security fixes, type annotations
2. `python/lib/processor.py` - Lazy config loading, type annotations
3. `python/lib/lineardoc/doc.py` - Type annotations, edge case fixes
4. `python/lib/lineardoc/text_block.py` - Type annotations, IndexError fix
5. `python/lib/lineardoc/parser.py` - Type annotations, error handling
6. `python/lib/lineardoc/builder.py` - Type annotations
7. `python/lib/lineardoc/utils.py` - Type annotations
8. `python/lib/lineardoc/contextualizer.py` - Type annotations
9. `python/lib/lineardoc/mw_contextualizer.py` - Type annotations, logging
10. `python/lib/lineardoc/normalizer.py` - Type annotations
11. `python/lib/segmentation/cx_segmenter.py` - Base class extraction, caching
12. `python/lib/lineardoc/types.py` - Proper TypedDict usage

---

*Report generated by static analysis tool*
