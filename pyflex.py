import c_pyflex

class ScannerIter(object):

    def __init__(self, module, handle):
        self.handle = handle
        self.module = module

    def __iter__(self):
        return self

    def next(self):
        return self.module.next_token(self.handle)

class Scanner(object):

    def __init_(self, module):
        self.module = module

    def scan_file(self, inf):
        return ScannerIter(self.module, self.module.scan_file(inf.fileno(), inf.mode))

    def scan_string(self, string):
        return ScannerIter(self.module, self.module.scan_string(string))

def compile(patterns):
    defn = c_pyflex.PatternDefinition(patterns)
    mod = defn.compile()
    return Scanner(mod)
