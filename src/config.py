import collections

def singleton(cls):
    """
    http://www.python.org/dev/peps/pep-0318/#examples
    """
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class Configuration(object):

    def __init__(self):
        self.options = {}

    def set_watch(self, option, observer):
        self.options[option].observers.append(observer)

    def __getitem__(self, option):
        return self.options[option].value
    
    def __setitem__(self, option, value):
        opt = self.options[option]

        oldvalue = opt.value
        if oldvalue != value:
            opt.value = value
            map(lambda o: o.option_updated(self, option), opt.observers)

    def get_option_value(self, option, default):
        if option in self.options:
            return self.options[option].value
        return default

    def add_option(self, short_key, long_key=None, description=None, default_value=None):
        if short_key in self.options:
            raise KeyError("The option already exists")

        option = collections.namedtuple('Option', 'long_key description value observers')
        option.long_key = long_key
        option.description = description
        option.value = default_value
        option.observers = []

        self.options[short_key] = option
        

def get_configuration():
    return Configuration()
