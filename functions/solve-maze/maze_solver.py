from typing import List, Tuple
from skimage.morphology import skeletonize
import numpy as np

from .helpers import SolveRequest

class MazeSolver:
    def __init__(self, image: np.ndarray, request: SolveRequest):
        self.image = image
        self.skeleton = skeletonize(image)
        self.graph = ~self.skeleton
        self.start_point = request.solve_start
        self.end_point = request.solve_end
        self.resolution = request.solve_resolution

        self.pts_x = [0]
        self.pts_y = [0]
        self.pts_c = [0]

        self.distance_graph = np.zeros((self.graph.shape))
    
    def __euclidean_dist(self, x0: int, y0: int, x1: int, y1: int) -> float:
        return np.sqrt((x0 - x1)**2 + (y0 - y1)**2)

    def __find_end_node(self) -> None:
        # get all of the points within 1 resolution bound on the end point
        points = self.graph[
            self.end_point[1] - self.resolution : self.end_point[1] + self.resolution,
            self.end_point[0] - self.resolution : self.end_point[0] + self.resolution
        ]
        # check which points are valid paths to traverse
        cpys, cpxs = np.where(points == 0)

        # calibrate points to main scale.
        cpys += self.end_point[1] - self.resolution
        cpxs += self.end_point[0] - self.resolution

        # calculate the index value of closest end node
        idx = np.argmin(self.__euclidean_dist(cpys, cpxs, self.end_point[1], self.end_point[0]))

        # add node coords to graph
        self.pts_x = [cpxs[idx]]
        self.pts_y = [cpys[idx]]
    
    def __init_displacements(self):
        # mesh of displacements.
        self.xmesh, self.ymesh = np.meshgrid(np.arange(-1, 2), np.arange(-1, 2))
        self.xmesh = self.xmesh.flatten()
        self.ymesh = self.ymesh.flatten()
    
    def __get_neighbours(self, x: int, y: int) -> np.ndarray:
        # get nodes in a 3x3 grid around [y,x]
        neighbours = self.distance_graph[y-1:y+2, x-1:x+2]
        # mark self as visited
        neighbours[1, 1] = np.Inf
        # set empty paths as invalid destinations
        neighbours[neighbours == 0] = np.Inf
        return neighbours
    
    def __bread_first_search(self) -> None:
        while(self.pts_c != []):
            idc = np.argmin(self.pts_c)
            x = self.pts_x.pop(idc)
            y = self.pts_y.pop(idc)
            c = self.pts_c.pop(idc)

            # search 3x3 neighbourhood for possible next moves
            ys, xs = np.where(self.graph[
                y - 1 : y + 2,
                x - 1 : x + 2
            ] == 0)

            # invalidate these point from future searches
            self.graph[ys + y - 1, xs + x - 1] = c
            self.graph[y, x] = np.Inf

            self.distance_graph[ys + y-1, xs + x-1] = c + 1

            self.pts_x.extend(xs + x-1)
            self.pts_y.extend(ys + y-1)
            self.pts_c.extend([c + 1] * xs.shape[0])

            if self.__euclidean_dist(x, y, self.start_point[0], self.start_point[1]) < self.resolution:
                self.edx = x
                self.edy = y
                break
    
    def __trace_path(self) -> List[Tuple[int, int]]:
        x, y = self.edx, self.edy
        path_x, path_y = [], []

        while(True):
            neighbours = self.__get_neighbours(x, y)

            # if there is a deadend / no path
            # TODO: change this to an exception
            if np.min(neighbours) == np.Inf: break

            # get next node in path
            idx = np.argmin(neighbours)

            # determine direction to travel
            x += self.xmesh[idx]
            y += self.ymesh[idx]

            # check if node is near to the start point
            if self.__euclidean_dist(x, y, self.start_point[0], self.start_point[1]) < self.resolution: break

            path_x.append(x)
            path_y.append(y)

        return list(zip(path_x, path_y))
    
    def solve(self) -> List[Tuple[int, int]]:
        # translate from pixel space to grid coords
        self.__find_end_node()
        self.__init_displacements()
        
        # perform BFS until solution has been found
        self.__bread_first_search()
        # retrace the path BFS solution and convert to pixel space
        self.solved_path = self.__trace_path()
        return self.solved_path
