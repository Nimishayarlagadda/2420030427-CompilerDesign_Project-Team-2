import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lexer import analyze

def kinds(code, lang='c'):
    return [(t['type'], t['sub'], t['value']) for t in analyze(code, lang)['tokens']]

class LexerTests(unittest.TestCase):
    def test_basic_c(self):
        k = kinds('int x = a + 42;')
        self.assertEqual(k[0], ('Keyword', 'Data type', 'int'))
        self.assertEqual(k[1][0], 'Identifier')
        self.assertEqual(k[2], ('Operator', 'Assignment', '='))
        self.assertEqual(k[4], ('Operator', 'Arithmetic', '+'))
        self.assertEqual(k[5], ('Constant', 'Integer', '42'))
        self.assertEqual(k[6], ('Symbol', 'Semicolon', ';'))
    def test_longest_operator(self):
        self.assertEqual(kinds('a<<=b')[1][2], '<<=')
        self.assertEqual(kinds('i++')[1], ('Operator', 'Increment/Decrement', '++'))
    def test_numbers(self):
        self.assertEqual([t[1] for t in kinds('0x1F 3.14 2e3 7')], ['Hexadecimal', 'Float', 'Float', 'Integer'])
    def test_function_detection(self):
        self.assertEqual(kinds('main(x)')[0][1], 'Function')
    def test_errors(self):
        r = analyze('int 2x = $; char c = \'ab; "oops', 'c')
        msgs = [d['msg'] for d in r['diagnostics']]
        self.assertTrue(any('Malformed' in m for m in msgs))
        self.assertTrue(any("'$'" in m for m in msgs))
        self.assertTrue(any('character' in m for m in msgs))
        r = analyze('/* never closed', 'c')
        self.assertIn('Unterminated block comment', r['diagnostics'][0]['msg'])
    def test_bracket_balance(self):
        self.assertEqual(len(analyze('f(a[1)', 'c')['diagnostics']), 3)
        self.assertEqual(analyze('f(a[1]);', 'c')['diagnostics'], [])
    def test_comments_and_positions(self):
        r = analyze('x // hi\ny', 'c')
        self.assertEqual(r['stats']['tokens'], 2)
        self.assertEqual((r['tokens'][-1]['line'], r['tokens'][-1]['col']), (2, 1))
    def test_other_languages(self):
        self.assertEqual(kinds('def f(): return None', 'python')[0], ('Keyword', 'Declaration', 'def'))
        self.assertEqual(kinds('None', 'python')[0], ('Constant', 'Null', 'None'))
        self.assertEqual(kinds('a === b', 'js')[1][1], 'Relational')
        self.assertEqual(kinds('"""doc\nstr"""', 'python')[0][1], 'String')
        self.assertEqual(kinds('#include <stdio.h>')[0][0], 'Preprocessor')

if __name__ == '__main__':
    unittest.main()
