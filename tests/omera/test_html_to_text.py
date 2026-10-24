from xavani_omera.html_to_text import html_to_text


def test_strips_scripts_and_collapses_whitespace():
    markup = (
        "<html><head><title>CIPC fees</title>"
        "<style>.x{color:red}</style></head>"
        "<body><script>alert('x')</script>"
        "<h1>Annual return</h1><p>Pay within   30 days.</p></body></html>"
    )
    title, text = html_to_text(markup)
    assert title == "CIPC fees"
    assert "alert" not in text
    assert "color:red" not in text
    assert "Pay within 30 days." in text
    assert "\n\n\n" not in text


def test_caps_output_length():
    _, text = html_to_text("<p>" + ("word " * 5000) + "</p>", max_chars=100)
    assert len(text) == 100


def test_decodes_entities():
    _, text = html_to_text("<p>Fees &amp; fines &lt; R500</p>")
    assert "Fees & fines < R500" in text
