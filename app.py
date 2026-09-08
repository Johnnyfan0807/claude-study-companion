"""Streamlit entry point for Claude Study Companion."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.claude_service import ClaudeService, ClaudeServiceError, GenerationResult
from src.config import MODEL_CATALOG, AppConfig, estimate_cost_usd
from src.documents import (
    DocumentExtractionError,
    combine_documents,
    extract_document,
)
from src.prompts import (
    base_system_prompt,
    explanation_message,
    quiz_message,
    socratic_setup_message,
    socratic_system_prompt,
    summary_message,
)
from src.study import (
    PreparedRequest,
    TokenBudgetError,
    approximate_token_count,
    prepare_with_budget,
    split_quiz_output,
    trim_socratic_history,
)

ROOT = Path(__file__).resolve().parent
CONFIG = AppConfig.from_env()

st.set_page_config(
    page_title="Claude Study Companion",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _load_css() -> None:
    css_path = ROOT / "assets" / "styles.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _secret(name: str, default: str = "") -> str:
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value
    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default
    return str(value)


def _as_bool(value: str, default: bool = True) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _init_state() -> None:
    defaults = {
        "usage": {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
        "outputs": {},
        "socratic_messages": [],
        "socratic_active": False,
        "socratic_goal": "",
        "socratic_source": "",
        "pasted_notes": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_demo_note() -> None:
    st.session_state["pasted_notes"] = (ROOT / "examples" / "probability_notes.md").read_text(
        encoding="utf-8"
    )
    st.session_state["source_method"] = "Paste text"


def _clear_learning_session() -> None:
    st.session_state["outputs"] = {}
    st.session_state["socratic_messages"] = []
    st.session_state["socratic_active"] = False
    st.session_state["socratic_goal"] = ""
    st.session_state["socratic_source"] = ""


def _record_usage(model: str, result: GenerationResult) -> None:
    usage = st.session_state["usage"]
    usage["requests"] += 1
    usage["input_tokens"] += result.input_tokens
    usage["output_tokens"] += result.output_tokens
    cost = estimate_cost_usd(model, result.input_tokens, result.output_tokens)
    if cost is not None:
        usage["estimated_cost_usd"] += cost


def _request_allowed() -> bool:
    if st.session_state["usage"]["requests"] >= CONFIG.session_request_limit:
        st.error(
            "This session has reached its request limit. Start a fresh session or "
            "raise SESSION_REQUEST_LIMIT only for a controlled deployment."
        )
        return False
    return True


def _call_claude(
    *,
    api_key: str,
    model: str,
    system: str,
    notes: str,
    message_factory: Callable[[str], list[dict[str, str]]],
    max_input_tokens: int,
    max_output_tokens: int,
) -> tuple[GenerationResult, PreparedRequest] | None:
    if not api_key:
        st.error("Add a Claude API key in the sidebar before generating.")
        return None
    if not _request_allowed():
        return None

    service: ClaudeService | None = None
    try:
        service = ClaudeService(
            api_key=api_key,
            model=model,
            timeout_seconds=CONFIG.request_timeout_seconds,
        )
        prepared = prepare_with_budget(
            notes=notes,
            system=system,
            message_factory=message_factory,
            count_tokens=lambda sys, messages: service.count_tokens(system=sys, messages=messages),
            max_input_tokens=max_input_tokens,
        )
        result = service.generate(
            system=system,
            messages=prepared.messages,
            max_tokens=max_output_tokens,
        )
    except (ClaudeServiceError, TokenBudgetError) as exc:
        st.error(str(exc))
        return None
    finally:
        if service is not None:
            service.close()

    _record_usage(model, result)
    return result, prepared


def _result_payload(
    result: GenerationResult, prepared: PreparedRequest, model: str
) -> dict[str, object]:
    return {
        "text": result.text,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "preflight_tokens": prepared.input_tokens,
        "truncated": prepared.notes_truncated,
        "model": model,
    }


def _render_result(payload: dict[str, object], *, filename: str) -> None:
    if payload.get("truncated"):
        st.warning(
            "The source exceeded your input budget. Excerpts were sampled across the "
            "notes before this response was generated."
        )
    st.markdown(str(payload["text"]))
    cost = estimate_cost_usd(
        str(payload["model"]),
        int(payload["input_tokens"]),
        int(payload["output_tokens"]),
    )
    cost_text = f" · estimated cost ${cost:.4f}" if cost is not None else ""
    st.caption(
        f"{payload['model']} · {payload['input_tokens']:,} input tokens · "
        f"{payload['output_tokens']:,} output tokens{cost_text}"
    )
    st.download_button(
        "Download as Markdown",
        data=str(payload["text"]),
        file_name=filename,
        mime="text/markdown",
        use_container_width=False,
    )


def _render_source_input() -> tuple[str, str]:
    st.subheader("1 · Add your lecture notes")
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.caption(
            "Paste text or upload up to five TXT, MD, PDF, DOCX, or PPTX files. "
            "Scanned PDFs require OCR first."
        )
    with top_right:
        st.button(
            "Use demo notes",
            on_click=_load_demo_note,
            use_container_width=True,
        )

    method = st.radio(
        "Note source",
        ["Paste text", "Upload files"],
        horizontal=True,
        key="source_method",
        label_visibility="collapsed",
    )

    source_label = "Pasted lecture notes"
    notes = ""
    if method == "Paste text":
        notes = st.text_area(
            "Lecture notes",
            key="pasted_notes",
            height=230,
            placeholder=(
                "Paste lecture notes here. Headings, formulas, examples, and lists are welcome…"
            ),
        ).strip()
    else:
        uploads = st.file_uploader(
            "Upload lecture-note files",
            type=["txt", "md", "pdf", "docx", "pptx"],
            accept_multiple_files=True,
            max_upload_size=max(1, CONFIG.max_file_bytes // (1024 * 1024)),
            help="Files are parsed in memory and are not written to this app's project folder.",
        )
        extracted = []
        if uploads:
            if len(uploads) > CONFIG.max_files:
                st.error(f"Upload at most {CONFIG.max_files} files at a time.")
            else:
                for upload in uploads:
                    try:
                        extracted.append(
                            extract_document(
                                upload.name,
                                upload.getvalue(),
                                max_bytes=CONFIG.max_file_bytes,
                                max_pdf_pages=CONFIG.max_pdf_pages,
                            )
                        )
                    except DocumentExtractionError as exc:
                        st.error(str(exc))
                if extracted:
                    notes = combine_documents(extracted)
                    source_label = ", ".join(item.name for item in extracted)

    if notes:
        approx_tokens = approximate_token_count(notes)
        metric_1, metric_2, metric_3 = st.columns(3)
        metric_1.metric("Characters", f"{len(notes):,}")
        metric_2.metric("Words", f"{len(notes.split()):,}")
        metric_3.metric("Local token preview", f"≈ {approx_tokens:,}")
        with st.expander("Preview extracted text"):
            st.text(notes[:8_000] + ("\n\n[Preview shortened]" if len(notes) > 8_000 else ""))
    else:
        st.info("Add notes to unlock the study modes. You can use the demo note to test the UI.")
    return notes, source_label


def _render_summary(
    *,
    notes: str,
    api_key: str,
    model: str,
    language: str,
    academic_level: str,
    max_input_tokens: int,
    max_output_tokens: int,
) -> None:
    st.markdown("#### Structured key summary")
    st.caption("Turn a long lecture into a hierarchy of ideas, formulas, links, and pitfalls.")
    with st.form("summary_form"):
        detail = st.select_slider(
            "Summary depth",
            options=["Concise", "Balanced", "Detailed"],
            value="Balanced",
        )
        focus = st.text_input(
            "Optional focus",
            placeholder="e.g. conditional probability and Bayes' theorem",
        )
        submitted = st.form_submit_button(
            "Generate summary", type="primary", disabled=not bool(notes)
        )
    if submitted:
        system = base_system_prompt(language=language, academic_level=academic_level)
        with st.spinner("Claude is structuring the lecture…"):
            response = _call_claude(
                api_key=api_key,
                model=model,
                system=system,
                notes=notes,
                message_factory=lambda current_notes: [
                    {
                        "role": "user",
                        "content": summary_message(current_notes, focus=focus, detail=detail),
                    }
                ],
                max_input_tokens=max_input_tokens,
                max_output_tokens=max_output_tokens,
            )
        if response:
            result, prepared = response
            st.session_state["outputs"]["summary"] = _result_payload(result, prepared, model)
    payload = st.session_state["outputs"].get("summary")
    if payload:
        _render_result(payload, filename="study-summary.md")


def _render_quiz(
    *,
    notes: str,
    api_key: str,
    model: str,
    language: str,
    academic_level: str,
    max_input_tokens: int,
    max_output_tokens: int,
) -> None:
    st.markdown("#### Practice-question builder")
    st.caption("Create retrieval and application questions, with answers kept out of sight.")
    with st.form("quiz_form"):
        left, right = st.columns(2)
        with left:
            count = st.slider("Number of questions", 3, 12, 6)
            difficulty = st.selectbox(
                "Difficulty", ["Foundation", "Intermediate", "Challenging"], index=1
            )
        with right:
            question_types = st.multiselect(
                "Question formats",
                ["Multiple choice", "Short answer", "Calculation", "True/false"],
                default=["Multiple choice", "Short answer"],
            )
            focus = st.text_input(
                "Optional focus", placeholder="e.g. focus on applications, not definitions"
            )
        submitted = st.form_submit_button(
            "Generate practice set", type="primary", disabled=not bool(notes)
        )
    if submitted:
        system = base_system_prompt(language=language, academic_level=academic_level)
        with st.spinner("Claude is designing the practice set…"):
            response = _call_claude(
                api_key=api_key,
                model=model,
                system=system,
                notes=notes,
                message_factory=lambda current_notes: [
                    {
                        "role": "user",
                        "content": quiz_message(
                            current_notes,
                            count=count,
                            difficulty=difficulty,
                            question_types=question_types,
                            focus=focus,
                        ),
                    }
                ],
                max_input_tokens=max_input_tokens,
                max_output_tokens=max_output_tokens,
            )
        if response:
            result, prepared = response
            st.session_state["outputs"]["quiz"] = _result_payload(result, prepared, model)

    payload = st.session_state["outputs"].get("quiz")
    if payload:
        questions, answers = split_quiz_output(str(payload["text"]))
        if payload.get("truncated"):
            st.warning(
                "The source exceeded your input budget. Excerpts were sampled across the notes."
            )
        st.markdown(questions)
        if answers:
            with st.expander("Reveal answer key"):
                st.markdown(answers)
        else:
            st.info(
                "Claude did not return a separable answer key; "
                "the full response is downloadable below."
            )
        cost = estimate_cost_usd(
            str(payload["model"]),
            int(payload["input_tokens"]),
            int(payload["output_tokens"]),
        )
        cost_text = f" · estimated cost ${cost:.4f}" if cost is not None else ""
        st.caption(
            f"{payload['model']} · {payload['input_tokens']:,} input tokens · "
            f"{payload['output_tokens']:,} output tokens{cost_text}"
        )
        st.download_button(
            "Download questions + answers",
            data=str(payload["text"]).replace("---ANSWER-KEY---", "\n\n"),
            file_name="practice-set.md",
            mime="text/markdown",
        )


def _render_explainer(
    *,
    notes: str,
    api_key: str,
    model: str,
    language: str,
    academic_level: str,
    max_input_tokens: int,
    max_output_tokens: int,
) -> None:
    st.markdown("#### Layered concept explainer")
    st.caption("Move from intuition to a worked example and then the technical detail.")
    with st.form("explanation_form"):
        concept = st.text_input(
            "Concept to explain",
            placeholder="e.g. Why does independence imply zero covariance, but not vice versa?",
        )
        depth = st.selectbox(
            "Depth",
            ["Quick refresher", "Layered explanation", "Technical deep dive"],
            index=1,
        )
        current_understanding = st.text_area(
            "What do you currently understand or find confusing?",
            height=90,
            placeholder="Optional, but it helps Claude explain at the right level.",
        )
        submitted = st.form_submit_button(
            "Explain concept", type="primary", disabled=not bool(notes)
        )
    if submitted:
        if not concept.strip():
            st.error("Tell Claude which concept you want explained.")
        else:
            system = base_system_prompt(language=language, academic_level=academic_level)
            with st.spinner("Claude is building the explanation in layers…"):
                response = _call_claude(
                    api_key=api_key,
                    model=model,
                    system=system,
                    notes=notes,
                    message_factory=lambda current_notes: [
                        {
                            "role": "user",
                            "content": explanation_message(
                                current_notes,
                                concept=concept,
                                depth=depth,
                                current_understanding=current_understanding,
                            ),
                        }
                    ],
                    max_input_tokens=max_input_tokens,
                    max_output_tokens=max_output_tokens,
                )
            if response:
                result, prepared = response
                st.session_state["outputs"]["explanation"] = _result_payload(
                    result, prepared, model
                )
    payload = st.session_state["outputs"].get("explanation")
    if payload:
        _render_result(payload, filename="concept-explanation.md")


def _socratic_turn(
    *,
    student_message: str | None,
    notes: str,
    api_key: str,
    model: str,
    language: str,
    academic_level: str,
    max_input_tokens: int,
    max_output_tokens: int,
) -> bool:
    history = st.session_state["socratic_messages"]
    added_user = bool(student_message)
    if student_message:
        history.append({"role": "user", "content": student_message})

    recent_history = trim_socratic_history(history, CONFIG.max_socratic_messages)
    goal = st.session_state["socratic_goal"]
    system = socratic_system_prompt(language=language, academic_level=academic_level)
    response = _call_claude(
        api_key=api_key,
        model=model,
        system=system,
        notes=notes,
        message_factory=lambda current_notes: [
            {
                "role": "user",
                "content": socratic_setup_message(current_notes, goal=goal),
            },
            *recent_history,
        ],
        max_input_tokens=max_input_tokens,
        max_output_tokens=min(max_output_tokens, 700),
    )
    if not response:
        if added_user and history and history[-1]["role"] == "user":
            history.pop()
        return False

    result, prepared = response
    history.append({"role": "assistant", "content": result.text})
    if prepared.notes_truncated:
        st.session_state["socratic_notes_truncated"] = True
    return True


def _render_socratic(
    *,
    notes: str,
    source_fingerprint: str,
    api_key: str,
    model: str,
    language: str,
    academic_level: str,
    max_input_tokens: int,
    max_output_tokens: int,
) -> None:
    st.markdown("#### Socratic guidance")
    st.caption(
        "Claude asks one question at a time and gives small hints before revealing an explanation."
    )

    with st.form("socratic_start_form"):
        goal = st.text_area(
            "What are you trying to understand or solve?",
            value=st.session_state.get("socratic_goal", ""),
            height=100,
            placeholder="Describe a concept, paste a problem, or state where you became stuck.",
        )
        start = st.form_submit_button(
            "Start a new guided session", type="primary", disabled=not bool(notes)
        )
    if start:
        if not goal.strip():
            st.error("Describe your learning goal or problem first.")
        else:
            st.session_state["socratic_messages"] = []
            st.session_state["socratic_goal"] = goal.strip()
            st.session_state["socratic_source"] = source_fingerprint
            st.session_state["socratic_active"] = True
            st.session_state["socratic_notes_truncated"] = False
            with st.spinner("Claude is choosing its first diagnostic question…"):
                _socratic_turn(
                    student_message=None,
                    notes=notes,
                    api_key=api_key,
                    model=model,
                    language=language,
                    academic_level=academic_level,
                    max_input_tokens=max_input_tokens,
                    max_output_tokens=max_output_tokens,
                )

    active = bool(st.session_state["socratic_active"])
    stale_source = active and st.session_state["socratic_source"] != source_fingerprint
    if stale_source:
        st.warning("The lecture notes changed. Start a new guided session to use the new source.")
    if st.session_state.get("socratic_notes_truncated"):
        st.warning("This conversation is using sampled excerpts because of the input-token cap.")

    for message in st.session_state["socratic_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    disabled = not active or stale_source or not api_key
    hint_col, reveal_col = st.columns(2)
    with hint_col:
        hint_clicked = st.button(
            "I’m stuck — one more hint",
            disabled=disabled,
            use_container_width=True,
        )
    with reveal_col:
        reveal_clicked = st.button(
            "Reveal and explain now",
            disabled=disabled,
            use_container_width=True,
        )

    typed = st.chat_input(
        "Reply with your reasoning…",
        disabled=disabled,
    )
    pending = typed
    if hint_clicked:
        pending = "I am stuck. Please give me one smaller hint without revealing the full answer."
    elif reveal_clicked:
        pending = (
            "I explicitly want the answer revealed now. Explain the reasoning step by step, "
            "then ask me one transfer question."
        )

    if pending:
        with st.chat_message("user"):
            st.markdown(pending)
        with st.spinner("Claude is considering your reasoning…"):
            success = _socratic_turn(
                student_message=pending,
                notes=notes,
                api_key=api_key,
                model=model,
                language=language,
                academic_level=academic_level,
                max_input_tokens=max_input_tokens,
                max_output_tokens=max_output_tokens,
            )
        if success:
            with st.chat_message("assistant"):
                st.markdown(st.session_state["socratic_messages"][-1]["content"])

    if st.session_state["socratic_messages"]:
        transcript = [
            f"## {item['role'].title()}\n\n{item['content']}"
            for item in st.session_state["socratic_messages"]
        ]
        st.download_button(
            "Download conversation",
            data="\n\n".join(transcript),
            file_name="socratic-session.md",
            mime="text/markdown",
        )


def main() -> None:
    _load_css()
    _init_state()

    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">RESPONSIBLE AI FOR LEARNING</div>
          <h1>Claude Study Companion</h1>
          <p>Turn your own lecture notes into clearer understanding,
          active recall, and guided thinking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Study controls")
        server_key = _secret("ANTHROPIC_API_KEY").strip()
        allow_user_key = _as_bool(_secret("ALLOW_USER_API_KEY", "true"))
        if server_key:
            api_key = server_key
            st.success("Claude API key configured", icon="🔒")
        elif allow_user_key:
            api_key = st.text_input(
                "Claude API key",
                type="password",
                placeholder="sk-ant-…",
                help=("Used for this session only. It is not written to the project or displayed."),
            ).strip()
            st.caption("For a public demo, bring-your-own-key mode prevents shared-key abuse.")
        else:
            api_key = ""
            st.error("No server API key is configured.")

        default_model = (
            _secret("CLAUDE_MODEL", CONFIG.default_model).strip() or "claude-haiku-4-5-20251001"
        )
        model_options = list(MODEL_CATALOG)
        if default_model not in model_options:
            model_options.insert(0, default_model)
        model = st.selectbox(
            "Model",
            model_options,
            index=model_options.index(default_model),
            format_func=lambda item: (
                MODEL_CATALOG.get(item).label if item in MODEL_CATALOG else item
            ),
        )
        if model in MODEL_CATALOG:
            st.caption(MODEL_CATALOG[model].description)

        language = st.selectbox("Response language", ["Match the notes", "English", "简体中文"])
        academic_level = st.selectbox(
            "Study level",
            ["undergraduate", "pre-university", "postgraduate", "general learner"],
        )
        max_input_tokens = st.slider(
            "Maximum input tokens",
            min_value=2_000,
            max_value=32_000,
            value=12_000,
            step=1_000,
            help="A hard per-request cap, enforced with Claude's token-counting endpoint.",
        )
        max_output_tokens = st.slider(
            "Maximum output tokens",
            min_value=300,
            max_value=4_000,
            value=1_200,
            step=100,
            help="Claude may finish before reaching this maximum.",
        )

        st.divider()
        usage = st.session_state["usage"]
        st.markdown("##### Session usage")
        st.progress(
            min(usage["requests"] / CONFIG.session_request_limit, 1.0),
            text=f"{usage['requests']} / {CONFIG.session_request_limit} generated requests",
        )
        st.caption(f"{usage['input_tokens']:,} input · {usage['output_tokens']:,} output tokens")
        st.caption(f"Estimated API cost: ${usage['estimated_cost_usd']:.4f}")
        st.button(
            "Clear generated work",
            on_click=_clear_learning_session,
            use_container_width=True,
        )

    notes, source_label = _render_source_input()
    source_fingerprint = hashlib.sha256(notes.encode("utf-8")).hexdigest() if notes else ""
    previous_source = st.session_state.get("last_source_fingerprint")
    if previous_source is not None and previous_source != source_fingerprint:
        st.session_state["outputs"] = {}
    st.session_state["last_source_fingerprint"] = source_fingerprint

    st.divider()
    st.subheader("2 · Choose a study mode")
    mode = st.radio(
        "Study mode",
        [
            "📌 Key Summary",
            "🧠 Practice Quiz",
            "🔍 Concept Explainer",
            "💬 Socratic Mode",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.caption(f"Current source: {source_label}")

    shared = {
        "notes": notes,
        "api_key": api_key,
        "model": model,
        "language": language,
        "academic_level": academic_level,
        "max_input_tokens": max_input_tokens,
        "max_output_tokens": max_output_tokens,
    }
    if mode == "📌 Key Summary":
        _render_summary(**shared)
    elif mode == "🧠 Practice Quiz":
        _render_quiz(**shared)
    elif mode == "🔍 Concept Explainer":
        _render_explainer(**shared)
    else:
        _render_socratic(source_fingerprint=source_fingerprint, **shared)

    st.divider()
    st.caption(
        "Privacy note: this app does not intentionally persist uploaded notes. Content is sent "
        "to Anthropic only when you generate a response. Review Anthropic's data policy before "
        "using sensitive or confidential material. AI output can be wrong—verify it against "
        "your course."
    )


if __name__ == "__main__":
    main()
