import random

import pytest

import wuxia_spire as ws


def test_run_game_is_reproducible_with_seed():
    a = ws.run_game(seed=7, floors=10, difficulty="normal")
    b = ws.run_game(seed=7, floors=10, difficulty="normal")
    assert a["win"] == b["win"]
    assert a["gold"] == b["gold"]
    assert a["deck_size"] == b["deck_size"]
    assert a["logs"] == b["logs"]


def test_game_has_progression_rewards_and_choices():
    result = ws.run_game(seed=42, floors=10, chooser=lambda _opts: 1)
    assert result["deck_size"] >= len(ws.starter_deck())
    assert any("获得遗物" in log for log in result["logs"])
    assert any("中选择了" in log for log in result["logs"])


def test_easy_mode_is_more_beginner_friendly():
    easy = ws.run_game(seed=3, difficulty="easy")
    hard = ws.run_game(seed=3, difficulty="hard")
    assert easy["hp"] >= hard["hp"]
    assert easy["max_hp"] > hard["max_hp"]


def test_invalid_difficulty_raises_error():
    with pytest.raises(ValueError, match="difficulty"):
        ws.run_game(seed=1, difficulty="nightmare")


def test_invalid_floor_count_raises_error():
    with pytest.raises(ValueError, match="floors"):
        ws.run_game(seed=1, floors=0)


def test_seeded_game_does_not_modify_global_random_state():
    random.seed(12345)
    before = random.random()
    ws.run_game(seed=99, floors=4)
    after = random.random()

    random.seed(12345)
    assert before == random.random()
    assert after == random.random()


def test_auto_mode_render_includes_summary_fields():
    result = ws.run_game(seed=8, floors=4, difficulty="easy")
    output = ws.render_result(result)
    assert "=== 结果 ===" in output
    assert "生命:" in output
    assert "卡组:" in output
    assert "遗物:" in output
