"""Replay loss of the older WTA state inputs across a recovery snapshot."""

import io
import tarfile

import pytest

from tennis_model.data import raw_archive as archive


def _complete(root):
    for relative in ("raw/atp/historical/2020.csv", "raw/wta/stats/2024.csv"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("historical input\n")
    for tour in ("atp", "wta"):
        (root / f"raw/{tour}/live").mkdir(parents=True)
    for year in range(2016, 2026):
        path = root / f"raw/wta/lower/{year}_wta_lower.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tourney_date,winner_name,loser_name,draw_level\n"
                        f"{year}0101,Gabriella Price,Opponent,qual\n")


def test_roundtrip_restores_all_adopted_history_and_preserves_warm_inputs(tmp_path):
    original, restored = tmp_path / "original", tmp_path / "restored"
    _complete(original)
    archive_path = tmp_path / "raw.tar.gz"
    archive.create_archive(original, archive_path, year=2026)
    warm = restored / "raw/wta/live/live.csv"
    warm.parent.mkdir(parents=True)
    warm.write_text("newer live results")
    current = restored / "raw/wta/lower/2026_wta_lower.csv"
    current.parent.mkdir(parents=True)
    current.write_text("newer current-season rows")
    predictor = restored / "output/wta/predictor.pkl"
    predictor.parent.mkdir(parents=True)
    predictor.write_bytes(b"old predictor without the restored players")

    archive.restore_archive(restored, archive_path, year=2026)

    assert archive.archive_problems(restored, year=2026) == []
    assert not predictor.exists()  # a quick refresh must rebuild, not reuse this state
    assert warm.read_text() == "newer live results"
    assert current.read_text() == "newer current-season rows"
    for year in range(2016, 2026):
        relative = f"raw/wta/lower/{year}_wta_lower.csv"
        assert (original / relative).read_bytes() == (restored / relative).read_bytes()


def test_incomplete_snapshot_cannot_replace_the_recovery_archive(tmp_path):
    _complete(tmp_path / "data")
    (tmp_path / "data/raw/wta/lower/2021_wta_lower.csv").unlink()
    destination = tmp_path / "raw.tar.gz"
    destination.write_bytes(b"previous good snapshot")
    with pytest.raises(ValueError, match="2021_wta_lower"):
        archive.create_archive(tmp_path / "data", destination, year=2026)
    assert destination.read_bytes() == b"previous good snapshot"


def test_legacy_snapshot_is_rejected_before_any_input_or_model_mutation(tmp_path):
    original, target = tmp_path / "original", tmp_path / "target"
    _complete(original)
    saved = target / "output/wta/predictor.pkl"
    saved.parent.mkdir(parents=True)
    saved.write_bytes(b"preserve on rejected archive")
    source = tmp_path / "legacy.tar.gz"
    with tarfile.open(source, "w:gz") as tar:
        for relative in archive.SNAPSHOT_DIRS:
            if (original / relative).exists() and relative != "raw/wta/lower":
                tar.add(original / relative, arcname=relative)
    with pytest.raises(ValueError, match="incomplete"):
        archive.restore_archive(target, source, year=2026)
    assert saved.read_bytes() == b"preserve on rejected archive"
    assert not (target / "raw").exists()


@pytest.mark.parametrize("contents", ["", "wrong,columns\n1,2\n",
                                      "tourney_date,winner_name,loser_name,draw_level\n"])
def test_empty_or_malformed_history_is_detected_and_repaired(tmp_path, contents):
    original, target = tmp_path / "original", tmp_path / "target"
    _complete(original)
    _complete(target)
    broken = target / "raw/wta/lower/2025_wta_lower.csv"
    broken.write_text(contents)
    assert archive.missing_lower_history(broken.parent, year=2026) == [2025]
    source = tmp_path / "raw.tar.gz"
    archive.create_archive(original, source, year=2026)
    archive.restore_archive(target, source, year=2026)
    assert archive.archive_problems(target, year=2026) == []


def test_unexpected_tar_path_is_rejected(tmp_path):
    source = tmp_path / "bad.tar.gz"
    with tarfile.open(source, "w:gz") as tar:
        member = tarfile.TarInfo("output/wta/predictor.pkl")
        member.size = 3
        tar.addfile(member, io.BytesIO(b"bad"))
    with pytest.raises(ValueError, match="unexpected path"):
        archive.restore_archive(tmp_path / "target", source, year=2026)
    assert not (tmp_path / "target").exists()


def test_healthy_restore_keeps_the_saved_predictor(tmp_path):
    _complete(tmp_path / "data")
    saved = tmp_path / "data/output/wta/predictor.pkl"
    saved.parent.mkdir(parents=True)
    saved.write_bytes(b"already trained on complete history")
    source = tmp_path / "raw.tar.gz"
    archive.create_archive(tmp_path / "data", source, year=2026)
    archive.restore_archive(tmp_path / "data", source, year=2026)
    assert saved.read_bytes() == b"already trained on complete history"
