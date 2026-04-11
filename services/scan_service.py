from pathlib import Path


class ScanService:
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        import pdfplumber
        pages_text = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        if not pages_text:
            raise ValueError("No extractable text found in PDF.")
        return "\n\n".join(pages_text)
