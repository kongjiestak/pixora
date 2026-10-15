"""Pixora configuration with APM environment migration compatibility."""
import os

def setting(name, default=""):
    return os.getenv("PIXORA_" + name, os.getenv("APM_" + name, default))
