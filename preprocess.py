import ast
import json
import sys

types = set()
funcs = []

def get_full_attr(node):
    if isinstance(node, ast.Attribute):
        return get_full_attr(node.value) + "." + node.attr
    elif isinstance(node, ast.Name):
        return node.id
    else:
        return ""
    
def get_func_name(node):
    if isinstance(node.func, ast.Name):
        func_name = node.func.id 
    elif isinstance(node.func, ast.Attribute):
        func_name = get_full_attr(node.func)
    else:
        func_name = ast.dump(node.func)
    return func_name
        
def get_args(node):
    arg_data = []
    # Positional arguments
    for arg in node.args:
        try:
            value = ast.literal_eval(arg)
        except Exception:
            value = ast.unparse(arg)  # fallback for complex expressions
        arg_data.append(value)

    # Keyword arguments
    for kw in node.keywords:
        if kw.arg is not None:
            try:
                value = ast.literal_eval(kw.value)
            except Exception:
                value = ast.unparse(kw.value)
            arg_data.append({kw.arg: value})
        else:
            arg_data.append({"**kwargs_unpack": ast.unparse(kw.value)})
    return arg_data
        
def ast_to_dict(node):
    if isinstance(node, ast.AST):
        node_type = node.__class__.__name__
        result = {"_type": node_type}
        types.add(node_type) # Collect type names

        if isinstance(node, ast.Call):
            func_name = get_func_name(node)                
            arg_data = get_args(node)
            funcs.append([node.lineno, func_name, arg_data]) # Collect function calls
            
        for field, value in ast.iter_fields(node):
            result[field] = ast_to_dict(value)
        return result
    elif isinstance(node, list):
        return [ast_to_dict(item) for item in node]
    else:
        return node

# ---------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------

code = """
def add(a, b):
    return a + b
for i in range(5):
    sum = add(2, b=3)
    print(sum)
"""

if len(sys.argv) > 1:
    with open(sys.argv[1], "r") as f:
        code = f.read()
 
# Parse into AST
tree = ast.parse(code)

# Convert AST to JSON
tree_dict = ast_to_dict(tree)
json_repr = json.dumps(tree_dict, indent=4)

# Output results
print(json_repr)
print("Collected AST Node Types:", types)
print("\nCollected Function Calls:\n")
print("Line: Function Name                  Arguments")
for f in funcs:
    print(f'{f[0]:4d}: {f[1]:30s} {f[2]}')
