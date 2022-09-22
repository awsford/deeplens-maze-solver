from collections import namedtuple
import unittest
import logging
import os
import sys

from .app import lambda_handler

class TestMazeSolveFullApp(unittest.TestCase):
    def test_simple_maze(self):
        payload = {
            "image_path": "images/generated_simple.png",
            "image_dimensions": (600, 400),
            "solve_resolution": 30,
            "solve_start": [0, 0],
            "solve_end": [599, 399]
        }
        response = lambda_handler(payload, lambda_context())
        return
    
    def test_hard_maze(self):
        payload = {
            "image_path": "images/generated_hard.png",
            "image_dimensions": (600, 400),
            "solve_resolution": 30,
            "solve_start": [0, 0],
            "solve_end": [599, 399]
        }
        response = lambda_handler(payload, lambda_context())
        return


def lambda_context():
    lambda_context = {
        "function_name": "test",
        "memory_limit_in_mb": 128,
        "invoked_function_arn": "arn:aws:lambda:eu-west-1:111111111111:function:test",
        "aws_request_id": "52fdfc07-2182-154f-163f-5f0f9a621d72",
    }

    return namedtuple("LambdaContext", lambda_context.keys())(*lambda_context.values())
    
if __name__ == "__main__":
    unittest.main()