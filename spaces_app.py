"""
LifeOS — HuggingFace Spaces entry point.

This is a thin wrapper that launches the Gradio app from spaces/app.py.
Required by some HF Spaces configurations that expect an app at the root.
"""
import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(__file__))

from spaces.app import demo

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
