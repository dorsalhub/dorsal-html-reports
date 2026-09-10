from dorsal_html_reports.templates.file.icons import ICON_MAP, get_media_type_icon


def test_get_media_type_icon_exact_match():
    assert get_media_type_icon("application/pdf") == ICON_MAP["application/pdf"]


def test_get_media_type_icon_prefix_match():

    assert get_media_type_icon("image/png") == ICON_MAP["image"]
    assert get_media_type_icon("audio/mpeg") == ICON_MAP["audio"]
    assert get_media_type_icon("video/mp4") == ICON_MAP["video"]


def test_get_media_type_icon_default_fallback():

    assert get_media_type_icon("text/plain") == ICON_MAP["default"]
    assert get_media_type_icon("unknown") == ICON_MAP["default"]
