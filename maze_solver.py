from skimage.morphology import skeletonize
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import uuid

IMAGE_DPI = 96
IMAGE_PATH = "./images/example_1.png"

COLOUR_THRESHOLD = 110

COORDS_START = [0, 0] # top left
COORDS_END = [599, 399] # bottom right

RESOLUTION = 30

def euclidean_dist(x0, y0, x1, y1):
    return np.sqrt((x0 - x1)**2 + (y0 - y1)**2)

prefix = uuid.uuid4().hex

image_file = Image.open(IMAGE_PATH)
image_file = image_file.convert('L') # convert to greyscale using single channel
image_file = image_file.point(lambda p: 255 if p > COLOUR_THRESHOLD else 0) # normalise to black and white
image_file = image_file.convert('1') # to mono
image_file = image_file.resize((600, 400))
image_file.save(f"/tmp/resize.png")

awslogo = plt.imread('./images/awslogo.png')
thr_img = plt.imread(f"/tmp/resize.png")
skeleton = skeletonize(thr_img)

# Create a map of routes
mapT = ~skeleton
_mapT = np.copy(mapT)

# Just a little safety check, if the points are too near the edge, it will error.
if COORDS_END[1] < RESOLUTION: COORDS_END[1] = RESOLUTION
if COORDS_END[0] < RESOLUTION: COORDS_END[0] = RESOLUTION

cpys, cpxs = np.where(_mapT[
    COORDS_END[1] - RESOLUTION : COORDS_END[1] + RESOLUTION,
    COORDS_END[0] - RESOLUTION : COORDS_END[0] + RESOLUTION
] == 0)

# calibrate points to main scale.
cpys += COORDS_END[1] - RESOLUTION
cpxs += COORDS_END[0] - RESOLUTION

# find closest point of possible path end points
idx = np.argmin(euclidean_dist(cpys, cpxs, COORDS_END[1], COORDS_END[0]))
y, x = cpys[idx], cpxs[idx]

pts_x = [x]
pts_y = [y]
pts_c = [0]

# mesh of displacements.
xmesh, ymesh = np.meshgrid(np.arange(-1, 2), np.arange(-1, 2))
ymesh = ymesh.reshape(-1)
xmesh = xmesh.reshape(-1)

dst = np.zeros((thr_img.shape))

# Breath first algorithm exploring a tree
while(True):
    # update distance.
    idc = np.argmin(pts_c)
    x = pts_x.pop(idc)
    y = pts_y.pop(idc)
    ct = pts_c.pop(idc)

    # Search 3x3 neighbourhood for possible next moves
    ys, xs = np.where(_mapT[y-1:y+2, x-1:x+2] == 0)

    # Invalidate these point from future searches.
    _mapT[ys+y-1, xs+x-1] = ct
    _mapT[y, x] = 9999999

    # set the distance in the distance image.
    dst[ys + y-1, xs + x-1] = ct + 1

    # extend our lists
    pts_x.extend(xs + x-1)
    pts_y.extend(ys + y-1)
    pts_c.extend([ct+1] * xs.shape[0])

    # if we run of points.
    if pts_x == []: break
    if euclidean_dist(x, y, COORDS_START[0], COORDS_START[1]) < RESOLUTION:
        edx = x
        edy = y
        break

path_x = []
path_y = []

y = edy
x = edx

# Traces best path
while(True):
    nbh = dst[y-1:y+2, x-1:x+2]
    nbh[1, 1] = 9999999
    nbh[nbh == 0] = 9999999

    # if we reach a deadend
    if np.min(nbh) == 9999999: break

    idx = np.argmin(nbh)

    # find direction
    y += ymesh[idx]
    x += xmesh[idx]

    if euclidean_dist(x, y, COORDS_START[0], COORDS_START[1]) < RESOLUTION: break
    path_y.append(y)
    path_x.append(x)



fig = plt.figure(figsize=(600/IMAGE_DPI, 400/IMAGE_DPI))
ax = plt.Axes(fig, [0., 0., 1., 1.])

ax.set_axis_off()
fig.add_axes(ax)
plt.imshow(image_file, cmap='gray')
plt.plot(path_x, path_y, 'r-', linewidth=5, color='#ff9900')
plt.plot(COORDS_START[0]+20, COORDS_START[1]+20,
         '#003181', markersize=15, marker='>')
plt.plot(COORDS_END[0]-15, COORDS_END[1]-25,
         '#003181', markersize=25, marker='*')

plt.imshow(awslogo, cmap='jet', alpha=0.9)

plt.savefig(f"./_{prefix}_solved.png")
