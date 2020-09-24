from src.waypoint_generation.base_wp_generator import BaseWPGenerator
from src.data_models.probability_map import ProbabilityMap
from src.data_models.positional.waypoint import Waypoint,Waypoints
from src.simulation.parameters import *

import matplotlib.pyplot as plt
import numpy as np
import time
import multiprocessing
from enum import IntEnum

from typing import List

class ConvolutionType(IntEnum):
    LARGE = 3
    MEDIUM = 2
    SMALL = 1
    HYUGE = 4

class ConvolutionResult:
    def __init__(self,pos:Waypoint,value:float,n:int):
        self.pos = pos 
        self.value = value 
        self.n = n
    @property
    def bounds(self) -> List[Waypoint]:
        const = int((self.n-1)/float(2))
        lower_x = self.pos.x - const
        upper_x = self.pos.x + const 
        lower_y = self.pos.y - const 
        upper_y = self.pos.y + const
        return [Waypoint(lower_x, lower_y), Waypoint(upper_x, upper_y)]
    def __getitem__(self,key):
        if key == 0:   return self.pos
        elif key == 1: return self.value 
        elif key == 2: return self.n
        else :         raise IndexError(f"{key} > 2")

class LHC_GW_CONV(BaseWPGenerator):
    def __init__(self, prob_map: ProbabilityMap, start: Waypoint, end:Waypoint = None, l:int=100, animate: bool = animate, threaded: bool = True):
        super().__init__()

        self.prob_map = prob_map
        self.start = start
        self.end = end
        self.l = l
        self.search_threshold = 0

        self.threaded = threaded
        self.animate = not self.threaded and animate

        if self.animate:
            plt.ion()
            fig = plt.figure()
            # for stopping simulation with the esc key.
            fig.canvas.mpl_connect('key_release_event',
                    lambda event: [exit(0) if event.key == 'escape' else None])

            self._ax = fig.add_subplot(111)

    @property
    def waypoints(self):
        return self.GW()

    def _inf(self) -> int:
        i = -1
        while True:
            if i>2500:
                break
            yield (i:=i+1)

    def GW(self) -> Waypoints:
        l_iterator = range(5,self.l)
        t = time.time()
        return_dict = {}
        if self.threaded:
            print("Starting GW w/ threading")
            manager = multiprocessing.Manager()
            return_dict = manager.dict()
            jobs = []

            for l in l_iterator:
                p = multiprocessing.Process(target=self.LHC_CONV, args=(l,return_dict))
                jobs.append(p)
                p.start()
        
            for proc in jobs:
                proc.join()

            print(f"\nFinished GW w/ threading. Time taken: {time.time()-t:.2f}s")
        else:
            print("Starting GW w/o threading")
            for l in l_iterator:
                return_dict[l] = self.LHC_CONV(l,return_dict)
                
            print(f"\nFinished GW w/o threading. Time taken: {time.time()-t:.2f}s")

        best_l = None
        best_wps = None
        best_prob = 0
        for key in return_dict:
            l = key
        for key in return_dict:
            l = key
            wps = return_dict[key]

            probability = self.calc_prob(wps)
            if probability > best_prob:
                best_prob = probability
                best_wps = wps
                best_l = l

        print(f"l={l} had {100*best_prob/float(self.prob_map.sum):.2f}% efficiency with {len(wps)} waypoints")
        return best_wps

    def LHC_CONV(self,l=0, ret_dict: dict={}) -> Waypoints:
        print(f"({l})\tStarting LHC_CONV with l={l}")
        wps = []
        accumulator = 0
        visited = []

        cur = self.start
        t = time.time()

        C = self.prob_map.max/float(l)
        temp_prob_map = ProbabilityMap(np.clip(self.prob_map.prob_map - C, 0, None))
        conflicts = 0
        for i in self._inf():
            plt.cla()
            neighbours = np.array(self.neighbours(cur, visited, temp_prob_map))
            if i%100 == 0:
                end='\n'
                if not self.threaded: end='\r'
                print(f"({l})\tProgress: i={i}", end=end)
            try:
                best = None
                while best is None:
                    inds = np.where(neighbours[:,1]==np.max(neighbours[:,1]))[0]
                    ind = inds[0] # default

                    if len(inds) > 1 or np.max(neighbours[:,1]) < self.search_threshold: # More than 1 "best" probability was found
                        ind = None
                        convs = [ConvolutionType.SMALL,ConvolutionType.MEDIUM,ConvolutionType.LARGE]
                        if np.max(neighbours[:,1]) <= self.search_threshold:
                            convs = [ConvolutionType.HYUGE] 
                        conv_c = 0
                        while ind is None:
                            conv_probs = np.array([self.convolute(neighbours[f][0],visited,temp_prob_map,convs[conv_c]) for f in inds])

                            conv = [f.value for f in conv_probs]
                            conv_max = np.max(conv)
                            inds2 = np.where(conv==conv_max)
                            
                            if self.animate:
                                for f in conv_probs:
                                    self._ax.add_artist(plt.Rectangle(f.bounds[0], f.n, f.n,fill=False, color=(f.value==conv_max,0,f.value!=conv_max)))
                                    if f.value==conv_max:
                                        self._ax.add_artist(plt.Arrow(cur.x, cur.y, 3*(f.pos.x-cur.x), 3*(f.pos.y-cur.y)))

                            if len(inds2) == 1:
                                ind = inds2[0][0]
                            else:
                                conv_c +=1
                            conflicts += 1

                    potential_best = neighbours[ind]

                    validated = self.validate(potential_best[0], visited, temp_prob_map) 
                    if validated or len(neighbours) == 1:
                        best = potential_best
                    else:
                        neighbours = np.delete(neighbours,ind,0)
                    
                    if self.animate: 
                       self._plot(cur, neighbours, potential_best[0], visited, temp_prob_map)
            except IndexError as e:
                break

            accumulator += best[1]
            best = best[0]
            wps.append(best)

            cur = wps[-1]
            visited.append(best)
           
        print(f"({l})\tCompleted in {time.time()-t:.3f}s with local score {accumulator:.1f} and {conflicts} conflicts")

        if self.threaded:
            ret_dict[l] = Waypoints(wps)
        else: 
            return Waypoints(wps)

    def convolute(self, pos: Waypoint, visited: Waypoints, prob_map: ProbabilityMap, conv_type: ConvolutionType):
        kernel = None
        n = 0
        if conv_type is ConvolutionType.SMALL:
            n = 3
        elif conv_type is ConvolutionType.MEDIUM:
            n = 5
        elif conv_type is ConvolutionType.LARGE:
            n = 7
        elif conv_type is ConvolutionType.HYUGE:
            n = 11
        else:
            raise TypeError(f"Unknown ConvolutionType: {type(conv_type)} with value {conv_type}")
        
        kernel = np.ones((n,n))

        sum_ = 0
        shift = int((n-1)/2)

        c = 1
        for i in range(n):
            for j in range(n):
                iprime, jprime =(i-shift, j-shift) 

                if (iprime,jprime) == (0,0): continue

                eval_pos = Waypoint(pos.x+iprime,pos.y+jprime)
                if eval_pos in visited: continue


                prob = prob_map[eval_pos] * kernel[i,j] 

                sum_ += prob
                c += 1
        return ConvolutionResult(pos,sum_/float(c),n)

    def validate(self, pos: Waypoint, visited: Waypoints, prob_map: ProbabilityMap):
        return len(self.neighbours(pos, visited, prob_map)) > 0 # True if 1 or more valid position exists
    
    def neighbours(self, pos: Waypoint, visited: Waypoints, prob_map: ProbabilityMap):
        neighbours = self.surrounding_grid(pos)
        return [(f, prob_map[f]) for f in neighbours if min(f) >= 0 and f.x < prob_map.shape[0] and f.y < prob_map.shape[1] if f not in visited]

    def calc_prob(self,wps: Waypoints) -> float:
        accumulator = 0
        if not isinstance(wps, Waypoints): 
            raise TypeError(f"wps is type {type(wps)} and not {Waypoints}")
        for wp in wps:
            accumulator += self.prob_map[wp]
        return accumulator

    def surrounding_grid(self, pos: Waypoint) -> list:
        tmp = [
            (-1, -1),
            (1, -1),
            ( 0,-1),
            (-1,1),
            (1,1),
            ( 0, 1),
            (-1, 0),
            ( 1, 0),
        ]
        return [Waypoint(pos.x+f[0],pos.y+f[1]) for f in tmp]
    
    def _plot(self, cur:Waypoint, neighbours: Waypoints, best: Waypoint, visited: Waypoints, prob_map: ProbabilityMap) -> None:
        # plt.cla()
        if len(visited) > 0:
            visited = np.array(visited)
            self._ax.plot(visited[:,0],visited[:,1], color='r')

        for i in neighbours:
            self._ax.add_artist(plt.Circle(i[0], size, color='b'))

        self._ax.add_artist(plt.Circle((cur.x,cur.y), size, color='r'))
        self._ax.add_artist(plt.Circle(best, size, color='g'))
        img = prob_map.toIMG()
        plt.imshow(img, origin='upper')
        plt.xlim(0,img.size[0])
        plt.ylim(0,img.size[1])

        plt.pause(0.001)
       

def main():
    import matplotlib.pyplot as plt
    wps = LHC_GW_CONV(ProbabilityMap.fromPNG("waypoint_generation/probs_map_1.png"), Waypoint(0,0)).LHC()

    plt.figure()
    plt.imshow(wps.prob_map.img.rotate(90))
    plt.show()

    print(wps)
