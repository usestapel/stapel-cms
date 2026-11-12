"""A provider at stapel-translate's LLM_PROVIDER seam: tags each text with the target."""
import json
import re

from stapel_translate.providers import BaseTranslationProvider

CALLS = []


class TaggingProvider(BaseTranslationProvider):
    def complete(self, prompt):
        texts = json.loads(re.search(r"\[.*\]", prompt, re.DOTALL).group(0))
        target = re.search(r"\(([a-z-]+)\)\.\n", prompt).group(1)
        CALLS.append(len(texts))
        return json.dumps([f"[{target}] {t}" for t in texts], ensure_ascii=False)
