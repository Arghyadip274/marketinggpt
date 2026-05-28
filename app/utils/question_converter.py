"""Questionnaire converter for parsing DOCX and generating configuration JSON."""

import json
import logging
import os
from pathlib import Path

try:
    from docx import Document
except ImportError:
    raise ImportError("python-docx is not installed. Run 'pip install python-docx'")

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class QuestionConverter:
    """Utility class to extract questions from a DOCX file and convert to JSON."""

    def __init__(self, docx_path: str, output_path: str):
        self.docx_path = Path(docx_path)
        self.output_path = Path(output_path)

    def convert(self) -> None:
        """Execute the conversion process."""
        logger.info("Starting conversion for: %s", self.docx_path)
        if not self.docx_path.exists():
            logger.error("DOCX file not found: %s", self.docx_path)
            raise FileNotFoundError(f"DOCX file not found: {self.docx_path}")

        doc = Document(self.docx_path)
        questions = []
        current_category = "General"

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            
            # Detect category based on length and common heuristics (e.g. bold or ends with Questions)
            is_heading_style = p.style.name.startswith('Heading')
            
            # Short lines that look like titles
            if is_heading_style or (len(text) < 40 and not text.endswith("?")):
                current_category = text
                continue
                
            # If it looks like a question or substantive line
            input_type = self._infer_input_type(text)
            
            # Remove any leading numbers like "1. " or "2. "
            import re
            cleaned_question = re.sub(r'^\d+[\.\)]\s*', '', text)
            
            question_data = {
                "category": current_category,
                "question": cleaned_question,
                "required": True,
                "input_type": input_type
            }
            questions.append(question_data)

        self._save_json(questions)
        logger.info("Successfully converted %d questions.", len(questions))

    def _infer_input_type(self, text: str) -> str:
        """Infer the required input type based on the question text."""
        text_lower = text.lower()
        if "email" in text_lower:
            return "email"
        if "url" in text_lower or "website" in text_lower or "link" in text_lower:
            return "url"
        # Everything else defaults to text
        return "text"

    def _save_json(self, data: list[dict]) -> None:
        """Save the extracted data to a JSON file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Saved JSON config to: %s", self.output_path)


if __name__ == "__main__":
    # Basic logging setup for direct script execution
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Path resolution relative to the project root
    project_root = Path(__file__).parent.parent.parent
    docx_file = project_root / "data" / "marketing_questions.docx"
    json_output = project_root / "app" / "config" / "marketing_questions.json"
    
    converter = QuestionConverter(
        docx_path=str(docx_file),
        output_path=str(json_output)
    )
    
    try:
        converter.convert()
    except Exception as e:
        logger.error("Conversion failed: %s", e)
        raise
