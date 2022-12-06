import base64
import json
import re
from io import StringIO
from typing import Any, Iterable, Optional

from lxml import etree

REGEX_TEMPLATE = r"window\.ts\.{component}\(\s+document\.getElementById\(\"{id}\"\),\s+\"([a-zA-Z0-9=]+)\"\s+\);"

# Sourced from https://mathiasbynens.be/demo/javascript-mime-type
#    snapshot: http://web.archive.org/web/20221111201024/https://mathiasbynens.be/demo/javascript-mime-type
VALID_SCRIPT_TYPES = {
    "",
    "application/ecmascript",
    "application/javascript",
    "application/x-ecmascript",
    "application/x-javascript",
    "text/ecmascript",
    "text/javascript",
    "text/jscript",
    "text/x-ecmascript",
    "text/x-javascript",
}


def enumerate_scripts(html: str) -> Iterable[str]:
    buffer = StringIO(html)
    tree = etree.parse(buffer, etree.HTMLParser())
    for entry in tree.findall(".//script"):
        if entry.get("type", "").lower() in VALID_SCRIPT_TYPES and entry.text:
            yield entry.text


def decode_props(props: str) -> Any:
    return json.loads(base64.b64decode(props))


def extract_props_from_html(
    html: str, component_name: str, component_id: str
) -> Optional[Any]:
    pattern = re.compile(
        REGEX_TEMPLATE.format(component=component_name, id=component_id)
    )
    for script in enumerate_scripts(html):
        result = re.search(pattern, script)
        if result:
            return decode_props(result.group(1))
