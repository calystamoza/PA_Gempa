import re
text = """
Namun, ini JSONnya:
{
  "intent": "average"
}
Dan pastikan JSON ini benar {ya}.
"""
match = re.search(r'\{.*\}', text, re.DOTALL)
print(match.group(0))
