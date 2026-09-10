import datetime
import pathlib
import pytest

from dorsal_html_reports import generator


# --- Standalone Utilities ---


def test_human_filesize_basic_and_types():
    assert generator.human_filesize(500) == "500 B"
    assert generator.human_filesize(500.5, dp=2) == "500.50 B"
    assert generator.human_filesize(-42) == "-42 B"


def test_human_filesize_units_binary_and_si():
    assert generator.human_filesize(1024) == "1.0 KiB"
    assert generator.human_filesize(1024 * 1024) == "1.0 MiB"
    assert generator.human_filesize(1024**3) == "1.0 GiB"
    assert generator.human_filesize(1024**4) == "1.0 TiB"
    assert generator.human_filesize(1024**5) == "1024.0 TiB"

    assert generator.human_filesize(1000, si=True) == "1.0 kB"
    assert generator.human_filesize(1_000_000, si=True) == "1.0 MB"
    assert generator.human_filesize(1_000_000_000, si=True) == "1.0 GB"
    assert generator.human_filesize(10**12, si=True) == "1.0 TB"
    assert generator.human_filesize(10**15, si=True) == "1000.0 TB"


def test_get_base_rec_and_local_attrs_fallbacks():
    assert generator._get_base_rec(None) == {}
    assert generator._get_base_rec({}) == {}
    assert generator._get_local_attrs(None) == {}
    assert generator._get_local_attrs({}) == {}

    f1 = {"local_attributes": {"record_id": "la1"}}
    assert generator._get_local_attrs(f1) == {"record_id": "la1"}

    f2 = {"local_attributes": {}, "local_filesystem": {"record_id": "lf2"}}
    assert generator._get_local_attrs(f2) == {"record_id": "lf2"}


def test_parse_date_handling():
    assert generator._parse_date(None) is None
    assert generator._parse_date("") is None
    assert generator._parse_date("not-a-valid-date-string") is None
    parsed = generator._parse_date("2026-01-01T00:00:00Z")
    assert parsed == datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)


# --- Template Resolution ---


def test_resolve_template_path(tmp_path: pathlib.Path):
    custom_tpl = tmp_path / "custom.html"
    custom_tpl.write_text("<div>Test</div>", encoding="utf-8")
    tpl_file, tpl_parent = generator.resolve_template_path("file", str(custom_tpl))
    assert tpl_file == custom_tpl.resolve()
    assert tpl_parent == tmp_path.resolve()

    tpl_file, tpl_parent = generator.resolve_template_path("file", "default")
    assert tpl_file.name == "default.html"
    assert tpl_file.is_file()

    with pytest.raises(FileNotFoundError, match="could not be found"):
        generator.resolve_template_path("file", "non_existent_template_xyz")


# --- Summary Stats Panel ---


def test_get_summary_stats_data_empty():
    res = generator.get_summary_stats_data([])
    assert res == {
        "overall": {
            "total_files": 0,
            "total_size": 0,
            "newest_file": {"date": None, "path": None},
            "oldest_file": {"date": None, "path": None},
        }
    }


def test_get_summary_stats_data_populated():
    files = [
        {
            "annotations": {"file/base": {"record": {"size": 100, "name": "old.txt"}}},
            "local_attributes": {"date_modified": "2026-01-01T00:00:00Z"},
        },
        {
            "annotations": {"file/base": {"record": {"size": 250, "name": "new.txt"}}},
            "local_attributes": {"date_modified": "2026-06-01T00:00:00Z"},
        },
    ]
    res = generator.get_summary_stats_data(files)
    assert res["overall"]["total_files"] == 2
    assert res["overall"]["total_size"] == 350
    assert res["overall"]["oldest_file"] == {
        "date": datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
        "path": "old.txt",
    }
    assert res["overall"]["newest_file"] == {
        "date": datetime.datetime(2026, 6, 1, 0, 0, tzinfo=datetime.timezone.utc),
        "path": "new.txt",
    }


# --- Duplicates Report Panel ---


def test_get_duplicates_data():
    files = [
        # Set 1 duplicates (3 files via 'hash')
        {
            "hash": "hash_aaa",
            "annotations": {"file/base": {"record": {"size": 1024, "name": "doc1.txt"}}},
            "local_attributes": {"file_path": "/tmp/doc1.txt"},
        },
        {
            "hash": "hash_aaa",
            "annotations": {"file/base": {"record": {"size": 1024, "name": "doc2.txt"}}},
            "local_attributes": {"file_path": "/tmp/doc2.txt"},
        },
        {
            "hash": "hash_aaa",
            "annotations": {"file/base": {"record": {"size": 1024, "name": "doc3.txt"}}},
            "local_attributes": {},  # Falls back to base name in paths list
        },
        # Set 2 duplicates (2 files via 'validation_hash')
        {
            "validation_hash": "val_hash_bbb",
            "annotations": {"file/base": {"record": {"size": 500}}},
            "local_attributes": {},
        },
        {
            "validation_hash": "val_hash_bbb",
            "annotations": {"file/base": {"record": {"size": 500}}},
            "local_attributes": {},
        },
        # Unique file using 'quick_hash'
        {
            "quick_hash": "quick_unique",
            "annotations": {"file/base": {"record": {"size": 2048}}},
        },
        # File missing any hash
        {
            "annotations": {"file/base": {"record": {"size": 100}}},
        },
    ]

    res = generator.get_duplicates_data(files)
    assert res["total_sets"] == 2
    assert res["total_wasted_space"] == generator.human_filesize(2548)
    assert len(res["duplicate_sets"]) == 2
    assert res["duplicate_sets"][0]["count"] == 3
    assert res["duplicate_sets"][0]["hash"] == "hash_aaa"[:12]
    assert res["duplicate_sets"][1]["count"] == 2


# --- Collection Overview Panel ---


def test_get_collection_overview_data_empty():
    assert generator.get_collection_overview_data([]) == {}


def test_get_collection_overview_data_populated():
    files = []
    for i in range(16):
        files.append(
            {
                "annotations": {
                    "file/base": {
                        "record": {
                            "name": f"file_{i}.ext{i}",
                            "extension": f".ext{i}",
                            "media_type": f"type/{i}",
                            "size": (i + 1) * 1000,
                        }
                    }
                },
                "local_attributes": {
                    "date_modified": f"2026-01-{i + 1:02d}T00:00:00Z",
                },
            }
        )

    res = generator.get_collection_overview_data(files)
    assert len(res["extension"]["by_count"]) == 14
    assert len(res["extension"]["by_size"]) == 14
    assert len(res["media_type"]["by_count"]) == 14
    assert len(res["media_type"]["by_size"]) == 14
    assert len(res["largest_files"]["by_size"]) == 14
    assert len(res["timeline_data"]) == 16
    assert res["most_recent_file_record"]["annotations"]["file/base"]["record"]["name"] == "file_15.ext15"


def test_get_collection_overview_data_missing_dates_and_metadata():
    files = [
        {"annotations": {}},
    ]
    res = generator.get_collection_overview_data(files)
    assert res["extension"]["by_count"][0]["extension"] == "None"
    assert res["media_type"]["by_count"][0]["media_type"] == "Unknown"
    assert res["timeline_data"] == []
    assert res["most_recent_file_record"] is None


# --- Dynamic Size Histogram Panel ---


def test_get_dynamic_size_histogram_data_empty_or_zero_sizes():
    assert generator.get_dynamic_size_histogram_data([]) == []
    assert generator.get_dynamic_size_histogram_data([{"annotations": {"file/base": {"record": {"size": 0}}}}]) == []


def test_get_dynamic_size_histogram_data_sparse_small_dataset():
    files = [
        {"annotations": {"file/base": {"record": {"size": 100}}}},
        {"annotations": {"file/base": {"record": {"size": 100}}}},
        {"annotations": {"file/base": {"record": {"size": 200}}}},
    ]
    res = generator.get_dynamic_size_histogram_data(files)
    assert len(res) == 2
    assert res[0]["count"] == 2
    assert res[0]["bin_label"] == "100 B"
    assert res[1]["count"] == 1
    assert res[1]["bin_label"] == "200 B"


def test_get_dynamic_size_histogram_data_linear_distribution():
    files = [{"annotations": {"file/base": {"record": {"size": 1000 + i * 10}}}} for i in range(25)]
    res = generator.get_dynamic_size_histogram_data(files)
    assert len(res) >= 1
    total_count = sum(bin_entry["count"] for bin_entry in res)
    assert total_count == 25
    assert " - " in res[0]["bin_label"]


def test_get_dynamic_size_histogram_data_logarithmic_distribution():
    sizes = [100] * 12 + [1_000_000] * 12
    files = [{"annotations": {"file/base": {"record": {"size": s}}}} for s in sizes]
    res = generator.get_dynamic_size_histogram_data(files)
    assert len(res) >= 1
    total_count = sum(bin_entry["count"] for bin_entry in res)
    assert total_count == 24


def test_get_dynamic_size_histogram_data_zero_iqr_fallback():
    files = [{"annotations": {"file/base": {"record": {"size": 5000}}}} for _ in range(22)]
    res = generator.get_dynamic_size_histogram_data(files)
    assert len(res) >= 1
    total_count = sum(bin_entry["count"] for bin_entry in res)
    assert total_count == 22


# --- File Explorer & Dispatch Registry ---


def test_get_file_explorer_data():
    assert generator.get_file_explorer_data([]) == {}


def test_report_data_generators_dict():
    expected_keys = {
        "summary_stats",
        "collection_overview",
        "duplicates_report",
        "dynamic_size_histogram",
        "file_explorer",
    }
    assert set(generator.REPORT_DATA_GENERATORS.keys()) == expected_keys
    for func in generator.REPORT_DATA_GENERATORS.values():
        assert callable(func)
