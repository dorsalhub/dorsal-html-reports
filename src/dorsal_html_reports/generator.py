
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

import math
import statistics
import pathlib
import logging
from collections import Counter, defaultdict
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

# --- Standalone Utilities ---

def human_filesize(bytes_size: int, si: bool = False, dp: int = 1) -> str:
    thresh = 1000 if si else 1024
    if abs(bytes_size) < thresh:
        return f"{bytes_size} B"
    units = ['kB','MB','GB','TB'] if si else ['KiB','MiB','GiB','TiB']
    u = -1
    r = 10**dp
    while round(abs(bytes_size) * r) / r >= thresh and u < len(units) - 1:
        bytes_size /= thresh
        u += 1
    return f"{bytes_size:.{dp}f} {units[u]}"

def _get_base_rec(f: dict) -> dict:
    return f.get("annotations", {}).get("file/base", {}).get("record", {})

def _get_local_attrs(f: dict) -> dict:
    return f.get("local_attributes", {}) or f.get("local_filesystem", {}) or {}

# --- Template Resolution ---

def resolve_template_path(report_type: str, name_or_path: str) -> tuple[pathlib.Path, pathlib.Path]:
    """Finds a template file. Defaults to bundled templates."""
    explicit_path = pathlib.Path(name_or_path).resolve()
    if explicit_path.is_file():
        return explicit_path, explicit_path.parent

    template_filename = f"{name_or_path}.html"
    built_in_path = pathlib.Path(__file__).parent / "templates" / report_type / template_filename
    
    if built_in_path.is_file():
        return built_in_path, built_in_path.parent

    raise FileNotFoundError(f"Template '{name_or_path}' for report type '{report_type}' could not be found.")

# --- Panel Data Generators ---

def get_summary_stats_data(files: list[dict]) -> dict:
    """Returns data needed for the summary stats panel."""
    total_size = sum(_get_base_rec(f).get("size", 0) for f in files)
    
    sorted_by_date = sorted(files, key=lambda f: _get_local_attrs(f).get("date_modified", ""))
    
    newest = sorted_by_date[-1] if sorted_by_date else None
    oldest = sorted_by_date[0] if sorted_by_date else None
    
    return {
        "overall": {
            "total_files": len(files),
            "total_size": total_size,
            "newest_file": {
                "date": _get_local_attrs(newest).get("date_modified", "") if newest else None,
                "path": _get_base_rec(newest).get("name", "") if newest else None
            },
            "oldest_file": {
                "date": _get_local_attrs(oldest).get("date_modified", "") if oldest else None,
                "path": _get_base_rec(oldest).get("name", "") if oldest else None
            }
        }
    }

def get_duplicates_data(files: list[dict]) -> dict:
    """Groups files by Hash/Size to find duplicates."""
    hash_map = defaultdict(list)
    for f in files:
        h = f.get("hash") or f.get("validation_hash") or f.get("quick_hash")
        if h:
            hash_map[h].append(f)
            
    duplicates = []
    wasted_space = 0
    
    for h, file_list in hash_map.items():
        if len(file_list) > 1:
            size = _get_base_rec(file_list[0]).get("size", 0)
            wasted_space += size * (len(file_list) - 1)
            duplicates.append({
                "count": len(file_list),
                "file_size": human_filesize(size),
                "hash": str(h)[:12],
                "paths": [_get_local_attrs(f).get("file_path", _get_base_rec(f).get("name", "Unknown")) for f in file_list]
            })
            
    return {
        "total_sets": len(duplicates),
        "total_wasted_space": human_filesize(wasted_space),
        "duplicate_sets": sorted(duplicates, key=lambda x: x["count"], reverse=True)
    }

def get_collection_overview_data(files: list[dict]) -> dict:
    """Prepares data for the composition doughnuts and timeline."""
    if not files:
        return {}

    CHART_ITEM_CAP = 14
    total_collection_size = sum(_get_base_rec(f).get("size", 0) for f in files)

    # Extension Stats
    ext_counts = Counter(_get_base_rec(f).get("extension", "None") for f in files)
    top_exts = [{"extension": ext, "count": count} for ext, count in ext_counts.most_common(CHART_ITEM_CAP)]
    
    ext_sizes = defaultdict(int)
    for f in files:
        ext_sizes[_get_base_rec(f).get("extension", "None")] += _get_base_rec(f).get("size", 0)
    top_ext_sizes = [{"extension": ext, "total_size": size} for ext, size in sorted(ext_sizes.items(), key=lambda x: x[1], reverse=True)[:CHART_ITEM_CAP]]

    # Media Type Stats
    mt_counts = Counter(_get_base_rec(f).get("media_type", "Unknown") for f in files)
    top_mts = [{"media_type": mt, "count": count} for mt, count in mt_counts.most_common(CHART_ITEM_CAP)]
    
    mt_sizes = defaultdict(int)
    for f in files:
        mt_sizes[_get_base_rec(f).get("media_type", "Unknown")] += _get_base_rec(f).get("size", 0)
    top_mt_sizes = [{"media_type": mt, "total_size": size} for mt, size in sorted(mt_sizes.items(), key=lambda x: x[1], reverse=True)[:CHART_ITEM_CAP]]

    # Largest Files
    sorted_by_size = sorted(files, key=lambda f: _get_base_rec(f).get("size", 0), reverse=True)
    largest_files = [{"name": _get_base_rec(f).get("name", "Unknown"), "size": _get_base_rec(f).get("size", 0)} for f in sorted_by_size[:CHART_ITEM_CAP]]

    # Timeline Data
    timeline_data = [{"x": _get_local_attrs(f).get("date_modified"), "y": _get_base_rec(f).get("name")} for f in files if _get_local_attrs(f).get("date_modified")]
    
    sorted_by_date = sorted([f for f in files if _get_local_attrs(f).get("date_modified")], key=lambda f: _get_local_attrs(f).get("date_modified"))
    most_recent = sorted_by_date[-1] if sorted_by_date else None

    return {
        "media_type": {"by_size": top_mt_sizes, "by_count": top_mts},
        "extension": {"by_size": top_ext_sizes, "by_count": top_exts},
        "largest_files": {"by_size": largest_files},
        "timeline_data": timeline_data,
        "most_recent_file_record": most_recent,
    }

def get_dynamic_size_histogram_data(files: list[dict]) -> list[dict]:
    sizes = [_get_base_rec(f).get("size", 0) for f in files if _get_base_rec(f).get("size", 0) > 0]
    if not sizes:
        return []

    if len(set(sizes)) < 5 and len(sizes) < 20:
        return [{"bin_label": human_filesize(size), "count": count} for size, count in sorted(Counter(sizes).items())]

    n = len(sizes)
    num_bins = 1
    if n > 1:
        q1 = statistics.quantiles(sizes, n=4)[0]
        q3 = statistics.quantiles(sizes, n=4)[2]
        iqr = q3 - q1
        if iqr > 0:
            bin_width = 2 * iqr / (n ** (1 / 3))
            num_bins = int(math.ceil((max(sizes) - min(sizes)) / bin_width)) if bin_width > 0 else 10

    num_bins = max(1, min(num_bins, 25))
    min_safe_size = min(sizes)
    
    if max(sizes) / min_safe_size > 1000:
        log_min = math.log10(min_safe_size)
        log_max = math.log10(max(sizes))
        bin_edges = [10**i for i in [log_min + x * (log_max - log_min) / num_bins for x in range(num_bins + 1)]]
    else:
        min_size, max_size = min(sizes), max(sizes)
        step = (max_size - min_size) / num_bins
        bin_edges = [min_size + i * step for i in range(num_bins + 1)]

    bin_counts = [0] * num_bins
    for size in sizes:
        for i in range(num_bins):
            if (bin_edges[i] <= size < bin_edges[i + 1]) or (i == num_bins - 1 and size == bin_edges[i + 1]):
                bin_counts[i] += 1
                break

    chart_data = []
    for i in range(len(bin_counts)):
        if bin_counts[i] > 0:
            chart_data.append({
                "bin_label": f"{human_filesize(bin_edges[i])} - {human_filesize(bin_edges[i + 1])}", 
                "count": bin_counts[i]
            })

    return chart_data

def get_file_explorer_data(files: list[dict]) -> dict:
    return {}

REPORT_DATA_GENERATORS: Dict[str, Callable[[list[dict]], Any]] = {
    "summary_stats": get_summary_stats_data,
    "collection_overview": get_collection_overview_data,
    "duplicates_report": get_duplicates_data,
    "dynamic_size_histogram": get_dynamic_size_histogram_data,
    "file_explorer": get_file_explorer_data,
}