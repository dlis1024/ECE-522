from lark import Lark, Transformer, Tree

# Updated Verilog Grammar
verilog_grammar = r"""
    start: module
    module: "module" CNAME "(" port_list ")" ";" decl* stmt* "endmodule"
    port_list: CNAME ("," CNAME)*
    decl: ("input" | "output" | "reg" | "wire") decl_list ";"
    decl_list: CNAME ("," CNAME)*
    stmt: gate | always_block
    gate: GATE_TYPE CNAME "(" arg_list ")" ";"
    arg_list: CNAME ("," CNAME)*
    always_block: "always" "@" "(" "posedge" CNAME ")" "begin" always_stmt* "end"

    always_stmt: CNAME "<=" CNAME ";"

    GATE_TYPE: "and" | "or" | "not" | "xor" | "nand" | "nor"

    %import common.CNAME
    %import common.WS
    %ignore WS
"""

# Create the Lark Parser
verilog_parser = Lark(verilog_grammar, parser="lalr")

class VerilogTransformer(Transformer):
    # Add a method for the start rule to unwrap the tree
    def start(self, items):
        return items[0]  # Return the module dictionary directly

    def module(self, items):
        ports = items[1] if len(items) > 1 else []
        declarations = [item for item in items if isinstance(item, tuple)]  # Extract declarations
        body = []
        # Extract gates from items that are Tree objects (ignore empty ones)
        for item in items:
            if isinstance(item, Tree) and item.children:
                body.extend(item.children)
            elif isinstance(item, list):
                body.extend(item)
        return {"ports": ports, "declarations": declarations, "body": body}

    def decl(self, items):
        decl_type = str(items[0])  # "input", "output", "reg", or "wire"
        signals = list(map(str, items[1:])) if len(items) > 1 else []
        return ("decl", decl_type, signals)

    def decl_list(self, items):
        return list(items)

    def gate(self, items):
        return ("gate", str(items[0]), str(items[1]), list(map(str, items[2])))

    def arg_list(self, items):
        return list(items)

    def port_list(self, items):
        return list(items)

    def always_block(self, items):
        # Ignore always block for CNF generation
        return []

    def always_stmt(self, items):
        return (str(items[0]), str(items[1]))

# Function to parse the Verilog code
def parse_verilog(verilog_code):
    tree = verilog_parser.parse(verilog_code)
    return VerilogTransformer().transform(tree)

# Convert Parsed Data to DIMACS CNF
def to_dimacs(parsed_data):
    var_map = {}
    clauses = []
    next_var = 1

    def get_var(name):
        nonlocal next_var
        if name not in var_map:
            var_map[name] = next_var
            next_var += 1
        return var_map[name]

    for stmt in parsed_data["body"]:
        if isinstance(stmt, tuple) and stmt[0] == "gate":
            gate_type, output, inputs = stmt[1], stmt[2], stmt[3]
            output_var = get_var(output)
            input_vars = [get_var(inp) for inp in inputs]

            if gate_type == "and":
                clauses.append([-input_vars[0], -input_vars[1], output_var])
                clauses.append([input_vars[0], -output_var])
                clauses.append([input_vars[1], -output_var])
            elif gate_type == "or":
                clauses.append([input_vars[0], input_vars[1], -output_var])
                clauses.append([-input_vars[0], output_var])
                clauses.append([-input_vars[1], output_var])
            elif gate_type == "not":
                clauses.append([-input_vars[0], -output_var])
                clauses.append([input_vars[0], output_var])
            elif gate_type == "xor":
                clauses.append([-input_vars[0], -input_vars[1], -output_var])
                clauses.append([input_vars[0], input_vars[1], -output_var])
                clauses.append([-input_vars[0], input_vars[1], output_var])
                clauses.append([input_vars[0], -input_vars[1], output_var])
            elif gate_type == "nand":
                clauses.append([input_vars[0], input_vars[1], output_var])
                clauses.append([-input_vars[0], -output_var])
                clauses.append([-input_vars[1], -output_var])
            elif gate_type == "nor":
                clauses.append([-input_vars[0], -input_vars[1], output_var])
                clauses.append([input_vars[0], -output_var])
                clauses.append([input_vars[1], -output_var])

    dimacs = f"p cnf {len(var_map)} {len(clauses)}\n"
    dimacs += "\n".join(" ".join(map(str, clause)) + " 0" for clause in clauses)
    return dimacs

# Main execution: read file and process
if __name__ == "__main__":
    verilog_filename = "demo.v"  # Your Verilog file name

    with open(verilog_filename, "r") as file:
        verilog_code = file.read()

    parsed = parse_verilog(verilog_code)
    #print("DEBUG: Parsed Data:", parsed)  # Debug print

    dimacs_cnf = to_dimacs(parsed)
    print(dimacs_cnf)
