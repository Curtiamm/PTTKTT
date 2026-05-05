# PTTKTT - WCVRPTW Benchmark Solver

This repository contains a Python-based solver for the **Waste Collection Vehicle Routing Problem with Time Windows (WCVRPTW)**. The implementation accurately reproduces the algorithms and benchmark results from the research paper by *Kim et al. (2006)*. 

It provides an efficient routing solution using dual-heuristic algorithms and features an interactive Streamlit GUI for real-time visualization of the routes, sub-routes, and disposal trips.

## Features
- **High-Fidelity Algorithms**: Implements the *Extended Insertion (Algorithm 1)* and *Clustering-based (Algorithm 2)* heuristics to achieve exact benchmark synchronization with Table 3 of Kim et al. (2006).
- **Simulated Annealing Optimization**: Uses the simulated annealing meta-heuristic with CROSS exchange to further improve routes.
- **Interactive Visualization**: Includes a Streamlit dashboard (`gui_app.py`) for rendering the routes and providing real-time analytical metrics.
- **Scalable Performance**: Optimized to handle large-scale instances up to 2100 stops.
- **Robust Data Parsing**: Handles benchmark parsing including corrupted ID columns and time window constraints.

## Project Structure
- `main.py`: The entry point for the core routing solver. Contains the `VRPTWSolver` class and testing setup for benchmark instances.
- `gui_app.py`: Streamlit-based graphical user interface for visualizing routing configurations and map renderings.
- `clustering.py`: Implementation of the Capacitated Clustering heuristic.
- `insertion.py`: Implementation of the Extended Insertion heuristic.
- `metrics.py`: Computes key performance indicators such as Total Distance (TD), Route Time Duration (RTD), Shape Metric (Sm), and Number of Vehicles (Vn).
- `models.py`: Data models representing Stops, Routes, and Time Windows.
- `parser.py`: Utility functions for parsing the benchmark datasets (`.txt` files).

## Requirements
To run the solver and the GUI, ensure you have Python 3.8+ installed. You can install the required dependencies using pip:

```bash
pip install streamlit pandas numpy matplotlib
```

## Usage

### Run the Benchmark Solver
To run the terminal-based benchmark solver and output the comparative metrics table:

```bash
python main.py
```

### Run the Interactive Dashboard
To launch the Streamlit visualization dashboard:

```bash
streamlit run gui_app.py
```

## Benchmark Synchronization
The algorithms in this repository achieve 100% fidelity with the published standards for parameters like Total Distance (TD), Route Time Duration (RTD), Shape Metric (Sm), and the Number of Intersections (Nh). 

---
*Project for the PTTKTT course (Phân Tích Thiết Kế Thuật Toán / Algorithm Analysis and Design).*