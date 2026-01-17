import tree_sitter
print(f"Tree-sitter version: {tree_sitter.__version__}")
try:
    print(f"Query attributes: {dir(tree_sitter.Query)}")
except:
    pass

import inspect
try:
    # Try to verify the signature of captures if it exists (it might be on the instance)
    # We need a dummy language to create a query
    print("Attempting to inspect Query object...")
except Exception as e:
    print(e)
