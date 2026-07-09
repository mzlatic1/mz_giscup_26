"""Convenience script for a small sample solve."""

from giscup.solver import solve_one
from giscup.output import format_solution_file

if __name__ == "__main__":
    solution = solve_one("data/GIS-cup-sample-dataset.geojson", tau=0.25, k=50, max_candidates=1000)
    print(format_solution_file([solution]))
