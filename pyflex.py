import c_pyflex

class ScannerIter(object):

    def __init__(self, scanner, handle):
        self.handle = handle
        self.scanner = scanner

    def __iter__(self):
        return self

    def next(self):
        return self.scanner.next_token(self.handle)

class StateMachine(object):

    def __init__(self, scanner):
        self.scanner = scanner

    def scan_file(self, inf):
        return ScannerIter(
                self.scanner,
                self.scanner.scan_file(inf.fileno(), inf.mode))

    def scan_string(self, string):
        return ScannerIter(
                self.scanner,
                self.scanner.scan_string(string))


def compile(patterns):
    thunker = c_pyflex.PatternDefinition(patterns)
    thing = thunker.compile()
    return StateMachine(thing)
