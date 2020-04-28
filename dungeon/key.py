from .dobject import DObject
from .utils import gen_id

class Key(DObject):
    def __init__(self):
        DObject.__init__(self)
        self.code = gen_id('key', random=True, reserved=[666])
        self.description = ["{key_size} key made of {key_material}", f"Key code: {self.code}"]

    def __str__(self):
        return f"Key(id={self.id}, code={self.code}, description={self.description})"