from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

# Definiamo il modulo C++
cpp_module = Pybind11Extension(
    'quant_engine',
    sources=['quant_engine.cpp'],
    language='c++',
    extra_compile_args=['-std=c++11'] # Standard C++ minimo richiesto
)

similarity_module = Pybind11Extension(
    "similarity_engine",
    sources=["similarity_engine.cpp"],
    language="c++",
    extra_compile_args=["-std=c++11"],
)

setup(
    name='quant_engine',
    version='1.0',
    description='Motore di calcolo C++ per Football Analytics',
    ext_modules=[cpp_module, similarity_module],
    cmdclass={'build_ext': build_ext},
)