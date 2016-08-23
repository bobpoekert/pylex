import re
import tempfile
import subprocess as sp
import os, platform
from distutils import sysconfig

def compile_extension(c_fname, outp_fname):
    getvar = sysconfig.get_config_var

    includes = ['-I' + sysconfig.get_python_inc(), '-I'+sysconfig.get_python_inc(plat_specific=True)]
    includes.extend(getvar('CFLAGS'))

    pyver = getvar('VERSION')

    libs = ['-lpython' + pyver]
    libs += getvar('LIBS').split()
    libs += getvar('SYSLIBS').split()
    # add the prefix/lib/pythonX.Y/config dir, but only if there is no
    # shared library in prefix/lib/.
    if not getvar('Py_ENABLE_SHARED'):
        libs.insert(0, '-L' + getvar('LIBPL'))
    if not getvar('PYTHONFRAMEWORK'):
        libs.extend(getvar('LINKFORSHARED').split())

    sp.check_call(['gcc', '-g', '-Ofast', '-fPIC'] + includes + ['-c', c_fname, '-o', '%s.o' % outp_fname])
    sp.check_call(['gcc', '-shared', '-lfl'] + libs + ['%s.o' % outp_fname, '-o', output_fname])

    os.unlink('%s.o' % outp_fname)

group_re = re.compile(r'\(\?\P\<(.+?)\>(.*?)\)')

def matchsplit(regex, inp):
    matches = regex.finditer(inp)
    idx = 0
    for match in matches:
        start, end = match.span()
        if start > idx:
            yield inp[idx:start]
        yield match
        idx = end

class BaseRule(object):

    def get_definitions(self):
        return ''

    def get_actions(self):
        return ''

class BasicRule(BaseRule):

    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def get_definitons(self):
        return '%s\t%s\n' % (self.name, self.pattern)

class CompoundRule(BaseRule):

    def __init__(self, child_rules):
        self.child_rules = child_rules

    def get_definitions(self):
        return '\n'.join(v.get_definitions() for v in self.child_rules)

    def get_actions(self):
        return '\n'.join(v.get_actions() for v in self.child_rules)

class EmittingRule(BaseRule):

    def __init__(self, defn, name, pattern):
        self.defn = defn
        self.name = name
        self.pattern = pattern

    def get_actions(self):
        return '%s\t%%{%s%%}\n' % (self.pattern, self.defn.action_code(name))

def named_capture_group_rule(defn, name, pattern, emitting):
    rules = []
    i = 0

    def add_rule(pattern):
        if i > 0:
            rules.append(BasicRule('_%s_%d' % (name, i), '{_%s_%d}%s' % (name, i-1, pattern)))
        else:
            rules.append(BasicRule('_%s_%d' % (name, i), pattern))
        i += 1

    for part in matchsplit(group_re, pattern):
        if type(part) in (str, unicode):
            add_rule(part)
        else:
            group_name = part.groups(1)
            group_pattern = part.groups(2)
            rule_name = '_%s_%s' % (name, group_name)
            rules.append(EmittingRule(defn, rule_name, rule_pattern))
            add_rule(group_pattern)
        i += 1

    return CompoundRule(rules)

def new_rule(defn, name, pattern, emit):
    match = group_re.match(pattern)
    if match:
        if emit:
            raise ValueError('rules with named capture groups cannot emit (groups themselves emit)')
        return named_capture_group_rule(defn, name, pattern)
    elif emit:
        return EmittingRule(defn, name, pattern)
    else:
        return BasicRule(name, pattern)

class PatternDefinition(object):

    def __init__(self, patterns):
        self.patterns = patterns
        self.rules = []
        self.rules.sort(key=lambda v: v[0])
        self.rule = None
        self.do_assertions()
        self.build_rules()

    def assert_unique_keys(self):
        ks = set([])
        for k, v in self.patterns:
            assert k not in ks, 'duplicate definition for %s' % k
            ks.add(k)

    def do_assertions(self):
        self.assert_unique_keys()

    @property
    def keys(self):
        return [v[0] for v in self.patterns]

    def build_rules(self):
        for rule in self.patterns:
            self.rules.append(new_rule(self, *rule))
        self.rule = CompoundRule(self.rules)

    def write_flex(self, outf):
        self.write_head(outf)
        outf.write('%top {')
        self.write_c_headers(outf)
        self.write_enum_definitions(outf)
        outf.write('}')
        outf.write(self.rule.get_definitions())
        outf.write('\n%%\n')
        outf.write(self.rule.get_actions())
        outf.write('\n%%\n')
        self.write_tail(outf)

    def compile(self):
        if not os.path.exists(self.so_filename()):
            with open(self.l_filename(), 'w') as outf:
                self.write_flex(outf)
            sp.check_call(['flex', self.l_filename()])
            compile_extension(self.c_filename(), self.so_filename())
            os.unlink(self.c_filename())
            os.unlink(self.h_filename())
            os.unlink(self.l_filename())

        return importlib.import_module(self.hash())

    def write_head(self, outf):
        outf.write('%option reentrant stack noyywrap full\n')
        outf.write('%option outfile="%s" header-file="%s"\n' % (self.c_filename(), self.h_filename()))

    def write_enum_definitions(self, outf):
        for k in self.keys:
            outf.write('PyObject *result_token_%s;\n')

    def action_code(self, name):
        return '''
            Py_INCREF(result_token_%s);
            return result_token_%s;
        ''' % (name, name)

    def write_module_definition(self, outf):
        outf.write('''
    typedef struct parse_context {
        yyscan_t scanner;
        YY_BUFFER_STATE buffer;
    } parse_context;

    const char *capsule_name = "c_pyflex.ParseContext";

    PyObject *scan_file(PyObject *self, PyObject *args) {
        parse_context *res_context = malloc(sizeof(parse_context));

        yyscan_t scanner;
        YY_BUFFER_STATE state;
        int fileno;
        char *mode;

        if (!PyArg_ParseTuple(args, "is", &fileno, &mode)) {
            return 0;
        }

        if (yylex_init(&scanner) != 0) {
            PyErr_SetString(PyExc_RuntimeError, "failed to initialize flex");
            return 0;
        }

        FILE *fileobj = fdopen(fileno, mode);
        state = yy_create_buffer(fileobj, -1);

        res_context->scanner = scanner;
        res_context->buffer = state;

        return PyCapsule_New(res_context, capsule_name, 0);
    }

    PyObject *scan_string(PyObject *self, PyObject *args) {
        char *instring;
        Py_ssize_t stringlen;
        if (!PyArg_ParseTuple(args, "s#", &instring, &stringlen)) {
            return 0;
        }
        yyscan_t scanner;
        YY_BUFFER_STATE buffer;
        if (yylex_init(&scanner) != 0) {
            PyErr_SetString(PyExc_RuntimeError, "failed to initialize flex");
            return 0;
        }

        YY_BUFFER_STATE buffer = yy_scan_buffer(scanner, instring, stringlen);

        parse_context *res_context = malloc(sizeof(parse_context));
        res_context->scanner = scanner;
        res_context->buffer = buffer;

        return PyCapsule_New(res_context, capsule_name, 0);
    }

    PyObject *next_token(PyObject *self, PyObject *args) {
        PyObject *capsule;
        if (!PyArg_ParseTuple(args, "o", &capsule)) {
            return 0;
        }

        parse_context *inp_context = (parse_context *) PyCapsule_GetPointer((PyCapsule *) capsule, capsule_name);

        yy_switch_to_buffer(inp_context->buffer);
        int rescount = yylex();


    }

    PyObject *free_scanner(PyObject *self, PyObject *args) {
        PyObject *capsule;
        if (!PyArg_ParseTuple(args, "o", &capsule)) {
            return 0;
        }

        parse_context *inp_context = (parse_context *) PyCapsule_GetPointer((PyCapsule *) capsule, capsule_name);

        yy_delete_buffer(inp_context->buffer);
        yylex_destroy(inp_context->scanner);

        free(inp_context);

        Py_RETURN_NONE;
    }

    static PyMethodDef ScannerMethods[] = {
        {"scan_file", scan_file, METH_VARARGS, "Takes a file descriptor and returns a scanner handle"},
        {"scan_string", scan_string, METH_VARARGS, "Takes a string and returns a scanner handle"},
        {"next_token", next_token, METH_VARARGS, "Gets the next match from a scanner handle"},
        {"free_scanner", free_scanner, METH_VARARGS, "Frees the scanner refered to by a handle"},
        {NULL, NULL, 0, NULL}
    };

    PyMODINIT_FUNC init_scanner(void) {
        %s
        (void) Py_InitModule("_%s", ScannerMethods);
    }
    ''' % ('\n'.join('result_token_%s = PyString_FromString("%s");' % (k, k) for k in self.keys), self.hash())

    def write_c_headers(self, outf):
        outf.write('#include <stdio.h>\n')
        outf.write('#include <Python.h>\n')

    def write_tail(self, outf):
        self.write_module_definition(outf)

    def hash(self):
        if not hasattr(self, '_hash'):
            self._hash = sha1('%s\0%s' % (self.rule.get_definitions(), self.rule.get_actions())).hexdigest()
        return self._hash

    def c_filename(self):
        return '%s_scanner.c' % self.hash()

    def h_filename(self):
        return '%s_scanner.h' % self.hash()

    def l_filename(self):
        return '%s_scanner.l' % self.hash()

    def so_filename(self):
        if platform.system == 'Linux':
            suffix = 'so'
        elif platform.system == 'Darwin':
            suffix = 'dylib'
        elif platform.system == 'Windows':
            suffix = 'dll'
        else:
            suffix = 'so'
        return '%s.%s' % (self.hash(), suffix)
