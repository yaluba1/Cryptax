"""
Service for handling localization of strings.
Loads language-specific files from the locales directory.
"""

import importlib
from typing import Dict
from worker.logging_config import logger

class LocalizationService:
    def __init__(self):
        self.cache = {}

    def get_email_strings(self, lang: str) -> Dict[str, str]:
        """
        Returns the dictionary of email strings for the given language.
        Falls back to English if the language is not supported or file not found.
        """
        lang = lang.lower() if lang else "en"
        
        # Supported languages
        supported_langs = ["en", "es", "fr", "de", "it", "ja", "pt"]
        if lang not in supported_langs:
            logger.warning("Language '{}' not supported. Falling back to English.", lang)
            lang = "en"

        if lang in self.cache:
            return self.cache[lang]

        try:
            # Import the module dynamically
            module_name = f"worker.locales.{lang}"
            module = importlib.import_module(module_name)
            strings = getattr(module, "EMAIL_STRINGS")
            self.cache[lang] = strings
            return strings
        except (ImportError, AttributeError) as e:
            logger.error("Failed to load localization for '{}': {}", lang, str(e))
            # Fallback to English if not already trying English
            if lang != "en":
                return self.get_email_strings("en")
            return {}

localization_service = LocalizationService()
