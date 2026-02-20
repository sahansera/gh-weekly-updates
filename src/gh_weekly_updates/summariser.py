"""Summarise weekly activity using GitHub Models (OpenAI-compatible endpoint)."""

from __future__ import annotations

import logging

from openai import OpenAI

from gh_weekly_updates.models import WeeklyActivity

log = logging.getLogger(__name__)

GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
DEFAULT_MODEL = "openai/gpt-4.1"

SYSTEM_PROMPT = """\
You are an expert engineering manager writing a weekly impact summary for a \
Software Engineer. Your job is to transform raw GitHub activity data into \
a compelling, concise narrative that highlights technical leadership, strategic \
influence, and execution quality.

Structure your response EXACTLY as follows:

<START>

# Weekly Impact Summary — {username} ({period})

## 🏆 Wins
Concrete deliverables and accomplishments. Focus on:
- Features shipped / PRs merged and their business or technical value
- Bugs fixed with severity/impact context
- Technical debt reduced
- Performance or reliability improvements
Write 3-7 bullet points. Each should name the repo, describe what was done, \
and articulate WHY it matters.

## 🧭 Strategic Influence
Evidence of leadership beyond individual contribution. Focus on:
- Code reviews that improved quality, caught issues, or mentored others
- Architectural discussions or RFCs
- Cross-team collaboration signals
- Process improvements proposed or implemented
- Issues filed that identify systemic problems
Write 3-7 bullet points. Frame each as a leadership action with impact.

## ⚡ Challenges
Honest reflection on difficulties. Focus on:
- Complex problems still in progress
- Blockers encountered and how they were navigated
- Areas where more investment is needed
- Technical risks identified
Write 2-5 bullet points. Frame constructively — show awareness and agency.

---

### 📊 Activity Summary
Provide a brief stats line: X PRs authored, Y PRs reviewed, Z issues created, \
etc.

<END>

Guidelines:
- ALWAYS use inline markdown links for PRs, issues, and discussions. \
For example: [repo#123](https://github.com/owner/repo/pull/123). \
The URLs are provided in the input data — use them directly.
- Be specific: use repo names, PR numbers, and concrete details
- Be concise: each bullet should be 1-2 sentences max
- Don't just list what was done — explain why it matters
- If the data is thin, acknowledge it honestly rather than inflating
- Use the actual PR/issue titles and numbers for traceability
- Do NOT mention any career level framing in the wording of the produced output
"""


def summarise(
    activity: WeeklyActivity,
    token: str,
    model: str = DEFAULT_MODEL,
    custom_prompt: str | None = None,
) -> str:
    """Send activity data to GitHub Models and return the formatted summary."""
    context = activity.to_prompt_context()

    if activity.total_activities == 0:
        return (
            f"# Weekly Impact Summary — {activity.username} "
            f"({activity.since.date()} → {activity.until.date()})\n\n"
            "No GitHub activity found for this period.\n"
        )

    log.info(
        "Sending %d activities to %s for summarisation",
        activity.total_activities,
        model,
    )

    client = OpenAI(
        base_url=GITHUB_MODELS_BASE_URL,
        api_key=token,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": custom_prompt or SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Here is my GitHub activity for the past week. "
                    f"Please generate my weekly impact summary.\n\n{context}"
                ),
            },
        ],
        temperature=0.3,
        max_tokens=4000,
    )

    summary = response.choices[0].message.content
    log.debug("Received summary (%d chars)", len(summary))
    return summary
