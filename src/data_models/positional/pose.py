from src.data_models.positional.waypoint import Waypoint
from .abstractPositionDataObjects import AbstractPositionDataObject
from typing import Type, TypeVar
T = TypeVar('T', bound='Pose')

class Pose(AbstractPositionDataObject):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x,y)
    
    @staticmethod
    def zero() -> T:
        return Pose(0,0)
    @staticmethod
    def fromWP(WP: Waypoint) -> T:
        return Pose(WP.x, WP.y)