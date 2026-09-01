import re
import os

matches = []
for dp, dn, fn in os.walk('app'):
    for f in fn:
        if f.endswith('.py'):
            path = os.path.join(dp, f)
            content = open(path).read()
            for m in re.finditer(r'except Exception:\s+pass', content, re.MULTILINE):
                matches.append((os.path.relpath(path), m.start()))

for f, p in matches[:50]:
    print(f"{f}:{p}")
