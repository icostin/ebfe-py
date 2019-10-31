from collections import namedtuple
from zlx.io import omsg

#* error ********************************************************************
class error (RuntimeError):
    def __init__ (self, fmt, *a, **b):
        RuntimeError.__init__(self, fmt.format(*a, **b))

UNKNOWN_NODE = 0
CDATA_NODE = 1
TAG_NODE = 2

#* node *********************************************************************
class node (object):
    node_type = UNKNOWN_NODE
    sub_nodes = tuple()
    def __init__ (self):
        object.__init__(self)
    def has_only_whitespaces (self):
        return False
    def del_whitespace_sub_nodes (self):
        self.sub_nodes = [ n for n in self.sub_nodes if not n.has_only_whitespaces() ]

#* cdata_node ***************************************************************
class cdata_node (node):
    node_type = CDATA_NODE
    def __init__ (self, text):
        node.__init__(self)
        self.text = text
    def has_only_whitespaces (self):
        return self.text.isspace()
    def __repr__ (self):
        return 'cdata({!r})'.format(self.text)

#* tag_node *****************************************************************
class tag_node (node):
    node_type = TAG_NODE
    def __init__ (self, tag_name = None, attr_map = None, closed = False):
        node.__init__(self)
        self.tag_name = tag_name
        self.attr_map = attr_map or {}
        self.closed = closed
    def add_sub_node (self, node):
        if isinstance(self.sub_nodes, tuple):
            self.sub_nodes = list(self.sub_nodes)
        self.sub_nodes.append(node)
    def sub_nodes_in_depth (self):
        for n in self.sub_nodes:
            yield n
            for sn in n.sub_nodes_in_depth():
                yield sn
    def __repr__ (self):
        return 'tag_node(name: {}, closed: {}, attrs={!r}, sub_nodes={!r}' \
                .format(self.tag_name, self.closed, 
                        self.attr_map, self.sub_nodes)

tag_close = namedtuple('tag_close', 'tag_name'.split())

#* sgml_parser **************************************************************
class sgml_parser (object):
    def __init__ (self, text):
        self.text = text
        self.text_len = len(text)
        self.pos = 0

    def got_text (self):
        return self.pos < self.text_len

    def can_match_whitespace (self):
        return self.pos < self.text_len and self.text[self.pos] in " \t\n"
    def skip_whitespace (self):
        while self.can_match_whitespace():
            self.pos += 1
    def can_match (self, s):
        slen = len(s)
        return self.text[self.pos : self.pos + slen] == s
    def match (self, s):
        if self.can_match(s):
            self.pos += len(s)
        else:
            raise error("expecting {!r} at {!r}", s, self.text[self.pos:])
    def try_match (self, s):
        r = self.can_match(s)
        if r: self.match(s)
        return r
    def extract_id (self, extra_chars = '_'):
        i = self.pos + 1
        ch = self.text[self.pos : i] 
        if not (ch.isalpha() or ch == '_'):
            return None
        while i < self.text_len and \
                (self.text[i : i + 1].isalnum() or self.text[i : i + 1] in extra_chars):
            i += 1
        v = self.text[self.pos : i]
        self.pos = i
        return v
    def extract_char (self):
        if self.try_match('&'):
            e = self.extract_id()
            self.match(';')
            if e == 'amp': return '&'
            if e == 'lt': return '<'
            if e == 'gt': return '>'
            if e in ('dq', 'dquot', 'dquote'): return '"'
            if e in ('q', 'quot', 'quote'): return '\''
            else: raise error('unrecognized char escape "&{};"', e)
        else:
            ch = self.text[self.pos]
            self.pos += 1
        return ch
    def extract_until (self, s):
        p = self.text.find(s, self.pos)
        if p == -1: p = self.text_len
        r = []
        while self.pos < p:
            r.append(self.extract_char())
        return ''.join(r)

    def extract_str (self):
        self.match('"')
        s = []
        while not self.can_match('"'):
            s.append(self.extract_char())
        self.match('"')
        return ''.join(s)

    def can_extract_num (self):
        return self.text[self.pos] in '0123456789'

    def extract_num (self):
        if not self.can_extract_num():
            raise error('expecting digits not {}', self.text[self.pos:])
        n = 0
        while self.can_extract_num():
            n = n * 10 + ord(self.text[self.pos]) - 48
        return n

    def can_extract_bool (self):
        return self.text[self.pos:].startswith('true') or \
                self.text[self.pos:].startswith('false')
    def extract_bool (self):
        if self.can_match('true'):
            self.match('true')
            return true
        elif self.can_match('false'):
            self.match('false')
            return false
        else:
            raise error('expecting bool not {}', self.text[self.pos:])
            
    def extract_lit (self):
        if self.can_match('"'): return self.extract_str()
        if self.can_extract_num(): return self.extract_num()
        if self.can_extract_bool(): return self.extract_bool()
        raise error('expecting literal not {}', self.text[self.pos:])

    def extract_token (self):
        if not self.got_text():
            raise error('no mode data')

        if self.try_match('</'):
            t = self.extract_id()
            self.match('>')
            return tag_close(t)
        elif self.try_match('<'):
            t = tag_node()
            t.tag_name = self.extract_id()
            while True:
                self.skip_whitespace()
                if self.try_match('/>'):
                    t.closed = True
                    return t
                if self.try_match('>'):
                    return t
                a = self.extract_id()
                self.skip_whitespace()
                self.match('=')
                v = self.extract_lit()
                t.attr_map[a] = v
        else:
            s = self.extract_until('<')
            n = cdata_node(s)
            #i = self.text.find('<', self.pos)
            #if i < 0: i = self.text_len
            #n = cdata_node(self.text[self.pos : i])
            #self.pos = i
            return n

    def extract_node (self):
        t = self.extract_token()
        if isinstance(t, cdata_node):
            return t
        if isinstance(t, tag_node):
            while not t.closed:
                sn = self.extract_node()
                if isinstance(sn, tag_close):
                    if sn.tag_name != t.tag_name:
                        raise error('closing tag {} but expecting to close {}',
                                sn.tag_name, t.tag_name)
                    t.closed = True
                else:
                    t.add_sub_node(sn)
            return t
        if isinstance(t, tag_close):
            return t
        raise error('not expecting {!r}', t)

    def extract_node_list (self):
        l = []
        while self.got_text():
            n = self.extract_node()
            l.append(n)
        return l



