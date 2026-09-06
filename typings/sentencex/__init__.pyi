from typing import TypedDict, List, Optional

class Boundary(TypedDict):
    start_index: int
    end_index: int
    text: str
    boundary_symbol: Optional[str]
    is_paragraph_break: bool

def segment(language: str, text: str) -> List[str]: ...

def get_sentence_boundaries(language: str, text: str) -> List[Boundary]: ...
