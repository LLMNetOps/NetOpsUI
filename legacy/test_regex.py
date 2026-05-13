import re

text="""0   address=10.26.121.37 mac-address=9C:6B:00:2E:40:C1 server=Lab-67-Admin status=waiting
1 D address=10.5.5.5 mac-address=AA:BB:CC:DD:EE:FF status=bound disabled=yes comment="hello world"
"""

for line in text.splitlines():
    props = dict(re.findall(r'([a-zA-Z0-9\-]+)=(".*?"|\S+)', line))
    print(props)
