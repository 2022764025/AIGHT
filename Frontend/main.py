import json
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

sys.path.append(str(ROOT))

from Backend.generator import (
    back_translate,
    generate,
    has_api_key,
    load_json,
)
from checks.checker import load_banned_words, run_checks
from Frontend.sample_data import (
    DASHBOARD_METRICS,
    DEFAULT_PROMPTS,
    HIGHLIGHTS,
    INSIGHT_TEXT,
    LANGUAGE_SHARE,
    MONTHLY_REVIEWS,
    PROMPT_CATEGORIES,
    REVIEW_METRICS,
    REVIEW_SAMPLES,
    TOPICS,
)


st.set_page_config(
    page_title="AIGHT | Hotel Marketing",
    page_icon="✦",
    layout="wide",
)

st.markdown(
    f"<style>{(HERE / 'style.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)

languages = load_json("languages.json")
channels = load_json("channels.json")
banned = load_banned_words()

LANG_ORDER = ["ko", "en", "ja", "zh", "ru", "fr", "it"]
PERIODS = ["최근 1개월", "최근 3개월", "최근 6개월", "최근 1년"]
PURPOSES = [
    "호텔 위치와 접근성 강조",
    "객실 및 편의시설 소개",
    "시즌 패키지 및 이벤트 안내",
    "친절한 서비스 강조",
    "고객 FAQ 및 프로모션",
]
TONES = ["친근하고 자연스럽게", "고급스럽고 차분하게", "짧고 눈에 띄게"]

NAV = [
    ("home", "▦", "대시보드"),
    ("review", "◷", "리뷰 분석"),
    ("generate", "✧", "콘텐츠 생성"),
    ("library", "▤", "프롬프트 보관함"),
    ("settings", "⚙", "설정"),
]
NAV_LABELS = {page: f"{icon}\u00a0\u00a0\u00a0{label}" for page, icon, label in NAV}
MENU = {label: page for page, label in NAV_LABELS.items()}

# Streamlit 버전에 따라 너비 옵션 이름이 달라 둘 다 대응한다
_VERSION = tuple(int(part) for part in st.__version__.split(".")[:2] if part.isdigit())
STRETCH = {"width": "stretch"} if _VERSION >= (1, 50) else {"use_container_width": True}


def H(markup):
    """들여쓰기·줄바꿈을 없애 마크다운이 HTML을 코드 블록으로 바꾸지 않게 한다."""
    return "".join(line.strip() for line in markup.strip().splitlines())


# ───────────── 상태 ─────────────

st.session_state.setdefault("hotel_name", "Arban Hotel")
st.session_state.setdefault("hotel_loc", "부산 부산진구 · 서면")
st.session_state.setdefault("avatar", "AH")
st.session_state.setdefault("gmaps_link", "https://maps.app.goo.gl/Pu4m5EvnPip9uGMG6")
st.session_state.setdefault("draft", None)

if "prompts" not in st.session_state:
    st.session_state["prompts"] = [
        {"id": index + 1, **item} for index, item in enumerate(DEFAULT_PROMPTS)
    ]
    st.session_state["prompt_seq"] = len(DEFAULT_PROMPTS)


# ───────────── 콜백 ─────────────

def use_prompt(text):
    st.session_state["extra_req"] = text
    st.session_state["nav"] = NAV_LABELS["generate"]
    st.toast("선택한 프롬프트가 적용되었습니다. [콘텐츠 초안 만들기]를 누르세요.")


def delete_prompt(prompt_id):
    st.session_state["prompts"] = [
        item for item in st.session_state["prompts"] if item["id"] != prompt_id
    ]
    st.toast("프롬프트가 삭제되었습니다.")


def save_prompt():
    title = st.session_state.get("new_prompt_title", "").strip()
    content = st.session_state.get("new_prompt_content", "").strip()

    if not title or not content:
        st.toast("제목과 지시문 내용을 모두 입력해 주세요.")
        return

    st.session_state["prompt_seq"] += 1
    st.session_state["prompts"].insert(
        0,
        {
            "id": st.session_state["prompt_seq"],
            "tag": st.session_state.get("new_prompt_tag", PROMPT_CATEGORIES[0]),
            "title": title,
            "content": content,
        },
    )
    st.session_state["new_prompt_title"] = ""
    st.session_state["new_prompt_content"] = ""
    st.toast("프롬프트 라이브러리에 성공적으로 저장되었습니다.")


def save_settings():
    name = st.session_state.get("input_hotel_name", "").strip()
    loc = st.session_state.get("input_hotel_loc", "").strip()

    if name:
        st.session_state["hotel_name"] = name
        st.session_state["avatar"] = name[:2].upper()
    if loc:
        st.session_state["hotel_loc"] = loc

    st.session_state["gmaps_link"] = st.session_state.get("input_gmaps", "").strip()
    st.toast("호텔 설정 정보가 저장되었습니다.")


def connect_gmaps():
    link = st.session_state.get("input_gmaps", "").strip()

    if not link:
        st.toast("Google Maps 링크를 입력해주세요.")
        return

    st.session_state["gmaps_link"] = link
    st.toast("링크가 등록되었습니다. 리뷰 자동 수집은 아직 연결되지 않았습니다.")


def on_period_change():
    st.toast(f"{st.session_state['period']} 데이터로 변경되었습니다.")


# ───────────── 공통 조각 ─────────────

def copy_button(text, height=42):
    """클립보드 복사 버튼 (Streamlit에는 기본 복사 버튼이 없어 작은 HTML로 만든다)."""
    payload = json.dumps(text).replace("</", "<\\/")
    page = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@700&family=Noto+Sans+KR:wght@700&display=swap');
        body {{ margin: 0; }}
        button {{
            width: 100%; height: 38px; background: #fff; color: #475569;
            border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer;
            font: 700 12px 'DM Sans', 'Noto Sans KR', sans-serif;
            transition: background .2s ease;
        }}
        button:hover {{ background: #eeeffe; color: #4f46e5; }}
        </style>
        <button id="b">문구 복사</button>
        <script>
        const text = {payload};
        const btn = document.getElementById('b');
        btn.onclick = () => {{
            const area = document.createElement('textarea');
            area.value = text;
            document.body.appendChild(area);
            area.select();
            try {{ document.execCommand('copy'); }} catch (e) {{}}
            document.body.removeChild(area);
            if (navigator.clipboard) {{ navigator.clipboard.writeText(text).catch(() => {{}}); }}
            btn.textContent = '복사되었습니다 ✓';
            setTimeout(() => {{ btn.textContent = '문구 복사'; }}, 1500);
        }};
        </script>
        """

    if hasattr(st, "iframe"):
        st.iframe(page, height=height)
    else:
        components.html(page, height=height)


def topline_html(tight=False):
    today = datetime.now().strftime("%Y. %m. %d")
    return H(
        f"""
        <div class="topline{' tight' if tight else ''}">
            <div class="crumb">AIGHT / HOTEL WORKSPACE</div>
            <div class="top-actions">
                <span class="date">{today}</span>
                <div class="avatar">{escape(st.session_state['avatar'])}</div>
            </div>
        </div>
        """
    )


def page_head_html(eyebrow, title, description):
    return H(
        f"""
        <div class="page-head">
            <div class="eyebrow">{escape(eyebrow)}</div>
            <div class="page-title">{escape(title)}</div>
            <div class="page-desc">{escape(description)}</div>
        </div>
        """
    )


def metrics_html(items):
    cells = "".join(
        f'<div class="metric"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'<div class="sub{" up" if up else ""}">{sub}</div></div>'
        for label, value, sub, up in items
    )
    return f'<div class="metrics">{cells}</div>'


def keyword_list_html(items):
    return (
        '<div class="keyword-list">'
        + "".join(
            f'<div class="keyword"><span>{name}</span>'
            f'<div class="track"><div class="fill" style="width:{pct}%"></div></div>'
            f"<b>{pct}%</b></div>"
            for name, pct in items
        )
        + "</div>"
    )


def pill_class(label):
    return "positive" if label == "긍정" else "negative"


# ───────────── 사이드바 ─────────────

def sidebar():
    with st.sidebar:
        st.markdown(
            H(
                """
                <div class="brand">
                    <div class="brand-small">AIGHT</div>
                    <div class="brand-title">Hotel Marketing</div>
                    <div class="brand-sub">We make AI right</div>
                </div>
                <div class="nav-label">WORKSPACE</div>
                """
            ),
            unsafe_allow_html=True,
        )

        choice = st.radio(
            "메뉴",
            list(MENU.keys()),
            key="nav",
            label_visibility="collapsed",
        )

        st.markdown(
            H(
                f"""
                <div class="hotel-chip">
                    <span>현재 분석 대상</span>
                    <strong>{escape(st.session_state['hotel_name'])}</strong>
                    <small>{escape(st.session_state['hotel_loc'])}</small>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    return MENU[choice]


# ───────────── 1. 대시보드 ─────────────

def dashboard_page():
    name = st.session_state["hotel_name"]

    st.markdown(topline_html(tight=True), unsafe_allow_html=True)

    left, right = st.columns([5, 1], vertical_alignment="bottom")

    with left:
        st.markdown(
            page_head_html(
                f"OVERVIEW / {name.upper()}",
                "호텔 마케팅 대시보드",
                "아르반호텔의 고객 반응을 살펴보고 다음 마케팅 기회를 확인하세요.",
            ),
            unsafe_allow_html=True,
        )

    with right:
        period = st.selectbox(
            "조회 기간",
            PERIODS,
            index=2,
            key="period",
            on_change=on_period_change,
            label_visibility="collapsed",
        )

    chart_sub = (
        "최근 6개월 · 글로벌 데이터" if period == "최근 6개월" else f"{period} · 수집 데이터"
    )

    bars = "".join(
        f'<div class="bar-col"><div class="bar" style="height:{height}%"></div>'
        f"<span>{month}</span></div>"
        for month, height in MONTHLY_REVIEWS
    )

    highlights = "".join(
        f'<div class="review"><span class="pill {pill_class(kind)}">{kind}</span>'
        f'<div class="rv-text">{text}</div><small>{tag}</small></div>'
        for kind, text, tag in HIGHLIGHTS
    )

    st.markdown(
        H(
            f"""
            <div class="notice">글로벌 고객 데이터 및 Google Maps 리뷰 분석 기반 대시보드 시안입니다.</div>
            {metrics_html(DASHBOARD_METRICS)}
            <div class="grid">
                <div class="panel">
                    <div class="panel-head"><div class="panel-title">월별 리뷰 흐름</div><span class="muted">리뷰 수</span></div>
                    <div class="panel-sub">{chart_sub}</div>
                    <div class="chart">{bars}</div>
                </div>
                <div class="panel">
                    <div class="panel-head"><div class="panel-title">고객이 자주 언급한 주제</div><span class="muted">언급 비중</span></div>
                    <div class="panel-sub">리뷰 핵심 키워드 분석</div>
                    {keyword_list_html(TOPICS)}
                </div>
            </div>
            <div class="panel gap-bottom">
                <div class="panel-head"><div class="panel-title">최근 리뷰 하이라이트</div><span class="muted">대표 의견</span></div>
                <div class="panel-sub">언어권별 대표 리뷰 요약</div>
                <div class="review-grid">{highlights}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ───────────── 2. 리뷰 분석 ─────────────

def review_page():
    rows = "".join(
        f"<tr><td>{stars}</td><td>{text}</td><td>{lang}</td>"
        f'<td><span class="pill {pill_class(kind)}">{kind}</span></td></tr>'
        for stars, text, lang, kind in REVIEW_SAMPLES
    )

    st.markdown(
        H(
            f"""
            {topline_html()}
            {page_head_html("CUSTOMER VOICE", "Google 리뷰 분석", "고객이 남긴 평가에서 호텔의 강점과 개선 지점을 찾습니다.")}
            <div class="notice">글로벌 방문객 데이터를 분석하여 감성 분류 및 주요 키워드를 도출한 결과입니다.</div>
            {metrics_html(REVIEW_METRICS)}
            <div class="grid">
                <div class="panel">
                    <div class="panel-title">언어별 리뷰 비중</div>
                    <div class="panel-sub">타깃 언어권 분포</div>
                    {keyword_list_html(LANGUAGE_SHARE)}
                </div>
                <div class="panel">
                    <div class="panel-title">분석 요약 및 인사이트</div>
                    <div class="panel-sub">마케팅 개선 반영점</div>
                    <div class="insight">{INSIGHT_TEXT}</div>
                </div>
            </div>
            <div class="panel">
                <div class="panel-title">리뷰 원문 예시</div>
                <div class="panel-sub">언어 및 감성 분류 상세</div>
                <table class="table">
                    <thead><tr><th>평점</th><th>리뷰 내용</th><th>언어</th><th>분류</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ───────────── 3. 콘텐츠 생성 ─────────────

def generate_page():
    st.markdown(
        topline_html()
        + page_head_html(
            "CONTENT STUDIO",
            "호텔 마케팅 콘텐츠 생성",
            "핵심 키워드와 프롬프트 조합으로 다국어 콘텐츠 및 FAQ를 자동 생성합니다.",
        ),
        unsafe_allow_html=True,
    )

    if not has_api_key():
        st.warning(
            "API 키가 연결되지 않았습니다. .env 파일에 OPENAI_API_KEY를 설정하면 "
            "실제 AI 콘텐츠 생성 기능을 사용할 수 있습니다."
        )

    st.session_state.setdefault("extra_req", "")

    left, right = st.columns([1.45, 1], gap="small")

    with left:
        with st.container(key="panel_content_form"):
            st.markdown('<div class="panel-title">콘텐츠 설정</div>', unsafe_allow_html=True)

            lang_options = [key for key in LANG_ORDER if key in languages]

            c1, c2 = st.columns(2)
            with c1:
                lang_key = st.selectbox(
                    "콘텐츠 언어",
                    lang_options,
                    format_func=lambda key: languages[key]["label"],
                )
            with c2:
                channel_key = st.selectbox(
                    "게시 채널",
                    list(channels.keys()),
                    format_func=lambda key: channels[key]["label"],
                )

            c3, c4 = st.columns(2)
            with c3:
                purpose = st.selectbox("홍보 목적", PURPOSES)
            with c4:
                tone = st.selectbox("문체 (톤앤매너)", TONES)

            extra = st.text_area(
                "추가 요청 (또는 프롬프트 라이브러리 자동 적용란)",
                key="extra_req",
                placeholder="예: 서면역 7번 출구 접근성 및 주변 전통시장 맛집 정보를 강조해 주세요.",
                height=120,
            )

            clicked = st.button("콘텐츠 초안 만들기", type="primary")

            if clicked:
                request = f"문체: {tone}"
                if extra.strip():
                    request += f"\n{extra.strip()}"

                with st.spinner("다국어 콘텐츠를 생성하고 있습니다..."):
                    text = generate(purpose, lang_key, channel_key, request)

                st.session_state["draft"] = {
                    "text": text,
                    "meta": f"{languages[lang_key]['label']} · {channels[channel_key]['label']} · {purpose}",
                    "lang": lang_key,
                    "channel": channel_key,
                }
                st.toast("마케팅 콘텐츠 초안이 생성되었습니다.")

    draft = st.session_state.get("draft")

    with right:
        with st.container(key="panel_content_preview"):
            meta = draft["meta"] if draft else "선택한 조건에 맞춘 다국어 콘텐츠"
            body = (
                escape(draft["text"]).replace("\n", "<br>")
                if draft
                else "왼쪽에서 콘텐츠 조건을 선택하거나 프롬프트 보관함에서 적용할 문구를 선택한 뒤 초안을 만들어 보세요."
            )

            st.markdown(
                H(
                    f"""
                    <div class="panel-title">생성 결과 미리보기</div>
                    <div class="panel-sub">{escape(meta)}</div>
                    <div class="draft-box">{body}</div>
                    """
                ),
                unsafe_allow_html=True,
            )

            if not draft:
                st.button("문구 복사", disabled=True)
                return

            copy_button(draft["text"])

            channel = channels[draft["channel"]]
            checks = run_checks(draft["text"], channel["max_chars"], banned)
            pills = "".join(
                f'<span class="pill {"positive" if ok else "negative"}">{escape(message)}</span>'
                for ok, message in checks
            )
            st.markdown(f'<div class="pill-row">{pills}</div>', unsafe_allow_html=True)

            if draft["lang"] != "ko":
                with st.expander("한국어 역번역으로 확인"):
                    if st.button("역번역하기", key="back_translate"):
                        st.write(back_translate(draft["text"], draft["lang"]))


# ───────────── 4. 프롬프트 보관함 ─────────────

def library_page():
    st.markdown(
        topline_html()
        + page_head_html(
            "PROMPT LIBRARY",
            "프롬프트 보관함",
            "담당자가 변경되더라도 기존 마케팅 방향과 제작 기준을 표준화하여 일관성을 유지합니다.",
        ),
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("new_prompt_title", "")
    st.session_state.setdefault("new_prompt_content", "")

    with st.container(key="panel_prompt_new"):
        st.markdown(
            '<div class="panel-title">새 마케팅 프롬프트 등록 (표준화 관리)</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1, 2])
        with c1:
            st.selectbox("카테고리 선택", PROMPT_CATEGORIES, key="new_prompt_tag")
        with c2:
            st.text_input(
                "프롬프트 제목",
                key="new_prompt_title",
                placeholder="예: [서면역 접근성] 다국어 인스타그램 홍보 템플릿",
            )

        st.text_area(
            "프롬프트 지시문 (보관함 저장 지시문)",
            key="new_prompt_content",
            placeholder="국가별 문화와 언어 특성을 반영한 마케팅 지시문 프롬프트를 등록하세요.",
            height=70,
        )

        st.button(
            "+ 프롬프트 라이브러리에 저장",
            type="primary",
            on_click=save_prompt,
        )

    prompts = st.session_state["prompts"]

    for start in range(0, len(prompts), 3):
        cols = st.columns(3, gap="small")

        for col, item in zip(cols, prompts[start:start + 3]):
            with col:
                with st.container(key=f"card_prompt_{item['id']}"):
                    top_left, top_right = st.columns([5, 1], vertical_alignment="center")

                    with top_left:
                        st.markdown(
                            f'<span class="pill">{escape(item["tag"])}</span>',
                            unsafe_allow_html=True,
                        )
                    with top_right:
                        st.button(
                            "×",
                            key=f"del_{item['id']}",
                            type="tertiary",
                            help="삭제",
                            on_click=delete_prompt,
                            args=(item["id"],),
                        )

                    st.markdown(
                        H(
                            f"""
                            <div class="rv-text"><b>{escape(item["title"])}</b><br>
                            <span>{escape(item["content"])}</span></div>
                            """
                        ),
                        unsafe_allow_html=True,
                    )

                    b1, b2 = st.columns([2.3, 1], vertical_alignment="center")
                    with b1:
                        st.button(
                            "이 프롬프트로 콘텐츠 생성 ➔",
                            key=f"use_{item['id']}",
                            type="primary",
                            **STRETCH,
                            on_click=use_prompt,
                            args=(item["content"],),
                        )
                    with b2:
                        copy_button(item["content"])

    with st.expander("시스템 기본 설정 보기 (기본 프롬프트 · 언어 · 콘텐츠 유형)"):
        prompt_path = ROOT / "prompts" / "base_prompt.txt"

        if prompt_path.exists():
            st.code(
                prompt_path.read_text(encoding="utf-8"),
                language=None,
                wrap_lines=True,
            )
        else:
            st.info("prompts/base_prompt.txt 파일을 찾을 수 없습니다.")

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "언어": value["label"],
                        "말투": value["tone"],
                        "문화 메모": value["culture_note"],
                        "밈 메모": value["meme_note"],
                    }
                    for value in languages.values()
                ]
            ),
            **STRETCH,
            hide_index=True,
        )
        st.caption("설정 변경은 prompts/languages.json 파일에서 진행합니다.")

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "콘텐츠 유형": value["label"],
                        "최대 글자 수": value["max_chars"],
                        "작성 규칙": value["rule"],
                    }
                    for value in channels.values()
                ]
            ),
            **STRETCH,
            hide_index=True,
        )
        st.caption("설정 변경은 prompts/channels.json 파일에서 진행합니다.")


# ───────────── 5. 설정 ─────────────

def settings_page():
    st.markdown(
        topline_html()
        + page_head_html(
            "WORKSPACE SETTINGS",
            "설정",
            "분석 대상 호텔과 화면 표시 옵션을 관리합니다.",
        ),
        unsafe_allow_html=True,
    )

    if "input_hotel_name" not in st.session_state:
        st.session_state["input_hotel_name"] = st.session_state["hotel_name"]
    if "input_hotel_loc" not in st.session_state:
        st.session_state["input_hotel_loc"] = "부산광역시 부산진구 서면"
    if "input_gmaps" not in st.session_state:
        st.session_state["input_gmaps"] = st.session_state["gmaps_link"]

    with st.container(key="panel_settings"):
        st.markdown('<div class="panel-title">호텔 정보 설정</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("호텔명", key="input_hotel_name")
        with c2:
            st.text_input("지역", key="input_hotel_loc")

        g1, g2 = st.columns([5, 1], vertical_alignment="bottom")
        with g1:
            st.text_input("Google Maps 링크 (리뷰 데이터 연동)", key="input_gmaps")
        with g2:
            st.button("연동하기", on_click=connect_gmaps, **STRETCH)

        st.markdown('<div class="settings-divider"></div>', unsafe_allow_html=True)

        s1, s2 = st.columns([3, 1])
        with s2:
            st.button(
                "설정 저장하기",
                type="primary",
                on_click=save_settings,
                **STRETCH,
            )


# ───────────── 실행 ─────────────

page = sidebar()

if page == "home":
    dashboard_page()
elif page == "review":
    review_page()
elif page == "generate":
    generate_page()
elif page == "library":
    library_page()
elif page == "settings":
    settings_page()