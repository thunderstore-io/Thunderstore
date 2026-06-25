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


@pytest.mark.parametrize(
    "markdown",
    (
        "README.md",
        "See CHANGELOG.md for details",
        "Run setup.sh to install",
        "example.io",
        "Edit the config.ai file",
    ),
)
def test_bare_word_with_tld_is_not_linkified(markdown: str) -> None:
    # Bare words ending in a valid TLD (.md, .sh, .io, .ai, ...) must stay plain
    # text, not become links to e.g. http://readme.md.
    assert "<a " not in render_markdown(markdown)


@pytest.mark.parametrize(
    "url",
    (
        "https://example.com",
        "http://example.com/path",
    ),
)
def test_explicit_url_is_still_linkified(url: str) -> None:
    assert f'<a href="{url}">{url}</a>' in render_markdown(url)
