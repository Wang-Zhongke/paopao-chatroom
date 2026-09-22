#!/usr/bin/env python3
"""Compatibility entry point; canonical evaluator lives inside the Skill."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'paopao-perspective-skill/scripts/eval_persona.py'), run_name='__main__')
