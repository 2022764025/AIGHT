# 프롬프트 만들기와 LLM 호출을 맡는 파일
import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"

# .env 파일에 적어 둔 API 키를 환경 변수로 불러옴
load_dotenv(ROOT / ".env")


def load_json(name: str) -> dict:
    # prompts 폴더의 설정 파일을 읽음 (언어, 채널 설정을 코드와 분리하려고)
    with open(PROMPTS / name, encoding="utf-8") as f:
        return json.load(f)


def has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def build_prompt(keywords: str, language_key: str, channel_key: str, extra: str = "") -> str:
    # 언어/채널 설정과 기본 문장을 합쳐 최종 프롬프트를 만듦
    lang = load_json("languages.json")[language_key]
    channel = load_json("channels.json")[channel_key]
    base = (PROMPTS / "base_prompt.txt").read_text(encoding="utf-8")
    return base.format(
        language_name=lang["name"],
        tone=lang["tone"],
        culture_note=lang["culture_note"],
        meme_note=lang["meme_note"],
        channel_label=channel["label"],
        channel_rule=channel["rule"],
        max_chars=channel["max_chars"],
        keywords=keywords,
        extra=extra or "없음",
    )


def call_llm(prompt: str) -> str:
    # 키가 없으면 목업을 돌려줘서 비용 없이 화면을 테스트할 수 있게 함
    if not has_api_key():
        return f"[테스트용 문장] {prompt[:60]}..."

    # openai는 실제 호출할 때만 불러옴 (설치 안 돼도 목업은 동작)
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate(keywords: str, language_key: str, channel_key: str, extra: str = "") -> str:
    # API 키가 없으면 프롬프트 전체가 아니라 짧은 안내 문장만 보여줌 (화면 확인용)
    if not has_api_key():
        lang = load_json("languages.json")[language_key]["name"]
        channel = load_json("channels.json")[channel_key]["label"]
        return (
            f"[테스트용 문장] {lang} / {channel}\n"
            f"키워드: {keywords}\n"
            "API 키를 .env에 넣으면 여기에 실제 홍보 문구가 나옵니다."
        )
    return call_llm(build_prompt(keywords, language_key, channel_key, extra))


def back_translate(text: str, language_key: str) -> str:
    # 결과를 한국어로 다시 번역해서 원래 뜻과 어긋나는지 눈으로 확인
    if not has_api_key():
        return "[테스트용] API 키를 넣으면 한국어 역번역이 나옵니다."
    lang = load_json("languages.json")[language_key]["name"]
    prompt = (
        f"다음 {lang} 문장을 한국어로 자연스럽게 번역해. 번역문만 출력해.\n\n{text}"
    )
    return call_llm(prompt)
