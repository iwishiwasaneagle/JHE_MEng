from enum import IntEnum, unique, auto
from data_models.positional.waypoint import Waypoints, Waypoint
from data_models.probability_map import ProbabilityMap
from typing import TypeVar
T = TypeVar("T", bound="WaypointFactory")
@unique
class WaypointAlgorithmEnum(IntEnum):
    LHC_GW_CONV_E = auto()
    PARALLEL_SWATHS = auto()
    MODIFIED_LAWNMOWER  = auto()
    CONSTANT_SPEED = auto()
    NONE = auto()


class WaypointFactory:
    def __init__(self, alg: WaypointAlgorithmEnum, prob_map: ProbabilityMap, start: Waypoint):
        self.alg = alg
        self.prob_map = prob_map

        self.start = start
        self.end = None
    
    def setEnd(self, x:int, y:int) -> T:
        self.end = Waypoint(x,y)
        return self

    def generate(self) -> Waypoints:
        if self.alg == WaypointAlgorithmEnum.LHC_GW_CONV_E:
            from waypoint_generation.LHC_GW_CONV import LHC_GW_CONV
            return LHC_GW_CONV(self.prob_map, self.start, self.end).waypoints
