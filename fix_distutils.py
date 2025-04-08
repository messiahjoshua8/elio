# Fix for missing distutils in Python 3.13
import sys
import importlib.metadata

sys.modules['distutils'] = importlib.import_module('setuptools._distutils')
sys.modules['distutils.version'] = importlib.import_module('setuptools._distutils.version')
sys.modules['distutils.errors'] = importlib.import_module('setuptools._distutils.errors')
sys.modules['distutils.util'] = importlib.import_module('setuptools._distutils.util') 