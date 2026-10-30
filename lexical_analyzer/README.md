# Lexical Analyzer Tool
Identifies tokens, keywords, operators, identifiers, constants and symbols in source code, and reports lexical errors.
(KL University, CSE – Batch 2 Section 4: Y. Nimisha, K. Sanuhya, A. Nikitha, Y. Revanth. Guide: K S Niraja)

**Stack:** Python 3.8+ (backend, `re` module, standard library only) · HTML/CSS/JavaScript (frontend). No installation needed.

## Run
    python app.py            # opens http://127.0.0.1:8000   (optional: python app.py 9000)

## Command line
    python lexer.py program.c            # token table
    python lexer.py program.py --json    # JSON output

## Tests
    python -m unittest discover tests -v

## Features
- Type/paste code or upload a file (.c .h .java .py .js); live analysis as you type; C, Java, Python, JavaScript
- Token classes: Keyword (data type / control flow / modifier…), Identifier (variable / function / class),
  Operator (arithmetic, relational, logical, bitwise, assignment…), Constant (int, float, hex, binary, string, char, boolean, null),
  Symbol, Preprocessor, Comment
- Error detection: unrecognized symbols, malformed numbers (`2x`), unterminated strings/chars/comments, unmatched brackets (click an error to jump to it)
- Colour-coded source with hover tooltips, filterable/searchable token table, summary counts, JSON/CSV export

## Structure
    app.py           HTTP server + REST API (POST /api/analyze, GET /api/meta)
    lexer.py         scanner: whitespace removal → master regex → classification → diagnostics
    static/index.html  UI
    tests/test_lexer.py

Known limits: Python indentation tokens and JavaScript regex literals are not modelled.
