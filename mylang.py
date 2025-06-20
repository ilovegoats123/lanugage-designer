import re
import sys

# === 1. Design the Language ===
# Example language: imperative, dynamic, strong typing
# Syntax: let x = 5; print(x + 2);

# === 2. Lexical Analysis (Tokenization) ===

TOKEN_SPEC = [
    ('NUMBER',   r'\d+(\.\d*)?'),     # Integer or decimal number
    ('ID',       r'[A-Za-z_]\w*'),   # Identifiers
    ('ASSIGN',   r'='),              # Assignment operator
    ('PLUS',     r'\+'),             # Addition operator
    ('LPAREN',   r'\('),             # Left parenthesis
    ('RPAREN',   r'\)'),             # Right parenthesis
    ('SEMI',     r';'),              # Statement terminator
    ('SKIP',     r'[ \t]+'),         # Skip spaces/tabs
    ('NEWLINE',  r'\n'),             # Line endings
    ('MISMATCH', r'.'),              # Any other character
]

TOKEN_REGEX = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)

KEYWORDS = {'let', 'print'}

def lexer(code):
    for mo in re.finditer(TOKEN_REGEX, code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'NUMBER':
            value = float(value) if '.' in value else int(value)
        elif kind == 'ID' and value in KEYWORDS:
            kind = value.upper()
        elif kind == 'SKIP' or kind == 'NEWLINE':
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f'Unexpected character: {value}')
        yield (kind, value)

# === 3. Parsing (Syntax Analysis) ===

class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return ('EOF', None)

    def eat(self, kind=None):
        token = self.peek()
        if kind and token[0] != kind:
            raise SyntaxError(f'Expected {kind}, got {token[0]}')
        self.pos += 1
        return token

    def parse(self):
        stmts = []
        while self.peek()[0] != 'EOF':
            stmts.append(self.statement())
        return {'type': 'Program', 'body': stmts}

    def statement(self):
        token = self.peek()
        if token[0] == 'LET':
            self.eat('LET')
            name = self.eat('ID')[1]
            self.eat('ASSIGN')
            expr = self.expr()
            self.eat('SEMI')
            return {'type': 'VarDecl', 'name': name, 'expr': expr}
        elif token[0] == 'PRINT':
            self.eat('PRINT')
            self.eat('LPAREN')
            expr = self.expr()
            self.eat('RPAREN')
            self.eat('SEMI')
            return {'type': 'Print', 'expr': expr}
        else:
            raise SyntaxError(f'Unknown statement: {token}')

    def expr(self):
        left = self.term()
        token = self.peek()
        if token[0] == 'PLUS':
            self.eat('PLUS')
            right = self.term()
            return {'type': 'BinaryExpr', 'operator': '+', 'left': left, 'right': right}
        return left

    def term(self):
        token = self.peek()
        if token[0] == 'NUMBER':
            value = self.eat('NUMBER')[1]
            return {'type': 'Number', 'value': value}
        elif token[0] == 'ID':
            name = self.eat('ID')[1]
            return {'type': 'Identifier', 'name': name}
        else:
            raise SyntaxError(f'Expected number or identifier, got {token}')

# === 4. Semantic Analysis ===

class SemanticAnalyzer:
    def __init__(self):
        self.symbols = {}

    def analyze(self, node):
        nodetype = node['type']
        if nodetype == 'Program':
            for stmt in node['body']:
                self.analyze(stmt)
        elif nodetype == 'VarDecl':
            if node['name'] in self.symbols:
                raise Exception(f"Variable '{node['name']}' already declared")
            value_type = self.analyze(node['expr'])
            self.symbols[node['name']] = value_type
        elif nodetype == 'Print':
            self.analyze(node['expr'])
        elif nodetype == 'BinaryExpr':
            ltype = self.analyze(node['left'])
            rtype = self.analyze(node['right'])
            if ltype != rtype:
                raise Exception('Type error in binary expression')
            return ltype
        elif nodetype == 'Number':
            return 'number'
        elif nodetype == 'Identifier':
            if node['name'] not in self.symbols:
                raise Exception(f"Undeclared variable '{node['name']}'")
            return self.symbols[node['name']]
        else:
            raise Exception(f"Unknown node type {nodetype}")

# === 5. Intermediate Representation (IR) ===

def to_ir(ast):
    # Simple stack-based IR
    code = []
    for stmt in ast['body']:
        if stmt['type'] == 'VarDecl':
            code.extend(expr_ir(stmt['expr']))
            code.append(('STORE', stmt['name']))
        elif stmt['type'] == 'Print':
            code.extend(expr_ir(stmt['expr']))
            code.append(('PRINT',))
    return code

def expr_ir(node):
    if node['type'] == 'Number':
        return [('PUSH', node['value'])]
    elif node['type'] == 'Identifier':
        return [('LOAD', node['name'])]
    elif node['type'] == 'BinaryExpr' and node['operator'] == '+':
        return expr_ir(node['left']) + expr_ir(node['right']) + [('ADD',)]
    else:
        raise Exception(f"Unknown expr node: {node}")

# === 6. Code Generation (Interpreter) ===

def run_ir(ir):
    env = {}
    stack = []
    for ins in ir:
        if ins[0] == 'PUSH':
            stack.append(ins[1])
        elif ins[0] == 'LOAD':
            stack.append(env[ins[1]])
        elif ins[0] == 'STORE':
            env[ins[1]] = stack.pop()
        elif ins[0] == 'ADD':
            b = stack.pop()
            a = stack.pop()
            stack.append(a + b)
        elif ins[0] == 'PRINT':
            print(stack.pop())
        else:
            raise Exception(f"Unknown IR instruction: {ins}")

# === 7. Optimization (Constant Folding) ===

def constant_fold(node):
    if node['type'] == 'BinaryExpr':
        left = constant_fold(node['left'])
        right = constant_fold(node['right'])
        if left['type'] == 'Number' and right['type'] == 'Number' and node['operator'] == '+':
            return {'type': 'Number', 'value': left['value'] + right['value']}
        return {'type': 'BinaryExpr', 'operator': '+', 'left': left, 'right': right}
    elif node['type'] in ('Number', 'Identifier'):
        return node
    else:
        return node

def optimize(ast):
    if ast['type'] == 'Program':
        ast['body'] = [optimize(stmt) for stmt in ast['body']]
        return ast
    elif ast['type'] == 'VarDecl':
        return {'type': 'VarDecl', 'name': ast['name'], 'expr': constant_fold(ast['expr'])}
    elif ast['type'] == 'Print':
        return {'type': 'Print', 'expr': constant_fold(ast['expr'])}
    else:
        return ast

# === CLI ===

def main():
    code = sys.stdin.read()
    print("=== Source Code ===")
    print(code)
    tokens = list(lexer(code))
    print("=== Tokens ===")
    print(tokens)
    parser = Parser(tokens)
    ast = parser.parse()
    print("=== AST ===")
    print(ast)
    print("=== Semantic Analysis ===")
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    print("OK")
    print("=== Optimized AST ===")
    ast = optimize(ast)
    print(ast)
    print("=== IR ===")
    ir = to_ir(ast)
    print(ir)
    print("=== Execution ===")
    run_ir(ir)

if __name__ == "__main__":
    main()
