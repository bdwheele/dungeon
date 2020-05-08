from .container import Container

class Inspectable:
    def __init__(self):
        self.is_inspectable = True
        self.inspect_count = 0

    def inspect(self, perception, passive):
        """Any contents or description which are <= the perception DC will
           be exposed and placed into to the main object's description or
           contents, as appropriate.  If anything was exposed, it will return
           true to indicate the UI should refresh.
        """
        #pylint: disable=no-member
        changed = False
        hidden_description = 0
        hidden_contents = 0
        for i, x in enumerate(self.description):
            if isinstance(x, (tuple, list)):
                print(f"{x} is a list")
                if x[0] <= perception:
                    print(f"Revealing {x[1]}")
                    self.description[i] = x[1]
                    changed = True
                else:
                    hidden_description += 1

        if self.is_a('Container'):
            for i, x in enumerate(self.contents):
                if x.is_hidden:
                    if x.is_hidden <= perception:
                        x.is_hidden = 0
                        changed = True
                    else:
                        hidden_contents += 1
        if not passive:
            self.inspect_count += 1

        if not hidden_contents and not hidden_description:
            if self.inspect_count:
                self.is_inspectable = False


        return changed
