import pyflex

tokenizer = pyflex.compile([
    ('token', '[^\s]+', True),
    ('line_end', r'[\r\n]', True)
])

def tokenize(ins):
    line = []
    for kind, val in tokenizer.scan_string(ins):
        if kind == 'token':
            line.append(val)
        elif kind == 'line_end':
            yield line
            line = []

def test():
    text = '''This is a line.
    And this is another.'''
    parsed = list(tokenize(text))
    assert text == [['This', 'is', 'a', 'line.'], ['And', 'this', 'is', 'another.']]

if __name__ == '__main__':
    test()
