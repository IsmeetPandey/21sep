import unittest

from mcp_changeguard.core import compare, load_tools


def tool(name, schema=None, description="tool", ident=None):
    value = {"name": name, "description": description, "inputSchema": schema or {"type": "object"}}
    if ident:
        value["x-changeguard-id"] = ident
    return value


class ContractTests(unittest.TestCase):
    def test_required_addition_is_breaking(self):
        before = [tool("search", {"type": "object", "properties": {"q": {"type": "string"}}})]
        after = [tool("search", {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]})]
        changes = compare(before, after)
        self.assertEqual([(c.severity, c.kind) for c in changes], [("breaking", "required-added")])

    def test_optional_property_addition_is_compatible(self):
        before = [tool("search", {"type": "object", "properties": {}})]
        after = [tool("search", {"type": "object", "properties": {"limit": {"type": "integer"}}})]
        changes = compare(before, after)
        self.assertEqual(changes[0].severity, "compatible")

    def test_enum_narrowing_is_breaking(self):
        before = [tool("mode", {"type": "object", "properties": {"mode": {"type": "string", "enum": ["a", "b"]}}})]
        after = [tool("mode", {"type": "object", "properties": {"mode": {"type": "string", "enum": ["a"]}}})]
        self.assertEqual(compare(before, after)[0].severity, "breaking")

    def test_stable_id_allows_rename(self):
        before = [tool("lookup", ident="lookup-v1")]
        after = [tool("search", ident="lookup-v1")]
        changes = compare(before, after)
        self.assertEqual(changes[0].kind, "renamed")
        self.assertEqual(changes[0].severity, "review")

    def test_removed_tool_is_breaking(self):
        self.assertEqual(compare([tool("old")], [])[0].kind, "tool-removed")

    def test_tools_list_shape(self):
        value = load_tools({"tools": [tool("x")]})
        self.assertEqual(value[0]["name"], "x")


if __name__ == "__main__":
    unittest.main()
