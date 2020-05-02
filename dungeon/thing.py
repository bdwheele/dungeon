from .lockable import Lockable
from .container import Container
from .dobject import DObject
from .inspectable import Inspectable
from .breakable import Breakable
from .trappable import Trappable
from .utils import gen_id

class Thing(DObject, Lockable, Container, Inspectable, Breakable, Trappable):
    def __init__(self, **kwargs):
        DObject.__init__(self)
        self.is_portable = True
        Lockable.__init__(self)
        Container.__init__(self)
        Inspectable.__init__(self)
        Breakable.__init__(self)
        Trappable.__init__(self)
        self.merge_attrs(kwargs)

    def __str__(self):
        return f"Thing(id={self.id}, description={self.description})"