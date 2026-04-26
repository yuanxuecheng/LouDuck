"""
Test script for mono_channel_matcher
Tests the smart channel matching algorithm against known filenames.
"""

import sys
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mono_channel_matcher import (
    _extract_channel_id,
    auto_match_mono_files,
    CHANNEL_TEMPLATES,
)


def create_mono_wav(path: Path):
    data = np.zeros(100, dtype=np.float32)
    sf.write(str(path), data, 48000)


def test_extract_channel_id():
    print("=" * 70)
    print("Test 1: _extract_channel_id")
    print("=" * 70)

    cases = [
        # 5.1.4 user files with digit prefix (e.g. 5.1L)
        ("16ChTest_Content_01_5.1L_20221222", "L"),
        ("16ChTest_Content_02_5.1R_20221222", "R"),
        ("16ChTest_Content_03_5.1C_20221222", "C"),
        ("16ChTest_Content_04_5.1Lfe_20221222", "LFE"),
        ("16ChTest_Content_05_5.1Ls_20221222", "Ls"),
        ("16ChTest_Content_06_5.1Rs_20221222", "Rs"),
        # Note: lmsvLtf etc. rely on template context in auto_match,
        # _extract_channel_id alone is conservative and returns "".
        ("16ChTest_Content_09_lmsvLtf_20221222", ""),
        ("16ChTest_Content_10_lmsvRtf_20221222", ""),
        ("16ChTest_Content_11_lmsvLtr_20221222", ""),
        ("16ChTest_Content_12_lmsvRtr_20221222", ""),
        # Dot suffix
        ("2005.L", "L"),
        ("2005.R", "R"),
        ("2005.C", "C"),
        ("2005.LFE", "LFE"),
        ("2005.Ls", "Ls"),
        ("2005.Rs", "Rs"),
        # Standard naming
        ("Track_L_01", "L"),
        ("Track_R_02", "R"),
        ("Track_C_03", "C"),
        (" ambience_L", "L"),
    ]

    all_pass = True
    for stem, expected in cases:
        result = _extract_channel_id(stem)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_pass = False
        print(f"  [{status}]  {stem:50s}  expected={expected:5s}  got={result or '-':5s}")

    print()
    print("Result:", "ALL PASSED" if all_pass else "SOME FAILED")
    return all_pass


def test_auto_match_5_1_4():
    print()
    print("=" * 70)
    print("Test 2: auto_match_mono_files (5.1.4, 10 files)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        expected = {
            "16ChTest_Content_01_5.1L_20221222.wav": "L",
            "16ChTest_Content_02_5.1R_20221222.wav": "R",
            "16ChTest_Content_03_5.1C_20221222.wav": "C",
            "16ChTest_Content_04_5.1Lfe_20221222.wav": "LFE",
            "16ChTest_Content_05_5.1Ls_20221222.wav": "Ls",
            "16ChTest_Content_06_5.1Rs_20221222.wav": "Rs",
            "16ChTest_Content_09_lmsvLtf_20221222.wav": "Ltf",
            "16ChTest_Content_10_lmsvRtf_20221222.wav": "Rtf",
            "16ChTest_Content_11_lmsvLtr_20221222.wav": "Ltr",
            "16ChTest_Content_12_lmsvRtr_20221222.wav": "Rtr",
        }

        paths = []
        for fname in expected:
            fpath = Path(tmpdir) / fname
            create_mono_wav(fpath)
            paths.append(str(fpath))

        results = auto_match_mono_files(paths)

        print("\nMatching results:")
        all_pass = True
        for fpath, ch in results:
            fname = Path(fpath).name
            exp = expected.get(fname, "?")
            status = "PASS" if ch == exp else "FAIL"
            if ch != exp:
                all_pass = False
            print(f"  [{status}]  [{ch:5s}]  <-  {fname}")

        unmatched = [Path(p).name for p, c in results if c == "?"]
        if unmatched:
            print(f"\nWARNING: {len(unmatched)} unmatched")
            all_pass = False

        template_order = CHANNEL_TEMPLATES["5.1.4 (10ch)"]["channels"]
        matched_chs = [ch for _, ch in results if ch != "?"]
        if matched_chs == template_order:
            print("\nOrder check: PASS")
        else:
            print("\nOrder check: FAIL")
            print(f"  Expected: {template_order}")
            print(f"  Got:      {matched_chs}")
            all_pass = False

        print()
        print("Result:", "ALL PASSED" if all_pass else "SOME FAILED")
        return all_pass


def test_auto_match_dot_suffix():
    print()
    print("=" * 70)
    print("Test 3: auto_match_mono_files (dot suffix 5.1)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        expected = {
            "2005.L.wav": "L",
            "2005.R.wav": "R",
            "2005.C.wav": "C",
            "2005.LFE.wav": "LFE",
            "2005.Ls.wav": "Ls",
            "2005.Rs.wav": "Rs",
        }
        paths = []
        for fname in expected:
            fpath = Path(tmpdir) / fname
            create_mono_wav(fpath)
            paths.append(str(fpath))

        results = auto_match_mono_files(paths)
        all_pass = True
        for fpath, ch in results:
            fname = Path(fpath).name
            exp = expected.get(fname, "?")
            status = "PASS" if ch == exp else "FAIL"
            if ch != exp:
                all_pass = False
            print(f"  [{status}]  [{ch:5s}]  <-  {fname}")

        print()
        print("Result:", "ALL PASSED" if all_pass else "SOME FAILED")
        return all_pass


def test_auto_match_7_1_4():
    print()
    print("=" * 70)
    print("Test 4: auto_match_mono_files (explicit 7.1.4)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        expected = {
            "Track_L_01.wav": "L",
            "Track_R_02.wav": "R",
            "Track_C_03.wav": "C",
            "Track_LFE_04.wav": "LFE",
            "Track_Lss_05.wav": "Lss",
            "Track_Rss_06.wav": "Rss",
            "Track_Lrs_07.wav": "Lrs",
            "Track_Rrs_08.wav": "Rrs",
            "Track_Ltf_09.wav": "Ltf",
            "Track_Rtf_10.wav": "Rtf",
            "Track_Ltb_11.wav": "Ltb",
            "Track_Rtb_12.wav": "Rtb",
        }
        paths = []
        for fname in expected:
            fpath = Path(tmpdir) / fname
            create_mono_wav(fpath)
            paths.append(str(fpath))

        results = auto_match_mono_files(paths, template_name="7.1.4 (12ch)")
        all_pass = True
        for fpath, ch in results:
            fname = Path(fpath).name
            exp = expected.get(fname, "?")
            status = "PASS" if ch == exp else "FAIL"
            if ch != exp:
                all_pass = False
            print(f"  [{status}]  [{ch:5s}]  <-  {fname}")

        print()
        print("Result:", "ALL PASSED" if all_pass else "SOME FAILED")
        return all_pass


def main():
    print("\n" + "=" * 70)
    print(" mono_channel_matcher test suite")
    print("=" * 70 + "\n")

    t1 = test_extract_channel_id()
    t2 = test_auto_match_5_1_4()
    t3 = test_auto_match_dot_suffix()
    t4 = test_auto_match_7_1_4()

    print()
    print("=" * 70)
    print(" Summary")
    print("=" * 70)
    results = [
        ("_extract_channel_id", t1),
        ("auto_match 5.1.4", t2),
        ("auto_match dot suffix", t3),
        ("auto_match 7.1.4", t4),
    ]
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    all_ok = all(r[1] for r in results)
    print()
    if all_ok:
        print("OVERALL: ALL TESTS PASSED")
    else:
        print("OVERALL: SOME TESTS FAILED")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
