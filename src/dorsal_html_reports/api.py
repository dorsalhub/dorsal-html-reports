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

import datetime
import html
import json
import logging
import pathlib
from typing import Any

from jinja2 import Environment, FileSystemLoader

from dorsal_html_reports.generator import REPORT_DATA_GENERATORS, _parse_date, human_filesize, resolve_template_path
from dorsal_html_reports.templates.file.icons import get_media_type_icon


logger = logging.getLogger(__name__)
__version__ = "0.1.0"


def generate_html_file_report(
    file_data: dict[str, Any] | Any,
    output_path: str | None = None,
    template: str = "default",
) -> str | None:
    """Generates a self-contained HTML report for a single file JSON payload."""
    if isinstance(file_data, str):
        raise TypeError("file_data must be a parsed dictionary, not a JSON string. Use json.loads() first.")

    try:
        template_file, template_base_dir = resolve_template_path(report_type="file", name_or_path=template)

        env = Environment(loader=FileSystemLoader(template_base_dir), autoescape=True)
        env.globals["human_filesize"] = human_filesize
        env.globals["get_media_type_icon"] = get_media_type_icon

        jinja_template = env.get_template(template_file.name)

        base_info = file_data.get("annotations", {}).get("file/base", {}).get("record", {})
        file_size_info = {
            "human": human_filesize(base_info.get("size", 0)),
            "raw": f"{base_info.get('size', 0)} bytes",
        }

        local_attrs = file_data.get("local_attributes") or file_data.get("local_filesystem") or {}

        date_created = local_attrs.get("date_created", "")
        date_modified = local_attrs.get("date_modified", "")

        local_fs_info = {
            "record_id": local_attrs.get("record_id")
            or local_attrs.get("instance_id")
            or file_data.get("record_id", ""),
            "full_path": local_attrs.get("full_path") or local_attrs.get("file_path", ""),
            "date_created": {"human": date_created, "raw": date_created},
            "date_modified": {"human": date_modified, "raw": date_modified},
        }

        context = {
            "report_title": f"Dorsal Report: {html.escape(base_info.get('name', 'Untitled File'))}",
            "generation_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "file": file_data,
            "file_size": file_size_info,
            "raw_data_json": json.dumps(file_data, indent=2, default=str),
            "local_filesystem_info": local_fs_info,
            "dorsal_version": __version__,
        }

        html_content = jinja_template.render(context)

        if output_path:
            output_file = pathlib.Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML file report saved to: {output_path}")
            return None

        return html_content
    except Exception as e:
        logger.exception("Failed to generate HTML file report.")
        raise RuntimeError(f"Could not generate HTML report: {e}") from e


def generate_html_directory_report(
    collection_data: dict[str, Any] | Any,
    output_path: str | None = None,
    template: str = "default",
    enabled_panels: list[str] | None = None,
) -> str | None:
    """Generates a dashboard for a directory using a collection JSON payload."""
    if isinstance(collection_data, str):
        raise TypeError("collection_data must be a parsed dictionary, not a JSON string. Use json.loads() first.")

    try:
        if enabled_panels is None:
            enabled_panels = [
                "summary_stats",
                "collection_overview",
                "duplicates_report",
                "dynamic_size_histogram",
                "file_explorer",
            ]

        files_array = collection_data.get("results", [])
        if isinstance(files_array, dict) and "results" in files_array:
            files_array = files_array["results"]

        for f in files_array:
            for attr_key in ("local_attributes", "local_filesystem"):
                attrs = f.get(attr_key)
                if isinstance(attrs, dict):
                    for d_field in ("date_modified", "date_created"):
                        val = attrs.get(d_field)
                        if isinstance(val, str):
                            parsed = _parse_date(val)
                            if parsed:
                                attrs[d_field] = parsed

        panels_to_render = []
        for panel_id in enabled_panels:
            generator_func = REPORT_DATA_GENERATORS.get(panel_id)
            if generator_func:
                panel_data = generator_func(files_array)
                panels_to_render.append(
                    {
                        "id": panel_id,
                        "title": panel_id.replace("_", " ").title(),
                        "data": panel_data,
                    }
                )

        template_file, template_base_dir = resolve_template_path(report_type="collection", name_or_path=template)

        env = Environment(loader=FileSystemLoader(template_base_dir), autoescape=True)
        env.globals["human_filesize"] = human_filesize
        env.globals["get_media_type_icon"] = get_media_type_icon

        jinja_template = env.get_template(template_file.name)

        collection_data["panels"] = panels_to_render
        full_collection_data_json = json.dumps(collection_data, default=str)

        scan_meta = collection_data.get("scan_metadata", {})
        dir_path = scan_meta.get("path", "Directory Scan")

        context = {
            "report_title": f"Directory Report: {html.escape(pathlib.Path(dir_path).name)}",
            "collection_source_path": dir_path,
            "generation_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "dorsal_version": __version__,
            "panels": panels_to_render,
            "full_collection_data_json": full_collection_data_json,
        }

        html_content = jinja_template.render(context)

        if output_path:
            output_file = pathlib.Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML dashboard saved to: {output_path}")
            return None

        return html_content
    except Exception as e:
        logger.exception("Failed to generate HTML dashboard.")
        raise RuntimeError(f"Could not generate HTML dashboard: {e}") from e
