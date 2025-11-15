from setuptools import setup, find_packages

setup(
    name="hydroclaude-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
    ],
)
