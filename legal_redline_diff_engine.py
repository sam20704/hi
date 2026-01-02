#!/usr/bin/env python3

import logging
import re
import difflib
import json
from typing import Dict, Optional, Any
from redlines import Redlines

# CONFIGURATION
def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - - %(message)s"
    )


# NORMALIZATION
def normalize_text(text: str) -> str:
    # Normalizes legal text so that visual differences aren't flagged.
    # Unifies whitespace (tabs to spaces)
    # Standardizes quotes (curly to straight)

    if not text:
        return ""
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    text = re.sub(r"\s+", " ", text)  # Collapse multiple spaces
    return text.strip()


def generate_legal_redline(reference_text: str, incoming_text: str) -> dict:
    
    # Compare two strings and produce a redline diff using Redlines.
    clean_old = normalize_text(reference_text)
    clean_new = normalize_text(incoming_text)

    if clean_old == clean_new:
        return {
            "status": "MATCH",
            "diff_markdown": None,
            "change_ratio": 0.0
        }

    differ = Redlines(clean_old, clean_new)
    redline_text = differ.compare()

    matcher = difflib.SequenceMatcher(None, clean_old, clean_new)
    similarity = matcher.ratio()
    change_ratio = 1.0 - similarity

    return {
        "status": "CHANGED",
        "diff_markdown": redline_text,
        "change_ratio": change_ratio
    }


#knowledge base loading
def load_knowledge_base(path: Optional[str] = None) -> Dict[str, str]:
    
    # Load section -> template text mapping.
    # If path is provided and is existing, load JSON from it otherwise return a small default dictionary 
    
    if path:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return {k: str(v) for k, v in data.items()}
        except Exception as e:
            logging.error(f"Failed to load knowledge base from {path}: {e}")

    default = {
        "Liability": "The Contractor shall be liable for all damages up to $1,000,000.",
        "Payment Terms": "The Client shall pay the Contractor within 30 days of invoice.",
    }
    return default


# section-wise comparison
def get_legal_redline_for_document(
    document_text: str,
    extracted_sections: Optional[Dict[str, str]] = None,
    knowledge_base: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    
   # Compare the incoming document against a knowledge_base (section -> reference text).
   #  If not provided, the engine will compare each reference section to the full document_text.

    configure_logging()

    # knowledge base exists
    kb = knowledge_base or load_knowledge_base()

    # 2. Normalize extracted_sections into a usable mapping
    extracted: Dict[str, str] = {}
    if isinstance(extracted_sections, dict) and extracted_sections:
        if "sections" in extracted_sections and isinstance(extracted_sections["sections"], dict):
            extracted = {k: str(v) for k, v in extracted_sections["sections"].items()}
        else:
            # treat as direct mapping section->text
            extracted = {k: str(v) for k, v in extracted_sections.items()}
    else:
        # fallback: treat entire document as single "Full Document" section
        extracted = {"Full Document": document_text}

    results: Dict[str, Any] = {}

    # 3. For each reference section, try to find matching extracted text
    for section_name, ref_text in kb.items():
        # best match: direct key match
        input_text: Optional[str] = None
        matched_input_section: Optional[str] = None

        if section_name in extracted:
            input_text = extracted[section_name]
            matched_input_section = section_name
        else:
            # fallback strategies: case-insensitive key match
            for k in extracted.keys():
                if k.lower() == section_name.lower():
                    input_text = extracted[k]
                    matched_input_section = k
                    break

        if input_text is None:
            # As last resort compare the whole document
            input_text = document_text
            matched_input_section = "Full Document"

        # 4. Run the low-level redline comparator
        try:
            diff_result = generate_legal_redline(ref_text, input_text)
        except Exception as e:
            logging.exception(f"Redline comparison failed for section '{section_name}': {e}")
            diff_result = {"status": "ERROR", "diff_markdown": None, "change_ratio": 1.0}

        # Attach metadata
        diff_result["matched_input_section"] = matched_input_section
        diff_result["reference_len"] = len(str(ref_text))
        diff_result["input_len"] = len(str(input_text))

        results[section_name] = diff_result

    return results
