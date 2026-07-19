"""Match-room core (SH-6/7/8): URL shape, spool tail, one-at-a-time control."""

from __future__ import annotations

import json
import threading

from cipherchase.sdk.live_match import MatchController, read_spool, valid_opponent_url


def test_url_shape_accepts_only_http_s_hosts_ending_in_mcp() -> None:
    assert valid_opponent_url("https://team.ngrok.app/mcp")
    assert valid_opponent_url("http://127.0.0.1:9001/mcp")
    assert not valid_opponent_url("https://team.ngrok.app/")     # no /mcp
    assert not valid_opponent_url("ftp://team/mcp")              # bad scheme
    assert not valid_opponent_url("/mcp")                        # no host
    assert not valid_opponent_url("")
    assert not valid_opponent_url("https://[::1/mcp")            # urlparse raises → False


def test_read_spool_skips_a_torn_final_line_and_tolerates_absence(tmp_path) -> None:
    assert read_spool(tmp_path / "nope.jsonl") == []
    p = tmp_path / "s.jsonl"
    p.write_text('{"turn": 1}\n{"turn": 2}\n{"partial":')
    assert read_spool(p) == [{"turn": 1}, {"turn": 2}]


def _writer_runner(frames):
    def run(role, url, spool):
        with open(spool, "w") as fh:
            for f in frames:
                fh.write(json.dumps(f) + "\n")
    return run


def test_start_happy_path_spawns_a_daemon_and_streams_frames(tmp_path) -> None:
    frames = [{"turn": 1, "role": "police"}, {"turn": 2, "role": "police"}]
    mc = MatchController(tmp_path / "spool.jsonl", runner=_writer_runner(frames))
    assert mc.spectate() == {"live": False, "frames": []}   # nothing yet
    status, body = mc.start({"role": "police", "opponent_url": "http://127.0.0.1:9001/mcp"})
    assert status == 200 and body["ok"] and body["stream"] == "/api/spectate"
    mc._thread.join(timeout=5)
    assert mc.spectate()["frames"] == frames


def test_bad_role_or_url_is_a_json_400(tmp_path) -> None:
    mc = MatchController(tmp_path / "s.jsonl", runner=_writer_runner([]))
    assert mc.start({"role": "referee", "opponent_url": "http://h/mcp"})[0] == 400
    assert mc.start({"role": "police", "opponent_url": "nope"})[0] == 400


def test_second_start_while_running_is_a_409(tmp_path) -> None:
    gate = threading.Event()

    def blocking(role, url, spool):
        open(spool, "w").close()
        gate.wait(5)                       # hold the "match" open
    mc = MatchController(tmp_path / "s.jsonl", runner=blocking)
    assert mc.start({"role": "thief", "opponent_url": "http://h:1/mcp"})[0] == 200
    assert mc.running()
    status, body = mc.start({"role": "thief", "opponent_url": "http://h:1/mcp"})
    assert status == 409 and body["ok"] is False
    gate.set()
    mc._thread.join(timeout=5)
