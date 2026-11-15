# 자동 검수 함수가 제대로 동작하는지 확인하는 테스트
from checks.checker import check_banned, check_length, load_banned_words, run_checks


def test_length_ok():
    ok, _ = check_length("hello", 10)
    assert ok


def test_length_over():
    ok, message = check_length("a" * 11, 10)
    assert not ok
    assert "초과" in message


def test_banned_found_ignores_case():
    ok, message = check_banned("This is the BEST hotel", ["best"])
    assert not ok
    assert "best" in message


def test_banned_none():
    ok, _ = check_banned("Nice stay in Busan", ["best"])
    assert ok


def test_run_checks_returns_two_results():
    assert len(run_checks("hi", 10, [])) == 2


def test_banned_file_skips_comments():
    # 기본 파일은 메모만 있으므로 빈 목록이어야 함
    assert load_banned_words() == []
