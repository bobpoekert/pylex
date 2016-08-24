import re
import tempfile
import subprocess as sp
import os, platform, sys
from distutils import sysconfig
from hashlib import sha1
import importlib

current_dir = os.path.abspath(__file__).split('/')[:-1]
if os.access('/'.join(current_dir), os.W_OK):
    scratch_dir = '/'.join(current_dir + ['.pyflex'])
else:
    scratch_dir = os.path.abspath('~/.pyflex')

def compile_extension(c_fname, outp_fname):
    getvar = sysconfig.get_config_var

    includes = ['-I' + sysconfig.get_python_inc(), '-I'+sysconfig.get_python_inc(plat_specific=True)]
    includes.extend(getvar('CFLAGS').split())

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

    print includes, libs

    sp.check_call(['gcc', '-g', '-Ofast', '-fPIC'] + includes + ['-c', c_fname, '-o', '%s.o' % outp_fname])
    sp.check_call(['gcc', '-shared'] + libs + ['%s.o' % outp_fname, '-o', outp_fname])

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
        return '%s\t%%{%s%%}\n' % (self.pattern, self.defn.action_code(self.name))

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

def new_rule(defn, rule):
    if len(rule) == 3:
        name, pattern, emit = rule
    elif len(rule) == 2:
        name, pattern = rule
        emit = False
    else:
        raise ValueError('wrong number of arguments')
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
        for row in self.patterns:
            k = row[0]
            if k in ks:
                raise ValueError('duplicate definition for %s' % k)
            ks.add(k)

    def assert_valid_key_names(self):
        for k in self.keys():
            if not re.match('^[a-zA-Z0-9_]+$', k):
                raise ValueError('invalid name: "%s". names can only contain letters, numbers, and underscores' % k)

    def do_assertions(self):
        self.assert_unique_keys()
        self.assert_valid_key_names()

    def keys(self):
        return [v[0] for v in self.patterns]

    def build_rules(self):
        for rule in self.patterns:
            self.rules.append(new_rule(self, rule))
        self.rule = CompoundRule(self.rules)

    def write_flex(self, outf):
        self.write_head(outf)
        outf.write('%{\n')
        self.write_c_headers(outf)
        self.write_enum_definitions(outf)
        outf.write('%}\n')
        outf.write(self.rule.get_definitions())
        outf.write('\n%%\n')
        outf.write(self.rule.get_actions())
        outf.write('\n%%\n')
        self.write_tail(outf)

    def compile(self):
        if not os.path.exists(scratch_dir):
            os.mkdir(scratch_dir)
        if True or not os.path.exists(self.so_filename()):
            with open(self.l_filename(), 'w') as outf:
                self.write_flex(outf)
            sp.check_call(['flex', self.l_filename()])
            compile_extension(self.c_filename(), self.so_filename())
            os.unlink(self.c_filename())
            os.unlink(self.h_filename())
            os.unlink(self.l_filename())

        if scratch_dir not in sys.path:
            sys.path.append(scratch_dir)
        return importlib.import_module('_%s' % self.hash())

    def write_head(self, outf):
        outf.write('%option reentrant stack noyywrap full\n')
        outf.write('%%option outfile="%s" header-file="%s"\n' % (self.c_filename(), self.h_filename()))

    def write_enum_definitions(self, outf):
        for k in self.keys():
            outf.write('PyObject *result_token_%s;\n' % k)

    def action_code(self, name):
        return 'return Py_BuildValue("(Os)", result_token_%s, yytext);' % name

    def write_module_definition(self, outf):
        outf.write('''
    typedef struct parse_context {
        yyscan_t scanner;
        YY_BUFFER_STATE buffer;
    } parse_context;

    const char *capsule_name = "c_pyflex.ParseContext";

    void free_context(parse_context *inp_context) {
        if (inp_context->buffer) {
            yy_delete_buffer(inp_context->buffer, inp_context->scanner);
        }
        if (inp_context->scanner) {
            yylex_destroy(inp_context->scanner);
        }
        free(inp_context);
    }

    void free_context_capsule(PyObject *capsule) {
        free_context((parse_context *) PyCapsule_GetPointer(capsule, capsule_name));
    }

    PyObject *scan_file(PyObject *self, PyObject *args) {
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
        state = yy_create_buffer(fileobj, -1, scanner);

        parse_context *res_context = malloc(sizeof(parse_context));
        res_context->scanner = scanner;
        res_context->buffer = state;

        return PyCapsule_New(res_context, capsule_name, free_context_capsule);
    }

    PyObject *scan_string(PyObject *self, PyObject *args) {
        char *instring;
        Py_ssize_t stringlen;
        if (!PyArg_ParseTuple(args, "s#", &instring, &stringlen)) {
            return 0;
        }
        yyscan_t scanner;
        if (yylex_init(&scanner) != 0) {
            PyErr_SetString(PyExc_RuntimeError, "failed to initialize flex");
            return 0;
        }

        YY_BUFFER_STATE buff = yy_scan_buffer(instring, stringlen, scanner);

        parse_context *res_context = malloc(sizeof(parse_context));
        res_context->scanner = scanner;
        res_context->buffer = buff;

        return PyCapsule_New(res_context, capsule_name, free_context_capsule);
    }

    PyObject *next_token(PyObject *self, PyObject *args) {
        PyObject *capsule;
        if (!PyArg_ParseTuple(args, "O", &capsule)) {
            return 0;
        }

        parse_context *inp_context = (parse_context *) PyCapsule_GetPointer((PyObject *) capsule, capsule_name);

        yy_switch_to_buffer(inp_context->buffer, inp_context->scanner);
        PyObject *res = yylex(inp_context->scanner);
        if (res == 0) {
            PyErr_SetNone(PyExc_StopIteration);
        }
        return res;
    }

    static PyMethodDef ScannerMethods[] = {
        {"scan_file", scan_file, METH_VARARGS, "Takes a file descriptor and returns a scanner handle"},
        {"scan_string", scan_string, METH_VARARGS, "Takes a string and returns a scanner handle"},
        {"next_token", next_token, METH_VARARGS, "Gets the next match from a scanner handle"},
        {NULL, NULL, 0, NULL}
    };

    PyMODINIT_FUNC init_%(hash)s(void) {
        printf("hello\\n");
        (void) Py_InitModule("_%(hash)s", ScannerMethods);
        printf("hello\\n");
        %(inits)s
        printf("hello\\n");
    }
    ''' % dict(
            hash=self.hash(),
            inits='\n'.join('result_token_%s = PyString_FromString("%s");' % (k, k) for k in self.keys())))

    def write_c_headers(self, outf):
        outf.write('#include <stdio.h>\n')
        outf.write('#include <Python.h>\n')
        outf.write('#define YY_DECL PyObject *yylex(yyscan_t yyscanner)\n')

    def write_tail(self, outf):
        self.write_module_definition(outf)

    def hash(self):
        if not hasattr(self, '_hash'):
            self._hash = sha1('%s\0%s' % (self.rule.get_definitions(), self.rule.get_actions())).hexdigest()
        return self._hash

    def c_filename(self):
        return os.path.join(scratch_dir, '%s_scanner.c' % self.hash())

    def h_filename(self):
        return os.path.join(scratch_dir, '%s_scanner.h' % self.hash())

    def l_filename(self):
        return os.path.join(scratch_dir, '%s_scanner.l' % self.hash())

    def so_filename(self):
        if platform.system == 'Linux':
            suffix = 'so'
        elif platform.system == 'Darwin':
            suffix = 'dylib'
        elif platform.system == 'Windows':
            suffix = 'dll'
        else:
            suffix = 'so'
        return os.path.join(scratch_dir, '_%s.%s' % (self.hash(), suffix))
