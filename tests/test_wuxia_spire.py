import wuxia_spire as ws


def test_run_game_is_reproducible_with_seed():
    a = ws.run_game(seed=7, floors=10, difficulty="normal")
    b = ws.run_game(seed=7, floors=10, difficulty="normal")
    assert a["win"] == b["win"]
    assert a["gold"] == b["gold"]
    assert a["deck_size"] == b["deck_size"]


def test_game_has_progression_rewards_and_choices():
    result = ws.run_game(seed=42, floors=10, chooser=lambda _opts: 1)
    assert result["deck_size"] >= len(ws.starter_deck())
    assert any("获得遗物" in log for log in result["logs"])
    assert any("中选择了" in log for log in result["logs"])


def test_easy_mode_is_more_beginner_friendly():
    easy = ws.run_game(seed=3, difficulty="easy")
    hard = ws.run_game(seed=3, difficulty="hard")
    assert easy["hp"] >= hard["hp"]


def test_invalid_difficulty_raises_error():
    try:
        ws.run_game(seed=1, difficulty="nightmare")
        assert False, "expected ValueError"
    except ValueError:
        assert True
