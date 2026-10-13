import sys
import traceback

print("Testing onnxruntime import...")
try:
    import onnxruntime
    print(f"onnxruntime version: {onnxruntime.__version__}")
except Exception as e:
    print("FAILED to import onnxruntime:")
    traceback.print_exc()
