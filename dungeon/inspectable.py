from .container import Container

class Inspectable:
    def __init__(self):
        self.is_inspectable = True
        self.hidden_description = []
        self.hidden_contents = []


    def inspect(self, perception):
        """Any contents or description which are <= the perception DC will
           be exposed and placed into to the main object's description or
           contents, as appropriate.  If anything was exposed, it will return
           true to indicate the UI should refresh.
        """
        changed = False
        for x in x.hidden_description:
            if x[0] <= perception:
                self.hidden_description.remove(x)
                self.description.extend(x[1]) #pylint: disable=no-member
                changed = True

        if isinstance(self, Container):
            for x in self.hidden_contents:
                if x[0] <= perception:
                    self.hidden_contents.remove(x)
                    self.contents.exted(x[1]) #pylint: disable=no-member
                    changed = True
        
        if not self.hidden_contents and not self.hidden_description:
            self.is_inspectable = False

        return changed
