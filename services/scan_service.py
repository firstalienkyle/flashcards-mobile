from pathlib import Path
import cv2
import pdfplumber


class ScanService:
    def capture_from_camera(self) -> bytes:
        """
        Opens the default webcam, shows a preview window, captures a frame
        on SPACE key press, closes the window, and returns the JPEG bytes.
        Raises RuntimeError if no camera is found.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("No camera found. Make sure a webcam is connected.")

        print("Camera preview open. Press SPACE to capture, Q to cancel.")
        captured = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Capture — SPACE to snap, Q to cancel", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                captured = frame
                break
            elif key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if captured is None:
            raise RuntimeError("Capture cancelled.")

        success, buffer = cv2.imencode(".jpg", captured)
        if not success:
            raise RuntimeError("Failed to encode captured frame as JPEG.")
        return buffer.tobytes()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extracts all text from a PDF file, concatenating pages with newlines.
        Raises FileNotFoundError if the path does not exist.
        Raises ValueError if no text could be extracted.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pages_text = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)

        if not pages_text:
            raise ValueError("No extractable text found in PDF. It may be image-only.")

        return "\n\n".join(pages_text)
