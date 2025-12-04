import os
import difflib
import logging
from sentence_transformers import SentenceTransformer, util

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

def configure_logging(level=logging.INFO):
    """Configure the logging settings for the module."""
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')


# ---------------------------------------------------------
# VALIDATION (TEXTUAL DIFFERENCE)
# ---------------------------------------------------------

def validate_legal_clauses(input_dict, knowledge_dict):
    """
    Compare text sections from input and knowledge base using direct text difference.

    Args:
        input_dict (dict): Section heading -> text from input document
        knowledge_dict (dict): Section heading -> text from knowledge base

    Returns:
        dict: Validation results with status and detected differences
    """
    validation_results = {}

    for section, input_text in input_dict.items():
        knowledge_text = knowledge_dict.get(section)
        status = "success"
        changes = None

        if knowledge_text:
            if input_text != knowledge_text:
                status = "changed"
                diff = difflib.ndiff(input_text.splitlines(), knowledge_text.splitlines())
                changes = '\n'.join(diff)
                logging.info(f"Changes detected in section '{section}'.")
            else:
                logging.info(f"No changes detected in section '{section}'.")
        else:
            status = "not_found"
            logging.warning(f"Section '{section}' not found in knowledge base.")

        validation_results[section] = {"status": status, "changes": changes}

    return validation_results


# ---------------------------------------------------------
# SEMANTIC SIMILARITY (EMBEDDING-BASED)
# ---------------------------------------------------------

def load_text_model(model_path):
    """Load a SentenceTransformer model from a given path."""
    try:
        model = SentenceTransformer(model_path, local_files_only=True)
        logging.info(f"Model loaded successfully from: {model_path}")
        return model
    except Exception as e:
        logging.error(f"Failed to load model: {e}")
        raise


def extract_text_embeddings(text1, text2, text_model):
    """Generate embeddings for two text inputs."""
    embedding1 = text_model.encode(text1, convert_to_tensor=True)
    embedding2 = text_model.encode(text2, convert_to_tensor=True)
    return embedding1, embedding2


def compare_embeddings(embedding1, embedding2):
    """Compute cosine similarity between two embeddings."""
    return util.pytorch_cos_sim(embedding1, embedding2).item()


def semantic_matching(text1, text2):
    """Compute semantic similarity score between two texts."""
    model = load_text_model(model_path)
    embedding1, embedding2 = extract_text_embeddings(text1, text2, model)
    score = compare_embeddings(embedding1, embedding2)
    logging.info(f"Semantic similarity score: {score:.4f}")
    return score


# ---------------------------------------------------------
# MAIN (EXAMPLE USAGE)
# ---------------------------------------------------------

def main():
    configure_logging()

    # Example data
    knowledge_dict = {
        "Central Points of Contact/Project Management": (
            "The Parties are required to handle service-related questions or comments exclusively with the responsible "
            "Central Points of Contact. All communication between the Customer and the Contractor’s employees must be made "
            "via the project manager of the Contractor."
        )
    }

    input_dict = {
        "Central Points of Contact/Project Management": (
            "service-related questions or comments exclusively with the responsible Central Points of Contact. "
            "All communication between the Customer and the employees must be made via the project manager of the Contractor."
        )
    }

    # Step 1: Basic diff comparison
    validation_results = validate_legal_clauses(input_dict, knowledge_dict)
    print("\nValidation Results:\n", validation_results)

    # Step 2: Semantic similarity comparison
    score = semantic_matching(
        knowledge_dict["Central Points of Contact/Project Management"],
        input_dict["Central Points of Contact/Project Management"]

    )
    print(f"\nSemantic Similarity Score: {score:.4f}")


if __name__ == "__main__":
    # absolute path for the current folder all-MiniLM-L6-v2
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.abspath(os.path.join(script_dir, "../all-MiniLM-L6-v2"))
    main()
