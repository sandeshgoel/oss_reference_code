import ast
import operator
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class CallInfo:
    """Information about a function call."""
    line: int
    func_name: str
    parent_func: Optional[str] = None
    args: List[Any] = field(default_factory=list)
    arg_names: List[str] = field(default_factory=list)
    arg_info: List[Dict[str, Any]] = field(default_factory=list)
    iteration: Optional[Union[int, Tuple[int, ...], str]] = None
    execution_path: str = "both"

@dataclass
class FunctionStats:
    """Statistics for a function's calls."""
    name: str
    min_calls: List[CallInfo] = field(default_factory=list)
    max_calls: List[CallInfo] = field(default_factory=list)
    min_count: Union[int, str] = 0
    max_count: Union[int, str] = 0

class VariableTracker:
    """Tracks variable assignments and their values throughout the AST."""
    
    def __init__(self):
        self.scope_stack = [{}]
    
    def push_scope(self):
        self.scope_stack.append({})
    
    def pop_scope(self):
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
    
    def assign(self, name, value):
        self.scope_stack[-1][name] = value
    
    def get(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return None
    
    def copy(self):
        new_tracker = VariableTracker()
        new_tracker.scope_stack = [scope.copy() for scope in self.scope_stack]
        return new_tracker

class ExecutionPath:
    """Represents an execution path with its calls."""
    
    def __init__(self):
        self.calls = []
        self.loop_stack = []
        self.variable_tracker = VariableTracker()
    
    def copy(self):
        new_path = ExecutionPath()
        new_path.calls = self.calls.copy()
        new_path.loop_stack = self.loop_stack.copy()
        new_path.variable_tracker = self.variable_tracker.copy()
        return new_path
    
    def add_call(self, call_info):
        self.calls.append(call_info)
    
    def enter_loop(self, iterations):
        self.loop_stack.append((iterations, None))
    
    def exit_loop(self):
        if self.loop_stack:
            self.loop_stack.pop()
    
    def set_loop_iteration(self, iteration):
        if self.loop_stack:
            loop_info = self.loop_stack[-1]
            self.loop_stack[-1] = (loop_info[0], iteration)
    
    def get_current_iteration(self):
        if not self.loop_stack:
            return None
        
        iterations = []
        for total_iters, current_iter in self.loop_stack:
            if current_iter is None:
                return "unknown"
            iterations.append(current_iter)
        
        return tuple(iterations) if len(iterations) > 1 else iterations[0]

class ComprehensiveASTAnalyzer(ast.NodeVisitor):
    """Analyzes AST to find all function calls with min/max path analysis."""
    
    def __init__(self):
        self.current_paths = [ExecutionPath()]  # List of current execution paths
        self.function_stats = defaultdict(lambda: FunctionStats(""))
        self.function_context_stack = []
    
    def visit_Assign(self, node):
        """Handle variable assignments."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            for path in self.current_paths:
                value = self._evaluate_expression(node.value, path.variable_tracker)
                if value is not None:
                    path.variable_tracker.assign(var_name, value)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Handle function definitions."""
        # Push current function to context stack
        self.function_context_stack.append(node.name)

        # Create new scope for function in all paths
        for path in self.current_paths:
            path.variable_tracker.push_scope()
        
        # Visit function body
        for stmt in node.body:
            self.visit(stmt)
        
        # Restore previous scope in all paths
        for path in self.current_paths:
            path.variable_tracker.pop_scope()
        
        # Pop current function from context stack
        self.function_context_stack.pop()
    
    def visit_For(self, node):
        """Handle for loops."""
        iterations = self._calculate_iterations(node.iter, self.current_paths[0].variable_tracker)

        if iterations == "unknown" or not isinstance(iterations, int) or iterations <= 0:
            # Handle unknown or zero iterations: visit body once with unknown iteration
            for path in self.current_paths:
                path.enter_loop(iterations)
                path.set_loop_iteration("unknown")
            
            for stmt in node.body:
                self.visit(stmt)
            
            for path in self.current_paths:
                path.exit_loop()
        else:
            # Known iterations: unroll the loop
            loop_paths = self.current_paths
            for i in range(iterations):
                # Set current paths to the result of the previous iteration
                self.current_paths = loop_paths
                for path in self.current_paths:
                    path.enter_loop(iterations)
                    path.set_loop_iteration(i)
                for stmt in node.body:
                    self.visit(stmt)
                for path in self.current_paths:
                    path.exit_loop()
                loop_paths = self.current_paths
    
    def visit_If(self, node):
        """Handle if statements by creating separate execution paths."""
        new_paths = []
        
        for path in self.current_paths:
            # Create path for if branch
            if_path = path.copy()
            self.current_paths = [if_path]
            
            for stmt in node.body:
                self.visit(stmt)
            
            if_result_paths = self.current_paths.copy()
            
            # Create path for else branch
            if node.orelse:
                else_path = path.copy()
                self.current_paths = [else_path]
                
                for stmt in node.orelse:
                    self.visit(stmt)
                
                else_result_paths = self.current_paths.copy()
            else:
                # No else branch - just continue with original path
                else_result_paths = [path.copy()]
            
            # Add both branches to new paths
            new_paths.extend(if_result_paths)
            new_paths.extend(else_result_paths)
        
        self.current_paths = new_paths
    
    def visit_Call(self, node):
        """Handle function calls."""
        func_name = self._get_function_name(node)
        if func_name:
            parent_func = self.function_context_stack[-1] if self.function_context_stack else None

            for path in self.current_paths:
                # Analyze arguments
                args = []
                arg_names = []
                arg_info = []
                
                for arg in node.args:
                    arg_value = self._evaluate_expression(arg, path.variable_tracker)
                    arg_name = self._get_argument_name(arg)
                    
                    args.append(arg_value)
                    arg_names.append(arg_name)
                    
                    # Determine argument info
                    info: Dict[str, Any] = {
                        "name": arg_name,
                        "type": type(arg_value).__name__ if arg_value is not None else "unknown"
                    }
                    if isinstance(arg_value, (list, tuple)):
                        info["is_sequence"] = True
                        info["length"] = len(arg_value)
                        dims = self._get_list_dimensions(arg_value)
                        if dims:
                            info["dimensions"] = dims
                    else:
                        info["is_sequence"] = False
                    arg_info.append(info)
                
                # Create call info
                call_info = CallInfo(
                    line=node.lineno,
                    func_name=func_name,
                    parent_func=parent_func,
                    args=args,
                    arg_names=arg_names,
                    arg_info=arg_info,
                    iteration=path.get_current_iteration()
                )
                
                path.add_call(call_info)
        
        self.generic_visit(node)
    
    def _get_argument_name(self, arg_node):
        """Get the string representation/name of an argument."""
        if isinstance(arg_node, ast.Name):
            return arg_node.id
        elif isinstance(arg_node, ast.Constant):
            return repr(arg_node.value)
        elif isinstance(arg_node, ast.List):
            elements = []
            for elt in arg_node.elts:
                elements.append(self._get_argument_name(elt))
            return f"[{', '.join(elements)}]"
        elif isinstance(arg_node, ast.Tuple):
            elements = []
            for elt in arg_node.elts:
                elements.append(self._get_argument_name(elt))
            return f"({', '.join(elements)})"
        elif isinstance(arg_node, ast.BinOp):
            left = self._get_argument_name(arg_node.left)
            right = self._get_argument_name(arg_node.right)
            op_map = {
                ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/', ast.FloorDiv: '//', 
                ast.Mod: '%', ast.Pow: '**', ast.LShift: '<<', ast.RShift: '>>', 
                ast.BitOr: '|', ast.BitXor: '^', ast.BitAnd: '&', ast.MatMult: '@'
            }
            # Fallback for unknown operators
            op_str = op_map.get(type(arg_node.op), f'<{type(arg_node.op).__name__}>')
            return f"({left} {op_str} {right})"
        elif isinstance(arg_node, ast.Call):
            func_name = self._get_function_name(arg_node)
            arg_names = []
            for arg in arg_node.args:
                arg_names.append(self._get_argument_name(arg))
            return f"{func_name}({', '.join(arg_names)})"
        elif isinstance(arg_node, ast.Attribute):
            value_name = self._get_argument_name(arg_node.value)
            return f"{value_name}.{arg_node.attr}"
        elif isinstance(arg_node, ast.Subscript):
            value_name = self._get_argument_name(arg_node.value)
            # In Python 3.9+, ast.Index is deprecated and the slice is the value directly.
            slice_name = self._get_argument_name(arg_node.slice)
            return f"{value_name}[{slice_name}]"
        else:
            try:
                return ast.unparse(arg_node)
            except AttributeError:
                return "<complex_expression>"

    def _get_list_dimensions(self, item: Any) -> Tuple[int, ...]:
        """Recursively determine the dimensions of a nested list/tuple."""
        if not isinstance(item, (list, tuple)):
            return ()
        if not item:
            return (0,)
        
        dims = [len(item)]
        
        # If all sub-elements are lists/tuples of the same length, recurse
        if all(isinstance(i, (list, tuple)) for i in item):
            sub_lengths = {len(i) for i in item}
            if len(sub_lengths) == 1:
                dims.extend(self._get_list_dimensions(item[0]))

        return tuple(dims)

    def _get_function_name(self, call_node):
        """Extract function name from call node."""
        node = call_node.func
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            # Recursively build the full attribute chain
            return f"{self._get_function_name(ast.Call(func=node.value, args=[], keywords=[]))}.{node.attr}"
        return self._get_argument_name(node)

    def _calculate_iterations(self, iter_node, variable_tracker):
        """Calculate the number of iterations for a given iterable."""
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Name):
                func_name = iter_node.func.id
                
                if func_name == 'range':
                    return self._handle_range_call(iter_node, variable_tracker)
                elif func_name == 'len':
                    return self._handle_len_call(iter_node, variable_tracker)
        
        elif isinstance(iter_node, ast.Name):
            var_value = variable_tracker.get(iter_node.id)
            if var_value is not None:
                try:
                    return len(var_value)
                except TypeError:
                    return "unknown"
        
        elif isinstance(iter_node, ast.List):
            return len(iter_node.elts)
        
        elif isinstance(iter_node, ast.Tuple):
            return len(iter_node.elts)
        
        elif isinstance(iter_node, ast.Constant):
            if isinstance(iter_node.value, str):
                return len(iter_node.value)
        
        return "unknown"
    
    def _handle_range_call(self, call_node, variable_tracker):
        """Handle range() function calls."""
        args = [self._evaluate_expression(arg, variable_tracker) for arg in call_node.args]
        
        if None in args:
            return "unknown"
        
        if any([not isinstance(a, int) for a in args]):
            return "unknown"
        
        # cast all elements of args to int
        args = [int(a) if isinstance(a, int) else 0 for a in args]
        
        try:
            if len(args) == 1:
                return max(0, args[0]) 
            elif len(args) == 2:
                return max(0, args[1] - args[0])
            elif len(args) == 3:
                start, stop, step = args
                if step == 0:
                    return "unknown"
                if step > 0:
                    return max(0, (stop - start + step - 1) // step)
                else:
                    return max(0, (start - stop - step - 1) // (-step))
        except Exception:
            return "unknown"
        
        return "unknown"
    
    def _handle_len_call(self, call_node, variable_tracker):
        """Handle len() function calls."""
        if len(call_node.args) == 1:
            arg_value = self._evaluate_expression(call_node.args[0], variable_tracker)
            if arg_value is not None and isinstance(arg_value, List):
                try:
                    return len(arg_value)
                except TypeError:
                    return "unknown"
        return "unknown"
    
    def _evaluate_expression(self, node, variable_tracker):
        """Evaluate simple expressions and return their values."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return variable_tracker.get(node.id)
        elif isinstance(node, ast.List):
            elements = []
            for elt in node.elts:
                val = self._evaluate_expression(elt, variable_tracker)
                if val is None:
                    return None
                elements.append(val)
            return elements
        elif isinstance(node, ast.Tuple):
            elements = []
            for elt in node.elts:
                val = self._evaluate_expression(elt, variable_tracker)
                if val is None:
                    return None
                elements.append(val)
            return tuple(elements)
        elif isinstance(node, ast.BinOp):
            return self._evaluate_binop(node, variable_tracker)
        
        return None
    
    def _evaluate_binop(self, node, variable_tracker):
        """Evaluate binary operations."""
        left = self._evaluate_expression(node.left, variable_tracker)
        right = self._evaluate_expression(node.right, variable_tracker)
        
        if left is None or right is None:
            return None
        
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
        }
        
        if type(node.op) in ops:
            try:
                return ops[type(node.op)](left, right)
            except Exception:
                return None
        
        return None
    
    def finalize_stats(self):
        """Finalize statistics by finding min/max paths."""
        if not self.current_paths:
            return
        
        all_func_names = set(call.func_name for path in self.current_paths for call in path.calls)

        # Find min and max call counts per function
        function_call_counts = defaultdict(list)
        for path in self.current_paths:
            path_counts = defaultdict(int)
            for call in path.calls:
                path_counts[call.func_name] += 1

            for func_name in all_func_names:
                function_call_counts[func_name].append((path_counts[func_name], path))
        
        # For each function, find the paths with min and max calls
        for func_name, count_path_pairs in function_call_counts.items():
            if not count_path_pairs:
                continue
                
            # Sort by call count
            count_path_pairs.sort(key=lambda x: x[0])
            
            min_count = count_path_pairs[0][0]
            max_count = count_path_pairs[-1][0]
            
            # Get all paths with minimum calls
            min_paths = [path for count, path in count_path_pairs if count == min_count]
            # Get all paths with maximum calls  
            max_paths = [path for count, path in count_path_pairs if count == max_count]
            
            # Create function stats
            stats = FunctionStats(func_name)
            
            # Add calls from one representative min path
            if min_paths:
                for call in min_paths[0].calls:
                    if call.func_name == func_name:
                        stats.min_calls.append(call)
            
            # Add calls from one representative max path
            if max_paths:
                for call in max_paths[0].calls:
                    if call.func_name == func_name:
                        stats.max_calls.append(call)
            
            # Set counts
            if any(call.iteration == "unknown" for call in stats.min_calls):
                stats.min_count = "unknown"
            else:
                stats.min_count = len(stats.min_calls)
            
            if any(call.iteration == "unknown" for call in stats.max_calls):
                stats.max_count = "unknown"
            else:
                stats.max_count = len(stats.max_calls)
            
            self.function_stats[func_name] = stats

def analyze_function_calls(code: str) -> Dict[str, FunctionStats]:
    """Analyze Python code and return comprehensive function call statistics."""
    try:
        tree = ast.parse(code)
        analyzer = ComprehensiveASTAnalyzer()
        analyzer.visit(tree)
        analyzer.finalize_stats()
        return dict(analyzer.function_stats)
    except SyntaxError as e:
        print(f"Syntax error in code: {e}")
        return {}

def print_analysis_report(stats: Dict[str, FunctionStats]):
    """Print a detailed analysis report with separate min/max call lists."""
    if not stats:
        print("No function calls found.")
        return
    
    print("=== FUNCTION CALL ANALYSIS REPORT ===\n")
    
    for func_name, func_stats in sorted(stats.items()):
        print(f"Function: {func_name}")
        
        # Print call counts
        if func_stats.min_count == func_stats.max_count:
            if func_stats.min_count == "unknown":
                print(f"Total calls: unknown (contains calls in loops with unknown iterations)")
            else:
                print(f"Total calls: {func_stats.min_count}")
        else:
            print(f"Total calls: min={func_stats.min_count}, max={func_stats.max_count}")
        
        # If min and max paths are the same, print the call list only once.
        if func_stats.min_calls == func_stats.max_calls:
            print(f"\nCALLS ({len(func_stats.min_calls)} calls):")
            call_list = func_stats.min_calls
            if not call_list:
                print("  (no calls in execution path)")
            else:
                for call in call_list:
                    iteration_str = ""
                    if call.iteration is not None:
                        iteration_str = f" [iteration: {call.iteration}]"
                    parent_str = f" (in {call.parent_func})" if call.parent_func else ""
                    args_str = ", ".join(call.arg_names)
                    print(f"  - Line {call.line}: {call.func_name}({args_str}){iteration_str}{parent_str}")
                    for arg_info in call.arg_info:
                        if arg_info.get("is_sequence"):
                            dims_str = ""
                            if "dimensions" in arg_info:
                                dims_str = f", dimensions={arg_info['dimensions']}"
                            print(f"    * Arg '{arg_info['name']}': type={arg_info['type']}, length={arg_info['length']}{dims_str}")
                            
        else:
            # Print minimum path calls
            print(f"\nMINIMUM PATH CALLS ({len(func_stats.min_calls)} calls):")
            if not func_stats.min_calls:
                print("  (no calls in minimum execution path)")
            else:
                for call in func_stats.min_calls:
                    iteration_str = f" [iteration: {call.iteration}]" if call.iteration is not None else ""
                    parent_str = f" (in {call.parent_func})" if call.parent_func else ""
                    args_str = ", ".join(call.arg_names)
                    print(f"  - Line {call.line}: {call.func_name}({args_str}){iteration_str}{parent_str}")
                    for arg_info in call.arg_info:
                        if arg_info.get("is_sequence"):
                            dims_str = ""
                            if "dimensions" in arg_info:
                                dims_str = f", dimensions={arg_info['dimensions']}"
                            print(f"    * Arg '{arg_info['name']}': type={arg_info['type']}, length={arg_info['length']}{dims_str}")
            
            # Print maximum path calls
            print(f"\nMAXIMUM PATH CALLS ({len(func_stats.max_calls)} calls):")
            if not func_stats.max_calls:
                print("  (no calls in maximum execution path)")
            else:
                for call in func_stats.max_calls:
                    iteration_str = f" [iteration: {call.iteration}]" if call.iteration is not None else ""
                    parent_str = f" (in {call.parent_func})" if call.parent_func else ""
                    args_str = ", ".join(call.arg_names)
                    print(f"  - Line {call.line}: {call.func_name}({args_str}){iteration_str}{parent_str}")
                    for arg_info in call.arg_info:
                        if arg_info.get("is_sequence"):
                            dims_str = ""
                            if "dimensions" in arg_info:
                                dims_str = f", dimensions={arg_info['dimensions']}"
                            print(f"    * Arg '{arg_info['name']}': type={arg_info['type']}, length={arg_info['length']}{dims_str}")
        
        print("\n" + "="*60 + "\n")

# Test cases
def test_analyzer():
    """Test the analyzer with the problematic case."""
    
    test_code = """
def process_item(item):
    print(f"Processing: {item}")
    return item * 2

data = [1, 2, 3]
result = []

for item in data:
    processed = process_item(item)
    if processed > 3:
        result.append(processed)
        log("added", processed)
    else:
        log("skipped", processed)

print("Done", data)
"""
    
    print("=== TEST CASE ===")
    print(f"Code:\n{test_code.strip()}\n")
    
    stats = analyze_function_calls(test_code)
    print_analysis_report(stats)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            code = f.read()    
        stats = analyze_function_calls(code)
        print_analysis_report(stats)
    else:
        test_analyzer()