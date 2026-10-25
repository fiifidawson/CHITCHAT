"""LLM prompts that turn a research question into a search plan.

The conversation is kept as a list of messages, so each revision sees the question,
the clarifying answers, every earlier draft and every piece of feedback.
"""

from __future__ import annotations

from typing import Any

from chitchat.config import SearchPreset
from chitchat.screening.llm import StructuredCaller
from chitchat.search.plan import ClarifyingQuestions, SearchPlan
from chitchat.stages import StageError

DRAFT_SYSTEM = """You design literature searches for OpenAlex, Europe PMC and arXiv.
Turn the user's research question into concepts and categories.

How the search works:
- A concept is one idea plus its synonyms. A paper matches a concept if it uses any of them.
- A category combines 2 or more concepts with AND. It becomes one search.
- Each category should cover one angle of the question.

Rules:
- Use short phrases (1 to 4 words) that appear in paper titles and abstracts.
- List synonyms most important first. Include common variants and abbreviations.
- No quotes, brackets or AND/OR/NOT inside a phrase.
- Every word in a category must be the `word` of one of your concepts.
- Prefer specific terms over very broad ones such as "system" or "model".
- Never leave out the question's central subject (for example the technology, population or
  practice it is about). If you must limit concepts, drop the most generic one instead.
- Choose the concepts that best separate relevant papers from the rest.
- A category's `words` are concept words only, never synonyms. Synonyms live in the concept.
- Every category combines at least 2 different concepts. A single concept is far too broad.

Example. Question: "How is consent handled when social media is scraped to train LLMs?"
concepts:
  - word "consent", synonyms ["informed consent", "opt-out", "data permission"]
  - word "social media", synonyms ["Twitter", "Reddit", "online platforms"]
  - word "web scraping", synonyms ["data scraping", "web crawling"]
  - word "large language models", synonyms ["LLMs", "language models"]
categories:
  - name "Consent in scraped social media", words ["consent", "social media", "web scraping"]
  - name "Consent for LLM training data", words ["consent", "large language models"]
"""

CLARIFY_SYSTEM = """You help a researcher plan a literature search.
Ask the questions whose answers would change the search the most:
scope, population, setting, time period, methods, what to leave out.
Keep each question short. Give 2 to 4 short possible answers for each.
"""


def _limits(preset: SearchPreset) -> str:
    if preset.min_categories == preset.max_categories:
        cats = (
            f"exactly {preset.max_categories} categor{'y' if preset.max_categories == 1 else 'ies'}"
        )
    else:
        cats = f"{preset.min_categories} to {preset.max_categories} categories"
    return (
        f"Make {cats}, each with 2 to {preset.max_concepts_per_category} concepts. "
        f"Give at most {preset.max_synonyms} synonyms per concept."
    )


def first_messages(
    question: str, answers: list[tuple[str, str]], preset: SearchPreset
) -> list[Any]:
    """System prompt plus the question and any clarifying answers."""
    from langchain_core.messages import HumanMessage, SystemMessage

    lines = [f"Research question: {question}"]
    answered = [(q, a) for q, a in answers if a.strip()]
    if answered:
        lines.append("\nClarifications from the researcher:")
        lines += [f"- {q} {a}" for q, a in answered]
    lines.append(f"\n{_limits(preset)}")
    return [SystemMessage(content=DRAFT_SYSTEM), HumanMessage(content="\n".join(lines))]


def add_feedback(messages: list[Any], draft: SearchPlan, feedback: str) -> list[Any]:
    """The conversation so far, plus the last draft and the researcher's change request."""
    from langchain_core.messages import AIMessage, HumanMessage

    return [
        *messages,
        AIMessage(content=draft.model_dump_json()),
        HumanMessage(content=f"Revise the whole search. Change request: {feedback}"),
    ]


def add_repair(messages: list[Any], draft: SearchPlan, problems: list[str]) -> list[Any]:
    """Ask the LLM to fix rule violations in its own draft, before the user sees it."""
    from langchain_core.messages import AIMessage, HumanMessage

    listing = "\n".join(f"- {p}" for p in problems)
    return [
        *messages,
        AIMessage(content=draft.model_dump_json()),
        HumanMessage(
            content=f"This draft breaks the rules:\n{listing}\nFix it and return the whole search."
        ),
    ]


class Drafter:
    """Asks the LLM for clarifying questions and search plans."""

    def __init__(self, chat_model: Any, method: str = "json_schema") -> None:
        self._clarify = StructuredCaller(chat_model, ClarifyingQuestions, method)
        self._plan = StructuredCaller(chat_model, SearchPlan, method)

    def clarify(self, question: str, n: int) -> ClarifyingQuestions:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=CLARIFY_SYSTEM),
            HumanMessage(content=f"Research question: {question}\nAsk {n} questions."),
        ]
        result = self._clarify(messages)
        if result.status != "ok":
            raise StageError(f"Couldn't get clarifying questions ({result.status}): {result.error}")
        parsed = result.parsed
        assert isinstance(parsed, ClarifyingQuestions)
        return ClarifyingQuestions(questions=parsed.questions[:n])

    def plan(self, messages: list[Any]) -> SearchPlan:
        result = self._plan(messages)
        if result.status != "ok":
            raise StageError(f"Couldn't draft the search ({result.status}): {result.error}")
        parsed = result.parsed
        assert isinstance(parsed, SearchPlan)
        return parsed
