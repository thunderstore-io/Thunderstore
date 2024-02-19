from io import BytesIO

import pytest
from django.test import Client
from lxml import etree

from thunderstore.community.models import CommunitySite
from thunderstore.frontend.models import FooterLink, LinkTargetChoices


@pytest.mark.django_db
def test_frontend_footer_links(client: Client, community_site: CommunitySite):
    test_link = FooterLink.objects.create(
        title="Test link",
        group_title="Test group",
        href="http://example.com",
        target=LinkTargetChoices.Blank,
    )
    inactive_link = FooterLink.objects.create(
        title="Inactive link",
        is_active=False,
        group_title=test_link.group_title,
        href="http://example.org",
        target=LinkTargetChoices.Blank,
    )
    response = client.get(
        f"/c/{community_site.community.identifier}/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    buffer = BytesIO(response.content)
    tree = etree.parse(buffer, etree.HTMLParser())
    groups = tree.xpath(
        f"//div[@class='footer_column']/h2[contains(text(), '{test_link.group_title}')]"
    )
    assert len(groups) == 1
    group_container = groups[0].getparent()
    links = group_container.xpath("./a")
    assert len(links) == 1
    link = links[0]
    assert link.attrib["href"] == test_link.href
    assert link.attrib["target"] == test_link.target
    assert link.text == test_link.title
