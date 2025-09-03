#!/usr/bin/env python3
"""
Setup script for Lead Finder system.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="lead-finder",
    version="1.0.0",
    author="Lead Finder Team",
    author_email="info@example.com",
    description="Find broken/outdated websites that need fixing",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/example/lead-finder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
    },
    entry_points={
        "console_scripts": [
            "lead-finder=cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="lead-generation, website-analysis, seo, performance, wordpress, web-development",
    project_urls={
        "Bug Reports": "https://github.com/example/lead-finder/issues",
        "Source": "https://github.com/example/lead-finder",
        "Documentation": "https://github.com/example/lead-finder#readme",
    },
) 