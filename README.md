# 🎓 PV Self-Consumption Optimizer

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)

A production-ready Python application designed to optimize household appliance schedules, maximizing photovoltaic (PV) self-consumption. Developed as a Bachelor Thesis project in the MET department at GUC.

## 📌 Project Overview

As renewable energy adoption grows, maximizing the self-consumption of rooftop solar PV systems is critical for grid stability and financial savings. This tool ingests household energy load and PV generation data, cleans it, and applies advanced search algorithms (Genetic Algorithm and Brute-Force) to find the absolute most cost-effective schedule for shiftable appliances.

## 🚀 Features

- **Robust Data Pipeline:** Handles missing timestamps, interpolates gaps, and formats raw CSV data.
- **Genetic Algorithm (GA):** Utilizes `pygad` for scalable, high-performance scheduling of multiple appliances.
- **Financial Evaluation:** Calculates self-consumption, self-sufficiency, and exact monetary savings.
- **Thesis-Ready Visualizations:** Generates high-DPI, publication-ready load comparison graphs.

## 📖 Documentation

- [User Guide](docs/user_guide.md) - Full setup and installation instructions.
- [Walkthrough Example](docs/example.md) - A step-by-step look at the optimization in action.

## 💻 Quick Start

```bash
# Clone and enter the directory
python -m venv venv
# Activate environment (Windows: .\venv\Scripts\activate | Mac/Linux: source venv/bin/activate)

# Install the package
pip install -e .

# Run the optimizer
pv-optimizer
```
