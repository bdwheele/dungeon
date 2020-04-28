from .mergeable import Mergeable
from .utils import gen_id

class Key(Mergeable):
    def __init__(self, prefix='K'):
        self.id = gen_id('thing', prefix=prefix) 
        self.code = gen_id('key', random=True, reserved=[666])
        self.description = ["{key_size} key made of {key_material}", f"Key code: {self.code}"]
        self.flags = []

    def __str__(self):
        return f"Key(id={self.id}, code={self.code}, description={self.description})"