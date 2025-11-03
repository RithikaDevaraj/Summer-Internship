import logging
from typing import Dict, Optional, List
import requests
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from config import config
import os
import csv
import re
import asyncio
import time

# try to load .env into environment (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv not installed or .env not present — rely on existing environment
    pass

# default SPARQL endpoint (can override via env/config)
AGROVOC_SPARQL_ENDPOINT_DEFAULT = "https://agrovoc.fao.org/sparql"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self):
        # IndicTrans2 models (preferred for Tamil and Hindi pairs)
        self.indic_models = {}
        self.indic_tokenizers = {}
        # Known model IDs for supported pairs
        self.indic_model_names: Dict[str, str] = {
            "en-ta": "ai4bharat/indictrans2-en-ta",
            "ta-en": "ai4bharat/indictrans2-ta-en",
            "en-hi": "ai4bharat/indictrans2-en-hi",
            "hi-en": "ai4bharat/indictrans2-hi-en",
        }
        # AGROVOC bilingual glossary maps (loaded from backend/agrovoc_glossary.csv)
        # en->hi and hi->en (lowercased keys for matching)
        self.agrovoc_en_to_hi: Dict[str, str] = {}
        self.agrovoc_hi_to_en: Dict[str, str] = {}
        # Hugging Face auth token (from env or config)
        self.hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN") or getattr(config, "HF_TOKEN", None)
        if self.hf_token:
            logger.info("Hugging Face token found in environment")
        # Load CSV fallback (optional) and initialize SPARQL cache
        self._load_agrovoc_glossary()
        self.agrovoc_sparql_endpoint = getattr(config, "AGROVOC_SPARQL_ENDPOINT", AGROVOC_SPARQL_ENDPOINT_DEFAULT)
        # simple in-memory cache: hi_lower -> en_label
        self._agrovoc_cache: Dict[str, Optional[str]] = {}
        # Allow override to force CPU if CUDA is flaky on Windows
        force_cpu = bool(int(getattr(config, "FORCE_CPU", 0)))
        self.device = torch.device("cpu" if force_cpu else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.initialized = False
        self.initialize_models()
    
    def _load_agrovoc_glossary(self) -> None:
        """Load AGROVOC bilingual glossary CSV into memory (en<->hi)."""
        try:
            csv_path = os.path.join(os.path.dirname(__file__), "agrovoc_glossary.csv")
            if not os.path.exists(csv_path):
                logger.warning("AGROVOC glossary not found at %s; skipping glossary load", csv_path)
                return
            with open(csv_path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh, fieldnames=["uri", "lang", "label"])
                # CSV might be headerless; iterate rows and build maps for en<->hi
                for row in reader:
                    try:
                        uri = (row.get("uri") or "").strip()
                        lang = (row.get("lang") or "").strip().lower()
                        label = (row.get("label") or "").strip()
                        if not label or not lang:
                            continue
                        if lang == "en":
                            en_label = label
                            # next line in CSV for same URI with 'hi' may follow; we'll catch it when it appears
                            # store temporarily using uri as key
                            self.agrovoc_en_to_hi.setdefault(en_label.lower(), None)
                        elif lang == "hi":
                            hi_label = label
                            self.agrovoc_hi_to_en.setdefault(hi_label.lower(), None)
                    except Exception:
                        continue
            # Second pass: parse file again to build actual en->hi and hi->en pairs by grouping by uri
            # Simpler approach: try to read full file into rows grouped by uri
            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh, fieldnames=["uri", "lang", "label"]))
            grouped = {}
            for r in rows:
                u = (r.get("uri") or "").strip()
                if not u:
                    continue
                grouped.setdefault(u, []).append(r)
            for u, items in grouped.items():
                en = None
                hi = None
                for it in items:
                    l = (it.get("label") or "").strip()
                    lang = (it.get("lang") or "").strip().lower()
                    if not l:
                        continue
                    if lang == "en":
                        en = l
                    elif lang == "hi":
                        hi = l
                if en and hi:
                    self.agrovoc_en_to_hi[en.lower()] = hi
                    self.agrovoc_hi_to_en[hi.lower()] = en
            logger.info("Loaded AGROVOC glossary entries: en->hi=%d, hi->en=%d", len(self.agrovoc_en_to_hi), len(self.agrovoc_hi_to_en))
        except Exception as e:
            logger.warning("Failed to load AGROVOC glossary: %s", e)
            self.agrovoc_en_to_hi = {}
            self.agrovoc_hi_to_en = {}
    
    def _apply_glossary_to_text(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Replace occurrences of domain terms using provided mapping.
        mapping keys are expected lowercased; replacement preserves basic spacing.
        Longer keys are replaced first to avoid partial overlap.
        """
        if not mapping or not text:
            return text
        lowered = text
        # Sort by length desc to replace longest matches first
        keys = sorted(mapping.keys(), key=lambda x: -len(x))
        for key in keys:
            val = mapping[key]
            if not val:
                continue
            # use simple replace on lowered text; reconstruct with original surrounding using regex
            try:
                # replace all occurrences case-insensitively
                pattern = re.compile(re.escape(key), flags=re.IGNORECASE)
                lowered = pattern.sub(val, lowered)
            except Exception:
                lowered = lowered.replace(key, val)
        return lowered

    def _sparql_lookup(self, hi_term: str) -> Optional[str]:
        """Sync SPARQL lookup: Hindi label -> English prefLabel (returns first match)."""
        try:
            if not hi_term:
                return None
            key = hi_term.strip().lower()
            if key in self._agrovoc_cache:
                return self._agrovoc_cache[key]

            # Build SPARQL query - exact match on prefLabel text (case-insensitive)
            q = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?en WHERE {{
  ?c a skos:Concept ;
     skos:prefLabel ?en ;
     skos:prefLabel ?hi .
  FILTER(lang(?en) = "en" && lang(?hi) = "hi" && lcase(str(?hi)) = "{key}")
}}
LIMIT 1
"""
            resp = requests.get(self.agrovoc_sparql_endpoint, params={"query": q, "format": "json"}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            bindings = data.get("results", {}).get("bindings", [])
            if bindings:
                en_label = bindings[0].get("en", {}).get("value")
                self._agrovoc_cache[key] = en_label
                return en_label
            # cache negative result briefly
            self._agrovoc_cache[key] = None
            return None
        except Exception as e:
            logger.debug("AGROVOC SPARQL lookup failed for '%s': %s", hi_term, e)
            # Do not raise — fallback to CSV/local mapping or leave unchanged
            self._agrovoc_cache[hi_term.strip().lower()] = None
            return None

    def _agrovoc_preprocess_text(self, text: str) -> str:
        """
        Replace Hindi phrases in text with English AGROVOC labels (on-demand SPARQL lookup).
        Uses greedy n-gram matching (max 5 tokens) and updates cache.
        """
        if not text:
            return text
        words = text.split()
        n = len(words)
        i = 0
        out_tokens = []
        max_ngram = 5
        while i < n:
            matched = False
            # try longest n-gram first
            for size in range(min(max_ngram, n - i), 0, -1):
                phrase = " ".join(words[i:i + size]).strip()
                if not phrase:
                    continue
                # check local CSV map first (hi->en), then SPARQL
                en = self.agrovoc_hi_to_en.get(phrase.lower())
                if en is None:
                    en = self._sparql_lookup(phrase)
                if en:
                    out_tokens.append(en)
                    i += size
                    matched = True
                    break
            if not matched:
                out_tokens.append(words[i])
                i += 1
        return " ".join(out_tokens)

    def initialize_models(self):
        """Initialize translation models for Indian languages"""
        try:
            logger.info("Starting translation model initialization...")
            # Preferred IndicTrans2 pairs for Tamil and Hindi
            indic_pairs = [
                ("en", "ta", self.indic_model_names["en-ta"]),
                ("ta", "en", self.indic_model_names["ta-en"]),
                ("en", "hi", self.indic_model_names["en-hi"]),
                ("hi", "en", self.indic_model_names["hi-en"]),
            ]
            for src, tgt, model_name in indic_pairs:
                try:
                    logger.info(f"Loading IndicTrans2 model: {model_name}")
                    use_token = self.hf_token if self.hf_token else None
                    tok = AutoTokenizer.from_pretrained(model_name, use_auth_token=use_token)
                    mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name, use_auth_token=use_token)
                    try:
                        mdl.to(self.device)
                    except Exception as e:
                        logger.warning(f"CUDA move failed for {model_name} ({e}), falling back to CPU")
                        mdl.to(torch.device("cpu"))
                    self.indic_models[f"{src}-{tgt}"] = mdl
                    self.indic_tokenizers[f"{src}-{tgt}"] = tok
                    logger.info(f"Loaded IndicTrans2 {model_name}")
                except Exception as e:
                    logger.warning(f"Failed to load IndicTrans2 {model_name}: {e}")
            
            self.initialized = True
            logger.info("Translation service initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing translation models: {e}")
            self.initialized = False
    
    async def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between languages"""
        try:
            # If same language, return original text
            if source_lang == target_lang:
                return text
            
            # Check if translation service is initialized
            if not self.initialized:
                logger.warning("Translation service not initialized, returning original text")
                return text
            
            # Use AGROVOC assistance for Hindi <-> English domain terms
            preprocessed = text
            if source_lang == "hi" and target_lang == "en":
                # Prefer CSV local mapping; fall back to live SPARQL lookups for unmatched phrases.
                # Run blocking lookups in a thread to avoid blocking event loop.
                preprocessed = await asyncio.to_thread(self._agrovoc_preprocess_text, text)
            # Prefer IndicTrans2 for all supported pairs (ta, hi)
            model_key = f"{source_lang}-{target_lang}"
            # Lazy-load if missing
            if model_key not in self.indic_models and model_key in self.indic_model_names:
                self._ensure_indic_pair_loaded(source_lang, target_lang)
            if model_key in self.indic_models:
                out = self._translate_with_indic(preprocessed, model_key)
                # Post-process en->hi: map English domain terms to Hindi after translation
                if source_lang == "en" and target_lang == "hi" and self.agrovoc_en_to_hi:
                    out = self._apply_glossary_to_text(out, self.agrovoc_en_to_hi)
                return out
            else:
                # Try indirect translation through English
                if source_lang != "en" and target_lang != "en":
                    english_text = await self.translate_text(text, source_lang, "en")
                    return await self.translate_text(english_text, "en", target_lang)
                else:
                    # Fallback to Google Translate API or return original
                    return await self._fallback_translation(text, source_lang, target_lang)
        
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def _translate_with_indic(self, text: str, model_key: str) -> str:
        """Translate using IndicTrans2 model"""
        try:
            tokenizer = self.indic_tokenizers[model_key]
            model = self.indic_models[model_key]
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            try:
                inputs = {k: v.to(next(model.parameters()).device) for k, v in inputs.items()}
                with torch.no_grad():
                    outputs = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
            except Exception as e:
                # On CUDA driver/runtime error, retry on CPU once
                if "CUDA" in str(e).upper():
                    model.to(torch.device("cpu"))
                    inputs = {k: v.to(torch.device("cpu")) for k, v in inputs.items()}
                    with torch.no_grad():
                        outputs = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
                else:
                    raise
            translated_text = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            logger.info(f"Translated with IndicTrans2 using {model_key}")
            return translated_text
        except Exception as e:
            logger.error(f"IndicTrans2 translation error: {e}")
            return text

    def _ensure_indic_pair_loaded(self, src: str, tgt: str) -> None:
        """Ensure an IndicTrans2 pair is loaded; load on demand if needed."""
        key = f"{src}-{tgt}"
        if key in self.indic_models:
            return
        model_name = self.indic_model_names.get(key)
        if not model_name:
            return
        try:
            logger.info(f"On-demand loading IndicTrans2 model: {model_name}")
            use_token = self.hf_token if self.hf_token else None
            tok = AutoTokenizer.from_pretrained(model_name, use_auth_token=use_token)
            mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name, use_auth_token=use_token)
            try:
                mdl.to(self.device)
            except Exception as e:
                logger.warning(f"CUDA move failed for {model_name} ({e}), using CPU")
                mdl.to(torch.device("cpu"))
            self.indic_models[key] = mdl
            self.indic_tokenizers[key] = tok
        except Exception as e:
            logger.warning(f"On-demand load failed for {model_name}: {e}")
    
    async def _fallback_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """Fallback translation using Google Translate API"""
        try:
            # This is a placeholder for Google Translate API integration
            # You would need to set up Google Cloud Translation API
            logger.warning(f"No direct translation model for {source_lang}-{target_lang}, returning original text")
            return text
            
        except Exception as e:
            logger.error(f"Fallback translation error: {e}")
            return text
    
    def detect_language(self, text: str) -> str:
        """Detect language of input text"""
        try:
            # Simple language detection based on script
            if any('\u0900' <= char <= '\u097F' for char in text):
                return "hi"  # Devanagari script (Hindi)
            elif any('\u0B80' <= char <= '\u0BFF' for char in text):
                return "ta"  # Tamil script
            elif any('\u0C00' <= char <= '\u0C7F' for char in text):
                return "te"  # Telugu script
            elif any('\u0980' <= char <= '\u09FF' for char in text):
                return "bn"  # Bengali script
            elif any('\u0A80' <= char <= '\u0AFF' for char in text):
                return "gu"  # Gujarati script
            elif any('\u0C80' <= char <= '\u0CFF' for char in text):
                return "kn"  # Kannada script
            elif any('\u0D00' <= char <= '\u0D7F' for char in text):
                return "ml"  # Malayalam script
            else:
                return "en"  # Default to English
                
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return "en"
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for translation"""
        return {
            "en": "English",
            "hi": "हिंदी (Hindi)",
            "ta": "தமிழ் (Tamil)",
            "te": "తెలుగు (Telugu)",
            "bn": "বাংলা (Bengali)",
            "gu": "ગુજરાતી (Gujarati)",
            "kn": "ಕನ್ನಡ (Kannada)",
            "ml": "മലയാളം (Malayalam)"
        }
    
    async def translate_agricultural_response(self, response: str, target_language: str) -> str:
        """Translate agricultural response with context preservation"""
        try:
            if target_language == "en":
                return response
            
            # Split response into sentences for better translation
            sentences = response.split('. ')
            translated_sentences = []
            
            for sentence in sentences:
                if sentence.strip():
                    translated = await self.translate_text(sentence.strip(), "en", target_language)
                    # For en->hi ensure AGROVOC english terms are replaced with Hindi labels
                    if target_language == "hi" and self.agrovoc_en_to_hi:
                        translated = self._apply_glossary_to_text(translated, self.agrovoc_en_to_hi)
                    translated_sentences.append(translated)
            
            return '. '.join(translated_sentences)
            
        except Exception as e:
            logger.error(f"Agricultural response translation error: {e}")
            return response

# Global translation service instance
translation_service = TranslationService()