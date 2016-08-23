import flexparse

NOVALUE_WORD = "_%|"  # special value used for later recognition


patterns = []

patterns.append(('CH_SENT_END', ".!?"))
patterns.append(('RE_ONLY_SENT_END', '^[{CH_SENT_END}]+$'))
patterns.append(('RE_STARTS_SENT_END', '^[{CH_SENT_END}]+'))
patterns.append(('RE_SPLIT_SENT_END', '[{CH_SENT_END}]'))

patterns.append(('RETXT_ALPHA', "[^\W\d_]"))
patterns.append(('RE_CONTRACTION', "^{RETXT_ALPHA}+'{RETXT_ALPHA}*$"))

# NUMBERS
patterns.append(('RE_NUMBER', "^[+\-]?[\.,]?[0-9]+([\.,][0-9]+)*$"))
patterns.append(('RE_ROMNR', "^(?P<M>M{1,3})?(?P<C>CM|DC{0,3}|CD|C{1,3})?(?P<X>XC|LX{0,3}|XL|X{1,3})?(?P<I>IX|VI{0,3}|IV|I{1,3})?$"))

patterns.append(('RE_AFT_DOT_SENT_END_PUNC', "^[\'\-\/\(\)\"\*\+\!\?\.\#]+$")

# sentence inner separators
patterns.append(('CH_SENT_INSEP_OTHER' r"\#\:\;\-\&\/"))
patterns.append(('CH_SENT_INSEP', r"\,\:\;\-\&\/"))
#_RE_STARTS_SENT_INSEP = re.compile('^[%s]+' % _CH_SENT_INSEP, flags=re.UNICODE)

# sub-sentence - no diff between start and end "", (), ...
# TODO: i have problem with "nagnuti navodnik" and coding of this file
#       »==\xbb, «==\xab
patterns.append(('CH_SENT_SUB1', unicode(r'\"\Ëť\`»«”’ť', "utf-8")))
# NOTE: ' -> ain't inner separator more: isn't -> one word -> isn't 
# _CH_SENT_SUB1 = unicode(r'\"\'\Ëť\`»«”’ť', "utf-8")

patterns.append(('CH_SENT_SUB2_START', r'\(\[\{')) # order of chars in start/end must be the same (==)
patterns.append(('CH_SENT_SUB2_END', r'\)\]\}'))

# PARAGRAPH MARKUP
# -------, ********, ======== etc. 
_RETXT_PAR_START1   = r'(%s[\-\=\*\/\\\+\#]{5,})'
_RETXT_PAR_START2   = '(%s[\n|\r\n]{2,})'

# TAG MATCH 
# matches something like this "$tag_name:opts:some-value$"
# {'tag': 'tag_name', 'tag_options' : 'opts', 'value': 'some-value'}
_RE_TAG = re.compile("^\$(?P<tag>\w+)\%(?P<tag_options>\S*)\%(?P<value>\S*)\$$")
_RETXT_WRAP_TAG = "(?P<tag_spec>\$\w+\%\S*\%\S*\$)"
# NOTE: order wrap_space / wrap_space_comma must be like this - probably greedy problem
patterns.append(('RETXT_SENT_DO_WRAP',  '{RETXT_WRAP_TAG}|%s|%s|(?P<wrap_space>[{CH_SENT_INSEP_OTHER}]|[{CH_SENT_SUB1}]|[{CH_SENT_SUB2_START}]|[{CH_SENT_SUB2_END}])|(?P<wrap_space_comma>.,.)' % (
                                                        _RETXT_PAR_START1 % "?P<wrap_dash>",
                                                        _RETXT_PAR_START2 % "?P<wrap_2nl>")))
_RE_SENT_DO_WRAP =re.compile(_RETXT_SENT_DO_WRAP, flags=re.UNICODE|re.DOTALL|re.MULTILINE)
# TODO: rest #, $, %, #, *, + , -, =, §, ÷, ×, @, <, >, €, |

# remove following chars - note -!=­(u'\xa')
_RE_SENT_REPLACE_CHARS_PAIRS = (
    (re.compile(unicode("([­])+", "utf-8"), re.UNICODE|re.DOTALL|re.MULTILINE), r""),
    (re.compile(unicode("([…])+", "utf-8"), re.UNICODE|re.DOTALL|re.MULTILINE), r" ... "),
    )

RE_WORD_ENDS_WITH_JUNK = re.compile(u"^([$\w%s%s%s%s%s%s]{3,})([^$\s\w%s%s%s%s%s%s]{,3})$" % (
                              _CH_SENT_END,
                              _CH_SENT_INSEP,
                              _CH_SENT_INSEP_OTHER, 
                              _CH_SENT_SUB1,
                              _CH_SENT_SUB2_START,
                              _CH_SENT_SUB2_END,

                              _CH_SENT_END,
                              _CH_SENT_INSEP,
                              _CH_SENT_INSEP_OTHER, 
                              _CH_SENT_SUB1,
                              _CH_SENT_SUB2_START,
                              _CH_SENT_SUB2_END,
                              ), re.UNICODE)

_RE_SPLIT_WHITE_SPACE=re.compile('\s', flags=re.UNICODE)

scanner = pyflex.compile(patterns)
