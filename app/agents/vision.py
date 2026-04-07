import asyncio
from typing import Dict, Any, List, Optional
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import easyocr
import os

# Resolve paths relative to the repo root (two levels up from this file)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class VisionAgent:
    """
    Real Computer Vision using YOLOv8 + EasyOCR.
    Detects vehicle type and reads license plates.
    """
    _model = None
    _reader = None
    _lock = threading.Lock()

    def __init__(self):
        pass

    def _get_model(self):
        """
        Singleton Model Loader (Thread-safe)
        """
        if self._model is None:
            with self._lock:
                if self._model is None:
                    # Try custom model (best.pt) in repo root, fallback to yolov8n.pt
                    model_path = os.path.join(_REPO_ROOT, "best.pt")
                    if not os.path.exists(model_path):
                        model_path = os.path.join(_REPO_ROOT, "yolov8n.pt")
                    print(f"[VisionAgent] Loading YOLO Model from {model_path}...")
                    try:
                        self._model = YOLO(model_path)
                        print("[VisionAgent] Model Loaded.")
                    except Exception as e:
                        print(f"[VisionAgent] Failed to load model: {e}. Fallback to yolov8n.pt")
                        self._model = YOLO('yolov8n.pt')
        return self._model

    def _get_reader(self):
        """
        Singleton OCR Reader Loader (Thread-safe)
        """
        if self._reader is None:
            with self._lock:
                if self._reader is None:
                    print("[VisionAgent] Loading EasyOCR...")
                    self._reader = easyocr.Reader(['en'], gpu=False)
                    print("[VisionAgent] EasyOCR Loaded.")
        return self._reader

    async def analyze_stream(self, gate_id: str, frames_bytes: List[bytes] = None) -> Dict[str, Any]:
        """
        Runs inference on one or more image frames.
        Implements Multi-Frame Voting for higher accuracy.
        """
        if not frames_bytes:
             await asyncio.sleep(0.1)
             return {"license_plate": "UNKNOWN", "vehicle_type": "car", "confidence": "0.00"}

        model = self._get_model()
        reader = self._get_reader()
        loop = asyncio.get_running_loop()

        # Run Heavy computation in a thread pool
        result = await loop.run_in_executor(None, self._analyze_sync, model, reader, frames_bytes)
        
        return result

    def _analyze_sync(self, model, reader, frames_bytes: List[bytes]) -> Dict[str, Any]:
        """
        Processes a burst of frames and determines the best plate via Smart Candidate Filtering.
        """
        all_candidates = []
        max_total_conf = 0.0
        vehicle_type = "car"
        
        # Limit to 10 frames max for stability
        burst = frames_bytes[:10]
        
        for frame_index, frame_bytes in enumerate(burst):
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None: continue

            results = model(img, verbose=False)
            if not results: continue
            
            for r in results:
                h, w, _ = img.shape
                for box in r.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.35: # Base detection threshold
                        # 1. Geometry Analysis (Aspect Ratio)
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        box_w = x2 - x1
                        box_h = y2 - y1
                        aspect_ratio = box_w / box_h if box_h != 0 else 0
                        
                        # Hardware-Agnostic Aspect Weight:
                        # Indian plates are ~4:1 (Rect) or ~2:1 (Square). 
                        # Banners/Titles are usually > 8:1
                        aspect_weight = 1.0
                        if aspect_ratio > 7.5: 
                            aspect_weight = 0.1 # Heavily penalize banners
                        elif aspect_ratio < 1.2:
                            aspect_weight = 0.1 # Penalize tiny squares
                        elif 3.0 < aspect_ratio < 5.0:
                            aspect_weight = 1.2 # Bonus for rectangular HSRP
                        
                        # 2. Preprocess & OCR
                        plate_crop = img[int(y1):int(y2), int(x1):int(x2)]
                        if plate_crop.size == 0: continue
                        
                        preprocessed = self._preprocess_image(plate_crop)
                        ocr_results = reader.readtext(preprocessed, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                        
                        for (_, text, ocr_conf) in ocr_results:
                            if ocr_conf > 0.1:
                                raw_text = ''.join(e for e in text if e.isalnum()).upper()
                                if len(raw_text) < 7: continue
                                
                                # 3. Structural Analysis
                                corrected_text, struct_score = self._correct_plate_format(raw_text)
                                
                                # Combined Trust Score
                                trust_score = conf * aspect_weight * struct_score
                                
                                candidate = {
                                    "text": corrected_text,
                                    "raw": raw_text,
                                    "trust_score": trust_score,
                                    "yolo_conf": conf,
                                    "struct_score": struct_score,
                                    "aspect_ratio": round(aspect_ratio, 2)
                                }
                                
                                # Rejection Logging
                                if aspect_weight < 0.5:
                                    print(f"[VisionAgent] Reject: Invalid Aspect Ratio ({aspect_ratio:.1f}) for '{raw_text}'")
                                elif struct_score < 0.4:
                                    print(f"[VisionAgent] Reject: Low Structure Score ({struct_score:.2f}) for '{raw_text}'")
                                else:
                                    all_candidates.append(candidate)

        # 4. Final Winner Selection
        if not all_candidates:
            return {"license_plate": "UNKNOWN", "vehicle_type": "car", "confidence": "0.00", "trust_score": 0.0}

        # Sort by total trust score
        all_candidates.sort(key=lambda x: x['trust_score'], reverse=True)
        winner = all_candidates[0]
        
        print(f"[VisionAgent] Winner Assigned: {winner['text']} (Trust: {winner['trust_score']:.2f})")

        return {
            "license_plate": winner['text'],
            "vehicle_type": vehicle_type,
            "confidence": f"{winner['yolo_conf']:.2f}",
            "dimensions": {"width_m": 1.8, "size_class": "Medium"},
            "frames_processed": len(burst),
            "trust_score": round(winner['trust_score'], 2)
        }

    def _preprocess_image(self, image):
        """The core 5-stage image enhancement pipeline from methodology"""
        try:
            # Step 1: Resize (Height=64px)
            h, w = image.shape[:2]
            resized = cv2.resize(image, (int(w * (64.0 / h)), 64))
            # Step 2: Grayscale
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            # Step 3: CLAHE (Contrast)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl1 = clahe.apply(gray)
            # Step 4: Bilateral Filter (Denoise)
            bfilter = cv2.bilateralFilter(cl1, 11, 17, 17)
            # Step 5: Otsu Thresholding (Binarize)
            _, thresh = cv2.threshold(bfilter, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        except Exception as e:
            print(f"[VisionAgent] Preprocess error: {e}")
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _vote_consensus(self, results: List[str]) -> str:
        """Determine most likely string from multiple frames via character-level voting"""
        if not results: return ""
        
        # Normalize lengths (voting only works well on similar strings)
        # We take the most frequent length
        lengths = [len(s) for s in results]
        target_len = max(set(lengths), key=lengths.count)
        filtered = [s for s in results if len(s) == target_len]
        
        if not filtered: filtered = results # Fallback
        
        target_len = len(filtered[0])
        voted = []
        for i in range(target_len):
            chars = [s[i] for s in filtered if i < len(s)]
            # Pick most common char at this index
            voted.append(max(set(chars), key=chars.count))
        
        return "".join(voted)

        # Fallback to Full Image OCR if YOLO fails significantly
        if not best_plate_text and max_conf < 0.4:
            print("[VisionAgent] Low Confidence YOLO. Running Full Image OCR...")
            gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ocr_results = reader.readtext(gray_full, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            for text in ocr_results:
                clean = ''.join(e for e in text if e.isalnum()).upper()
                corrected = self._correct_plate_format(clean)
                if corrected:
                    best_plate_text = corrected
                    break
        
        # Optimized: Always return default dimensions (User Request: No vision-based sizing)
        best_dims = {"width_m": 1.8, "size_class": "Medium"} 

        return {
            "license_plate": best_plate_text if best_plate_text else "UNKNOWN",
            "vehicle_type": vehicle_type,
            "confidence": f"{max_conf:.2f}",
            "dimensions": best_dims
        }

    def _correct_plate_format(self, text: str) -> str | None:
        """
        Enforce Strict Format: TTNNTTNNNN (10 Chars) -> Output: TT NN TT NNNN
        """
        # 1. IND Prefix Stripping (Methodology Requirement)
        if text.startswith("IND"): text = text[3:]
        
        # 2. Cleanup
        text = ''.join(e for e in text if e.isalnum()).upper()
        
        # Mappings
        text_to_digit = {
            'O': '0', 'Q': '0', 'D': '0', 'U': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'B': '8', 'A': '4'
        }
        digit_to_text = {
            '0': "O", '1': 'I', '2': 'Z', '5': 'S', '6': 'G', '8': 'B', '4': 'A'
        }
        
        structure = [True, True, False, False, True, True, False, False, False, False]
        
        candidates = []
        
        # If length match (10), try direct correction
        if len(text) == 10:
            candidates.append(text)
        
        # If longer (11-13), try sliding window of 10
        elif len(text) > 10 and len(text) <= 13:
            for i in range(len(text) - 9):
                candidates.append(text[i : i+10])
                
        # Also try "IND" removal if not already handled
        if text.startswith("IND") and len(text) > 3:
             sub = text[3:]
             if len(sub) >= 10:
                 candidates.append(sub[:10])

        best_score = -1
        best_corrected = None
        
        for idx, candidate in enumerate(candidates):
            current_corrected = []
            score = 0
            valid = True
            print(f"[VisionAgent DEBUG] Candidate {idx}: {candidate}")
            
            for i, char in enumerate(candidate):
                expect_text = structure[i]
                
                if expect_text: # Indices 0,1, 4,5
                    if char.isalpha():
                        # Q is very rare in text positions (State/Series), but O is common.
                        # Visual similarity implies Q is likely a misread O (dirt/screw).
                        if char == 'Q':
                            current_corrected.append('O')
                            score += 0.9 # Corrected match
                        else:
                            current_corrected.append(char)
                            score += 1.0
                    elif char.isdigit():
                        if char in digit_to_text:
                            current_corrected.append(digit_to_text[char])
                            score += 0.9 # High confidence correction
                        else:
                            print(f"[VisionAgent DEBUG] Fail at {i} (Expect Text): {char}")
                            valid = False; break
                    else:
                         valid = False; break
                else: # Expect Digit # Indices 2,3, 6,7,8,9
                    if char.isdigit():
                        current_corrected.append(char)
                        score += 1.0
                    elif char.isalpha():
                        # Explicit user rule: Q -> 0 in number slots
                        if char == 'Q':
                            current_corrected.append('0')
                            score += 1.0 # Treat as almost perfect match due to user rule
                        elif char in text_to_digit:
                            current_corrected.append(text_to_digit[char])
                            score += 0.9 # High confidence correction
                        else:
                            print(f"[VisionAgent DEBUG] Fail at {i} (Expect Digit): {char}")
                            valid = False; break
                    else:
                        valid = False; break
            
            if valid:
                print(f"[VisionAgent DEBUG] Valid! Score: {score}")
                if score > best_score:
                    best_score = score
                    best_corrected = "".join(current_corrected)
            else:
                print(f"[VisionAgent DEBUG] Invalid Candidate")
                
        if best_corrected:
            final = best_corrected
            return f"{final[:2]} {final[2:4]} {final[4:6]} {final[6:]}", (best_score / 10.0)
            
        print("[VisionAgent DEBUG] No valid candidates found.")
        return text, 0.0
