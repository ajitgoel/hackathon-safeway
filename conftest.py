"""
Root conftest.py — ensures the project root is on sys.path so that
modules like data_store, classifier, etc. are importable from tests/.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
