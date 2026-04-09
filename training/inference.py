"""
Dummy inference.py to match requested folder structure.
Actual inference happens in the root inference.py
"""
import sys
import os

# Delegate to the top-level inference.py
def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, root_dir)
    try:
        from inference import main as root_main
        root_main()
    except ImportError:
        print("Could not import main inference script.")

if __name__ == "__main__":
    main()
