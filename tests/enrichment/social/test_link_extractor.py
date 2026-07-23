from app.enrichment.social.link_extractor import SocialLinkExtractor, classify_platform


def test_classify_platform() -> None:
    assert classify_platform("https://www.instagram.com/foo/") == "instagram"
    assert classify_platform("https://www.facebook.com/foo/") == "facebook"
    assert classify_platform("https://m.facebook.com/foo/") == "facebook"
    assert classify_platform("https://example.com/foo/") is None


def test_extracts_from_footer_and_header() -> None:
    html = """
    <html><body>
      <header><a href="https://instagram.com/headeronly">ig</a></header>
      <footer><a href="https://facebook.com/footeronly">fb</a></footer>
    </body></html>
    """
    candidates = SocialLinkExtractor().extract(html)
    sources = {(c.platform, c.source) for c in candidates}
    assert ("instagram", "header") in sources
    assert ("facebook", "footer") in sources


def test_footer_header_links_are_not_also_labeled_anchor() -> None:
    html = '<html><body><footer><a href="https://instagram.com/only">ig</a></footer></body></html>'
    candidates = SocialLinkExtractor().extract(html)
    assert len(candidates) == 1
    assert candidates[0].source == "footer"


def test_extracts_from_generic_anchor() -> None:
    html = '<html><body><div><a href="https://www.facebook.com/mybiz">Follow us</a></div></body></html>'
    candidates = SocialLinkExtractor().extract(html)
    assert any(c.platform == "facebook" and c.source == "anchor" for c in candidates)


def test_extracts_from_link_rel_me() -> None:
    html = '<html><head><link rel="me" href="https://www.instagram.com/mybiz"></head><body></body></html>'
    candidates = SocialLinkExtractor().extract(html)
    assert any(c.platform == "instagram" and c.source == "meta" for c in candidates)


def test_extracts_from_json_ld_same_as() -> None:
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Organization", "sameAs": ["https://www.instagram.com/mybiz", "https://www.facebook.com/mybiz"]}
    </script>
    </head><body></body></html>
    """
    candidates = SocialLinkExtractor().extract(html)
    platforms_sources = {(c.platform, c.source) for c in candidates}
    assert ("instagram", "json_ld") in platforms_sources
    assert ("facebook", "json_ld") in platforms_sources


def test_extracts_from_json_ld_graph() -> None:
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@graph": [{"@type": "Organization", "sameAs": "https://www.instagram.com/mybiz"}]}
    </script>
    </head><body></body></html>
    """
    candidates = SocialLinkExtractor().extract(html)
    assert any(c.platform == "instagram" and c.source == "json_ld" for c in candidates)


def test_malformed_json_ld_is_skipped_without_raising() -> None:
    html = '<html><head><script type="application/ld+json">{not valid json</script></head><body></body></html>'
    candidates = SocialLinkExtractor().extract(html)
    assert candidates == []


def test_ignores_non_social_links() -> None:
    html = '<html><body><a href="https://example.com/about">About</a></body></html>'
    candidates = SocialLinkExtractor().extract(html)
    assert candidates == []


def test_no_content_beyond_url_is_extracted() -> None:
    """Nothing about the linked profile's content is read — only the href."""
    html = '<html><body><a href="https://www.instagram.com/mybiz">Follow us on Instagram!</a></body></html>'
    candidates = SocialLinkExtractor().extract(html)
    assert len(candidates) == 1
    assert candidates[0].url == "https://www.instagram.com/mybiz"
