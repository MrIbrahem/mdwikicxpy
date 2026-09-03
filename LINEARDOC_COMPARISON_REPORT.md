# Lineardoc Module Comparison Report: Python vs JavaScript

**Date:** 2026-02-05
**Python Path:** `/cxsever/www/python/lib/lineardoc/__init__.py`
**JavaScript Source:** https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lib/lineardoc/index.js

---

## Executive Summary

This report compares the Python implementation of the lineardoc module with the original JavaScript implementation from the mediawiki-services-cxserver repository. The analysis identified key discrepancies in module exports that need to be addressed to ensure consistency between the two implementations.

---

## File Structure Comparison

### JavaScript Files (lib/lineardoc/)
```
Builder.js
Contextualizer.js
Doc.js
MwContextualizer.js
Normalizer.js
Parser.js
TextBlock.js
TextChunk.js
Utils.js
index.js         ← Main export file
```

### Python Files (cxsever/www/python/lib/lineardoc/)
```
__init__.py      ← Main export file
builder.py
contextualizer.py
doc.py
mw_contextualizer.py
normalizer.py
parser.py
text_block.py
text_chunk.py
util.py          ← Additional file not in JS
utils.py
README.md        ← Additional file not in JS
```

### Analysis
- ✅ **Core files match**: All main classes have corresponding files in both implementations
- ⚠️ **Python has extra files**:
  - `util.py` (contains `get_prop` function)
  - `README.md` (documentation)
- ⚠️ **JavaScript has singular Utils.js**, Python has both `util.py` and `utils.py`

---

## Module Exports Comparison

### JavaScript (index.js)
```javascript
import Doc from './Doc.js';
import TextBlock from './TextBlock.js';
import TextChunk from './TextChunk.js';
import Builder from './Builder.js';
import Parser from './Parser.js';
import Contextualizer from './Contextualizer.js';
import MwContextualizer from './MwContextualizer.js';
import Normalizer from './Normalizer.js';

export { Doc, TextBlock, TextChunk, Builder, Parser, Contextualizer, MwContextualizer, Normalizer };
```

**Exports (8 items):**
1. Doc
2. TextBlock
3. TextChunk
4. Builder
5. Parser
6. Contextualizer
7. MwContextualizer
8. Normalizer

**NOT exported:**
- Utils module functions (they remain internal)
- getProp function (it's imported in Utils.js from '../util.js' but not re-exported)

### Python (__init__.py)
```python
from .text_chunk import TextChunk
from .text_block import TextBlock
from .doc import Doc
from .utils import *
from .util import get_prop
from .normalizer import Normalizer
from .contextualizer import Contextualizer
from .mw_contextualizer import MwContextualizer
from .builder import Builder
from .parser import Parser

__all__ = [
    'TextChunk',
    'TextBlock',
    'Doc',
    'Normalizer',
    'Contextualizer',
    'MwContextualizer',
    'Builder',
    'Parser',
    'get_prop'
]
```

**Exports (9+ items):**
1. TextChunk
2. TextBlock
3. Doc
4. Normalizer
5. Contextualizer
6. MwContextualizer
7. Builder
8. Parser
9. get_prop
10. **PLUS all functions from utils.py** via `from .utils import *`

---

## Issues Identified

### 🔴 **CRITICAL ISSUE 1: Over-exporting from utils module**

**Problem:**
Python exports `from .utils import *` which exposes ALL utility functions from utils.py. JavaScript does NOT export anything from Utils.js.

**JavaScript Utils.js Exports:**
```javascript
export {
    addCommonTag,
    cloneOpenTag,
    dumpTags,
    esc,
    findAll,
    getChunkBoundaryGroups,
    getCloseTagHtml,
    getOpenTagHtml,
    isIgnorableBlock,
    isExternalLink,
    isGallery,
    isInlineEmptyTag,
    isMath,
    isReference,
    isSegment,
    isTransclusion,
    isTransclusionFragment,
    isNonTranslatable,
    setLinkIdsInPlace
}
```

**Impact:**
These functions are exported in Python but NOT in JavaScript. This creates API inconsistency where Python users might depend on functions that don't exist in the JavaScript public API.

**Recommendation:**
❌ **REMOVE** `from .utils import *` from `__init__.py`

The utils functions should remain internal to the module, just like in JavaScript.

---

### 🟡 **ISSUE 2: get_prop function export discrepancy**

**Problem:**
Python explicitly exports `get_prop` in `__all__`, but JavaScript does NOT export `getProp` from index.js.

**JavaScript behavior:**
- `getProp` is defined in `lib/util.js` (not in lineardoc/)
- `Utils.js` imports it: `import { getProp } from './../util.js';`
- `index.js` does NOT re-export it

**Python behavior:**
- `get_prop` is defined in `util.py` (inside lineardoc/)
- `__init__.py` imports and exports it: `from .util import get_prop`

**Impact:**
Moderate - creates API inconsistency. The function is used internally in both implementations but only exposed publicly in Python.

**Recommendation:**
❌ **REMOVE** `get_prop` from `__all__` and remove the import `from .util import get_prop`

Keep it as an internal utility function, matching JavaScript behavior.

---

### 🟢 **MINOR ISSUE 3: Export order differs**

**Problem:**
The order of exports differs between implementations.

**JavaScript order:**
Doc, TextBlock, TextChunk, Builder, Parser, Contextualizer, MwContextualizer, Normalizer

**Python order:**
TextChunk, TextBlock, Doc, Normalizer, Contextualizer, MwContextualizer, Builder, Parser, get_prop

**Impact:**
Minimal - doesn't affect functionality, but consistency is better for maintenance.

**Recommendation:**
✅ **MATCH** the order to JavaScript for consistency (optional)

---

## Recommended Changes to Python __init__.py

### Current Code
```python
"""
Lineardoc module - Linear document representation for HTML.
"""

from .text_chunk import TextChunk
from .text_block import TextBlock
from .doc import Doc
from .utils import *
from .util import get_prop
from .normalizer import Normalizer
from .contextualizer import Contextualizer
from .mw_contextualizer import MwContextualizer
from .builder import Builder
from .parser import Parser

__all__ = [
    'TextChunk',
    'TextBlock',
    'Doc',
    'Normalizer',
    'Contextualizer',
    'MwContextualizer',
    'Builder',
    'Parser',
    'get_prop'
]
```

### Recommended Code (Matches JavaScript)
```python
"""
Lineardoc module - Linear document representation for HTML.
"""

from .doc import Doc
from .text_block import TextBlock
from .text_chunk import TextChunk
from .builder import Builder
from .parser import Parser
from .contextualizer import Contextualizer
from .mw_contextualizer import MwContextualizer
from .normalizer import Normalizer

__all__ = [
    'Doc',
    'TextBlock',
    'TextChunk',
    'Builder',
    'Parser',
    'Contextualizer',
    'MwContextualizer',
    'Normalizer'
]
```

### Changes Made:
1. ❌ Removed `from .utils import *` (keeps utils internal)
2. ❌ Removed `from .util import get_prop` (keeps util internal)
3. ❌ Removed `get_prop` from `__all__`
4. ✅ Reordered imports to match JavaScript order
5. ✅ Updated `__all__` to match JavaScript exports exactly

---

## Additional Findings

### Utils Module Functions (Should Remain Internal)

The following functions exist in both Python and JavaScript but should NOT be exported from the main module:

**Utility Functions (utils.py / Utils.js):**
- `esc` / `esc` - HTML escaping
- `findAll` / `find_all` - Regex matching
- `getOpenTagHtml` / `get_open_tag_html` - Tag rendering
- `getCloseTagHtml` / `get_close_tag_html` - Tag rendering
- `cloneOpenTag` / `clone_open_tag` - Tag manipulation
- `dumpTags` / `dump_tags` - Debugging
- `isReference` / `is_reference` - Tag checking
- `isMath` / `is_math` - Tag checking
- `isGallery` / `is_gallery` - Tag checking
- `isExternalLink` / `is_external_link` - Tag checking
- `isSegment` / `is_segment` - Tag checking
- `isTransclusion` / `is_transclusion` - Tag checking
- `isTransclusionFragment` / `is_transclusion_fragment` - Tag checking
- `isNonTranslatable` / `is_non_translatable` - Tag checking
- `isInlineEmptyTag` / `is_inline_empty_tag` - Tag checking
- `getChunkBoundaryGroups` / `get_chunk_boundary_groups` - Processing
- `addCommonTag` / `add_common_tag` - Tag manipulation
- `setLinkIdsInPlace` / `set_link_ids_in_place` - ID assignment
- `isIgnorableBlock` / `is_ignorable_block` - Block checking

**Helper Functions (util.py / util.js):**
- `get_prop` / `getProp` - Safe property access

These are helper functions used internally by the main classes but not part of the public API.

---

## Testing Recommendations

After making changes to `__init__.py`:

1. ✅ **Import Test**: Verify that all 8 main classes can still be imported:
   ```python
   from cxsever.www.python.lib.lineardoc import (
       Doc, TextBlock, TextChunk, Builder, Parser,
       Contextualizer, MwContextualizer, Normalizer
   )
   ```

2. ✅ **No Utils Export Test**: Verify that utils functions are NOT exported:
   ```python
   # This should FAIL:
   from cxsever.www.python.lib.lineardoc import esc  # Should raise ImportError
   from cxsever.www.python.lib.lineardoc import get_prop  # Should raise ImportError
   ```

3. ✅ **Internal Access Test**: Verify that classes can still access utils internally:
   ```python
   from cxsever.www.python.lib.lineardoc import Parser
   # Parser should still be able to use utils internally
   ```

4. ✅ **Run existing unit tests**: Ensure no tests break due to changed exports

---

## Conclusion

The Python implementation currently over-exports utility functions that are kept internal in the JavaScript implementation. To achieve parity:

1. **Remove** `from .utils import *`
2. **Remove** `from .util import get_prop` and `get_prop` from `__all__`
3. **Reorder** exports to match JavaScript (optional but recommended)

This will ensure the Python module has the same public API as JavaScript, with utility functions remaining internal implementation details.

---

## Summary Table

| Item | JavaScript | Python (Current) | Python (Recommended) | Action |
|------|-----------|------------------|---------------------|--------|
| Doc | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| TextBlock | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| TextChunk | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| Builder | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| Parser | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| Contextualizer | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| MwContextualizer | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| Normalizer | ✅ Exported | ✅ Exported | ✅ Export | Keep |
| get_prop / getProp | ❌ Internal | ✅ Exported | ❌ Internal | **REMOVE** from exports |
| utils functions | ❌ Internal | ✅ Exported | ❌ Internal | **REMOVE** wildcard import |

---

**Report prepared by:** Copilot Analysis
**Implementation Priority:** High - API consistency issue
