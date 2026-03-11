from setuptools import setup, find_packages

setup(
    name="pv-optimizer",
    version="1.0.0",
    author="Omar Darwish",
    description="PV Self-Consumption Optimizer using Smart Appliance Scheduling",
    # Tell setup to find the 'src' folder as the main package
    packages=find_packages(), 
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "matplotlib>=3.4.0",
        "pygad>=3.0.0",
        "pyyaml>=5.4.0",
        "pytest>=6.2.0",
        "pytest-cov>=2.12.0",
        "plotly>=5.0.0"
    ],
    entry_points={
        "console_scripts": [
            # Point directly to the main function inside src/cli.py
            "pv-optimizer=src.cli:main", 
        ],
    },
)