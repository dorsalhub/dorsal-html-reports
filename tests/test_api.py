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

import json
import pathlib
from unittest.mock import patch

import pytest

from dorsal_html_reports import api

DATA_DIR = pathlib.Path(__file__).parent / "data"


@pytest.fixture
def real_file_data() -> dict:
    with open(DATA_DIR / "file.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def real_directory_data() -> dict:
    with open(DATA_DIR / "directory.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_generate_html_file_report_type_error():
    with pytest.raises(TypeError, match="file_data must be a parsed dictionary"):
        api.generate_html_file_report('{"key": "value"}')


def test_generate_html_file_report_returns_html(real_file_data: dict):
    html = api.generate_html_file_report(real_file_data)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "bill.pdf" in html
    assert "bb6c5d0d7011c114" in html
    assert "80.0 KiB" in html


def test_generate_html_file_report_writes_to_file(real_file_data: dict, tmp_path: pathlib.Path):
    out_file = tmp_path / "nested" / "output.html"
    result = api.generate_html_file_report(real_file_data, output_path=str(out_file))

    assert result is None
    assert out_file.is_file()
    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "bill.pdf" in content


def test_generate_html_file_report_attribute_fallbacks():

    payload_instance = {
        "local_filesystem": {
            "instance_id": "inst_9999",
            "file_path": "/fallback/path.txt",
        },
        "annotations": {"file/base": {"record": {"media_type": "text/plain", "name": "Untitled File"}}},
    }
    html = api.generate_html_file_report(payload_instance)
    assert isinstance(html, str)
    assert "Untitled File" in html
    assert "inst_9999" in html
    assert "/fallback/path.txt" in html

    payload_root = {
        "record_id": "root_rec_id",
        "local_attributes": {
            "file_path": "/fallback/file.txt",
        },
        "annotations": {"file/base": {"record": {"media_type": "text/plain", "name": "Untitled File"}}},
    }
    html2 = api.generate_html_file_report(payload_root)
    assert isinstance(html2, str)
    assert "root_rec_id" in html2


def test_generate_html_file_report_error_handling(real_file_data: dict):
    with patch("dorsal_html_reports.api.resolve_template_path", side_effect=Exception("Template engine failure")):
        with pytest.raises(RuntimeError, match="Could not generate HTML report: Template engine failure"):
            api.generate_html_file_report(real_file_data)


def test_generate_html_directory_report_type_error():
    with pytest.raises(TypeError, match="collection_data must be a parsed dictionary"):
        api.generate_html_directory_report('{"key": "value"}')


def test_generate_html_directory_report_default_panels(real_directory_data: dict):
    html = api.generate_html_directory_report(real_directory_data)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Directory Report: testmix" in html
    assert "Game Files.7z" in html
    assert "Chinua Achebe" in html


def test_generate_html_directory_report_custom_panels(real_directory_data: dict):

    html = api.generate_html_directory_report(
        real_directory_data,
        enabled_panels=["summary_stats", "non_existent_panel_xyz"],
    )
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Summary Stats" in html


def test_generate_html_directory_report_nested_dict_results(real_file_data: dict):

    collection = {
        "results": {
            "results": [real_file_data],
        }
    }
    html = api.generate_html_directory_report(collection)
    assert isinstance(html, str)
    assert "Directory Report: Directory Scan" in html


def test_generate_html_directory_report_writes_to_file(real_directory_data: dict, tmp_path: pathlib.Path):
    out_file = tmp_path / "sub" / "dashboard.html"
    result = api.generate_html_directory_report(real_directory_data, output_path=str(out_file))

    assert result is None
    assert out_file.is_file()
    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Directory Report: testmix" in content


def test_generate_html_directory_report_error_handling(real_directory_data: dict):
    with patch("dorsal_html_reports.api.resolve_template_path", side_effect=Exception("Disk read error")):
        with pytest.raises(RuntimeError, match="Could not generate HTML dashboard: Disk read error"):
            api.generate_html_directory_report(real_directory_data)
