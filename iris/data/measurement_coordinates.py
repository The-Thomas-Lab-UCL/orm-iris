import sys
import os

from dataclasses import dataclass
import pickle
from typing import Callable, Self
import pandas as pd
from random import random

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

@dataclass
class MeaCoor_mm:
    """
    A dataclass to store the mapping coordinates for the mapping measurement.
    
    Attributes:
        mappingUnit_name: str: The name of the mapping unit.
        mapping_coordinates: list[tuple[float, float, float]]: The coordinates for the mapping measurement.
    """
    mappingUnit_name: str
    mapping_coordinates: list[tuple[float, float, float]]
    
    def __init__(self, mappingUnit_name:str|None=None, mapping_coordinates:list[tuple[float, float, float]]|None=None,
                 loadpath:str|None=None):
        """
        Initialises the mapping coordinates dataclass.
        
        Args:
            mappingUnit_name (str|None): The name of the mapping unit. Defaults to None.
            mapping_coordinates (list[tuple[float, float, float]]|None): The coordinates for the mapping measurement. Defaults to None.
            loadpath (str|None): The path to load the coordinates from. Defaults to None.
        """
        if loadpath is None:
            if not isinstance(mappingUnit_name, str): raise TypeError(f"Expected str, got {type(mappingUnit_name)}")
            if not isinstance(mapping_coordinates, list) or not all(isinstance(coord, tuple) and len(coord) == 3 for coord in mapping_coordinates):
                raise TypeError(f"Expected list of tuples, got {type(mapping_coordinates)}")
            
            self.mappingUnit_name = mappingUnit_name
            self.mapping_coordinates = mapping_coordinates
        else:
            assert os.path.exists(loadpath), f"File {loadpath} does not exist"
            if loadpath.endswith('.csv'):
                self.load_csv(loadpath)
            elif loadpath.endswith('.pkl'):
                self.load_pickle(loadpath)
        
    def save_csv(self, filename:str):
        """
        Saves the mapping coordinates to a CSV file.
        
        Args:
            filename (str): The name of the file to save the coordinates to.
        """
        if not isinstance(filename, str): raise TypeError(f"Expected str, got {type(filename)}")
        if not filename.endswith('.csv'): filename += '.csv'
        df = pd.DataFrame(self.mapping_coordinates, columns=['x', 'y', 'z'])
        df.to_csv(filename, index=False)
        
    def load_csv(self, filename:str):
        """
        Loads the mapping coordinates from a CSV file.
        
        Args:
            filename (str): The name of the file to load the coordinates from.
        """
        if not isinstance(filename, str): raise TypeError(f"Expected str, got {type(filename)}")
        if not filename.endswith('.csv'): filename += '.csv'
        df = pd.read_csv(filename)
        if df.shape[1] != 3:
            raise ValueError(f"CSV file {filename} does not have exactly 3 columns")
        self.mapping_coordinates = [tuple(row) for row in df.to_numpy()]
        self.mappingUnit_name = os.path.splitext(os.path.basename(filename))[0]
        
    def save_pickle(self, filename:str):
        """
        Saves the mapping coordinates to a pickle file.
        
        Args:
            filename (str): The name of the file to save the coordinates to.
        """
        if not isinstance(filename, str): raise TypeError(f"Expected str, got {type(filename)}")
        if not filename.endswith('.pkl'): filename += '.pkl'
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
            
    def load_pickle(self, filename:str):
        """
        Loads the mapping coordinates from a pickle file.
        
        Args:
            filename (str): The name of the file to load the coordinates from.
        """
        with open(filename, 'rb') as f:
            data:MeaCoor_mm = pickle.load(f)
            if not isinstance(data, MeaCoor_mm):
                raise TypeError(f"Expected MappingCoordinates, got {type(data)}")
            if not hasattr(data, 'mappingUnit_name') or not hasattr(data, 'mapping_coordinates'):
                raise AttributeError("MappingCoordinates object does not have the required attributes")
            if not isinstance(data.mappingUnit_name, str):
                raise TypeError(f"Expected str, got {type(data.mappingUnit_name)}")
            if not isinstance(data.mapping_coordinates, list) or not all(isinstance(coord, tuple) and len(coord) == 3 for coord in data.mapping_coordinates):
                raise TypeError(f"Expected list of tuples, got {type(data.mapping_coordinates)}")
            if not all(isinstance(coord[0], (int, float)) and isinstance(coord[1], (int, float)) and isinstance(coord[2], (int, float)) for coord in data.mapping_coordinates):
                raise TypeError(f"Expected tuple of 3 floats, got {type(data.mapping_coordinates[0])}")
            self.mappingUnit_name = data.mappingUnit_name
            self.mapping_coordinates = data.mapping_coordinates
            
    def copy(self) -> Self:
        """
        Returns a copy of the mapping coordinates object.

        Returns:
            MappingCoordinates_mm: A copy of the mapping coordinates object.
        """
        return MeaCoor_mm(
            mappingUnit_name=self.mappingUnit_name,
            mapping_coordinates=self.mapping_coordinates.copy()
        ) # type: ignore

class List_MeaCoor_Hub(list[MeaCoor_mm]):
    """
    A list of mapping coordinates dataclass objects.
    """
    def __init__(self, *args):
        super().__init__(*args)
        self._list_observers:list[Callable] = []
        
    def validator_new_name(self, new_name:str) -> bool:
        """
        Checks if a new mapping unit name is valid (i.e., not already in use).
        
        Args:
            new_name (str): The new mapping unit name to check.
            
        Returns:
            bool: True if the name is valid, False otherwise.
        """
        if not isinstance(new_name, str): raise TypeError(f"Expected str, got {type(new_name)}")
        for mapcoor in self:
            if mapcoor.mappingUnit_name == new_name:
                return False
        return True
        
    def add_observer(self, observer:Callable):
        """
        Adds an observer to the list of observers.
        
        Args:
            observer (Callable): The observer to add.
        """
        if not callable(observer): raise TypeError(f"Expected Callable, got {type(observer)}")
        self._list_observers.append(observer)
        
    def _notify_observers(self):
        """
        Notifies all observers in the list of observers.
        """
        for observer in self._list_observers:
            try: observer()
            except Exception as e: print(f"Error notifying observer {observer}: {e}")
        
    def search_mappingCoor(self, mappingUnit_name:str) -> int|None:
        """
        Searches for a mapping unit in the list of mapping coordinates and returns its index or None if not found.
        
        Args:
            mappingUnit_name (str): The name of the mapping unit to search for.
            
        Returns:
            int|None: The index of the mapping unit in the list or None if not found.
        """
        if not isinstance(mappingUnit_name, str): raise TypeError(f"Expected str, got {type(mappingUnit_name)}")
        list_names = [mapcoor.mappingUnit_name for mapcoor in self]
        idx = None
        if mappingUnit_name in list_names: idx =  list_names.index(mappingUnit_name)
        return idx
    
    def get_mappingCoor(self, mappingUnit_name:str) -> MeaCoor_mm|None:
        """
        Gets a mapping coordinates object from the list by its mapping unit name.
        
        Args:
            mappingUnit_name (str): The name of the mapping unit to get.
            
        Returns:
            MappingCoordinates: The mapping coordinates object, or None if not found.
        """
        if not isinstance(mappingUnit_name, str): raise TypeError(f"Expected str, got {type(mappingUnit_name)}")
        for mapcoor in self:
            if mapcoor.mappingUnit_name == mappingUnit_name:
                return mapcoor
        return None

    def remove_mappingCoor(self, mappingUnit_name:str):
        """
        Removes a mapping unit from the list of mapping coordinates.
        
        Args:
            mappingUnit_name (str): The name of the mapping unit to remove.
            
        Raises:
            TypeError: If the mapping unit name is not a string.
            KeyError: If the mapping unit name is not found in the list.
        """
        if not isinstance(mappingUnit_name, str): raise TypeError(f"Expected str, got {type(mappingUnit_name)}")
        idx = self.search_mappingCoor(mappingUnit_name)
        if idx is not None:
            self.pop(idx)
            self._notify_observers()
        else: raise KeyError(f"Mapping unit {mappingUnit_name} not found in the list")
    
    def rename_mappingCoor(self, old_name:str, new_name:str):
        """
        Renames a mapping unit in the list of mapping coordinates.
        
        Args:
            old_name (str): The current name of the mapping unit.
            new_name (str): The new name for the mapping unit.
            
        Raises:
            TypeError: If the old or new name is not a string.
            KeyError: If the old name is not found in the list.
            ValueError: If the new name already exists in the list.
        """
        if not isinstance(old_name, str) or not isinstance(new_name, str): raise TypeError(f"Expected str, got {type(old_name)} and {type(new_name)}")
        idx = self.search_mappingCoor(old_name)
        if idx is None: raise KeyError(f"Mapping unit {old_name} not found in the list")
        if old_name == new_name: return
        if self.search_mappingCoor(new_name) is not None: raise ValueError(f"Mapping unit {new_name} already exists in the list")
        
        self[idx].mappingUnit_name = new_name
        self._notify_observers()
    
    def append(self, mapCoor:MeaCoor_mm):
        """
        Appends a mapping coordinates object to the list.
        
        Args:
            mapCoor (MappingCoordinates): The mapping coordinates object to append.
            
        Raises:
            TypeError: If the object is not an instance of MappingCoordinates.
            KeyError: If the mapping unit name already exists in the list.
        """
        if not isinstance(mapCoor, MeaCoor_mm): raise TypeError(f"Expected MappingCoordinates, got {type(mapCoor)}")
        if self.search_mappingCoor(mapCoor.mappingUnit_name) is not None: raise KeyError(f"Mapping unit {mapCoor.mappingUnit_name} already exists in the list")
        
        super().append(mapCoor)
        self._notify_observers()
        
    def extend(self, mapCoor:list[MeaCoor_mm], *args, **kwargs):
        """
        Extends the list with a list of mapping coordinates objects.
        
        Args:
            mapCoor (list[MappingCoordinates]): The list of mapping coordinates objects to extend the list with.
        """
        if not isinstance(mapCoor, list) or not all(isinstance(coor, MeaCoor_mm) for coor in mapCoor):
            raise TypeError(f"Expected list of MappingCoordinates, got {type(mapCoor)}")
        super().extend(mapCoor)
        self._notify_observers()
        
    def pop(self, idx:int, *args, **kwargs) -> MeaCoor_mm:
        """
        Pops a mapping coordinates object from the list by index.
        
        Args:
            idx (int): The index of the mapping coordinates object to pop.
            
        Returns:
            MappingCoordinates: The popped mapping coordinates object.
            
        Raises:
            IndexError: If the index is out of range.
        """
        mappingcoor = super().pop(idx)
        self._notify_observers()
        return mappingcoor
        
    def get_list_MappingCoordinates(self,list_unitNames:list[str]) -> list[MeaCoor_mm]:
        """
        Returns a list of mapping coordinates objects from the list based on the given unit names.
        
        Args:
            list_unitNames (list[str]): The list of unit names to search for.
            
        Returns:
            list[MappingCoordinates]: The list of mapping coordinates objects that match the given unit names.
        """
        if not isinstance(list_unitNames, list) or not all(isinstance(name, str) for name in list_unitNames):
            raise TypeError(f"Expected list of str, got {type(list_unitNames)}")
        
        list_mapCoor = [self[idx] for idx in range(len(self)) if self[idx].mappingUnit_name in list_unitNames]
        return list_mapCoor
    
    def generate_dummy_data(self, num_units:int=5, num_coords:int=10):
        """
        Generates dummy data for testing purposes.
        
        Args:
            num_units (int): The number of mapping units to generate. Defaults to 5.
            num_coords (int): The number of coordinates per mapping unit. Defaults to 10.
        """
        for i in range(num_units):
            mappingUnit_name = f"Unit_{i+1}"
            # Randomise the coordinates between 0 and 1 multiplied by a factor
            multiplier = 10000
            mapping_coordinates = [(float(random()*multiplier), float(random()*multiplier), float(random()*multiplier)) for _ in range(num_coords)]
            mapCoor = MeaCoor_mm(mappingUnit_name=mappingUnit_name, mapping_coordinates=mapping_coordinates)
            self.append(mapCoor)