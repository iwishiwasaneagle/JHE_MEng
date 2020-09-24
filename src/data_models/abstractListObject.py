from typing import TypeVar, List
T = TypeVar('T',bound='AbstractListObject')

class AbstractListObject:
    def __init__(self,list_) -> None:
        self.items: List = list_

    def __getitem__(self,key: int) -> T:
        if key<self.__len__():
            return self.items[key]
        else:
            raise IndexError()

    def __iter__(self) -> T:
        self._n = 0
        return self

    def __next__(self) -> T:
        if self._n<self.__len__():
            result = self.items[self._n]
            self._n += 1
            return result
        else:
            raise StopIteration

    def __len__(self) -> None:
        return len(self.items)

    def add(self,item:T)-> None:
        self.items.append(item)
