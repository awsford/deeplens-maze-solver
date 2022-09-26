import uuid
import math
import time
import json
from PIL import Image
import matplotlib.pyplot as plt
from typing import Any, Dict, List
from numpy.typing import ArrayLike
from dataclasses import asdict, dataclass

from .helpers import SolveRequest
from .maze_solver import MazeSolver

IMAGE_DPI = 96
COLOUR_THRESHOLD = 140
AWS_LOGO_IMAGE = './function/awslogo.png'

awslogo = plt.imread(AWS_LOGO_IMAGE)

def lambda_handler(event: Any, context: Dict = {}) -> Dict:
    """
    INPUT: {
        "image_path": str,
        "image_dimensions": Tuple[int, int]
        "solve_resolution": int
        "solve_start": List[int, int]
        "solve_end": List[int, int]
    }
    """
    print("REQUEST", json.dumps(event))
    request = SolveRequest(**event)
    prefix = uuid.uuid4().hex[:8]

    # constrain maze points to within 1 resolution step from edge
    # request.solve_end[0] = max(request.solve_end[0], request.solve_resolution)
    # request.solve_end[1] = max(request.solve_end[1], request.solve_resolution)
    # request.solve_start[0] = min(request.solve_start[0], request.solve_resolution)
    # request.solve_start[1] = min(request.solve_start[1], request.solve_resolution)

    img = read_raw_image(request, prefix)
    # read thresholded image, purely black and white
    thr_img = plt.imread(f"/tmp/{prefix}_threshold.png", format='png')

    write_image(request, img, f"/tmp/{prefix}_unsolved.png")

    # start timer
    t1_start = time.perf_counter()

    solver = MazeSolver(thr_img, request)

    write_image(request, solver.skeleton, f"/tmp/{prefix}_skeleton.png")

    # actually solve the maze using BFS
    path_coords = solver.solve()

    # stop time
    t1_stop = time.perf_counter()
    elapsed = t1_stop - t1_start
    print(f"Elapsed time: {elapsed}")

    write_image(
        request, 
        img,
        f"/tmp/{prefix}_solved.png",
        pathX=[x[0] for x in path_coords],
        pathY=[y[1] for y in path_coords]
    )
    # save_to_s3(f"/tmp/{prefix}_solved.png", "s3://<bucket>/<key>")

    response = asdict(request)
    response["solution_image_path"] = "s3://<bucket>/<key>"
    response["solution_path"] = path_coords
    response["solution_time"] = elapsed

    return response


def read_raw_image(request: SolveRequest, prefix:str):
    img = Image.open(request.image_path)
    img = img.convert('L')  # convert to greyscale using single channel
    # normalise to black or white
    img = img.point(lambda p: 255 if p > COLOUR_THRESHOLD else 0)
    img = img.convert('1')  # to mono
    img = img.resize((request.image_dimensions[0], request.image_dimensions[1]))
    img.save(f"/tmp/{prefix}_threshold.png", format='png')
    return img

def write_image(
        request: SolveRequest,
        img: ArrayLike,
        path: str,
        pathX: List[int] = [],
        pathY: List[int] = []) -> None:
    
    # setup watermark
    dim = math.ceil(max(request.image_dimensions[1], request.image_dimensions[0]) / 8)
    watermark_image = Image.open('./function/awslogo.png')
    watermark_image = watermark_image.resize((dim, dim))

    # build figure with base image, route, start and end
    fig, ax = plt.subplots(figsize=(
        request.image_dimensions[0] / IMAGE_DPI,
        request.image_dimensions[1] / IMAGE_DPI
    ))
    plt.ion()
    ax.axis('off')
    ## original image
    ax.imshow(img, cmap='gray')
    ## route through
    ax.plot(pathX, pathY, 'r-', linewidth=5, color='#ff9900')
    # start marker
    plt.plot(request.solve_start[0], request.solve_start[1], '#FF00E6', markersize=10, marker='o')
    # end marker
    plt.plot(request.solve_end[0], request.solve_end[1], '#0066FF', markersize=10, marker='o')
    # watermark
    fig.figimage(watermark_image, 0, 0, zorder=3, alpha=.5, origin='upper')
    plt.close()
    fig.savefig(path, format='png', bbox_inches='tight', pad_inches=0, dpi=150)

def save_to_s3(path: str, key: str) -> None:
    return

