from skimage.morphology import skeletonize
import numpy as np
from PIL import Image
import sys 
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import uuid

prefix = uuid.uuid4().hex
dpi=96

if(len(sys.argv)!=2):
    sys.exit("Usage:\nmaze_solver.py [Input Image]")

arg = sys.argv[1]
threshold = 110

image_file = Image.open(arg)
# Grayscale instead of using single channel (see comments below)
image_file = image_file.convert('L')
# Threshold
image_file = image_file.point( lambda p: 255 if p > threshold else 0 )
# To mono
image_file = image_file.convert('1')

img = image_file.resize((600,400))

img.save("/tmp/"+ prefix + "resize.png")

rgb_img = plt.imread("/tmp/"+ prefix + "resize.png")
awslogo = plt.imread('./awslogo.png')
plt.figure(figsize=(600/dpi,400/dpi))
fig = plt.figure(figsize=(600/dpi,400/dpi))
ax = plt.Axes(fig, [0., 0., 1., 1.])
ax.set_axis_off()
fig.add_axes(ax)
plt.imshow(rgb_img, cmap='gray')


x0,y0 = 0,0
x1,y1 = 599,399

plt.plot(x0+20,y0+20, '#003181', markersize = 15, marker = '>')
plt.plot(x1-15,y1-25, '#003181', markersize = 25, marker = '*')
plt.imshow(awslogo,cmap='jet',alpha=0.9)
plt.savefig("/tmp/"+ prefix + "resize.png")

thr_img = rgb_img
skeleton = skeletonize(thr_img)
plt.imshow(skeleton, cmap='gray')

# Create a map of routes through
#map of routes.
mapT = ~skeleton
plt.plot(x0+20,y0+20, '#003181', markersize = 15, marker = '>')
plt.plot(x1-15,y1-25, '#003181', markersize = 25, marker = '*')
plt.imshow(awslogo,cmap='jet',alpha=0.9)
plt.savefig("/tmp/"+ prefix + "start_end.png")
_mapt = np.copy(mapT)

#searching for our end point and connect to the path.
boxr = 30

#Just a little safety check, if the points are too near the edge, it will error.
if y1 < boxr: y1 = boxr
if x1 < boxr: x1 = boxr

cpys, cpxs = np.where(_mapt[y1-boxr:y1+boxr, x1-boxr:x1+boxr]==0)
#calibrate points to main scale.
cpys += y1-boxr
cpxs += x1-boxr
#find clooset point of possible path end points
idx = np.argmin(np.sqrt((cpys-y1)**2 + (cpxs-x1)**2))
y, x = cpys[idx], cpxs[idx]

pts_x = [x]
pts_y = [y]
pts_c = [0]

#mesh of displacements.
xmesh, ymesh = np.meshgrid(np.arange(-1,2),np.arange(-1,2))
ymesh = ymesh.reshape(-1)
xmesh = xmesh.reshape(-1)

dst = np.zeros((thr_img.shape))
               
#Breath first algorithm exploring a tree
while(True):
    #update distance.
    idc = np.argmin(pts_c)
    ct = pts_c.pop(idc)
    x = pts_x.pop(idc)
    y = pts_y.pop(idc)
    #Search 3x3 neighbourhood for possible
    ys,xs = np.where(_mapt[y-1:y+2,x-1:x+2] == 0)
    #Invalidate these point from future searchers.
    _mapt[ys+y-1, xs+x-1] = ct
    _mapt[y,x] = 9999999
    #set the distance in the distance image.
    dst[ys+y-1,xs+x-1] = ct+1
    #extend our list.s
    pts_x.extend(xs+x-1)
    pts_y.extend(ys+y-1)
    pts_c.extend([ct+1]*xs.shape[0])
    #If we run of points.
    if pts_x == []:
        break
    if np.sqrt((x-x0)**2 + (y-y0)**2) <boxr:
        edx = x
        edy = y
        break
plt.figure(figsize=(600/dpi,400/dpi))
fig = plt.figure(figsize=(600/dpi,400/dpi))
ax = plt.Axes(fig, [0., 0., 1., 1.])
ax.set_axis_off()
fig.add_axes(ax)
plt.imshow(dst, cmap='gray')

path_x = []
path_y = []

y = edy
x = edx
#Traces best path
while(True):
    nbh = dst[y-1:y+2,x-1:x+2]
    nbh[1,1] = 9999999
    nbh[nbh==0] = 9999999
    #If we reach a deadend
    if np.min(nbh) == 9999999:
        break
    idx = np.argmin(nbh)
    #find direction
    y += ymesh[idx]
    x += xmesh[idx]
    
    if np.sqrt((x-x1)**2 + (y-y1)**2) < boxr:
        print('Optimum route found.')
        break
    path_y.append(y)
    path_x.append(x)

fig = plt.figure(figsize=(600/dpi,400/dpi))
ax = plt.Axes(fig, [0., 0., 1., 1.])

ax.set_axis_off()
fig.add_axes(ax)
plt.imshow(rgb_img, cmap='gray')
plt.plot(path_x,path_y, 'r-', linewidth=5,color='#ff9900')
plt.plot(x0+20,y0+20, '#003181', markersize = 15, marker = '>')
plt.plot(x1-15,y1-25, '#003181', markersize = 25, marker = '*')

plt.imshow(awslogo,cmap='jet',alpha=0.9)

plt.savefig("/tmp/"+ prefix + "solved.png")