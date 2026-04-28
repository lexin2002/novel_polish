"""Text masking utility for handling extreme LLM refusals in fiction writing"""

import logging
import random
import string
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class TextMasker:
    """
    Masks sensitive words in text and provides a way to restore them.
    Used to bypass extreme safety refusals by replacing sensitive terms with neutral tokens.
    """

    def __init__(self, sensitive_words: List[str] = None):
        self.sensitive_words = sensitive_words or []
        self.mask_map: Dict[str, str] = {}

    def _generate_token(self, index: int) -> str:
        """Generate a neutral-looking token like [TOKEN_A1]"""
        char = random.choice(string.ascii_uppercase)
        return f"[TOKEN_{char}{index}]"

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace sensitive words with tokens.
        Returns the masked text and the map to restore it.
        """
        if not self.sensitive_words:
            return text, {}

        current_mask_map = {}
        masked_text = text
        
        for i, word in enumerate(self.sensitive_words):
            if word in masked_text:
                token = self._generate_token(i)
                current_mask_map[token] = word
                masked_text = masked_text.replace(word, token)
        
        return masked_text, current_mask_map

    def unmask(self, text: str, mask_map: Dict[str, str]) -> str:
        """Restore original words from tokens."""
        unmasked_text = text
        for token, original in mask_map.items():
            unmasked_text = unmasked_text.replace(token, original)
        return unmasked_text

def create_text_masker(sensitive_words: List[str] = None) -> TextMasker:
    return TextMasker(sensitive_words)
