import pytest

from thunderstore.markdown.templatetags.markdownify import render_markdown

EDGE_CASE_MARKDOWN = "> QUOTE\n+ UNORDERED LIST ITEM\n  > INDENTED QUOTE\n\n\n"


EDGE_CASE_MARKUP = (
    "<blockquote>\n"
    "<p>QUOTE</p>\n"
    "</blockquote>\n"
    "<ul>\n"
    "<li>UNORDERED LIST ITEM\n"
    "<blockquote>\n"
    "<p>INDENTED QUOTE</p>\n"
    "</blockquote>\n"
    "</li>\n"
    "</ul>\n"
)


@pytest.mark.parametrize(
    ("markdown", "expected"),
    (
        ("", ""),
        ("\ufeff", ""),
        ("This is some text", "<p>This is some text</p>\n"),
        (EDGE_CASE_MARKDOWN, EDGE_CASE_MARKUP),
    ),
)
def test_markdown_is_rendered_to_markup(markdown: str, expected: str) -> None:
    actual = render_markdown(markdown)

    assert actual == expected
