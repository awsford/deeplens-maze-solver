from collections import namedtuple
import unittest
import json

from .app import lambda_handler

class TestMazeSolveFullApp(unittest.TestCase):
    def test_simple_maze(self):
        payload = {
            "image_path": "images/generated_simple.png",
            "image_dimensions": (400, 400),
            "solve_resolution": 30,
            "solve_start": [0, 0],
            "solve_end": [399, 399]
        }
        response = lambda_handler(payload)
        return

    def test_hard_maze(self):
        payload = {
            "image_path": "images/generated_hard.png",
            "image_dimensions": (400, 400),
            "solve_resolution": 30,
            "solve_start": [0, 0],
            "solve_end": [399, 399]
        }
        response = lambda_handler(payload)
        return

    def test_handdrawn_mazes(self):
        image_paths = [
            "images/example_1.png",
            "images/example_2.png",
            "images/example_3.png",
            "images/example_4.jpg"
        ]
        payload = {
            "image_dimensions": (600, 400),
            "solve_resolution": 30,
            "solve_start": [0, 0],
            "solve_end": [599, 399]
        }
        responses = []
        for image_path in image_paths:
            _payload = {"image_path": image_path, **payload}
            responses.append(lambda_handler(_payload))

        return

if __name__ == "__main__":
    unittest.main()
