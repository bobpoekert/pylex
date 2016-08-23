# coding=utf-8
# # doctest: +NORMALIZE_WHITESPACE
"""
Unit tests in test_parse.txt

TODO: how to deal with this www.page, or name.com (should be same) 
      with this abbr.testing -> abbr. testing

"""
import re
import logging
#logger = logging.getLogger()

# ----------------------------------------

ABBR_MAX_LEN=5

NOVALUE_WORD = "_%|"  # special value used for later recognition

_CH_SENT_END = ".!?"
_RE_ONLY_SENT_END   = re.compile('^[%s]+$' % _CH_SENT_END, flags=re.UNICODE)
_RE_STARTS_SENT_END = re.compile('^[%s]+' % _CH_SENT_END, flags=re.UNICODE)
_RE_SPLIT_SENT_END  = re.compile('[%s]' % _CH_SENT_END, flags=re.UNICODE)
# e.g. isn't 
_RETXT_ALPHA = "[^\W\d_]"
_RE_CONTRACTION     = re.compile("^%s+'%s*$" % (_RETXT_ALPHA, _RETXT_ALPHA), flags=re.UNICODE)

# NUMBERS
_RE_NUMBER          = re.compile("^[+\-]?[\.,]?[0-9]+([\.,][0-9]+)*$")
_RE_ROMNR           = re.compile("^(?P<M>M{1,3})?(?P<C>CM|DC{0,3}|CD|C{1,3})?(?P<X>XC|LX{0,3}|XL|X{1,3})?(?P<I>IX|VI{0,3}|IV|I{1,3})?$")

_RE_AFT_DOT_SENT_END_PUNC = re.compile("^[\'\-\/\(\)\"\*\+\!\?\.\#]+$")

# sentence inner separators
_CH_SENT_INSEP_OTHER = r"\#\:\;\-\&\/"
_CH_SENT_INSEP = r"\,\:\;\-\&\/"
#_RE_STARTS_SENT_INSEP = re.compile('^[%s]+' % _CH_SENT_INSEP, flags=re.UNICODE)

# sub-sentence - no diff between start and end "", (), ...
# TODO: i have problem with "nagnuti navodnik" and coding of this file
#       »==\xbb, «==\xab
_CH_SENT_SUB1 = unicode(r'\"\Ëť\`»«”’ť', "utf-8")
# NOTE: ' -> ain't inner separator more: isn't -> one word -> isn't 
# _CH_SENT_SUB1 = unicode(r'\"\'\Ëť\`»«”’ť', "utf-8")

_CH_SENT_SUB2_START = r'\(\[\{' # order of chars in start/end must be the same (==)
_CH_SENT_SUB2_END   = r'\)\]\}'

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
_RETXT_SENT_DO_WRAP = '%s|%s|%s|(?P<wrap_space>[%s]|[%s]|[%s]|[%s])|(?P<wrap_space_comma>.,.)' % (
                                                        _RETXT_WRAP_TAG,
                                                        _RETXT_PAR_START1 % "?P<wrap_dash>",
                                                        _RETXT_PAR_START2 % "?P<wrap_2nl>",
                                                        _CH_SENT_INSEP_OTHER, 
                                                        _CH_SENT_SUB1,
                                                        _CH_SENT_SUB2_START,
                                                        _CH_SENT_SUB2_END
                                                        )
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

# ----------------------------------------

def get_value_repr(value):
    value_repr = repr(value)
    if value_repr[:2] in ("u'", 'u"'):
        value_repr = value_repr[1:]
    return value_repr

def to_unicode2(text, cp="utf-8"):
    # TODO: use util to_unicode instead
    if not isinstance(text, unicode):
        text = unicode(text, cp, 'replace')
    return text

# ----------------------------------------

class ItemList(object):
    def __init__(self, item_klass, initial_list=()):
        """
        >>> print ItemList(item_klass=Abbr)
        ItemList(Abbr, 0 items/0 new)
        >>> x = ItemList(Abbr, [Abbr("test."), ('tes.', ), ('te.', True)])
        >>> print x
        ItemList(Abbr, 3 items/0 new)
        >>> print x.get_item("te.")
        A('te.'/0/init/bef_name)
        >>> print x.get_item("not_found") is None
        True
        >>> a = x.add_or_update("t.")
        >>> a = x.add_or_update("t.")
        >>> a = x.add_or_update("T.")
        >>> print list(x.iter_only_new())
        [A('T.'/1/new), A('t.'/2/new)]

        >>> def abbr_getter(value_base):
        ...     if value_base in 'a. b. c.'.split():
        ...         return Abbr(value_base)
        >>> x = ItemList(Abbr, abbr_getter)
        >>> x.get_item('d.')
        >>> x.get_item('a.')
        A('a.'/0/init)

        Second time it reads from _dict (cached value from last db read):
        >>> x.get_item('a.')
        A('a.'/0/init)
        """
        self.item_klass = item_klass
        self._dict = {}
        self.initial_list_callable=callable(initial_list)
        if self.initial_list_callable:
            self.initial_list_getter = initial_list
        else:
            for item in initial_list:
                self.add_initial(item)
        self._list_only_new = []


    def add_or_update(self, value):
        if not self._dict.has_key(value):
            item = self.item_klass(value=value, is_new=True)
            self._dict[item.value] = item
            self._list_only_new.append(item)
        else:
            item = self._dict[value]
            item.freq+=1
        return item

    def add_initial(self, item):
        is_created = False
        if not isinstance(item, self.item_klass):
            is_created = True
            assert isinstance(item, (list, tuple))
            item = self.item_klass(*tuple(item))
        assert not self._dict.has_key(item.value)
        item.set_is_new(is_new=False)
        self._dict[item.value] = item
        return None

    # TODO:
    # params.abbr_list = Lemma.get_abbr_item(value_base)
    # params.name_list = Lemma.get_name_item(value_base)

    def __getitem__(self, value):
        raise Exception("who uses this??")
        return self._dict[value]

    def get_item(self, value):
        if self.initial_list_callable:
            if value in self._dict:
                return self._dict[value]
            item = self.initial_list_getter(value)
            if item:
                self.add_initial(item)
            return item
        return self._dict.get(value, None)

    def iter_only_new(self):
        for item in sorted(self._list_only_new, cmp=lambda x,y: cmp(x.value, y.value)):
            yield item
        
    def __iter__(self):
        for item in sorted(self._dict.values(), cmp=lambda x,y: cmp(x.value, y.value)):
            yield item

    def __str__(self):
        return "ItemList(%s, %d items/%d new)" % (self.item_klass.__name__, 
                        len(self._dict), len(self._list_only_new))

    def __repr__(self):
        return "%s at %0X" % (str(self), id(self))

# ----------------------------------------

class _Base(object):
    def __init__(self):
        self.is_new = self.freq = self.is_confirmed = self.is_saved = self.freq_until_confirmed = None

    def set_is_new(self, is_new):
        self.is_new = is_new
        self.freq = 1 if self.is_new else 0
        self.is_confirmed = not self.is_new
        self.is_saved = self.is_confirmed
        self.freq_until_confirmed = 0
            
    def confirm(self):
        if not self.is_confirmed:
            self.freq_until_confirmed = self.freq - 1
            assert self.freq_until_confirmed>=0
            self.is_confirmed = True
            assert not self.is_saved

    def __str__(self):
        attrs = ["%s" % an[2:] for an, av in sorted(self.__dict__.iteritems()) if an.startswith("a_") if av==True]
        # TODO: don't know how to solve this better.
        value_repr = get_value_repr(self.value)
        # value_repr = repr(self.value)[1:]
        # if value_repr.startswith("u'"):
        #     value_repr = value_repr[1:]
        return u"%s(%s%s%s%s%s)" % (self.__class__.__name__[0],
                                value_repr,
                                "/%d" % self.freq, 
                                "/new" if self.is_new else "/init",
                                "/conf/%d" % self.freq_until_confirmed if self.is_new and self.is_confirmed else "",
                                "/"+("+".join(attrs)) if attrs else "")


    def __repr__(self):
        return "%s" % (str(self), )
        #return "%s at %0X" % (str(self), id(self))

# ----------------------------------------

class Name(_Base):
    def __init__(self, value, is_new=True, can_start_sent=False):
        """
        >>> Name("Pero")
        N('Pero'/1/new)
        >>> Name(u"Peri\u0107")
        N('Peri\u0107'/1/new)
        >>> Name(unicode("Perić", "utf-8"))
        N('Peri\u0107'/1/new)
        >>> Name("Pero", is_new=False, can_start_sent=True)
        N('Pero'/0/init/start_sent)
        """
        super(Name, self).__init__()
        self.value =  to_unicode2(value)
        assert self.value.istitle(), self.value
        self.a_start_sent = can_start_sent
        self.set_is_new(is_new)

# ----------------------------------------

class Abbr(_Base):
    def __init__(self, value, a_bef_name=False, a_end_sent=False, is_new=True):
        """ Not used for now: 
             - a_bef_name - usually before name, but not allways
             - a_end_sent - can end sentence - is such case
        >>> Abbr("test.")
        A('test.'/1/new)
        >>> Abbr("test.", True)
        A('test.'/1/new/bef_name)
        >>> Abbr("test.", False, True)
        A('test.'/1/new/end_sent)
        >>> Abbr("test.", True, True, False)
        A('test.'/0/init/bef_name+end_sent)
        """
        super(Abbr, self).__init__()
        self.value = to_unicode2(value)
        assert Tokenizer.looks_like_abbr(self.value), "'%s'" % value
        self.a_bef_name, self.a_end_sent = a_bef_name, a_end_sent
        # TODO: name/abbr freq/value/is_new -> base class
        self.set_is_new(is_new)

    #def confirm(self):
    #    super(Abbr, self).confirm()

# ----------------------------------------

class Token(object):
    def __init__(self, value, 
                 is_sent_start=False, 
                 is_sent_end=False, 
                 #is_line_start=False, 
                 known_obj=None):
        self.known_abbr = self.known_name = None
        self.value = value.strip()
        assert self.value
        self.value_len = len(self.value)
        self.is_sent_start = is_sent_start
        # TODO: should i check if sent_start that it starts with upper case

        # TODO: should i check if sent_end that it is not word
        self.is_sent_end   = is_sent_end
       
        #self.is_line_start = is_line_start

        # TODO: we can distinguish normal and ordinal nr (123.) for reg. and roman numbers
        #       maybe new prop
        self.is_number = Tokenizer.looks_like_number(self.value, can_end_dot=True)
        # for I. this is roman and abbr. - we count it as abbr.
        self.is_romnr = False
        if not (known_obj and isinstance(known_obj, (Abbr, Name))):
            self.is_romnr = Tokenizer.looks_like_roman_number(self.value, can_end_dot=True)
        self.is_abbr = ( not self.is_romnr and not self.is_number and not self.is_sent_end 
                         and Tokenizer.looks_like_abbr(self.value)
                       )

        # is it contraction e.g. isn't, oš'
        self.is_contr = Tokenizer.looks_like_contraction(self.value)

        self._is_alpha = self.value.isalpha()
        assert not (self.is_abbr and not self.value[:-1].isalpha()), self.value
        if known_obj:
            assert isinstance(known_obj, (Abbr, Name))

        if known_obj and isinstance(known_obj, Name):
            self.known_name = known_obj
            self.is_name = True
        else:
            self.known_name = None
            self.is_name = (not self.is_sent_start 
                            and not self.is_abbr
                            and not self.is_romnr
                            and self._is_alpha
                            and self.value.istitle()
                            and len(self.value)>1)
        self.is_fuzzy_abbr = ( not self.is_romnr and not self.is_number 
                               and not self.is_contr
                               and self.value.find(".") not in (-1, 0, self.value_len-1) )
        self.is_inner_sep   = self.value in _CH_SENT_INSEP
        self.is_sent_sub1   = self.value in _CH_SENT_SUB1
        self.is_sent_sub2_s = self.value in _CH_SENT_SUB2_START
        self.is_sent_sub2_e = self.value in _CH_SENT_SUB2_END
        self.is_par_start=False 
        m = _RE_TAG.match(self.value)
        # NOTE: only one tag supported
        if m:
            self._is_tagged = True
            self.tag         = m.groupdict()["tag"]
            self.tag_options = m.groupdict()["tag_options"]
            self.value       = m.groupdict()["value"]
            self.value       = self.value if self.value else ""
            if self.tag=="par_start":
                self.is_sent_start=False
                self.is_par_start =True
            # TODO: generalize like this: 
            # self.is_fuzzy_type = (0==sum([av for an, av in self.__dict__.iteritems() if an.startswith("is_")]))
            self.is_fuzzy_type = False
        else:
            self._is_tagged = False
            self.tag = self.tag_options = self.tag_value = None 
            self.is_fuzzy_type = (not self.is_abbr 
                                  and not self.is_fuzzy_abbr
                                  and not self.is_inner_sep
                                  and not self.is_sent_sub1
                                  and not self.is_sent_sub2_s
                                  and not self.is_sent_sub2_e
                                  and not self.is_sent_end 
                                  and not self.is_number 
                                  and not self.is_romnr 
                                  and not self.is_contr
                                  and not self._is_alpha)
        if known_obj and isinstance(known_obj, Abbr):
            if not self.is_abbr:
                assert self.is_abbr
            self.known_abbr = known_obj
        assert not (self.is_abbr and self.is_name)

        # ------------ when to do or not to do lowercase ----------------
        # TODO: there is a problem with lately determined names e.g. 
        #       Pero goes home . Is Pero home ?
        #       N?                  N!
        #       pero goes home . is Pero home ?
        # what will happen in db I don't know       
        #do_lower = True
        self.is_upper = False
        do_lower = True
        if self.is_number or self.is_romnr:
            # self.is_romnr 
            do_lower=False
        elif self.value.startswith("NLx"):
            do_lower=False
        elif self.is_name:
            do_lower = False
        elif self._is_tagged:
            do_lower = False
        elif self.is_abbr and not self.is_sent_start and self.value.istitle():
            do_lower = False
        else:
            self.is_upper = self.value.isupper()
        #elif self.value.isupper():
        #    self.is_upper = True
        if do_lower:
            self.value = self.value.lower()

    def __unicode__(self):
        """
        Matches something like this "$par_start%%test$"
        >>> print Token(r"   $par_start%%test$   ", is_sent_start=True)
        T('test'/par_start)

        >>> print Token(" 1232,   ")
        T('1232,'/fuzzy_type)

        >>> print Token(" +1232.0032,00   ")
        T('+1232.0032,00'/number)
        
        >>> print Token(" Miro,   ")
        T('miro,'/fuzzy_type)
        >>> print Token("test")
        T('test')
        >>> print Token("test", is_sent_start=True)
        T('test'/sent_start)

        >>> print Token("   Test   ")
        T('Test'/name)
        >>> print Token("   Test   ", is_sent_start=True)
        T('test'/sent_start)
        >>> print Token("   Abbr.   ", is_sent_start=True)
        T('abbr.'/abbr+sent_start)
        >>> print Token("   abbr.   ")
        T('abbr.'/abbr)
        >>> print Token("   www.abbr.   ")
        T('www.abbr.'/fuzzy_abbr)
        >>> print Token("   www.abbr.com   ")
        T('www.abbr.com'/fuzzy_abbr)
        >>> print Token("   Mr.   ")
        T('Mr.'/abbr)
        >>> print Token("   J.   ")
        T('J.'/abbr)
        >>> print Token("   J.   ", known_obj=Abbr("dummy.", is_new=False))
        T('J.'/abbr+known)
        >>> print Token(" Miro   ", known_obj=Name("Dummy", is_new=False))
        T('Miro'/name+known)
        >>> print Token(" ,   ")
        T(','/inner_sep)
        >>> print Token(" 123   ")
        T('123'/number)
        """
        attrs = ["%s" % an[3:] for an, av in sorted(self.__dict__.iteritems()) if an.startswith("is_") and an not in ("is_par_start",) and av==True]
        if self._is_tagged :
            attrs.append("%s%s" % (self.tag, ("=%s" % self.tag_options) if self.tag_options else ""))
        if self.known_abbr and not self.known_abbr.is_new:
            attrs.append("known")
        if self.known_name and not self.known_name.is_new:
            attrs.append("known")
        value_repr = get_value_repr(self.value)

        return "T(%s%s)" % (value_repr, "/"+("+".join(attrs)) if attrs else "")

    def __repr__(self):
        # return "T(%s)" % (repr(self.value),)
        return "%s" % (unicode(self), )
        # return "%s at %0X" % (str(self), id(self))

# ----------------------------------------

class TokenizerParams(object):
    """ this is done also for hiding long object in django error page"""
    def __init__(self):
        self.abbr_list = []
        self.name_list = []
        self.lines = []
        self.text  = ""
        self.word_list  = []
        self.fun_abbr_name = self.callback_abbr_all

    # ---------------
    @classmethod
    def callback_abbr_none(cls, word, known_obj, params, word_list_next):
        return False

    @classmethod
    def callback_abbr_all(cls, word, known_obj, params, word_list_next):
        return True

    @classmethod
    def get_callback_abbr_choices(cls):
        """
        >>> TokenizerParams.get_callback_abbr_choices()
        [('all', 'All'), ('none', 'None')]
        """
        return [(k[len("callback_abbr_"):],k[len("callback_abbr_"):].title()) 
                for k in cls.__dict__ if k.startswith("callback_abbr_")]

    @classmethod
    def get_callback_abbr_by_name(cls, name):
        """
        >>> TokenizerParams.get_callback_abbr_by_name("all")==TokenizerParams.callback_abbr_all
        True
        """
        return getattr(cls, "callback_abbr_" + name)

    def __str__(self):
        return "abbr_list=%s, name_list=%s, lines=%s, word_list=%s, text=%s, fun_abbr_name=%s" % (
                len(self.abbr_list._dict),
                len(self.name_list._dict),
                len(self.lines),
                len(self.word_list),
                len(self.text),
                getattr(self.fun_abbr_name, "__name__", str(self.fun_abbr_name)),
                )


    def __repr__(self):
        return "%s at %0X" % (str(self), id(self))

# ----------------------------------------
        
class Tokenizer(object):
    """ nltk.PunktTokenizer() or pickled one was not good enough so i 
        write my own
        Tests are in test_parse.txt.
    """
    def __init__(self):
        pass

    @classmethod
    def looks_like_contraction(cls, word):
        """
        >>> _RE_CONTRACTION.match("CD")
        >>> Tokenizer.looks_like_contraction("test")
        False
        >>> Tokenizer.looks_like_contraction("test'")
        True
        >>> Tokenizer.looks_like_contraction("test's")
        True
        >>> Tokenizer.looks_like_contraction("test's'")
        False
        >>> Tokenizer.looks_like_contraction(unicode("Oš'", "utf-8"))
        True
        >>> Tokenizer.looks_like_contraction(unicode("Oš'neš", "utf-8"))
        True
        >>> Tokenizer.looks_like_contraction("tes3t'n")
        False
        """
        m = _RE_CONTRACTION.match(word)
        return m is not None

        
    @classmethod
    def looks_like_roman_number(cls, word, can_end_dot=False, can_be_short=True):
        """
        >>> _RE_ROMNR.match("CD").groups()
        (None, 'CD', None, None)
        >>> _RE_ROMNR.match("MMM").groups()
        ('MMM', None, None, None)
        >>> _RE_ROMNR.match("MMMCM").groups()
        ('MMM', 'CM', None, None)
        >>> _RE_ROMNR.match("MMMCMD") is None
        True
        >>> _RE_ROMNR.match("MMMCD").groups()
        ('MMM', 'CD', None, None)
        >>> _RE_ROMNR.match("MMMD").groups()
        ('MMM', 'D', None, None)
        >>> _RE_ROMNR.match("MMMDCCC").groups()
        ('MMM', 'DCCC', None, None)
        >>> _RE_ROMNR.match("MMMDCCCXC").groups()
        ('MMM', 'DCCC', 'XC', None)
        >>> _RE_ROMNR.match("MMMDCCCXCVIII").groups()
        ('MMM', 'DCCC', 'XC', 'VIII')

        >>> Tokenizer.looks_like_roman_number("+123.000,00")
        False
        >>> Tokenizer.looks_like_roman_number("VIII")
        True
        >>> Tokenizer.looks_like_roman_number("VIII.")
        False
        >>> Tokenizer.looks_like_roman_number("VIII.",can_end_dot=True)
        True
        >>> Tokenizer.looks_like_roman_number("VIII",can_end_dot=True)
        True

        I and V are exeptions:
        >>> Tokenizer.looks_like_roman_number("I")
        False
        >>> Tokenizer.looks_like_roman_number("I.", can_end_dot=True)
        True
        """
        if can_end_dot and word.endswith("."):
            w = word[:-1]
        else:
            # some exceptions
            if len(word)==1 or word in ("VI", "MI", "DI", "LI"):
                return False
            w = word
        if w=="":
            return False
        m = _RE_ROMNR.match(w)
        return m is not None
        # value = roman2nr(w, raise_on_err=False)
        # return value is not None

    @classmethod
    def looks_like_number(cls, word, can_end_dot=False):
        """
        >>> Tokenizer.looks_like_number("+123.000,00")
        True
        >>> Tokenizer.looks_like_number("+.000,00")
        True
        >>> Tokenizer.looks_like_number("+.,00")
        False
        >>> Tokenizer.looks_like_number("+.00,")
        False
        >>> Tokenizer.looks_like_number("+.00,00,00")
        True
        >>> Tokenizer.looks_like_number("100.00,00,00")
        True
        >>> Tokenizer.looks_like_number("100.00,00,00", can_end_dot=True)
        True
        >>> Tokenizer.looks_like_number("100.", can_end_dot=False)
        False
        >>> Tokenizer.looks_like_number("100.", can_end_dot=True)
        True
        """
        if can_end_dot and word.endswith("."):
            w = word[:-1]
        else:
            w = word
        m = _RE_NUMBER.match(w)
        return m is not None

    @classmethod
    def looks_like_abbr(cls, word, istitle=False, max_len=None):
        """
        >>> Tokenizer.looks_like_abbr("J.")
        True
        >>> Tokenizer.looks_like_abbr(".")
        False
        >>> Tokenizer.looks_like_abbr("test.")
        True
        >>> Tokenizer.looks_like_abbr("www.test")
        False
        >>> Tokenizer.looks_like_abbr("Test.")
        True
        >>> Tokenizer.looks_like_abbr("T.")
        True
        >>> Tokenizer.looks_like_abbr("J.", istitle=True)
        True
        >>> Tokenizer.looks_like_abbr("j.", istitle=True)
        False
        >>> Tokenizer.looks_like_abbr("Jr.", istitle=True)
        False
        >>> Tokenizer.looks_like_abbr("Jr.", istitle=True, max_len=2)
        True
        """
        #and len(word[:-1])<=1 and word[0].isupper())
        if not max_len:
            max_len = 1 if istitle else ABBR_MAX_LEN
        ret = word.endswith(".") and len(word)>1  and len(word)<=max_len+1 and word[:-1].isalpha()
        if istitle and ret:
            ret = ret and word[0].isupper()
        return ret

    @classmethod
    def split_word(cls, word, abbr_list=None, name_list=None):
        """
        TODO: get use od name_list

        >>> abbr_list = ItemList(Abbr, [Abbr("ing."), ("prof.",), Abbr("dr.")])
        >>> Tokenizer.split_word("prof.dr.J.Malkovich", abbr_list)
        ['prof.', 'dr.', 'J.', 'Malkovich']

        >>> Tokenizer.split_word("ing.J.Malkovich")
        ['ing.', 'J.', 'Malkovich']

        This is the way to solve this:
        >>> Tokenizer.split_word("ing.J.Malkovich", abbr_list)
        ['ing.', 'J.', 'Malkovich']

        >>> Tokenizer.split_word("J.Malkovich")
        ['J.', 'Malkovich']

        >>> Tokenizer.split_word("Mr.J.Malkovich")
        ['Mr.', 'J.', 'Malkovich']

        >>> Tokenizer.split_word("Ing.J.Malkovich")
        ['Ing.', 'J.', 'Malkovich']

        # TODO: 
        >>> Tokenizer.split_word("test...Test")
        ['test', '.', '.', '.', 'Test']

        >>> Tokenizer.split_word("test.?test")
        ['test.', '?', 'test']
        >>> Tokenizer.split_word("test?!.test")
        ['test', '?', '!', '.', 'test']
        >>> Tokenizer.split_word("test.Rest")
        ['test.', 'Rest']

        This is not abbr. it is too long
        >>> Tokenizer.split_word("testing.Rest")
        ['testing', '.', 'Rest']
        >>> Tokenizer.split_word("test!Rest")
        ['test', '!', 'Rest']
        >>> Tokenizer.split_word("test!Rest?")
        ['test', '!', 'Rest', '?']
        >>> Tokenizer.split_word("test!Rest?.")
        ['test', '!', 'Rest', '?', '.']
        >>> Tokenizer.split_word("test.test") is None
        True
        >>> Tokenizer.split_word("test") is None
        True
        """
        abbr_list = cls._check_item_list(Abbr, abbr_list)
        name_list = cls._check_item_list(Name, name_list)
        word_last_ind = len(word)-1
        if word_last_ind==0:
            return None

        start_last = 0
        words_inner = []
        for m in _RE_SPLIT_SENT_END.finditer(word):
            start = m.start()
            word_orig = word[start_last:start+1]
            abbr_obj = abbr_list.get_item(word_orig)
            if abbr_obj or word[start]!="." or start_last==start or (
                    start!=word_last_ind and (word[start+1].isupper() or word[start+1]==".")):
                word_inner = word[start_last:start]
                #if not (abbr_obj or cls.looks_like_short_name_abbr(word_orig, ismax_len=4)
                if not (abbr_obj 
                        or cls.looks_like_abbr(word_orig)
                        # or cls.looks_like_abbr(word_orig, istitle=True)
                        or cls.looks_like_number(word_orig)
                        or cls.looks_like_roman_number(word_orig)
                    ) or (start!=word_last_ind and word[start+1]=="."):
                    word_inner += " "
                word_inner += word[start]
                words_inner.append(word_inner)
                start_last = start+1
        last_word = word[start_last:].strip()
        if last_word:
            last_word = words_inner.append(word[start_last:])
        assert words_inner
        #assert isinstance(words_inner, list)
        words_inner_old = words_inner[:]
        words_inner = []
        for word in words_inner_old:
            words_inner.extend(RE_WORD_ENDS_WITH_JUNK.sub(r"\1 \2", word).split())
        words_inner = " ".join(words_inner)
        words_inner = words_inner.split()
        
        if len(words_inner)==1:
            return None
        return words_inner

    @classmethod
    def _check_item_list(cls, item_klass, item_list):
        if not item_list:
            item_list = ItemList(item_klass)
        elif callable(item_list):
            item_list = ItemList(item_klass, item_list)
        assert isinstance(item_list, ItemList), item_list
        return item_list

    @classmethod
    def join_punc_chars(cls, word_list, punc_word, ind):
        """
        The question is - should this be applied or not
        NOTE: that .Test is not joined nor splitted
                         0      1        2     3   4    5 
        >>> word_list = ["Test", "test.", "..? ", ".!", "?", "!.?Test", "..test"]
        >>> Tokenizer.join_punc_chars(word_list, ".", 1)
        ('...?.!?!.?', 5)
        >>> word_list
        ['Test', 'test.', '..? ', '.!', '?', '!.?', 'Test', '..test']

        check last index
        >>> word_list = ["Test", "test.", "..? ", ".!", "?", "!.?Test"]
        >>> Tokenizer.join_punc_chars(word_list, ".", 1)
        ('...?.!?!.?', 5)
        >>> word_list
        ['Test', 'test.', '..? ', '.!', '?', '!.?', 'Test']
        """
        assert punc_word in _CH_SENT_END, word
        ind_new = ind 
        punc_word_new = [punc_word]
        while True:
            ind_new += 1 
            if ind_new>len(word_list)-1:
                ind_new -= 1 
                break
            tmp_word = word_list[ind_new].strip()
            m_starts = _RE_STARTS_SENT_END.match(tmp_word)
            if _RE_ONLY_SENT_END.match(tmp_word):
                punc_word_new.append(tmp_word)
            elif m_starts:
                ind_split = m_starts.end() 
                tmp_punc_word = tmp_word[:ind_split]
                word_list[ind_new:ind_new+1] = [tmp_punc_word, tmp_word[ind_split:]]
                punc_word_new.append(tmp_punc_word)
                # NOTE: ind_new stays same - increased by one
                break
            else:
                ind_new-=1
                break
        return "".join(punc_word_new), ind_new

    @classmethod
    def get_word_tag(cls, word):
        m = _RE_TAG.match(word)
        if not m: 
            return None, None, None
        return m.groupdict()["tag"], m.groupdict()["tag_options"], m.groupdict()["value"]

    
    @classmethod
    def split_text(cls, text):
        return _RE_SPLIT_WHITE_SPACE.split(text)

    # -------------------------------------------------

    @classmethod
    def preprocess_word_list(cls, word_list):
        """ preprocess word list - strip spaces, remove empty words
        and most important remove SHOUTING/UPPER CASE markup
        it is done sentence by sentence - par_start, .!? but only when >=4 tokens


        TODO: what to do with emphasize token markers E+1, E+2, E+3
              shouting is just like this. But you can't get everything at once ;)

        >>> t = Tokenizer()
        >>> t.preprocess_word_list(t.split_text("THIS IS UPPER CASE"))
        ['This', 'is', 'upper', 'case']
        
        Removes "upravni govor"
        >>> t.preprocess_word_list(t.split_text('Andjeo Jahvin je zapita : " Hagaro , sluskinjo Sarajina , odakle dolazis i kamo ides ? " " Bjezim , evo , od svoje gospodarice Saraje " , odgovori ona. ')) # doctest: +NORMALIZE_WHITESPACE
        ['Andjeo', 'Jahvin', 'je', 'zapita', '!', 'Hagaro', ',', 'sluskinjo',
         'Sarajina', ',', 'odakle', 'dolazis', 'i', 'kamo', 'ides', '?', '!',
         'Bjezim', ',', 'evo', ',', 'od', 'svoje', 'gospodarice', 'Saraje',
         '"', ',', 'odgovori', 'ona.'] 

        >>> t.preprocess_word_list(t.split_text('Nadjem samo trideset . " Evo se opet usudjujem govoriti Gospodinu " , nastavi dalje .')) # doctest: +NORMALIZE_WHITESPACE
        ['Nadjem', 'samo', 'trideset', '.', 'Evo', 'se', 'opet', 'usudjujem', 'govoriti', 
         'Gospodinu', '"', ',', 'nastavi', 'dalje', '.']
        
        TODO: Last " is not removed, is this ok?
        >>> t.preprocess_word_list(t.split_text('I rece Bog : " Za narastaje buduce : Dugu svoju u oblak stavljam ."')) # doctest: +NORMALIZE_WHITESPACE
        ['I', 'rece', 'Bog', '!', 'Za', 'narastaje', 'buduce', '!', 'Dugu', 'svoju',
         'u', 'oblak', 'stavljam', '."']

        >>> t.preprocess_word_list(t.split_text("Samo za plod stabla sto je nasred vrta rekao je Bog : ' Da ga niste jeli ! I ne dirajte u nj , da ne umrete ! '")) # doctest: +NORMALIZE_WHITESPACE
        ['Samo', 'za', 'plod', 'stabla', 'sto', 'je', 'nasred', 'vrta',
         'rekao', 'je', 'Bog', '!', 'Da', 'ga', 'niste', 'jeli', '!', 'I', 'ne',
         'dirajte', 'u', 'nj', ',', 'da', 'ne', 'umrete', '!']

        >>> t.preprocess_word_list(t.split_text('I rece Bog : " Neka bude svjetlost ! " I bi svjetlost .')) # doctest: +NORMALIZE_WHITESPACE
        ['I', 'rece', 'Bog', '!', 'Neka', 'bude', 'svjetlost', '!', 
         'I', 'bi', 'svjetlost', '.']

        >>> t.preprocess_word_list(t.split_text('This he said : " Today is the day. "'))
        ['This', 'he', 'said', '!', 'Today', 'is', 'the', 'day.']

        First one is too short - 3 is min length
        >>> t.preprocess_word_list(t.split_text("THIS IS. This is not."))
        ['THIS', 'IS.', 'This', 'is', 'not.']

        >>> t.preprocess_word_list(t.split_text(\"\"\"This is not upper case! 
        ... THIS IS UPPER CASE. This is not.\"\"\")) # doctest: +NORMALIZE_WHITESPACE
        ['This', 'is', 'not', 'upper', 'case!', 
         'This', 'is', 'upper', 'case.', 'This', 'is', 'not.']

        >>> t.preprocess_word_list(t.split_text(\"\"\"This is not UPPER CASE! 
        ... this is not UPPER CASE. This is NOT.\"\"\")) # doctest: +NORMALIZE_WHITESPACE
        ['This', 'is', 'not', 'UPPER', 'CASE!', 
         'this', 'is', 'not', 'UPPER', 'CASE.', 'This', 'is', 'NOT.']
        """
        # older logic ;)
        #word_list = [w.strip() for w in word_list if w]

        word_list_new = []

        word_list_last_ind = len(word_list)-1

        current_wl = []
        current_cnt_upper = 0

        ind = -1

        def is_word_upper(word):
            """ returns 1 if yes else 0. Currently used only once"""
            if word.isupper() or not word.isalpha():
                return 1
            return 0

        while True:
            ind+=1
            if ind>word_list_last_ind:
                assert not current_wl, current_wl
                break
            is_new_sentence = (ind==word_list_last_ind)
            word = word_list[ind]

            def get_next_word(word_list, ind):
                if ind is None:
                    return None
                i = ind+1
                while i<=word_list_last_ind:
                    #if not (i-ind)<250:
                    #    import pdb;pdb.set_trace() 
                    assert i-ind<250, "preprocessing problem - there is more than 250 empty words between %s and %s (locations %d-%d)" % (
                        word_list[ind-15:ind+1], word_list[i:i+15], ind, i)
                    if word_list[i]:
                        return i
                    i+=1
                return None
                
            if word:
                ind_next = get_next_word(word_list, ind)
                ind_next2 = get_next_word(word_list, ind_next)

                #       w wn wn2
                # 'this : "  Title' -> 'this ! Title'
                # 'this : 'Title' -> 'this ! Title'
                # 'this - "Title' -> 'this ! Title'
                # , '"', "'"
                if (ind_next is not None 
                    and ind_next2 is not None 
                    and word in (':', '-', ',', ';')
                    and word_list[ind_next] in ('"', "'")
                    and word_list[ind_next2].istitle()):
                    word = "!"
                    word_list[ind_next] = ""
                #       w wn    wn2
                # 'this " Title ... ' -> 'this ! Title'
                # 'this : Title ... ' -> 'this ! Title'
                elif (ind_next is not None 
                    and word in ('"', "'", ":")
                    and word_list[ind_next].istitle()):
                    word = "!"

                #     w wn wn2
                # 'this. - Title ... ' -> 'this. Title'
                elif (ind_next is not None 
                    and ind_next2 is not None 
                    and word.endswith(".")
                    and word_list[ind_next] in ('-', "!", '"', "'", "*")
                    and word_list[ind_next2].istitle()):
                    word_list[ind_next] = ""
                
                current_wl.append(word.strip())

                current_cnt_upper += is_word_upper(word)

                tag, tag_options, tag_value = cls.get_word_tag(word)

                
                # Not exact but good enough
                # at least 4 words are considered sentence - 
                # to avoid abbr. terminate sentence
                if not is_new_sentence:
                    is_new_sentence = len(current_wl)>=3 and (
                                         (tag=="par_start" or 
                                          word[-1] in (_CH_SENT_END)))

                if is_new_sentence and ind_next is not None:
                    # 'end." Title' -> 'end. Title'
                    if word_list[ind_next] in ('"', "'"):
                        word_list[ind_next] = ''

            if is_new_sentence and current_wl:
                def is_upper(cnt_upper, list_len):
                    return (((cnt_upper+0.0)/list_len)>=0.75)
                current_is_upper = is_upper(current_cnt_upper, len(current_wl))

                # TODO: wanted to implement joining/windowing several sentences
                #       in order to have better accuracy, but didn't managed to 
                #       do it right. current can be too small, but dump can be too long
                #dump_is_upper = is_upper(dump_cnt_upper, len(wl_dump))
                #if dump_is_upper and current_is_upper==dump_is_upper: # join else split

                if current_is_upper:
                    # lower all which
                    for i,w in enumerate(current_wl):
                        # TODO: how to avoid to call get_word_tag several times??
                        if cls.get_word_tag(w)[0] is None:
                            if i==0 and w.isupper():
                                w = w.title()
                            else:
                                w = w.lower()
                        word_list_new.append(w)
                else:
                    word_list_new.extend(current_wl)
                current_wl = []
                current_cnt_upper = 0
                 
        return word_list_new

    @classmethod
    def get_next_is_punct_title(cls, start_ind, word_list_next):
        """
        >>> T = Tokenizer
        >>> T.get_next_is_punct_title(1, ["Test", "test"])
        (False, None)
        >>> T.get_next_is_punct_title(1, ["test", "Test"])
        (False, None)
        >>> T.get_next_is_punct_title(1, ["...", "Test", "test"])
        (True, 2)
        >>> T.get_next_is_punct_title(1, ["...", "test", "test"])
        (False, None)
        >>> T.get_next_is_punct_title(1, ["...", "1", "Test"])
        (False, None)
        >>> T.get_next_is_punct_title(1, ["...", "#", "!", "Test", "test"])
        (True, 4)
        >>> T.get_next_is_punct_title(1, ["#", "$par_start%%test$", "test", "test"])
        (True, None)
        >>> T.get_next_is_punct_title(2, ["#", "$par_start%%test$", "#", "TEST"])
        (True, 5)
        >>> T.get_next_is_punct_title(2, [])
        (False, None)
        >>> T.get_next_is_punct_title(2, ["$par_start%%test$"])
        (True, None)
        """
        next_is_punct_title = False
        set_lower_title_ind = None
        for i, word in enumerate(word_list_next):
            # TODO: maybe this is not optimal - convert to token idea 
            if _RE_AFT_DOT_SENT_END_PUNC.match(word) is not None:
                continue 
            elif word[0].isupper():
                if i>0:
                    next_is_punct_title = True
                    set_lower_title_ind = start_ind + i
                break
            elif cls.get_word_tag(word)[0]=="par_start":
                next_is_punct_title = True
            else:
                break

        return next_is_punct_title, set_lower_title_ind

    @classmethod
    def preprocess_text(cls, text):
        """ REGEXP REPLACE PREPROCESS
        NOTE: insert space before and/or after some interpunction chars

        >>> Tokenizer.preprocess_text(unicode('''Alat­ni stro­je­vi za ski­da­nje ­srha, oš­tre­nje, bru­še­nje, vlač­no
        ... gla­ča­nje (honanje), glačanje brusnom prašinom (le­pa­nje), po­li­ra­nje ili
        ... druk­či­ju završnu obradu ko­vi­na ili ker­me­ta po­mo­ću bru­se­va, abra­zi­va
        ... ili sredstava za po­li­ra­nje, ozubljivanje rezanjem ili bru­še­njem ili za do­vr­ša­va­nje
        ... zup­ča­ni­ka iz tar. bro­ja 84.61''', "utf-8")).split() # doctest: +NORMALIZE_WHITESPACE
        [u'Alatni', u'strojevi', u'za', u'skidanje', u'srha', u',',
         u'o\u0161trenje', u',', u'bru\u0161enje', u',', u'vla\u010dno',
         u'gla\u010danje', u'(', u'honanje', u')', u',', u'gla\u010danje',
         u'brusnom', u'pra\u0161inom', u'(', u'lepanje', u')', u',',
         u'poliranje', u'ili', u'druk\u010diju', u'zavr\u0161nu', u'obradu',
         u'kovina', u'ili', u'kermeta', u'pomo\u0107u', u'bruseva', u',',
         u'abraziva', u'ili', u'sredstava', u'za', u'poliranje', u',',
         u'ozubljivanje', u'rezanjem', u'ili', u'bru\u0161enjem', u'ili', u'za',
         u'dovr\u0161avanje', u'zup\u010danika', u'iz', u'tar.', u'broja',
         u'84.61']
        """
        # ------------------- MAIN FUNCTION for replacements ----------------------
        def fun_repl_wrap_spaces(m):
            wrap_space = m.groupdict()["wrap_space"]
            wrap_space_comma = m.groupdict()["wrap_space_comma"]
            wrap_dash = m.groupdict()["wrap_dash"]
            wrap_2nl  = m.groupdict()["wrap_2nl"]
            tag_spec= m.groupdict()["tag_spec"]
            if wrap_dash:
                return "\n"+ r"$par_start%dash%" + wrap_dash[:5] + "$ \n"
            elif wrap_2nl:
                return "\n"+ r"$par_start%2nl%" + "NLx%d" % len(wrap_2nl) + "$ \n"
            elif tag_spec:
                return " " + tag_spec + " "
            elif wrap_space_comma:
                # don't wrap first char - e.g. "9,test" -> "9 , test" (9, is matched)
                assert not wrap_space, m.groupdict()
                assert len(wrap_space_comma)==3, m.groupdict()
                bef,comma,aft = wrap_space_comma
                if bef.isdigit() and aft.isdigit():
                    return wrap_space_comma
                return " ".join(wrap_space_comma)

            assert wrap_space, m.groupdict()
            return " " + wrap_space + " "
            
        assert isinstance(text, unicode)
        text_new = text
        for regexp, repl in _RE_SENT_REPLACE_CHARS_PAIRS:
            text_new = regexp.sub(repl, text_new)
        text_new = _RE_SENT_DO_WRAP.sub(fun_repl_wrap_spaces, text_new)
        return text_new

    def tokenize(self, text_or_paramsobject, cp="utf-8", in_abbr_list=None, in_name_list=None):
        " splits and marks if sentence end, abbr, name"
        if isinstance(text_or_paramsobject, basestring):
            params = TokenizerParams()
            params.abbr_list = in_abbr_list
            params.name_list = in_name_list
            params.text = text_or_paramsobject
        elif isinstance(text_or_paramsobject, TokenizerParams):
            assert in_abbr_list is None and in_name_list is None, "should be empty %s, %s" % (in_abbr_list, in_name_list)
            params = text_or_paramsobject

        else:
            raise Exception("for first param I expected string or TokenizerParams object, got %s" % text_or_paramsobject)

        assert len(params.text)>0

        params.text = to_unicode2(params.text, cp)
        params.abbr_list = self._check_item_list(Abbr, params.abbr_list)
        params.name_list = self._check_item_list(Name, params.name_list)

            
        # ------------- REGEXP REPLACE PREPROCESS -----------------
        # NOTE: insert space before and/or after some interpunction chars
        params.text = self.preprocess_text(params.text)

        # ------------- SPLIT BY WHITESPACE -----------------------
        #word_list = list(_RE_SPLIT_WHITE_SPACE.split(params.text))
        params.word_list = self.split_text(params.text)

        def _add_token(current, name_list, word_or_name_or_abbr, is_sent_end=False):
            known_obj = None
            word = word_or_name_or_abbr
            is_sent_start=(len(current)==0)
            if isinstance(word_or_name_or_abbr, Abbr):
                known_obj = word_or_name_or_abbr
                word = word_or_name_or_abbr.value
            elif word.istitle() and len(word)>1:
                known_name = name_list.add_or_update(word)
                if known_name and known_name.is_confirmed and not (is_sent_start and not known_name.a_start_sent):
                    known_obj = name_list.add_or_update(word)
                elif not is_sent_start:
                    # detected name
                    known_obj = known_name
                    known_obj.confirm()
            current.append(Token(word, is_sent_start=is_sent_start,
                                 is_sent_end=is_sent_end, 
                                 known_obj=known_obj))

        # --------------- FIRST PASS - preprocess ---------------

        # OLD_LOGIC: params.word_list = [w.strip() for w in params.word_list if w]
        params.word_list = self.preprocess_word_list(params.word_list)

        # --------------- SECOND PASS - tokenize and yield ---------------
        current = []
        ind = -1 # this is important
        # TODO: second pass will better dinstinguish between abbr. and sent. end and Name and sent start

        def postprocess_sentence(current, mark_last=False):
            """ I needed this for something and then rejected. Can be useful later ... """
            #if not word_next.endswith(".") and word_next.istitle():
            #   params.word_list[ind+1] = word_next.lower()
            if not current:
                return []
            current_new = []
            current_ind_last = len(current) - 1
            for i, token in enumerate(current):
                if mark_last and i==current_ind_last:
                    token.is_sent_end = True
                current_new.append(token)
            return current_new

        while True:
            ind+=1
            #assert ind<=len(params.word_list)
            if ind==len(params.word_list):
                # send last sentence
                for i, token in enumerate(postprocess_sentence(current, mark_last=True)):
                    yield token
                break
            word_outer = params.word_list[ind]
            word_outer = word_outer.strip()
            # TODO: upper?
            assert word_outer, ind
            word_inner_list = self.split_word(word_outer, params.abbr_list) 
            if word_inner_list:
                # NOTE: content changed - stay on first new and go on
                params.word_list[ind:ind+1] = word_inner_list
            word = params.word_list[ind].strip()
            assert word, word_outer
            is_last_word = (ind+1==len(params.word_list))
            word = word.strip()
            assert word
            is_new_sentence = False


            word_next = NOVALUE_WORD
            word_next2 = NOVALUE_WORD
            if not is_last_word:
                word_next = params.word_list[ind+1].strip()
                if not (ind+2==len(params.word_list)):
                    word_next2 = params.word_list[ind+2].strip()

            tag, tag_options, tag_value = self.get_word_tag(word)
            if tag:
                _add_token(current, params.name_list, word)
                if tag=="par_start":
                    is_new_sentence = True
            elif word[-1] in (_CH_SENT_END):
                # TODO: needs better distinction between . (problematic) and !? 

                if len(word)==1 and not current:
                    # TODO: append to previous??
                    # pass # ignored leading .?!
                    logging.warning("punct. '%s' leading sentence - no current sentence" % word)
                    _add_token(current, params.name_list, word)
                    # else: sentences[-1]+=" "+word
                # RETURN_THIS: 
                # elif len(word)==1:
                #     is_new_sentence = True
                else:
                    # test. Is -> New sent
                    # test. is -> not new sent

                    # abbr. or sentence end
                    is_abbr = False
                    is_number_or_romnr = False
                    word_list_next = params.word_list[ind+1:ind+6]
                    next_is_punct_title, set_lower_title_ind = self.get_next_is_punct_title(ind+1, 
                                                                                   word_list_next)
                    #if word.startswith("2008."):
                    #    import pdb;pdb.set_trace() 
                    if self.looks_like_abbr(word):
                        # known_abbr
                        known_abbr = params.abbr_list.add_or_update(word)

                        # don't apply abbr. in these situations
                        next_is_sent_end = next_is_punct_title

                        # don't allow - not bef name and next is name, and abbr. at the end of sentence (next is par_start)
                        if known_abbr.is_confirmed:
                            #import pdb; pdb.set_trace() 
                            if (not(   (not known_abbr.a_bef_name and word_next[0].isupper())
                                     or next_is_sent_end) 
                                and params.fun_abbr_name(word, known_abbr, params, word_list_next)):
                                _add_token(current, params.name_list, known_abbr)
                                is_abbr = True
                        # sentence starts with I. III. Jr. 
                        elif len(current)==0:
                            # "I. Počeci ..." -> I.(romnr) + počeci
                            if self.looks_like_roman_number(word, can_end_dot=True):
                                is_number_or_romnr = True
                                _add_token(current, params.name_list, word)
                                if not word_next.endswith(".") and word_next.istitle():
                                    params.word_list[ind+1] = word_next.lower() # won't be recognized as name
                            # next two have the same logic
                            # Mr. Magoo is nice guy. 
                            elif params.fun_abbr_name(word, known_abbr, params, word_list_next):
                                # TODO: until there is no distinction between short-name-abbr and other - the logic is the same
                                _add_token(current, params.name_list, word)
                                is_abbr = True
                            # elif (    self.looks_like_abbr(word, istitle=True) 
                            #       and word_next.isalpha() and word_next.istitle()
                            #       and params.fun_abbr_name(word, known_abbr, params, word_list_next)):
                            #     # TODO: there should be distinction between name and other abbrs.
                            #     # known_abbr.confirm() 
                            #     _add_token(current, params.name_list, word)
                            #     is_abbr = True
                            # # SO. this not good.
                            # elif params.fun_abbr_name(word, known_abbr, params, word_list_next):
                            #     # don't end the sentence - will be abbr.
                            #     _add_token(current, params.name_list, word)
                            #     is_abbr = True

                        # new abbr.?
                        elif (not is_last_word
                              and (
                                      # don't apply abbr. in these situations
                                      # word_next.istitle() -> isupper()
                                      not (next_is_sent_end or word_next[0].isupper())
                                      or (
                                          self.looks_like_abbr(word, istitle=True)
                                          and word_next.istitle()
                                          )
                                      )
                               and params.fun_abbr_name(word, known_abbr, params, word_list_next)
                             ):
                            known_abbr.confirm() 
                            _add_token(current, params.name_list, known_abbr)
                            is_abbr = True
                    elif (self.looks_like_number(word)
                          or self.looks_like_roman_number(word)):
                        is_number_or_romnr = True
                        _add_token(current, params.name_list, word)
                    # order nr. like 1. 2113. Next word must be titled.
                    # 2013.), is also ok
                    # TODO: this is not safe, since next word can be Name and then I false declare it not number.
                    #       e.g. The 123. John Mc. Street.
                    #       probably this line needs to updated - 2003. Name -> not sent. end
                    #         not (word_next.isalpha() and word_next.istitle() and !!!not word_next is name)
                    elif (word.endswith(".") and 
                         not (word_next.isalpha() and word_next.istitle())
                         #and (len(word_next)>1 or not word_next.isalpha()) 
                         and (
                              (self.looks_like_number(word, can_end_dot=True)
                           or self.looks_like_roman_number(word, can_end_dot=True)))
                         ):
                        is_number_or_romnr = True
                        _add_token(current, params.name_list, word)


                    # sentence end!
                    if not is_abbr and not is_number_or_romnr:
                        if set_lower_title_ind is not None:
                            params.word_list[set_lower_title_ind] = params.word_list[set_lower_title_ind].lower() # won't be recognized as name  
                            
                        if len(word)!=1:
                            _add_token(current, params.name_list, word[:-1])
                        punc_word = word[-1]
                        punc_word, ind = self.join_punc_chars(params.word_list, punc_word, ind)
                        _add_token(current, params.name_list, punc_word, is_sent_end=True)
                        is_new_sentence = True
            else:
                # normal start/middle word
                _add_token(current, params.name_list, word)
            if is_new_sentence:
                # NOTE: don't forget to copy code at the end of loop
                for i, token in enumerate(postprocess_sentence(current)):
                    yield token
                current = []

        return 

# TODO: move this function somewhere!!!
# TODO: is this needed, not in this way, see _RE_ROMNR and unit test - that is much easier
#def roman2nr(s, raise_on_err=True):
#    """
#    raise_on_err if false then will return None on error
#        if true then it raises ValueError
#
#    >>> roman2nr("MCMXCIII")
#    1993
#    >>> roman2nr("MCMIII")
#    1903
#    >>> roman2nr("MMCMIII")
#    2903
#    >>> roman2nr("III")
#    3
#    >>> roman2nr("IX")
#    9
#    >>> roman2nr("VIII")
#    8
#    >>> roman2nr("IV")
#    4
#
#    # TODO: This passes
#    >>> roman2nr("IIIIII")
#    6
#
#    >>> roman2nr("") # doctest: +ELLIPSIS 
#    Traceback (most recent call last):
#        ...
#    ValueError: ...
#
#    >>> roman2nr("", raise_on_err=False) is None
#    True
#    >>> roman2nr("VIII", raise_on_err=False)
#    8
#
#    # TODO: check if this is legal IM (1000-1=999), XD, ID, etc.
#    """
#    map = {}
#    map["M" ] = (1000, 1000) 
#    map["L" ] = (500 , 100) 
#    map["C" ] = (100 , 100) 
#    map["D" ] = (50  , 10) 
#    map["X" ] = (10  , 10) 
#    map["V" ] = (5   , 1) 
#    map["I" ] = (1   , 1) 
#
#    map2 = {}
#    map2["CM"] = (900, 90)
#    map2["XC"] = (90 , 9)
#    # check this?? and similar
#    #map2["XD"] = (40 , -1)
#    map2["IX"] = (9  , -1)
#    map2["IV"] = (4  , -1)
#
#    sum = 0
#    last_added = None
#    next_le = None
#    i_last = len(s) - 1
#    i = 0
#    try:
#        if not s:
#            raise ValueError("input string is empty")
#        while True:
#            if i<i_last:
#                ch_next = s[i+1]
#            elif i==i_last:
#                ch_next = None
#            else:
#                break
#            ch = s[i]
#            if ch_next and ch+ch_next in map2.keys():
#                to_add, next_le_fut = map2[ch+ch_next]
#                i+=1
#            elif ch in map.keys():
#                to_add, next_le_fut = map[ch]
#            else:
#                raise ValueError("invalid character %d, %s, %s, %s" % (i, ch, ch_next, s))
#            if next_le:
#                if not (to_add<=next_le):
#                    raise ValueError("invalid next character bigger than prev %d, %s, %s, %s, %s" % (i, ch, ch_next, s, next_le))
#            sum+=to_add
#            i+=1
#            next_le = next_le_fut
#    except ValueError, e:
#        if raise_on_err:
#            raise e
#        return None
#    return sum

def tokenize(text_or_paramsobject, cp="utf-8", in_abbr_list=None, in_name_list=None):
    tokenizer = Tokenizer()
    result = tokenizer.tokenize(text_or_paramsobject=text_or_paramsobject, 
                                cp=cp, in_abbr_list=in_abbr_list, 
                                in_name_list=in_name_list)
    return result

def main():
    # TODO: tokenize input text)
    pass

def test():
    print "%s: running doctests" % __name__
    import doctest
    # RETURN_THIS: 
    doctest.testmod()

    fname = "test_sentence.txt"
    print "%s: running doctests" % fname
    doctest.testfile(fname)

if __name__ == "__main__":
    test()
    #main()


