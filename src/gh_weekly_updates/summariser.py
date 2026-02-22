"""Summarise weekly activity using GitHub Models (OpenAI-compatible endpoint)."""

from __future__ import annotations

import logging

from openai import OpenAI

from gh_weekly_updates.models import WeeklyActivity

log = logging.getLogger(__name__)

GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
DEFAULT_MODEL = "openai/gpt-4.1"

SYSTEM_PROMPT = """\
You are a developer writing a concise weekly update for an open-source audience. \
Your job is to transform raw GitHub activity data into a clear, honest summary \
grouped by project or theme.

Structure your response EXACTLY as follows:

<START>

# Weekly Update — {username} ({period})

## 🏆 Wins

Group accomplishments by project or theme. For each group, use a heading \
(### Project/Theme Name) followed by bullet points. Focus on:
- Features shipped / PRs merged and what they do
- Bugs fixed and their impact
- Performance or reliability improvements
- Technical debt reduced

Each bullet should name the repo, describe what was done, and briefly explain \
why it matters. Write 1-4 bullets per group.

## ⚡ Challenges

Group ongoing difficulties by project or theme using the same heading style. \
Focus on:
- Complex problems still in progress
- Blockers encountered and how they were navigated
- Areas where more investment is needed
- Technical risks identified
Write 1-3 bullets per group. Frame constructively — show awareness and agency.

## 🔮 What's Next

Group planned or upcoming work by project or theme using the same heading \
style. Focus on:
- Open PRs expected to land soon
- Issues or epics being actively worked on
- Follow-up work triggered by this week's changes
- Areas of investigation or exploration
Write 1-3 bullets per group. Be concrete — reference specific PRs, issues, \
or discussions where possible.

---

### 📊 Activity Summary
Provide a brief stats line: X PRs authored, Y PRs reviewed, Z issues created, \
etc.

<END>

Guidelines:
- ALWAYS group updates by project or theme — never output a flat list
- ALWAYS use inline markdown links for PRs, issues, and discussions. \
For example: [repo#123](https://github.com/owner/repo/pull/123). \
The URLs are provided in the input data — use them directly.
- Be specific: use repo names, PR numbers, and concrete details
- Be concise: each bullet should be 1-2 sentences max
- Don't just list what was done — explain why it matters
- If the data is thin, acknowledge it honestly rather than inflating
- Use the actual PR/issue titles and numbers for traceability
- Infer "What's Next" from open PRs, open issues, and discussion threads — \
do not fabricate future plans
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
