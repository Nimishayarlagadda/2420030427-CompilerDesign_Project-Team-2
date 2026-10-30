
"""Regex-based lexical analyzer engine.
CLI: python lexer.py program.c [--lang c|java|python|js] [--json]
"""
import re
import sys
import json
from bisect import bisect_right
from collections import Counter

LANGS = {'c': 'C', 'java': 'Java', 'python': 'Python', 'js': 'JavaScript'}

KW = {
    'c': "auto break case char const continue default do double else enum extern float for goto if inline int long register return short signed sizeof static struct switch typedef union unsigned void volatile while",
    'java': "abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static super switch synchronized this throw throws transient try void volatile while var",
    'python': "and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield",
    'js': "async await break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while with yield",
}
KW = {k: set(v.split()) for k, v in KW.items()}

_lit = {'true': 'Boolean', 'false': 'Boolean', 'null': 'Null'}
LIT = {
    'c': {},
    'java': _lit,
    'js': _lit,
    'python': {'True': 'Boolean', 'False': 'Boolean', 'None': 'Null'}
}

TYPES = set("int char float double void long short signed unsigned boolean byte".split())
CTRL = set("if else for while do switch case default break continue return goto try catch finally throw throws yield elif except raise with assert pass await".split())
MOD = set("static const volatile extern register public private protected final abstract synchronized transient native inline async global nonlocal".split())
OPKW = set("and or not in is instanceof sizeof typeof delete new".split())


def kw_sub(w):
    return (
        'Data type' if w in TYPES else
        'Control flow' if w in CTRL else
        'Modifier' if w in MOD else
        'Operator keyword' if w in OPKW else
        'Declaration'
    )


OPG = [
    ('Arithmetic', '+ - * / % ** //'),
    ('Increment/Decrement', '++ --'),
    ('Relational', '== != <= >= < > === !=='),
    ('Logical', '&& || !'),
    ('Bitwise', '& | ^ ~ << >> >>>'),
    ('Assignment', '= += -= *= /= %= &= |= ^= <<= >>= >>>= **= //= := ??='),
    ('Other', '? -> :: => ?? ?. ... @')
]

OPSUB = {o: g for g, s in OPG for o in s.split()}

_c = "<<= >>= ... -> ++ -- << >> <= >= == != && || += -= *= /= %= &= |= ^= + - * / % = < > ! ~ & | ^ ?"

OPS = {
    'c': _c,
    'java': _c + " >>> >>>= :: @",
    'js': _c + " === !== >>>= **= ??= >>> => ?? ?. **",
    'python': "**= //= >>= <<= -> := ** // == != <= >= << >> += -= *= /= %= &= |= ^= @ + - * / % = < > & | ^ ~"
}

SYM = {
    '(': 'Left parenthesis',
    ')': 'Right parenthesis',
    '{': 'Left brace',
    '}': 'Right brace',
    '[': 'Left bracket',
    ']': 'Right bracket',
    ';': 'Semicolon',
    ',': 'Comma',
    '.': 'Dot',
    ':': 'Colon',
    '#': 'Hash'
}

ERR = {
    'ERR_COMMENT': 'Unterminated block comment',
    'ERR_STR': 'Unterminated string literal',
    'ERR_CHAR': 'Invalid or unterminated character literal',
    'ERR_NUM': 'Malformed number / identifier cannot start with a digit'
}

DQ = r'"(?:\\.|[^"\\\n])*"'
SQ = r"'(?:\\.|[^'\\\n])*'"

NUM = (
    r'(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|'
    r'(?:\d[\d_]*\.[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?|'
    r'\d[\d_]*[eE][+-]?\d+|\d[\d_]*)[uUlLfFdD]*(?![A-Za-z0-9_])'
)


def build(lang):
    r = []

    if lang == 'python':
        r.append(('COMMENT', r'#[^\n]*'))
        r.append((
            'STRING',
            r'[rRbBfFuU]{0,2}(?:"""[\s\S]*?"""|'
            + "'''[\\s\\S]*?'''" + '|'
            + DQ + '|' + SQ + ')'
        ))
        r.append(('ERR_STR', r'[rRbBfFuU]{0,2}["\'][^\n]*'))

    else:
        r += [
            ('COMMENT', r'//[^\n]*|/\*[\s\S]*?\*/'),
            ('ERR_COMMENT', r'/\*[\s\S]*')
        ]

        if lang == 'c':
            r.append(('PREPROC', r'#[^\n]*'))

        if lang == 'js':
            r += [
                ('STRING', DQ + '|' + SQ + r'|`[\s\S]*?`'),
                ('ERR_STR', r'''["'`][^\n]*''')
            ]
        else:
            r += [
                ('STRING', DQ),
                ('CHAR', r"'(?:\\[0-9a-zA-Z]+|\\.|[^'\\\n])'"),
                ('ERR_STR', r'"[^\n]*'),
                ('ERR_CHAR', r"'[^\n]*")
            ]

    r += [
        ('NUM', NUM),
        ('ERR_NUM', r'\d[\w.]*')
    ]

    r.append((
        'ID',
        {
            'c': r'[A-Za-z_][A-Za-z0-9_]*',
            'python': r'[^\W\d]\w*'
        }.get(lang, r'[^\W\d][\w$]*|\$[\w$]*')
    ))

    r.append((
        'OP',
        '|'.join(
            re.escape(o)
            for o in sorted(
                set(OPS[lang].split()),
                key=len,
                reverse=True
            )
        )
    ))

    syms = ''.join(
        s for s in SYM
        if not (lang == 'python' and s == '#')
    )

    r += [
        ('SYM', '[' + re.escape(syms) + ']'),
        ('WS', r'\s+'),
        ('ERR_CH', r'.')
    ]

    return r


def classify(k, v, lang):
    # Comments are handled separately in analyze()
    if k == 'COMMENT':
        return dict(type='Comment', sub='Block' if v.startswith('/*') else 'Line')

    if k == 'PREPROC':
        return dict(type='Preprocessor', sub=(v[1:].split() or [''])[0])

    if k == 'STRING':
        return dict(type='Constant', sub='String')

    if k == 'CHAR':
        return dict(type='Constant', sub='Character')

    if k == 'NUM':
        low = v.lower()
        sub = (
            'Hexadecimal' if low.startswith('0x') else
            'Binary' if low.startswith('0b') else
            'Float' if re.search(r'[.e]', low) else
            'Integer'
        )
        return dict(type='Constant', sub=sub)

    if k == 'ID':
        if v in LIT[lang]:
            return dict(type='Constant', sub=LIT[lang][v])

        if v in KW[lang]:
            return dict(type='Keyword', sub=kw_sub(v))

        return dict(type='Identifier', sub='Variable')

    if k == 'OP':
        return dict(type='Operator', sub=OPSUB[v])

    if k == 'SYM':
        return dict(type='Symbol', sub=SYM[v])

    return dict(
        type='Error',
        sub='Lexical error',
        msg=ERR.get(k, "Unrecognized symbol '%s'" % v)
    )


def analyze(code, lang='c'):
    lang = lang if lang in LANGS else 'c'

    pat = re.compile(
        '|'.join(
            '(?P<%s>%s)' % (n, p)
            for n, p in build(lang)
        )
    )

    starts = [0] + [m.end() for m in re.finditer('\n', code)]

    toks = []
    pos = 0
    ws = 0

    while pos < len(code):
        m = pat.match(code, pos)

        if m is None:
            break

        k = m.lastgroup
        v = m.group()
        s = pos
        pos = m.end()

        # Ignore whitespace, including multiple spaces and tabs.
        if k == 'WS':
            ws += len(v)
            continue

        # Detect comments but do NOT add them to the token list.
        # This applies to // comments, /* */ comments, and Python # comments.
        if k == 'COMMENT':
            continue

        # Preserve the existing error handling for unfinished comments.
        ln = bisect_right(starts, s)

        if k == 'PREPROC' and code[starts[ln - 1]:s].strip():
            k, v, pos = 'SYM', '#', s + 1

        t = classify(k, v, lang)

        t.update(
            id=len(toks) + 1,
            value=v,
            line=ln,
            col=s - starts[ln - 1] + 1,
            start=s,
            len=len(v)
        )

        toks.append(t)

    # All tokens here are visible tokens because comments were skipped.
    sig = toks

    for i, t in enumerate(sig):
        if t['type'] != 'Identifier':
            continue

        nxt = sig[i + 1]['value'] if i + 1 < len(sig) else ''
        prv = sig[i - 1]['value'] if i else ''

        t['sub'] = (
            'Function' if nxt == '(' else
            'Class' if prv in (
                'class', 'struct', 'enum', 'interface', 'union', 'new'
            ) else
            'Variable'
        )

    diags = []
    stack = []

    for t in sig:
        if t['type'] == 'Error':
            diags.append(dict(
                sev='error',
                msg=t['msg'],
                id=t['id']
            ))

        elif t['type'] == 'Symbol' and t['value'] in '([{':
            stack.append(t)

        elif t['type'] == 'Symbol' and t['value'] in ')]}':
            want = {')': '(', ']': '[', '}': '{'}[t['value']]

            if stack and stack[-1]['value'] == want:
                stack.pop()
            else:
                diags.append(dict(
                    sev='warning',
                    msg="Unmatched '%s'" % t['value'],
                    id=t['id']
                ))

    diags += [
        dict(
            sev='warning',
            msg="Unclosed '%s'" % t['value'],
            id=t['id']
        )
        for t in stack
    ]

    by_id = {t['id']: t for t in toks}

    for d in diags:
        t = by_id[d['id']]
        d.update(
            line=t['line'],
            col=t['col'],
            start=t['start'],
            len=t['len']
        )

    cnt = Counter(t['type'] for t in toks)

    stats = dict(
        lines=code.count('\n') + 1 if code else 0,
        chars=len(code),
        whitespace=ws,
        tokens=sum(
            v for k, v in cnt.items()
            if k not in ('Comment', 'Error')
        ),
        errors=cnt['Error'],
        counts=dict(cnt),
        unique_identifiers=len({
            t['value'] for t in toks
            if t['type'] == 'Identifier'
        })
    )

    return dict(
        language=lang,
        tokens=toks,
        diagnostics=diags,
        stats=stats
    )


if __name__ == '__main__':
    a = sys.argv[1:]

    if not a or a[0] in ('-h', '--help'):
        sys.exit(__doc__)

    lang = (
        a[a.index('--lang') + 1]
        if '--lang' in a
        else {
            'java': 'java',
            'py': 'python',
            'js': 'js'
        }.get(a[0].rsplit('.', 1)[-1], 'c')
    )

    with open(a[0], encoding='utf-8') as f:
        res = analyze(f.read(), lang)

    if '--json' in a:
        print(json.dumps(res, indent=2))
        sys.exit()

    print('%-5s %-5s %-13s %-20s %s' % (
        'Line', 'Col', 'Type', 'Category', 'Lexeme'
    ))

    for t in res['tokens']:
        print('%-5d %-5d %-13s %-20s %s' % (
            t['line'],
            t['col'],
            t['type'],
            t['sub'],
            t['value'].replace('\n', ' ')[:50]
        ))

    print(
        '\n',
        res['stats']['tokens'],
        'tokens,',
        res['stats']['errors'],
        'errors'
    )
