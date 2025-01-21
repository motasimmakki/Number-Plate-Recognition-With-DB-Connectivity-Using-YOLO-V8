# Specify the paths to the local model directories
det_model_dir = "./en_PP-OCRv3_det_infer"  # Path to detection model
rec_model_dir = "./en_PP-OCRv3_rec_infer"  # Path to recognition model
cls_model_dir = "./ch_ppocr_mobile_v2.0_cls_infer"  # Path to classification model

# Initialize the OCR system with local models
self.ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    det_model_dir=det_model_dir,
    rec_model_dir=rec_model_dir,
    cls_model_dir=cls_model_dir
)