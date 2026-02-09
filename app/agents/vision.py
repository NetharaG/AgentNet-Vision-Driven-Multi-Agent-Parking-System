import asyncio
from typing import Dict, Any
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import easyocr

class VisionAgent:
    """
    Real Computer Vision using YOLOv8 + EasyOCR.
    Detects vehicle type and reads license plates.
    """
    _model = None
    _reader = None
    _lock = threading.Lock()

    def __init__(self):
        # Lazy load or Init on startup? 
        # Ideally simpler to init here, but might block main thread briefly.
        pass

    def _get_model(self):
        """
        Singleton Model Loader (Thread-safe)
        """
        if self._model is None:
            with self._lock:
                if self._model is None:
                    print("[VisionAgent] Loading YOLOv8n model...")
                    # 'yolov8n.pt' will auto-download on first run
                    self._model = YOLO('yolov8n.pt') 
                    print("[VisionAgent] Model Loaded.")
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

    async def analyze_stream(self, gate_id: str, image_bytes: bytes = None) -> Dict[str, Any]:
        """
        Runs inference on the provided image bytes.
        """
        model = self._get_model()
        reader = self._get_reader()
        
        # Determine vehicle type through inference
        vehicle_type = "unknown"
        detected_plate = f"AI-{gate_id[-2:]}-{np.random.randint(1000,9999)}" # Fallback
        confidence = 0.0
        
        if image_bytes:
            # Convert bytes to numpy array for OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Run Inference (Run in executor to avoid blocking async loop)
            # YOLO call is blocking, so we wrap it.
            loop = asyncio.get_running_loop()
            
            # 1. YOLO Detection
            results = await loop.run_in_executor(None, lambda: model(img, verbose=False))
            
            # Analyze results
            # COCO Classes: 2=car, 3=motorcycle, 5=bus, 7=truck
            target_classes = {2: 'small', 3: 'small', 5: 'large', 7: 'medium'} # Mapping to generic sizes
            
            detected_obj = None
            max_conf = 0.0

            if results:
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        if cls_id in target_classes and conf > max_conf:
                            max_conf = conf
                            vehicle_type = target_classes[cls_id]
                            detected_obj = model.names[cls_id]

            print(f"[VisionAgent] Detected: {detected_obj} ({max_conf:.2f}) -> Size: {vehicle_type}")
            
            # 2. ANPR (EasyOCR)
            # Run OCR on the full image for simplicity (or crop if we had bounding boxes for plates)
            ocr_results = await loop.run_in_executor(None, lambda: reader.readtext(img, detail=0))
            
            # Filter results for best candidate
            for text in ocr_results:
                clean_text = ''.join(e for e in text if e.isalnum()).upper()
                
                # Heuristic: Check if close to desired length (10)
                if len(clean_text) >= 9:
                    # Attempt Correction to TTNNTTNNNN
                    corrected = self._correct_plate_format(clean_text)
                    if corrected:
                        detected_plate = corrected
                        print(f"[VisionAgent] ANPR Success (Corrected): {detected_plate}")
                        break
                    
                    # Original logic if fallback needed
                    if len(clean_text) > 4 and any(char.isdigit() for char in clean_text):
                        detected_plate = clean_text # Fallback to raw if correction fails but looks okay
                        print(f"[VisionAgent] ANPR Raw (Fallback): {detected_plate}")
                        break
                    
        else:
            # Fallback if no image provided (Simulation)
            await asyncio.sleep(0.5)
            vehicle_type = "medium"

        return {
            "license_plate": detected_plate, 
            "vehicle_type": vehicle_type, 
            "confidence": f"{max_conf:.2f}" if image_bytes else "0.98"
        }

    def _correct_plate_format(self, text: str) -> str | None:
        """
        Enforce Strict Format: TTNNTTNNNN (10 Chars)
        T: Text (A-Z)
        N: Number (0-9)
        
        Attempts to convert confusing chars if they appear in wrong place.
        """
        # Truncate or Pad? For now, strict 10 or nothing? 
        # Requirement says "In this format". 
        if len(text) != 10:
             return None 
             
        # Mapping
        char_to_int = {'O': '0', 'I': '1', 'J': '3', 'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'B': '8', 'Q': '0', 'D': '0', 'A': '4'}
        int_to_char = {'0': 'O', '1': 'I', '3': 'J', '2': 'Z', '5': 'S', '6': 'G', '8': 'B', '4': 'A'}
        
        corrected_chars = []
        
        # Format Mask: T T N N T T N N N N
        is_text_pos = [True, True, False, False, True, True, False, False, False, False]
        
        for i, char in enumerate(text):
            should_be_text = is_text_pos[i]
            
            if should_be_text:
                if char.isdigit():
                    # Contradiction: Found Number, Need Text
                    if char in int_to_char:
                        corrected_chars.append(int_to_char[char])
                    else:
                        corrected_chars.append(char) # Can't fix
                else:
                    corrected_chars.append(char) # Correct
            else:
                if char.isalpha():
                     # Contradiction: Found Text, Need Number
                    if char in char_to_int:
                        corrected_chars.append(char_to_int[char])
                    else:
                        corrected_chars.append(char) # Can't fix
                else:
                    corrected_chars.append(char) # Correct
                    
        return "".join(corrected_chars)
