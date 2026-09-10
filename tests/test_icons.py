# Copyright 2026 Dorsal Hub LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
