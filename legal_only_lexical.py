import logging
import re
from redlines import Redlines  # SOTA library for "Track Changes" style diffs

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
def configure_logging(level=logging.INFO):
    """Configure logging to standard Azure stdout format."""
    logging.basicConfig(
        level=level, 
        format='%(asctime)s - %(levelname)s - - %(message)s'
    )

# ---------------------------------------------------------
# NORMALIZATION (CRITICAL FOR LEGAL TEXT)
# ---------------------------------------------------------
def normalize_text(text):
    """
    Normalizes legal text to ensure 'visual' differences aren't flagged.
    - Unifies whitespace (tabs to spaces).
    - Standardizes quotes (curly to straight).
    """
    if not text: return ""
    text = text.replace('“', '"').replace('”', '"').replace("’", "'")
    text = re.sub(r'\s+', ' ', text) # Collapse multiple spaces
    return text.strip()

# ---------------------------------------------------------
# REDLINING LOGIC (THE "WORD LEVEL" DIFFERENCE)
# ---------------------------------------------------------
def generate_legal_redline(text_old, text_new):
    """
    Generates a 'Track Changes' style difference using Redlines (diff-match-patch).
    Returns: Markdown/HTML string showing deletions and insertions.
    """
    clean_old = normalize_text(text_old)
    clean_new = normalize_text(text_new)

    if clean_old == clean_new:
        return {"status": "MATCH", "diff_markdown": None}

    # Redlines produces: "The <del>quick</del> <ins>slow</ins> brown fox"
    differ = Redlines(clean_old, clean_new)
    redline_text = differ.compare()
    
    return {
        "status": "CHANGED",
        "diff_markdown": redline_text,
        "change_ratio": differ.distance / max(len(clean_old), len(clean_new))
    }

# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------
def compare_legal_sections(input_dict, knowledge_dict):
    """
    Compares specific sections.
    """
    results = {}
    
    for section, input_text in input_dict.items():
        knowledge_text = knowledge_dict.get(section)
        
        if not knowledge_text:
            logging.warning(f"Section '{section}' missing in Knowledge Base.")
            results[section] = {"status": "MISSING_REFERENCE"}
            continue

        logging.info(f"Processing Section: {section}")
        
        # Run Redline Check
        diff_result = generate_legal_redline(knowledge_text, input_text)
        
        if diff_result["status"] == "CHANGED":
            logging.info(f"--> CHANGES DETECTED: {section}")
            # In Azure logs, printing the diff helps debugging
            logging.debug(f"Diff: {diff_result['diff_markdown']}")
        else:
            logging.info(f"--> MATCH: {section}")
            
        results[section] = diff_result

    return results

# ---------------------------------------------------------
# EXAMPLE USAGE
# ---------------------------------------------------------
if __name__ == "__main__":
    configure_logging()

    # 1. Define Data (Simulating Inputs)
    # Note: 'knowledge' is the gold standard (Old version), 'input' is the new version
    knowledge_base = {
        "Liability": "The Contractor shall be liable for all damages up to $1,000,000."
    }
    
    incoming_doc = {
        "Liability": "The Contractor shall not be liable for any damages."
    }

    # 2. Run Comparison
    report = compare_legal_sections(incoming_doc, knowledge_base)

    # 3. Output for API Response
    import json
    print("\n--- FINAL JSON OUTPUT ---")
    print(json.dumps(report, indent=2))
