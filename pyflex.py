import c_pyflex

class ScannerIter(object):

    def __init__(self, scanner, handle):
        self.scanner = scanner
        self.handle = handle

    def __del__(self):
        self.scanner.module.free_scanner(self.handle)

    def next(self):
        return self.scanner.module.next_token(self.handle)

class Scanner(object):

    def __init_(self, module, keys):
        self.keys = keys
        self.module = module

    def scan_file(self, inf):
        return ScannerIter(self, self.module.scan_file(
            inf.fileno(),
            inf.mode))

    def scan_string(self, string):
        return ScannerIter(self, self.module.scan_string(string))

def compile(patterns):
    defn = c_pyflex.PatternDefinition(patterns)
    mod = defn.compile()
    return Scanner(mod, defn.keys())
