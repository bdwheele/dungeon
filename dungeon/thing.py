from .lockable import Lockable
from .container import Container
from .mergeable import Mergeable
from .inspectable import Inspectable
from .breakable import Breakable
from .utils import gen_id

class Thing(Lockable, Container, Mergeable, Inspectable, Breakable):
    def __init__(self, prefix='O'):
        self.id = gen_id('thing', prefix=prefix)
        self.is_portable = True
        self.location = None
        self.description = []
        self.flags = []
        Lockable.__init__(self)
        Container.__init__(self)
        Inspectable.__init__(self)
        Breakable.__init__(self)

    def __str__(self):
        return f"Thing(id={self.id}, description={self.description})"