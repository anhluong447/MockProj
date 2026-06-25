import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import MagicMock, patch
from src.core.expression_parser import ExpressionParser, Token, ParserError, NumberNode, VariableNode, FunctionNode

@pytest.fixture
def parser():
    # Pass a dummy expression to constructor so Tokenizer doesn't fail
    return ExpressionParser("")

def test_primary_number(parser):
    # Test that a NUMBER token returns a NumberNode with its float value
    token_num = Token(Token.NUMBER, "42")
    
    with patch.object(parser, 'peek', return_value=token_num) as mock_peek, \
         patch.object(parser, 'advance', return_value=token_num) as mock_advance:
        result = parser._primary()
        assert isinstance(result, NumberNode)
        assert result.value == 42.0
        mock_peek.assert_called_once()
        mock_advance.assert_called_once()

def test_primary_identifier_variable(parser):
    # Test that an IDENTIFIER token not followed by LPAREN returns a VariableNode
    token_id = Token(Token.IDENTIFIER, "x")
    token_eof = None
    
    with patch.object(parser, 'peek', side_effect=[token_id, token_eof]) as mock_peek, \
         patch.object(parser, 'advance', return_value=token_id) as mock_advance:
        result = parser._primary()
        assert isinstance(result, VariableNode)
        assert result.name == "x"
        mock_advance.assert_called_once()

def test_primary_function_call_no_args(parser):
    # Test function call with no arguments: f()
    token_id = Token(Token.IDENTIFIER, "f")
    token_lparen = Token(Token.LPAREN, "(")
    token_rparen = Token(Token.RPAREN, ")")
    
    # peek calls:
    # 1. in _primary: check IDENTIFIER
    # 2. check if next is LPAREN
    # 3. inside LPAREN block, check if next is RPAREN
    # 4. at the end, check if next is RPAREN (to confirm and consume)
    with patch.object(parser, 'peek', side_effect=[token_id, token_lparen, token_rparen, token_rparen]) as mock_peek, \
         patch.object(parser, 'advance', side_effect=[token_id, token_lparen, token_rparen]) as mock_advance:
        result = parser._primary()
        assert isinstance(result, FunctionNode)
        assert result.name == "f"
        assert result.args == []
        assert mock_advance.call_count == 3

def test_primary_function_call_one_arg(parser):
    # Test function call with one argument: f(42)
    token_id = Token(Token.IDENTIFIER, "f")
    token_lparen = Token(Token.LPAREN, "(")
    token_num = Token(Token.NUMBER, "42")
    token_rparen = Token(Token.RPAREN, ")")
    
    mock_node = NumberNode(42.0)
    
    # peek calls:
    # 1. in _primary: IDENTIFIER
    # 2. check if next is LPAREN
    # 3. inside LPAREN: check if next is RPAREN (not RPAREN, it's NUMBER)
    # 4. in loop: check if next is COMMA (not COMMA, it's RPAREN)
    # 5. after loop: check if next is RPAREN (it is RPAREN)
    with patch.object(parser, 'peek', side_effect=[token_id, token_lparen, token_num, token_rparen, token_rparen]) as mock_peek, \
         patch.object(parser, 'advance', side_effect=[token_id, token_lparen, token_rparen]) as mock_advance, \
         patch.object(parser, '_expr', return_value=mock_node) as mock_expr:
        result = parser._primary()
        assert isinstance(result, FunctionNode)
        assert result.name == "f"
        assert len(result.args) == 1
        assert result.args[0] == mock_node

def test_primary_function_call_multiple_args(parser):
    # Test function call with multiple arguments: f(x, y)
    token_id = Token(Token.IDENTIFIER, "f")
    token_lparen = Token(Token.LPAREN, "(")
    token_x = Token(Token.IDENTIFIER, "x")
    token_comma = Token(Token.COMMA, ",")
    token_y = Token(Token.IDENTIFIER, "y")
    token_rparen = Token(Token.RPAREN, ")")
    
    mock_x_node = VariableNode("x")
    mock_y_node = VariableNode("y")
    
    # peek calls:
    # 1. in _primary: IDENTIFIER
    # 2. check if next is LPAREN
    # 3. inside LPAREN: check if next is RPAREN (not RPAREN, it's IDENTIFIER x)
    # 4. in loop: check if next is COMMA (it is COMMA) -> advance
    # 5. in loop after comma: check if next is COMMA (not COMMA, it's RPAREN)
    # 6. after loop: check if next is RPAREN (it is RPAREN) -> advance
    with patch.object(parser, 'peek', side_effect=[token_id, token_lparen, token_x, token_comma, token_rparen, token_rparen]) as mock_peek, \
         patch.object(parser, 'advance', side_effect=[token_id, token_lparen, token_comma, token_rparen]) as mock_advance, \
         patch.object(parser, '_expr', side_effect=[mock_x_node, mock_y_node]) as mock_expr:
        result = parser._primary()
        assert isinstance(result, FunctionNode)
        assert result.name == "f"
        assert result.args == [mock_x_node, mock_y_node]
        assert mock_advance.call_count == 4

def test_primary_parenthesized_expression(parser):
    # Test parenthesized expression: (42)
    token_lparen = Token(Token.LPAREN, "(")
    token_num = Token(Token.NUMBER, "42")
    token_rparen = Token(Token.RPAREN, ")")
    
    mock_node = NumberNode(42.0)
    
    with patch.object(parser, 'peek', side_effect=[token_lparen, token_rparen]) as mock_peek, \
         patch.object(parser, 'advance', side_effect=[token_lparen, token_rparen]) as mock_advance, \
         patch.object(parser, '_expr', return_value=mock_node) as mock_expr:
        result = parser._primary()
        assert result == mock_node
        assert mock_advance.call_count == 2

def test_primary_unexpected_token(parser):
    # Test unexpected token type raises ParserError
    token_comma = Token(Token.COMMA, ",")
    
    with patch.object(parser, 'peek', return_value=token_comma):
        with pytest.raises(ParserError, match="Unexpected token"):
            parser._primary()

def test_primary_unexpected_end(parser):
    # Test unexpected end of expression raises ParserError
    with patch.object(parser, 'peek', return_value=None):
        with pytest.raises(ParserError, match="Unexpected end of expression"):
            parser._primary()

def test_primary_function_missing_rparen(parser):
    # Test function call missing closing parenthesis
    token_id = Token(Token.IDENTIFIER, "f")
    token_lparen = Token(Token.LPAREN, "(")
    token_num = Token(Token.NUMBER, "42")
    token_eof = None
    
    mock_node = NumberNode(42.0)
    
    with patch.object(parser, 'peek', side_effect=[token_id, token_lparen, token_num, token_eof, token_eof]) as mock_peek, \
         patch.object(parser, 'advance', side_effect=[token_id, token_lparen]) as mock_advance, \
         patch.object(parser, '_expr', return_value=mock_node) as mock_expr:
        with pytest.raises(ParserError, match="Expected closing parenthesis for function 'f'"):
            parser._primary()

def test_primary_parenthesis_missing_rparen(parser):
    # Test parenthesized expression missing closing parenthesis
    token_lparen = Token(Token.LPAREN, "(")
    token_eof = None
    
    mock_node = NumberNode(42.0)
    
    with patch.object(parser, 'peek', side_effect=[token_lparen, token_eof]) as mock_peek, \
         patch.object(parser, 'advance', side_effect=[token_lparen]) as mock_advance, \
         patch.object(parser, '_expr', return_value=mock_node) as mock_expr:
        with pytest.raises(ParserError, match="Expected closing parenthesis"):
            parser._primary()
