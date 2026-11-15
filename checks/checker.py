# 생성된 문구를 자동으로 검수하는 파일 (글자 수, 금지 표현)
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED_FILE = ROOT / "prompts" / "banned_words.txt"


def load_banned_words(path: Path = BANNED_FILE) -> list[str]:
    # 한 줄에 하나씩 적고, #으로 시작하는 줄은 메모로 보고 건너뜀
    if not path.exists():
        return []
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line.lower())
    return words


def check_length(text: str, max_chars: int) -> tuple[bool, str]:
    # 채널마다 글자 수 제한이 달라서 따로 확인
    n = len(text)
    if n <= max_chars:
        return True, f"글자 수 {n}자 (최대 {max_chars}자)"
    return False, f"글자 수 초과: {n}자 (최대 {max_chars}자)"


def check_banned(text: str, banned: list[str]) -> tuple[bool, str]:
    # 대소문자 구분 없이 금지 표현이 들어 있는지 찾음
    lowered = text.lower()
    found = [w for w in banned if w in lowered]
    if not found:
        return True, "금지 표현 없음"
    return False, "금지 표현 발견: " + ", ".join(found)


def run_checks(text: str, max_chars: int, banned: list[str]) -> list[tuple[bool, str]]:
    # 화면에서 한 번에 보여 주려고 결과를 리스트로 묶음
    return [check_length(text, max_chars), check_banned(text, banned)]
