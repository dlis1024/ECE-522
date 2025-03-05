from lark import Lark, Transformer

# Define a simple arithmetic grammar
grammar = """
    start: expr
    expr: term ("+" term | "-" term)*
    term: factor ("*" factor | "/" factor)*
    factor: NUMBER | "(" expr ")"
    NUMBER: /[0-9]+/
    %ignore " "
"""

# Create the parser
parser = Lark(grammar, parser="lalr")

# Transformer to evaluate expressions
class Calculate(Transformer):
    def NUMBER(self, n):
        return int(n)
    
    def expr(self, values):
        result = values[0]
        for i in range(1, len(values), 2):
            if values[i] == "+":
                result += values[i + 1]
            else:
                result -= values[i + 1]
        return result
    
    def term(self, values):
        result = values[0]
        for i in range(1, len(values), 2):
            if values[i] == "*":
                result *= values[i + 1]
            else:
                result /= values[i + 1]
        return result

# Function to parse and evaluate expressions
def evaluate_expression(expression):
    tree = parser.parse(expression)
    return Calculate().transform(tree)

# Example usage
if __name__ == "__main__":
    expr = input("Enter an arithmetic expression: ")
    result = evaluate_expression(expr)
    print(f"Result: {result}")
