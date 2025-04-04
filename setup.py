#!/usr/bin/env python
"""
Setup script for excel_db_excel_v2 package.
"""

from setuptools import setup, find_packages
import os

# Read version from __init__.py
with open(os.path.join('excel_db_excel_v2', '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip("'").strip('"')
            break
    else:
        version = '0.0.1'

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='excel_db_excel_v2',
    version=version,
    description='A modular system for processing Excel workbooks with formula and formatting preservation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/excel-processing-system',
    packages=find_packages(),
    install_requires=[
        'openpyxl>=3.1.0',
        'pandas>=1.3.0',
        'pyyaml>=6.0',  # Optional, for YAML config support
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
            'isort>=5.0.0',
            'mypy>=0.9.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'excel-processor=excel_db_excel_v2.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Office/Business :: Financial :: Spreadsheet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
)