import tree_sitter
print(dir(tree_sitter))
try:
   from tree_sitter import Query
   print(f"Query dir: {dir(Query)}")
except:
   print("Cannot import Query")
