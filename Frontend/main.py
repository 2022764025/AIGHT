
import sys
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

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
from Frontend.sample_data import PERFORMANCE, REVIEW


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

LANG_ORDER = ["en", "zh", "ja", "ru", "ko", "fr", "it"]

MENU = {
    "대시보드": "home",
    "리뷰 분석": "review",
    "콘텐츠 생성": "generate",
    "프롬프트 보관함": "library",
    "설정": "settings",
}


def sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div class="brand">
                <div class="brand-mark">A</div>
                <div class="brand-name">AIGHT</div>
                <div class="brand-caption">HOTEL MARKETING AGENT</div>
                <div class="brand-slogan">We make AI right.</div>
            </div>
            <div class="nav-label">WORKSPACE</div>
            """,
            unsafe_allow_html=True,
        )

        choice = st.radio(
            "메뉴",
            list(MENU.keys()),
            label_visibility="collapsed",
        )

        st.markdown(
            """
            <div class="sidebar-hotel">
                <div class="hotel-label">CURRENT HOTEL</div>
                <div class="hotel-name">Arban Hotel</div>
                <div class="hotel-location">Busan · Seomyeon</div>
            </div>
            <div class="sidebar-footer">
                <span class="status-dot"></span> AI MARKETING WORKSPACE
            </div>
            """,
            unsafe_allow_html=True,
        )

    return MENU[choice]


def topbar(title, description):
    left, right = st.columns([5, 1.5], vertical_alignment="center")

    with left:
        st.markdown(
            f"""
            <div class="page-eyebrow">AIGHT / HOTEL WORKSPACE</div>
            <div class="page-title">{escape(title)}</div>
            <div class="page-description">{escape(description)}</div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.selectbox(
            "분석 지점",
            ["Arban Hotel · 부산 서면점"],
            label_visibility="collapsed",
        )

    st.markdown('<div class="top-divider"></div>', unsafe_allow_html=True)


def section_title(title, description=None):
    sub = f'<span class="section-description">{escape(description)}</span>' if description else ""
    st.markdown(
        f'<div class="section-heading"><span>{title}</span>{sub}</div>',
        unsafe_allow_html=True,
    )


def metric_card(label, value, caption, icon):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-top">
                <span class="metric-label">{escape(label)}</span>
                <span class="metric-icon">{icon}</span>
            </div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-caption">{escape(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dashboard_page():
    topbar(
        "대시보드",
        "호텔 리뷰와 마케팅 콘텐츠 성과를 한눈에 확인하세요.",
    )

    st.markdown(
        '<div class="notice-strip"><span class="notice-dot"></span>'
        '현재 표시되는 분석 수치는 화면 확인을 위한 샘플 데이터입니다.'
        '</div>',
        unsafe_allow_html=True,
    )

    section_title("Overview", "호텔 마케팅 현황")

    cols = st.columns(4)
    metrics = [
        ("긍정 리뷰 비율", f'{REVIEW["positive_ratio"]}%', "샘플 리뷰 분석 기준", "↗"),
        ("분석 대상 언어", "4개", "영어 · 중국어 · 일본어 · 러시아어", "◎"),
        ("긍정 키워드", len(REVIEW["positive_keywords"]), "샘플 리뷰에서 추출", "＋"),
        ("개선 키워드", len(REVIEW["negative_keywords"]), "샘플 리뷰에서 추출", "⌁"),
    ]

    for col, item in zip(cols, metrics):
        with col:
            metric_card(*item)

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.5, 1], gap="large")

    with left:
        with st.container(key="dashboard_performance"):
            section_title("언어별 콘텐츠 반응", "언어별 노출수와 참여율 비교")

            df = pd.DataFrame(PERFORMANCE).melt(
                "언어",
                var_name="지표",
                value_name="값",
            )

            chart = (
                alt.Chart(df)
                .mark_bar(
                    cornerRadiusTopLeft=5,
                    cornerRadiusTopRight=5,
                    size=22,
                )
                .encode(
                    x=alt.X(
                        "언어:N",
                        sort=None,
                        axis=alt.Axis(title=None, labelAngle=0),
                    ),
                    xOffset="지표:N",
                    y=alt.Y(
                        "값:Q",
                        scale=alt.Scale(domain=[0, 100]),
                        axis=alt.Axis(title=None, ticks=False, grid=True),
                    ),
                    color=alt.Color(
                        "지표:N",
                        scale=alt.Scale(
                            domain=["노출수", "참여율"],
                            range=["#C7C9F8", "#6259D9"],
                        ),
                        legend=alt.Legend(
                            orient="top",
                            direction="horizontal",
                            title=None,
                        ),
                    ),
                    tooltip=["언어", "지표", "값"],
                )
                .properties(height=250)
                .configure_view(strokeWidth=0)
                .configure(background="#FFFFFF")
            )

            st.altair_chart(chart, use_container_width=True)
            st.caption("※ 샘플 데이터 기준이며 실제 마케팅 성과가 아닙니다.")

    with right:
        with st.container(key="dashboard_keywords"):
            section_title("리뷰 주요 키워드", "고객 리뷰에서 확인한 긍정 및 개선 요소")

            positive = "".join(
                f'<span class="keyword-chip">{escape(word)}</span>'
                for word in REVIEW["positive_keywords"]
            )
            negative = "".join(
                f'<span class="keyword-chip">{escape(word)}</span>'
                for word in REVIEW["negative_keywords"]
            )

            st.markdown(
                f"""
                <div class="keyword-panel positive-panel">
                    <div class="keyword-panel-title">
                        <span class="keyword-symbol">＋</span> 긍정 키워드
                    </div>
                    {positive}
                </div>
                <div class="keyword-panel negative-panel">
                    <div class="keyword-panel-title">
                        <span class="keyword-symbol">!</span> 개선이 필요한 키워드
                    </div>
                    {negative}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="dashboard_quick"):
        section_title("Quick Access", "자주 사용하는 기능")

        q1, q2, q3 = st.columns(3)

        with q1:
            st.markdown(
                '<div class="quick-card"><div class="quick-icon">✦</div>'
                '<div class="quick-title">콘텐츠 생성</div>'
                '<div class="quick-desc">다국어 홍보 콘텐츠 제작</div></div>',
                unsafe_allow_html=True,
            )
        with q2:
            st.markdown(
                '<div class="quick-card"><div class="quick-icon">◉</div>'
                '<div class="quick-title">리뷰 분석</div>'
                '<div class="quick-desc">고객 의견과 개선 요소 확인</div></div>',
                unsafe_allow_html=True,
            )
        with q3:
            st.markdown(
                '<div class="quick-card"><div class="quick-icon">▤</div>'
                '<div class="quick-title">프롬프트 보관함</div>'
                '<div class="quick-desc">콘텐츠 제작 템플릿 관리</div></div>',
                unsafe_allow_html=True,
            )


def review_page():
    topbar(
        "리뷰 분석",
        "고객 리뷰의 반응과 주요 키워드를 확인하세요.",
    )

    st.markdown(
        '<div class="notice-strip"><span class="notice-dot"></span>'
        '현재 리뷰 분석 결과는 sample_data.py의 샘플 데이터입니다. '
        'Google Maps 리뷰 자동 수집 기능은 아직 연결되지 않았습니다.'
        '</div>',
        unsafe_allow_html=True,
    )

    section_title("Review Summary", "리뷰 데이터 요약")

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card(
            "긍정 리뷰 비율",
            f'{REVIEW["positive_ratio"]}%',
            "샘플 데이터",
            "↗",
        )
    with c2:
        metric_card(
            "긍정 키워드",
            len(REVIEW["positive_keywords"]),
            "고객 만족 요소",
            "＋",
        )
    with c3:
        metric_card(
            "개선 키워드",
            len(REVIEW["negative_keywords"]),
            "확인 및 개선 필요 요소",
            "!",
        )

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(key="review_positive"):
            section_title("긍정 리뷰 키워드")
            for word in REVIEW["positive_keywords"]:
                st.markdown(
                    f'<div class="review-word positive-word">'
                    f'<span>＋</span>{escape(word)}</div>',
                    unsafe_allow_html=True,
                )

    with right:
        with st.container(key="review_negative"):
            section_title("개선 필요 키워드")
            for word in REVIEW["negative_keywords"]:
                st.markdown(
                    f'<div class="review-word negative-word">'
                    f'<span>!</span>{escape(word)}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="review_language"):
        section_title("언어별 콘텐츠 반응", "언어별 노출수와 참여율")

        df = pd.DataFrame(PERFORMANCE).melt(
            "언어",
            var_name="지표",
            value_name="값",
        )

        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("언어:N", sort=None, axis=alt.Axis(title=None)),
                xOffset="지표:N",
                y=alt.Y("값:Q", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(title=None)),
                color=alt.Color(
                    "지표:N",
                    scale=alt.Scale(
                        domain=["노출수", "참여율"],
                        range=["#C7C9F8", "#6259D9"],
                    ),
                    legend=alt.Legend(orient="top", title=None),
                ),
                tooltip=["언어", "지표", "값"],
            )
            .properties(height=280)
            .configure_view(strokeWidth=0)
            .configure(background="#FFFFFF")
        )

        st.altair_chart(chart, use_container_width=True)
        st.caption("※ 실제 리뷰 데이터와 연결되기 전까지 샘플 데이터로 표시됩니다.")


def generate_page():
    topbar(
        "콘텐츠 생성",
        "호텔의 마케팅 목적에 맞는 다국어 홍보 콘텐츠를 제작하세요.",
    )

    if not has_api_key():
        st.warning(
            "API 키가 연결되지 않았습니다. .env 파일에 OPENAI_API_KEY를 설정하면 "
            "실제 AI 콘텐츠 생성 기능을 사용할 수 있습니다."
        )

    with st.container(key="content_generator"):
        section_title("Create Content", "생성할 콘텐츠의 조건을 선택하세요.")

        c1, c2 = st.columns([1, 1])

        with c1:
            keywords = st.multiselect(
                "마케팅 키워드",
                options=[
                    "서면 쇼핑",
                    "부산 미식 투어",
                    "시즌 패키지",
                ],
                default=[
                    "서면 쇼핑",
                    "부산 미식 투어",
                    "시즌 패키지",
                ],
                accept_new_options=True,
                placeholder="키워드를 선택하거나 직접 입력하세요.",
            )

        with c2:
            channel_key = st.selectbox(
                "콘텐츠 유형",
                options=list(channels.keys()),
                format_func=lambda key: channels[key]["label"],
            )

        st.markdown("<div class='form-gap'></div>", unsafe_allow_html=True)

        lang_keys = st.pills(
            "대상 언어",
            options=[key for key in LANG_ORDER if key in languages],
            default=["en", "zh", "ja", "ru"],
            selection_mode="multi",
            format_func=lambda key: (
                f'{languages[key]["flag"]} {languages[key]["label"]}'
            ),
        )

        extra = st.text_area(
            "추가 요청",
            placeholder="예: 20대 여행객을 대상으로 가볍고 친근한 말투로 작성",
            height=90,
        )

        clicked = st.button(
            "✦ 다국어 콘텐츠 생성하기",
            type="primary",
            use_container_width=True,
        )

    if clicked:
        if not keywords:
            st.warning("마케팅 키워드를 하나 이상 선택해 주세요.")
        elif not lang_keys:
            st.warning("대상 언어를 하나 이상 선택해 주세요.")
        else:
            results = {}

            with st.spinner("다국어 콘텐츠를 생성하고 있습니다..."):
                for language_key in lang_keys:
                    results[language_key] = generate(
                        ", ".join(keywords),
                        language_key,
                        channel_key,
                        extra,
                    )

            st.session_state["results"] = results
            st.session_state["channel_key"] = channel_key

    results = st.session_state.get("results")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="content_results"):
        section_title("Generated Content", "언어별 생성 결과")

        if not results:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">✦</div>'
                '<div class="empty-title">아직 생성된 콘텐츠가 없습니다.</div>'
                '<div class="empty-description">'
                '위에서 키워드와 언어를 선택하고 콘텐츠를 생성해 주세요.'
                '</div></div>',
                unsafe_allow_html=True,
            )
            return

        current_channel = channels[st.session_state["channel_key"]]

        items = list(results.items())

        for start in range(0, len(items), 2):
            row = items[start:start + 2]
            cols = st.columns(2)

            for col, (language_key, content) in zip(cols, row):
                with col:
                    with st.container(border=True):
                        language = languages[language_key]

                        st.markdown(
                            f'<div class="result-language">'
                            f'{language["flag"]} {escape(language["label"])}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        st.text_area(
                            "생성된 콘텐츠",
                            value=content,
                            height=190,
                            key=f"result_text_{language_key}",
                        )

                        checks = run_checks(
                            content,
                            current_channel["max_chars"],
                            banned,
                        )

                        pills = "".join(
                            f'<span class="check-pill {"check-ok" if ok else "check-warn"}">'
                            f'{escape(message)}</span>'
                            for ok, message in checks
                        )

                        st.markdown(
                            f'<div class="check-list">{pills}</div>',
                            unsafe_allow_html=True,
                        )

                        if language_key != "ko":
                            with st.expander("한국어 역번역으로 확인"):
                                if st.button(
                                    "역번역하기",
                                    key=f"back_translate_{language_key}",
                                ):
                                    st.write(back_translate(content, language_key))


def library_page():
    topbar(
        "프롬프트 보관함",
        "AI 콘텐츠 생성에 사용하는 기본 프롬프트와 언어별 설정을 확인하세요.",
    )

    with st.container(key="library_base"):
        section_title("Base Prompt", "전체 콘텐츠 생성에 적용되는 기본 지침")
        prompt_path = ROOT / "prompts" / "base_prompt.txt"

        if prompt_path.exists():
            st.code(
                prompt_path.read_text(encoding="utf-8"),
                language=None,
                wrap_lines=True,
            )
        else:
            st.info("prompts/base_prompt.txt 파일을 찾을 수 없습니다.")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="library_language"):
        section_title("Language Settings", "언어별 말투와 문화적 표현 설정")

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
            use_container_width=True,
            hide_index=True,
        )

        st.caption("설정 변경은 prompts/languages.json 파일에서 진행합니다.")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="library_channel"):
        section_title("Content Type Settings", "콘텐츠 유형별 글자 수와 작성 규칙")

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
            use_container_width=True,
            hide_index=True,
        )

        st.caption("설정 변경은 prompts/channels.json 파일에서 진행합니다.")


def settings_page():
    topbar(
        "설정",
        "AIGHT 서비스의 연결 상태와 기본 설정을 확인하세요.",
    )

    with st.container(key="settings_api"):
        section_title("API Connection", "AI 콘텐츠 생성 연결 상태")

        if has_api_key():
            st.success("OpenAI API 키가 연결되어 있습니다.")
        else:
            st.warning("OpenAI API 키가 연결되지 않았습니다.")

        st.caption("API 키는 프로젝트 루트의 .env 파일에서 설정합니다.")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="settings_check"):
        section_title("Content Check", "콘텐츠 생성 시 적용되는 검사 설정")

        st.markdown(
            f"""
            <div class="setting-row">
                <span>금지 표현 등록 수</span>
                <strong>{len(banned)}개</strong>
            </div>
            <div class="setting-row">
                <span>금지 표현 설정 파일</span>
                <strong>prompts/banned_words.txt</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    with st.container(key="settings_hotel"):
        section_title("Hotel Information", "현재 분석 대상 호텔")

        st.markdown(
            """
            <div class="setting-row">
                <span>호텔명</span>
                <strong>Arban Hotel</strong>
            </div>
            <div class="setting-row">
                <span>위치</span>
                <strong>부산 부산진구 서면</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            "Google Maps 리뷰 자동 수집은 아직 연결되지 않았습니다. "
            "현재 리뷰 분석 화면에는 샘플 데이터가 표시됩니다."
        )


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
