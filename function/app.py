import uuid
import math
import time
from PIL import Image
import matplotlib.pyplot as plt
from typing import Any, Dict, List
from numpy.typing import ArrayLike

from function.maze_solver import MazeSolver

IMAGE_DPI = 96
COLOUR_THRESHOLD = 110
AWS_LOGO_IMAGE = './function/awslogo.png'

IMAGE_WIDTH = 400
IMAGE_HEIGHT = 400

SOLVE_RESOLUTION = 30


awslogo = plt.imread(AWS_LOGO_IMAGE)

def lambda_handler(event: Dict[str, Any], context: Dict) -> Dict:
    """
    INPUT: {
        "start_point": List[int],
        "end_point": List[int],
        "image_path": str
    }
    """
    prefix = uuid.uuid4().hex[:8]

    # constrain maze points to within 1 resolution step from edge
    if event["end_point"][1] < SOLVE_RESOLUTION: event["end_point"][1] = SOLVE_RESOLUTION
    if event["end_point"][0] < SOLVE_RESOLUTION: event["end_point"][0] = SOLVE_RESOLUTION

    img = read_raw_image(prefix, event["image_path"])
    # read thresholded image, purely black and white
    thr_img = plt.imread(f"/tmp/{prefix}_threshold.png", format='png')

    write_processed_image(img, event["start_point"], event["end_point"], f"/tmp/{prefix}_unsolved.png")

    # start timer
    t1_start = time.perf_counter()

    solver = MazeSolver(thr_img, event["start_point"], event["end_point"], SOLVE_RESOLUTION)

    write_processed_image(solver.skeleton, event["start_point"], event["end_point"], f"/tmp/{prefix}_skeleton.png")

    # actually solve the maze using BFS
    path_coords = solver.solve()

    # stop time
    t1_stop = time.perf_counter()
    elapsed = t1_stop - t1_start
    print(f"Elapsed time: {elapsed}")

    write_processed_image(
        img,
        event["start_point"],
        event["end_point"],
        f"/tmp/{prefix}_solved.png",
        pathX=[x[0] for x in path_coords],
        pathY=[y[1] for y in path_coords]
    )
    # save_to_s3(output_path, "s3://<bucket>/<key>")

    return {}


def read_raw_image(prefix:str, path: str):
    img = Image.open(path)
    img = img.convert('L')  # convert to greyscale using single channel
    # normalise to black or white
    img = img.point(lambda p: 255 if p > COLOUR_THRESHOLD else 0)
    img = img.convert('1')  # to mono
    img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT))
    img.save(f"/tmp/{prefix}_threshold.png", format='png')
    return img

def write_processed_image(
        img: ArrayLike,
        start: List[int],
        end: List[int],
        path: str,
        pathX: List[int] = [],
        pathY: List[int] = []) -> None:
    
    # setup watermark
    dim = math.ceil(max(IMAGE_HEIGHT, IMAGE_WIDTH) / 8)
    watermark_image = Image.open('./function/awslogo.png')
    watermark_image = watermark_image.resize((dim, dim))

    # build figure with base image, route, start and end
    fig, ax = plt.subplots(figsize=(IMAGE_WIDTH / IMAGE_DPI, IMAGE_HEIGHT / IMAGE_DPI))
    ax.axis('off')
    ## original image
    ax.imshow(img, cmap='gray')
    ## route through
    ax.plot(pathX, pathY, 'r-', linewidth=5, color='#ff9900')
    # start marker
    plt.plot(start[0] + 8, start[1] + 8, '#FF00E6', markersize=24, marker='o')
    # end marker
    plt.plot(end[0] - 8, end[1] - 8, '#0066FF', markersize=24, marker='o')
    # watermark
    fig.figimage(watermark_image, 0, 0, zorder=3, alpha=.5, origin='upper')
    fig.savefig(path, format='png', bbox_inches='tight', pad_inches=0, dpi=150)

def save_to_s3(path: str, key: str) -> None:
    return

