from distutils.core import setup
import py2exe

setup(console=['nayadra.py'], options={"py2exe": {"includes": ["ctypes", "logging"], "excludes": ["OpenGL"]}})
