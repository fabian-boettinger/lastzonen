"""Baut index.html aus page_head.html + zonen.json + app.js.

Aufruf: python assemble.py [ordner]   (ohne Angabe: Ordner dieses Skripts)
"""
import os
import sys

d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return f.read()


head = read("page_head.html")
data = read("zonen.json").replace("</", "<\\/")
app = read("app.js")
html = (head + '<script id="zonen" type="application/json">' + data + '</script>\n'
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n<script>\n' + app + '</script>\n</body>\n</html>\n')
with open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print(len(html))
