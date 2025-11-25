"""
Vercel serverless function entry point.
This file wraps the Flask application for Vercel's Python runtime.
"""
import os
import sys

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects the app to be named 'app' or 'handler'
# Flask apps work directly with Vercel's Python runtime

