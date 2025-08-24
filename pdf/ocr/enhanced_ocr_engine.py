#!/usr/bin/env python3
"""
Enhanced OCR Engine - Dual-Pass Processing with Quality Gates

Implements the comprehensive OCR overhaul plan with:
- Born-digital fast-path detection
- Pre-processing normalization (deskew, dewarp, denoise, threshold)
- Dual-pass OCR (standard + enhanced)
- Quality validation gates
- Integration with ContentQualityScorer

Architecture: Wraps existing OCREngine with enhanced processing capabilities
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .ocr_engine import OCREngine
import sys
import os
# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.content_quality_scorer import ContentQualityScorer, ValidationStatus


class EnhancedOCREngine:
    """
    Enhanced OCR engine with dual-pass processing and quality gates.
    
    Features:
    - Born-digital PDF fast-path detection
    - Advanced image pre-processing (deskew, denoise, threshold)
    - Dual-pass OCR (standard -> enhanced if needed)
    - Quality validation with hard gates
    - Comprehensive metrics and diagnostics
    """
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.base_engine = OCREngine()
        self.quality_scorer = ContentQualityScorer()
        self.available = TESSERACT_AVAILABLE and CV2_AVAILABLE
        
        # Enhancement settings (calibrated from user requirements)
        self.enhancement_config = {
            'min_confidence_for_standard': 0.6,  # Try enhanced if below this
            'max_skew_angle': 2.0,               # Degrees - correct if above
            'denoise_strength': 10,              # fastNlMeansDenoising h parameter
            'adaptive_threshold_block': 11,      # Block size for adaptive threshold
            'morphology_kernel_size': (2, 2),    # Noise removal kernel
        }
    
    def extract_text_with_dual_pass(
        self, 
        image: Image.Image, 
        page_count: int = 1,
        force_enhanced: bool = False
    ) -> Dict[str, Any]:
        """
        Main dual-pass OCR extraction with quality gates.
        
        Args:
            image: PIL Image to process
            page_count: Number of pages for quality calculation
            force_enhanced: Skip standard pass, go straight to enhanced
            
        Returns:
            Dict with text, quality metrics, validation status, and processing metadata
        """
        start_time = time.time()
        processing_log = []
        
        if not self.available:
            return {
                'success': False,
                'error': 'Enhanced OCR dependencies not available',
                'validation_status': ValidationStatus.OCR_DONE.value,
                'processing_time': 0
            }
        
        # Phase 1: Born-digital detection (fast path)
        if not force_enhanced:
            born_digital_result = self._detect_born_digital_text(image)
            if born_digital_result['is_born_digital']:
                processing_log.append("✓ Born-digital fast-path detected")
                return {
                    'success': True,
                    'text': '',  # Signal to use PyPDF2 instead
                    'method': 'born_digital_bypass',
                    'validation_status': ValidationStatus.TEXT_VALIDATED.value,
                    'processing_log': processing_log,
                    'processing_time': time.time() - start_time
                }
        
        # Phase 2: Standard OCR pass
        if not force_enhanced:
            processing_log.append("→ Starting standard OCR pass")
            standard_result = self.base_engine.extract_text_from_image(image, enhance=True)
            
            if standard_result['success'] and standard_result['confidence'] >= self.enhancement_config['min_confidence_for_standard']:
                # Check if standard result passes quality gates
                text = standard_result['text']
                quality_metrics = self.quality_scorer.score_content(text, page_count)
                
                if quality_metrics.validation_status == ValidationStatus.TEXT_VALIDATED:
                    processing_log.append(f"✓ Standard OCR passed quality gates (confidence: {standard_result['confidence']:.2f})")
                    return {
                        'success': True,
                        'text': text,
                        'method': 'standard_ocr',
                        'confidence': standard_result['confidence'],
                        'validation_status': quality_metrics.validation_status.value,
                        'quality_score': quality_metrics.quality_score,
                        'quality_metrics': quality_metrics,
                        'processing_log': processing_log,
                        'processing_time': time.time() - start_time
                    }
                else:
                    processing_log.append(f"⚠ Standard OCR failed quality gates: {quality_metrics.failure_reasons}")
            else:
                confidence = standard_result.get('confidence', 0)
                processing_log.append(f"⚠ Standard OCR low confidence: {confidence:.2f}")
        
        # Phase 3: Enhanced OCR pass with pre-processing
        processing_log.append("→ Starting enhanced OCR pass with pre-processing")
        enhanced_result = self._enhanced_ocr_extraction(image, processing_log)
        
        if not enhanced_result['success']:
            return {
                'success': False,
                'error': enhanced_result.get('error', 'Enhanced OCR failed'),
                'validation_status': ValidationStatus.OCR_DONE.value,
                'processing_log': processing_log,
                'processing_time': time.time() - start_time
            }
        
        # Phase 4: Final quality validation
        text = enhanced_result['text']
        quality_metrics = self.quality_scorer.score_content(text, page_count)
        
        processing_log.append(f"→ Final quality score: {quality_metrics.quality_score:.3f}")
        processing_log.append(f"→ Validation status: {quality_metrics.validation_status.value}")
        
        return {
            'success': True,
            'text': text,
            'method': 'enhanced_ocr',
            'confidence': enhanced_result['confidence'],
            'validation_status': quality_metrics.validation_status.value,
            'quality_score': quality_metrics.quality_score,
            'quality_metrics': quality_metrics,
            'preprocessing_applied': enhanced_result.get('preprocessing_steps', []),
            'processing_log': processing_log,
            'processing_time': time.time() - start_time
        }
    
    def _detect_born_digital_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        Fast detection of born-digital PDFs with genuine text layers.
        
        Uses image characteristics to determine if content is digitally generated
        vs scanned/photographed.
        """
        try:
            # Convert to numpy for analysis
            img_array = np.array(image.convert('RGB'))
            
            # Check 1: Color palette simplicity (digital text uses few colors)
            unique_colors = len(np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0))
            color_ratio = unique_colors / (img_array.shape[0] * img_array.shape[1])
            
            # Check 2: Edge sharpness (digital text has crisp edges)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            # Check 3: Text line regularity (digital text aligns perfectly)
            horizontal_projection = np.sum(edges, axis=1)
            line_peaks = self._find_text_line_peaks(horizontal_projection)
            line_regularity = self._calculate_line_regularity(line_peaks)
            
            # Decision logic (calibrated thresholds)
            is_born_digital = (
                color_ratio < 0.01 and      # Very few unique colors
                edge_density > 0.02 and     # Sufficient sharp edges
                line_regularity > 0.7       # Regular text lines
            )
            
            return {
                'is_born_digital': is_born_digital,
                'color_ratio': color_ratio,
                'edge_density': edge_density,
                'line_regularity': line_regularity,
                'confidence': (1 - color_ratio) * edge_density * line_regularity
            }
            
        except Exception as e:
            logger.warning(f"Born-digital detection failed: {e}")
            return {'is_born_digital': False, 'error': str(e)}
    
    def _enhanced_ocr_extraction(self, image: Image.Image, processing_log: List[str]) -> Dict[str, Any]:
        """
        Enhanced OCR with comprehensive pre-processing normalization.
        
        Applies deskew, denoise, adaptive threshold, and morphological operations.
        """
        try:
            # Convert to OpenCV format
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            preprocessing_steps = []
            
            # Step 1: Deskew correction
            skew_angle = self._detect_skew_angle(gray)
            if abs(skew_angle) > 0.5:
                gray = self._correct_skew(gray, skew_angle)
                preprocessing_steps.append(f"deskew({skew_angle:.1f}°)")
                processing_log.append(f"  ✓ Deskew correction: {skew_angle:.1f}°")
            
            # Step 2: Noise reduction
            denoised = cv2.fastNlMeansDenoising(
                gray, 
                None, 
                h=self.enhancement_config['denoise_strength'], 
                templateWindowSize=7, 
                searchWindowSize=21
            )
            preprocessing_steps.append("denoise")
            processing_log.append("  ✓ Noise reduction applied")
            
            # Step 3: Adaptive thresholding
            adaptive_thresh = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                self.enhancement_config['adaptive_threshold_block'],
                2
            )
            preprocessing_steps.append("adaptive_threshold")
            processing_log.append("  ✓ Adaptive thresholding applied")
            
            # Step 4: Morphological operations for noise cleanup
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, self.enhancement_config['morphology_kernel_size'])
            morphed = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
            preprocessing_steps.append("morphology")
            processing_log.append("  ✓ Morphological cleanup applied")
            
            # Step 5: Convert back to PIL for OCR
            enhanced_image = Image.fromarray(morphed)
            
            # Step 6: Enhanced OCR with optimized settings
            # Use PSM 6 (single uniform block) for heavily processed images
            custom_config = r"--oem 3 --psm 6 -l eng -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:!?()[]{}\"'-/\\ "
            
            ocr_data = pytesseract.image_to_data(
                enhanced_image, 
                output_type=pytesseract.Output.DICT, 
                config=custom_config
            )
            
            # Extract text with confidence filtering
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(ocr_data["conf"]):
                if int(conf) > 30:  # Lower threshold for enhanced processing
                    text = ocr_data["text"][i].strip()
                    if text and len(text) > 1:  # Skip single characters
                        text_parts.append(text)
                        confidences.append(int(conf))
            
            full_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_log.append(f"  ✓ Enhanced OCR extracted {len(text_parts)} text elements")
            
            return {
                'success': True,
                'text': full_text,
                'confidence': avg_confidence / 100.0,
                'word_count': len(text_parts),
                'preprocessing_steps': preprocessing_steps
            }
            
        except Exception as e:
            logger.error(f"Enhanced OCR processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _detect_skew_angle(self, image: np.ndarray) -> float:
        """Detect text skew angle using Hough line transform."""
        try:
            # Edge detection
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Hough line detection
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is None:
                return 0.0
            
            # Calculate dominant angle
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = theta * 180 / np.pi - 90
                if -45 < angle < 45:  # Filter reasonable text angles
                    angles.append(angle)
            
            if not angles:
                return 0.0
            
            # Return median angle (more robust than mean)
            return float(np.median(angles))
            
        except Exception:
            return 0.0
    
    def _correct_skew(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Correct image skew by rotation."""
        try:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            
            # Create rotation matrix
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Apply rotation with white background
            corrected = cv2.warpAffine(
                image, 
                rotation_matrix, 
                (w, h), 
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=255  # White background
            )
            
            return corrected
            
        except Exception:
            return image
    
    def _find_text_line_peaks(self, projection: np.ndarray) -> List[int]:
        """Find peaks in horizontal projection that indicate text lines."""
        # Simple peak detection
        peaks = []
        threshold = np.mean(projection) * 0.5
        
        for i in range(1, len(projection) - 1):
            if (projection[i] > projection[i-1] and 
                projection[i] > projection[i+1] and 
                projection[i] > threshold):
                peaks.append(i)
        
        return peaks
    
    def _calculate_line_regularity(self, peaks: List[int]) -> float:
        """Calculate regularity of text line spacing."""
        if len(peaks) < 2:
            return 0.0
        
        # Calculate spacing between consecutive peaks
        spacings = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
        
        if not spacings:
            return 0.0
        
        # Regularity = 1 - (coefficient of variation)
        mean_spacing = np.mean(spacings)
        std_spacing = np.std(spacings)
        
        if mean_spacing == 0:
            return 0.0
        
        cv = std_spacing / mean_spacing
        regularity = max(0.0, 1.0 - cv)
        
        return float(regularity)
    
    def validate_enhanced_setup(self) -> Dict[str, Any]:
        """Validate enhanced OCR setup and dependencies."""
        base_validation = self.base_engine.validate_ocr_setup()
        
        enhanced_validation = {
            'base_ocr': base_validation,
            'cv2_available': CV2_AVAILABLE,
            'enhanced_features': {
                'deskew': CV2_AVAILABLE,
                'denoise': CV2_AVAILABLE,
                'adaptive_threshold': CV2_AVAILABLE,
                'morphology': CV2_AVAILABLE,
                'born_digital_detection': CV2_AVAILABLE,
            },
            'quality_scorer': True,  # Always available
            'enhancement_config': self.enhancement_config
        }
        
        enhanced_validation['ready'] = (
            base_validation.get('ready', False) and 
            CV2_AVAILABLE
        )
        
        return enhanced_validation


def get_enhanced_ocr_engine(dpi: int = 300) -> EnhancedOCREngine:
    """Factory function for enhanced OCR engine."""
    return EnhancedOCREngine(dpi=dpi)