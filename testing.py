from lark import Lark, Transformer, Tree
import sys
import subprocess

# Updated Verilog Grammar
verilog_grammar = r"""
    start: module
    module: "module" CNAME "(" port_list ")" ";" decl* states* wire* stmt* "endmodule"
    port_list: CNAME ("," CNAME)*
    decl: ("input" | "output" ) decl_list ";"
    states: "reg" state_list ";"
    state_list: CNAME ("," CNAME)* 
    decl_list: CNAME ("," CNAME)*
    wire: ("wire") wire_list ";"
    wire_list: CNAME ("," CNAME)*
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
        return items[0]  # Return the module dictionary dir



    def module(self, items):
        ports = items[1] if len(items) > 1 else []
        declarations = [item for item in items if isinstance(item, tuple)]  # Extract declarations
        body = []
        states = []
        test = list(items) 
        filtered = [item for item in test if not isinstance(item, Tree)]

        for i in range(len(filtered)):
            if filtered[i][0][0] == "S0" :
                for x in range(len(filtered[i][0])):
                    states.append(filtered[i][0][x])
                    #print(states)

        
        
        # Extract gates from items that are Tree objects (ignore empty ones)
        for item in items:
            if isinstance(item, Tree) and item.children:
                body.extend(item.children)

            elif isinstance(item, list):
                body.extend(item)
        return {"ports": ports, "declarations": declarations, "body": body, "states": states}

    def decl(self, items):
        decl_type = str(items[0])  # "input", "output", "reg", or "wire"
        #signals = list(map(str, items[1:])) if len(items) > 1 else []
       # print(signals)
        return ("decl", decl_type)

    def decl_list(self, items):
        return list(items)
    
    def states(self,items):
        return (items)
    
    def state_list(self,items):
        #states.extend(items)
        return list(items)
    
    def wire(self,items):
        return ("wire",items)
    
    def wire_list(self,items):
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
def to_dimacs(parsed_data, target_states,transitions):
    var_map = {}
    clauses = []
    next_var = 1
    targets = {}
    test = len(target_states) - 1
    iteration = 0
    book = []

    def get_var(name):
        for i in range(int(transitions)):
            if name in var_map:
                return var_map[name]
            rolled_name = str(name) + "_" + str(i)
            nonlocal next_var
            if rolled_name not in var_map:
                var_map[rolled_name] = next_var
                next_var += 1
        return var_map[rolled_name]
    
    def clause_maker(name):
        return var_map[name]



    for stmt in parsed_data["states"]: 
               variable = get_var(str(stmt))
               variable = clause_maker(str(stmt) + "_0")
               clauses.append([-variable])
 
    for stmt in parsed_data["body"]:
        if isinstance(stmt, tuple) and stmt[0] == "gate":
            gate_type, output = stmt[1], stmt[3][0]
            inputs = []
            for i in range(1, len(stmt[3])):
                inputs.append(stmt[3][i])    
            output_var = get_var(output)
            input_vars = [get_var(inp) for inp in inputs]

            for i in range(int(transitions)):

                if len(inputs) == 1:
                    input_A = clause_maker(str(inputs[0]) + "_" + str(i))
                else:
                    input_A = clause_maker(str(inputs[0]) + "_" + str(i))
                    input_B = clause_maker(str(inputs[1]) + "_" + str(i)) 
                out =  clause_maker(output + "_" + str(i) )
            
                if gate_type == "and":
                    clauses.append([-input_A, -input_B, out])
                    clauses.append([input_A, -out])
                    clauses.append([input_B, -out])
                elif gate_type == "not":
                    clauses.append([-input_A, -out])
                    clauses.append([input_A, out])
   
   
    reversed_ordered = dict(reversed(sorted(var_map.items())))
    #print(clauses)
    for item in reversed_ordered:
        if item == "NS" + str(test) + "_" + str(int(transitions) - 1):
            if target_states[iteration] == "1":
                test = test - 1 
                iteration = iteration + 1 
                clauses.append([get_var(item)])
            else:
                test = test - 1 
                iteration = iteration + 1 
                clauses.append([-get_var(item)])  
    
    if int(transitions) >= 2:
        for i in range(int(transitions) - 1):
            for x in range(len(target_states)):
                next_state = clause_maker("NS" + str(x) + "_" + str(i)) #NS0_0 for first run through
                current_state = clause_maker("S" + str(x) + "_" + str(i + 1)) #S0_1
                clauses.append([-next_state , current_state])
                clauses.append([next_state , -current_state])
    # print(var_map)    
    dimacs = f"p cnf {len(var_map)} {len(clauses)}\n"

    dimacs += "\n".join(" ".join(map(str, clause)) + " 0 \n" for clause in clauses)
    #dimacs += "\n".join(" ".join(map(str, target)) + " 0" for target in targets)
    #print(var_map["S1"])
    return dimacs

# Main execution: read file and process
if __name__ == "__main__":

    verilog_filename = sys.argv[1]  # Your Verilog file name
    transitions = sys.argv[2] # Amount of Transitions
    target_states = sys.argv[3] #Target State from Command Line
        

    
    with open(verilog_filename, "r") as file:
        verilog_code = file.read()
    parsed = parse_verilog(verilog_code)
    #print(parsed)
    #print("DEBUG: Parsed Data:", parsed)  # Debug print

    dimacs_cnf = to_dimacs(parsed,target_states,transitions)
    dimacs_filename = verilog_filename.replace(".v", ".dimacs")
    with open(dimacs_filename, "w") as file:
        file.write(dimacs_cnf)

    # picosat-965 folder must be in project directory in order for this command to run properly
    # also assuming that `./configure.sh && make` has been run already (picosat is compiled & executable exists)
    # command = f'./picosat-965/picosat {dimacs_filename}'
    result = subprocess.run(['./picosat-965/picosat', dimacs_filename], capture_output=True, text=True)
    print(result.stdout)
    # print(dimacs_cnf)
