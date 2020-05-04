from .dobject import DObject
from .utils import gen_id


class Key(DObject):
    def __init__(self):
        DObject.__init__(self)
        self.description = ["{key_size} key made of {key_material}"]
        self.is_portable = True

    def __str__(self):
        return f"Key(id={self.id}, description={self.description})"