from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SolveRequest:
    image_path: str
    image_dimensions: Tuple[int, int]
    solve_resolution: int
    solve_start: List[int]
    solve_end: List[int]