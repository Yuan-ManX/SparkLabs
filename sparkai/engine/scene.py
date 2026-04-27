"""
SparkAI Engine - Scene and Entity Python Interface

Re-exports from engine.py for backward compatibility.
"""

from sparkai.engine.engine import SparkEngine, Scene, SceneEntity

__all__ = ["SparkEngine", "Scene", "SceneEntity"]
