import math
import re
from typing import List, Dict, Union, Any

class ParserError(Exception):
    """Base exception for parsing errors."""
    pass

class Token:
    NUMBER = "NUMBER"
    OPERATOR = "OPERATOR"
    IDENTIFIER = "IDENTIFIER"  # For functions and variables
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"

    def __init__(self, type_: str, value: str):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

class Tokenizer:
    # Match numbers, operators, words (identifiers), or parentheses/commas
    TOKEN_REGEX = re.compile(
        r'\s*(?:'
        r'(?P<num>\d+(?:\.\d+)?)'
        r'|(?P<op>[\+\-\*/\^])'
        r'|(?P<id>[a-zA-Z_][a-zA-Z0-9_]*)'
        r'|(?P<lparen>\()'
        r'|(?P<rparen>\))'
        r'|(?P<comma>,)'
        r')'
    )

    @classmethod
    def tokenize(cls, expression: str) -> List[Token]:
        tokens = []
        pos = 0
        while pos < len(expression):
            match = cls.TOKEN_REGEX.match(expression, pos)
            if not match:
                # Skip whitespace if not matched
                if expression[pos].isspace():
                    pos += 1
                    continue
                raise ParserError(f"Unexpected character '{expression[pos]}' at position {pos}")
            
            group_dict = match.groupdict()
            if group_dict["num"] is not None:
                tokens.append(Token(Token.NUMBER, group_dict["num"]))
            elif group_dict["op"] is not None:
                tokens.append(Token(Token.OPERATOR, group_dict["op"]))
            elif group_dict["id"] is not None:
                tokens.append(Token(Token.IDENTIFIER, group_dict["id"]))
            elif group_dict["lparen"] is not None:
                tokens.append(Token(Token.LPAREN, group_dict["lparen"]))
            elif group_dict["rparen"] is not None:
                tokens.append(Token(Token.RPAREN, group_dict["rparen"]))
            elif group_dict["comma"] is not None:
                tokens.append(Token(Token.COMMA, group_dict["comma"]))
            
            pos = match.end()
        return tokens

# AST Nodes
class ASTNode:
    def evaluate(self, variables: Dict[str, float]) -> float:
        raise NotImplementedError()

class NumberNode(ASTNode):
    def __init__(self, value: float):
        self.value = value

    def evaluate(self, variables: Dict[str, float]) -> float:
        return self.value

    def __repr__(self):
        return f"Number({self.value})"

class VariableNode(ASTNode):
    def __init__(self, name: str):
        self.name = name

    def evaluate(self, variables: Dict[str, float]) -> float:
        if self.name not in variables:
            raise ParserError(f"Undefined variable '{self.name}'")
        return variables[self.name]

    def __repr__(self):
        return f"Variable({self.name})"

class BinOpNode(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right

    def evaluate(self, variables: Dict[str, float]) -> float:
        l_val = self.left.evaluate(variables)
        r_val = self.right.evaluate(variables)
        if self.op == "+":
            return l_val + r_val
        elif self.op == "-":
            return l_val - r_val
        elif self.op == "*":
            return l_val * r_val
        elif self.op == "/":
            if r_val == 0:
                raise ZeroDivisionError("Division by zero in formula evaluation.")
            return l_val / r_val
        elif self.op == "^":
            try:
                return math.pow(l_val, r_val)
            except OverflowError:
                raise ParserError("Math overflow in exponentiation")
            except ValueError:
                # Handle imaginary results like (-4)^0.5
                raise ParserError("Negative base with non-integer exponent results in a complex number")
        else:
            raise ParserError(f"Unknown binary operator: {self.op}")

    def __repr__(self):
        return f"BinOp({self.left} {self.op} {self.right})"

class FunctionNode(ASTNode):
    FUNCTIONS = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log,
        "exp": math.exp,
        "abs": abs
    }

    def __init__(self, name: str, args: List[ASTNode]):
        self.name = name.lower()
        self.args = args

    def evaluate(self, variables: Dict[str, float]) -> float:
        if self.name not in self.FUNCTIONS:
            raise ParserError(f"Unknown function '{self.name}'")
        
        evaluated_args = [arg.evaluate(variables) for arg in self.args]
        func = self.FUNCTIONS[self.name]
        
        # Check argument count
        # Most of our functions take 1 arg, log can take 1 or 2
        if self.name == "log":
            if len(evaluated_args) not in (1, 2):
                raise ParserError("Function 'log' expects 1 or 2 arguments")
            if evaluated_args[0] <= 0:
                raise ValueError("Logarithm argument must be positive")
            if len(evaluated_args) == 2:
                if evaluated_args[1] <= 0 or evaluated_args[1] == 1:
                    raise ValueError("Logarithm base must be positive and not equal to 1")
                return math.log(evaluated_args[0], evaluated_args[1])
            return math.log(evaluated_args[0])
        else:
            if len(evaluated_args) != 1:
                raise ParserError(f"Function '{self.name}' expects exactly 1 argument")
            val = evaluated_args[0]
            if self.name == "sqrt" and val < 0:
                raise ValueError("Square root of a negative number")
            return func(val)

    def __repr__(self):
        return f"Func({self.name}, {self.args})"

class ExpressionParser:
    """
    Parses expressions using the Shunting-yard algorithm to build an AST.
    """
    PRECEDENCE = {
        "+": 1,
        "-": 1,
        "*": 2,
        "/": 2,
        "^": 3
    }
    
    # Right-associative operators (only power ^ here)
    RIGHT_ASSOCIATIVE = {"^"}

    def __init__(self, expression: str):
        self.tokens = Tokenizer.tokenize(expression)
        self.pos = 0

    def peek(self) -> Union[Token, None]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> ASTNode:
        # We can implement a Recursive Descent Parser for robust AST building,
        # which is easier for function arguments than raw Shunting-Yard.
        # Grammar:
        # expr   -> term ( ( "+" | "-" ) term )*
        # term   -> factor ( ( "*" | "/" ) factor )*
        # factor -> power ( "^" factor )*   (right associative)
        # power  -> [ "-" | "+" ] primary
        # primary-> NUMBER | IDENTIFIER ( "(" args? ")" )? | "(" expr ")"
        node = self._expr()
        if self.peek() is not None:
            raise ParserError(f"Unexpected token {self.peek()} at end of expression")
        return node

    def _expr(self) -> ASTNode:
        node = self._term()
        while True:
            tok = self.peek()
            if tok and tok.type == Token.OPERATOR and tok.value in ("+", "-"):
                op = self.advance().value
                right = self._term()
                node = BinOpNode(node, op, right)
            else:
                break
        return node

    def _term(self) -> ASTNode:
        node = self._factor()
        while True:
            tok = self.peek()
            if tok and tok.type == Token.OPERATOR and tok.value in ("*", "/"):
                op = self.advance().value
                right = self._factor()
                node = BinOpNode(node, op, right)
            else:
                break
        return node

    def _factor(self) -> ASTNode:
        node = self._power()
        tok = self.peek()
        if tok and tok.type == Token.OPERATOR and tok.value == "^":
            op = self.advance().value
            # Right-associative: recursive call to factor
            right = self._factor()
            node = BinOpNode(node, op, right)
        return node

    def _power(self) -> ASTNode:
        # Handle unary prefix operator (+ or -)
        tok = self.peek()
        if tok and tok.type == Token.OPERATOR and tok.value in ("+", "-"):
            op = self.advance().value
            primary = self._primary()
            if op == "-":
                return BinOpNode(NumberNode(0.0), "-", primary)
            return primary
        return self._primary()

    def _primary(self) -> ASTNode:
        tok = self.peek()
        if not tok:
            raise ParserError("Unexpected end of expression")

        if tok.type == Token.NUMBER:
            self.advance()
            return NumberNode(float(tok.value))

        elif tok.type == Token.IDENTIFIER:
            name = self.advance().value
            next_tok = self.peek()
            if next_tok and next_tok.type == Token.LPAREN:
                # Function call
                self.advance()  # consume '('
                args = []
                next_tok = self.peek()
                if next_tok and next_tok.type != Token.RPAREN:
                    args.append(self._expr())
                    while True:
                        next_tok = self.peek()
                        if next_tok and next_tok.type == Token.COMMA:
                            self.advance()  # consume ','
                            args.append(self._expr())
                        else:
                            break
                r_paren = self.peek()
                if not r_paren or r_paren.type != Token.RPAREN:
                    raise ParserError(f"Expected closing parenthesis for function '{name}'")
                self.advance()  # consume ')'
                return FunctionNode(name, args)
            else:
                # Variable
                return VariableNode(name)

        elif tok.type == Token.LPAREN:
            self.advance()  # consume '('
            node = self._expr()
            r_paren = self.peek()
            if not r_paren or r_paren.type != Token.RPAREN:
                raise ParserError("Expected closing parenthesis")
            self.advance()  # consume ')'
            return node

        else:
            raise ParserError(f"Unexpected token: {tok}")

def parse_and_evaluate(expression: str, variables: Dict[str, float] = None) -> float:
    if variables is None:
        variables = {}
    parser = ExpressionParser(expression)
    ast = parser.parse()
    return ast.evaluate(variables)
