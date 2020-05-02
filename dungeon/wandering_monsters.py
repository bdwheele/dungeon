from .container import Container
from .dobject import DObject

class WanderingMonsters(DObject, Container):
    def __init__(self, **kwargs):
        DObject.__init__(self)
        Container.__init__(self)
        self.can_contain = True
        self.description = ['Wayward monsters']
        self.merge_attrs(kwargs)
