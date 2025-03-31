import enum

class Turn(enum.Enum):
    """ Enum che rappresenta le direzioni possibile di svolta del veicolo """
    LEFT = 1
    RIGHT = 2
    STRAIGHT = 3