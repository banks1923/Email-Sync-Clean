"""OCR engine module - performs optical character recognition."""

from typing import Any

from loguru import logger

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Logger is now imported globally from loguru


class OCREngine:
    """Performs OCR on images with enhancement capabilities."""

    def __init__(self) -> None:
        self.available = TESSERACT_AVAILABLE
        self.cv2_available = CV2_AVAILABLE

    def enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Enhance image quality for better OCR results.

        Args:
            image: PIL Image to enhance

        Returns:
            Enhanced PIL Image
        """
        try:
            # Convert to grayscale
            if image.mode != "L":
                image = image.convert("L")

            # Increase contrast more aggressively for better OCR
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            # Apply stronger sharpening
            image = image.filter(ImageFilter.SHARPEN)
            image = image.filter(ImageFilter.SHARPEN)  # Double sharpen for clarity

            # Enhance brightness slightly for faded documents
            brightness = ImageEnhance.Brightness(image)
            image = brightness.enhance(1.1)

            # Additional CV2 processing if available
            if self.cv2_available:
                image = self._enhance_with_cv2(image)

            return image

        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image  # Return original on error

    def _enhance_with_cv2(self, image: Image.Image) -> Image.Image:
        """Apply advanced CV2 enhancements."""
        try:
            # Convert PIL to numpy array
            img_array = np.array(image)

            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)

            # Apply threshold to get binary image
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Deskew if needed
            angle = self._get_skew_angle(binary)
            if abs(angle) > 0.5:
                binary = self._rotate_image(binary, angle)

            # Convert back to PIL
            return Image.fromarray(binary)

        except Exception as e:
            logger.warning(f"CV2 enhancement failed: {e}")
            return image

    def _get_skew_angle(self, image: np.ndarray) -> float:
        """Detect text skew angle."""
        try:
            coords = np.column_stack(np.where(image > 0))
            angle = cv2.minAreaRect(coords)[-1]

            if angle < -45:
                angle = 90 + angle

            return angle
        except Exception:
            return 0.0

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image to correct skew."""
        try:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        except Exception:
            return image

    def extract_text_from_image(self, image: Image.Image, enhance: bool = True) -> dict[str, Any]:
        """
        Extract text from image using OCR.

        Args:
            image: PIL Image to process
            enhance: Whether to enhance image before OCR

        Returns:
            Dict with extracted text and confidence
        """
        if not self.available:
            return {
                "success": False,
                "error": "Tesseract not available",
                "text": "",
                "confidence": 0.0,
            }

        try:
            # Enhance image if requested
            if enhance:
                image = self.enhance_image_for_ocr(image)

            # Perform OCR with confidence scores and English language hint
            # Add config for better legal document processing
            custom_config = r"--oem 3 --psm 6 -l eng"
            ocr_data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, config=custom_config
            )

            # Extract text and calculate confidence
            text_parts = []
            confidences = []

            for i, conf in enumerate(ocr_data["conf"]):
                if int(conf) > 0:  # Only include detected text
                    text = ocr_data["text"][i].strip()
                    if text:
                        text_parts.append(text)
                        confidences.append(int(conf))

            full_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "success": True,
                "text": full_text,
                "confidence": avg_confidence / 100.0,  # Convert to 0-1 scale
                "word_count": len(text_parts),
            }

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {"success": False, "error": str(e), "text": "", "confidence": 0.0}

    def validate_ocr_setup(self) -> dict[str, Any]:
        """Validate OCR setup and dependencies."""
        result = {
            "tesseract_available": self.available,
            "cv2_available": self.cv2_available,
            "enhancement_available": True,
        }

        if self.available:
            try:
                version = pytesseract.get_tesseract_version()
                result["tesseract_version"] = str(version)
            except Exception:
                result["tesseract_version"] = "unknown"

        result["ready"] = self.available
        return result
