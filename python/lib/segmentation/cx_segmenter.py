"""
CXSegmenter - Sentence segmentation for Content Translation.

This port delegates segmentation to the upstream ``sentencex`` library -- the
very same JavaScript package the JS port uses, installed under
``js/node_modules``. A small long-lived Node.js helper
(``sentencex_bridge.mjs`` in this directory) exposes ``sentencex`` to Python
over a stdin/stdout JSON protocol.

Using ``sentencex`` (instead of a separate Python segmenter such as ``pysbd``)
guarantees that the Python output matches the JS/sentencex-generated test
fixtures byte-for-byte, including multilingual segmentation that ``pysbd`` does
not support (e.g. Amharic, Hindi, Armenian, Punjabi, Japanese, Chinese).
"""

from __future__ import annotations

import atexit
import json
import subprocess
from pathlib import Path

# Location of the Node.js bridge script (same directory as this file).
_BRIDGE_SCRIPT = Path(__file__).resolve().parent / "sentencex_bridge.mjs"


class _SentencexBridge:
    """A long-lived Node.js process that segments text using ``sentencex``."""

    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["node", str(_BRIDGE_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def get_boundaries(self, language: str, text: str) -> list[int]:
        """Return sentence start offsets for ``text`` in ``language``."""
        request = json.dumps({"lang": language, "text": text}) + "\n"
        self.proc.stdin.write(request)
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            # The bridge exited unexpectedly; surface stderr if we can.
            stderr = ""
            try:
                stderr = self.proc.stderr.read() if self.proc.stderr else ""
            except Exception:
                pass
            raise RuntimeError(
                f"sentencex bridge process ended early. stderr={stderr!r}"
            )
        response = json.loads(line)
        if isinstance(response, dict) and "error" in response:
            raise RuntimeError(f"sentencex bridge error: {response['error']}")
        return response

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


_bridge: _SentencexBridge | None = None


def _get_bridge() -> _SentencexBridge:
    global _bridge
    if _bridge is None:
        _bridge = _SentencexBridge()
        atexit.register(_bridge.close)
    return _bridge


class CXSegmenter:
    """Segmenter for CX documents."""

    def segment(self, parsed_doc, language: str):
        """
        Segment the given parsed linear document object.

        Args:
            parsed_doc: Parsed Doc object
            language: Language code

        Returns:
            Segmented Doc object
        """
        return parsed_doc.segment(self.get_segmenter(language))

    def get_segmenter(self, language: str):
        """
        Get the segmenter for the given language.

        Returns a function that maps plaintext to an array of sentence start
        offsets, mirroring the behaviour of the JS ``CXSegmenter.getSegmenter``.

        Args:
            language: Language code

        Returns:
            Function taking plaintext, returning offset array
        """
        bridge = _get_bridge()

        def segmenter(text):
            """Segment text into sentences, returning start offsets."""
            return bridge.get_boundaries(language, text)

        return segmenter

    def is_language_supported(self, language: str) -> bool:
        return True


__all__ = [
    "CXSegmenter",
]
