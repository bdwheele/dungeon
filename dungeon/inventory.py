from .container import Container
from .dobject import DObject

class Inventory(DObject, Container):
    "The players' inventory"
    def __init__(self, **kwargs):
        DObject.__init__(self)
        Container.__init__(self)
        self.description = ['Player inventory']
        self.merge_attrs(kwargs)

