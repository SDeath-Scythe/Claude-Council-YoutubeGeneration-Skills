"""Set C: 600 template-generated DMs (seeded). usage: python3 fuzz.py <output dir>"""
import sys, os, random, json, re, importlib, signal
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from grade import norm, gov_key  # noqa  (grade.py runs on import, so guard below)
