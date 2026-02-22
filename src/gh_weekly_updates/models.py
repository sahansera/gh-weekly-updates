"""Pydantic data models for GitHub activities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    PR_AUTHORED = "pr_authored"
    PR_REVIEWED = "pr_reviewed"
    ISSUE_CREATED = "issue_created"
    ISSUE_COMMENTED = "issue_commented"
    DISCUSSION_CREATED = "discussion_created"
    DISCUSSION_COMMENTED = "discussion_commented"
    COMMIT = "commit"


class PullRequest(BaseModel):
    repo: str
    number: int
    title: str
    url: str
    state: str
    created_at: datetime
    merged_at: datetime | None = None
    body: str | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    labels: list[str] = Field(default_factory=list)
    review_comments: int = 0


class Review(BaseModel):
    repo: str
    pr_number: int
    pr_title: str
    pr_url: str
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED
    submitted_at: datetime
    body: str | None = None


class Issue(BaseModel):
    repo: str
    number: int
    title: str
    url: str
    state: str
    created_at: datetime
    body: str | None = None
    labels: list[str] = Field(default_factory=list)
    comments: int = 0


class IssueComment(BaseModel):
    repo: str
    issue_number: int
    issue_title: str
    issue_url: str
    body: str
    created_at: datetime


class Discussion(BaseModel):
    repo: str
    number: int
    title: str
    url: str
    created_at: datetime
    body: str | None = None
    category: str | None = None


class DiscussionComment(BaseModel):
    repo: str
    discussion_number: int
    discussion_title: str
    discussion_url: str
    body: str
    created_at: datetime


class WeeklyActivity(BaseModel):
    """Aggregated weekly activity for a user."""

    username: str
    since: datetime
    until: datetime
    repos: list[str] = Field(default_factory=list)
    prs_authored: list[PullRequest] = Field(default_factory=list)
    prs_reviewed: list[Review] = Field(default_factory=list)
    issues_created: list[Issue] = Field(default_factory=list)
    issue_comments: list[IssueComment] = Field(default_factory=list)
    discussions_created: list[Discussion] = Field(default_factory=list)
    discussion_comments: list[DiscussionComment] = Field(default_factory=list)

    @property
    def total_activities(self) -> int:
        return (
            len(self.prs_authored)
            + len(self.prs_reviewed)
            + len(self.issues_created)
            + len(self.issue_comments)
            + len(self.discussions_created)
            + len(self.discussion_comments)
        )

    def to_prompt_context(self) -> str:
        """Serialize activities into a text block suitable for an LLM prompt."""
        sections: list[str] = []
        sections.append(f"## GitHub Activity for {self.username}")
        sections.append(f"Period: {self.since.date()} → {self.until.date()}")
        sections.append(f"Repos touched: {', '.join(self.repos)}")
        sections.append("")

        if self.prs_authored:
            sections.append("### Pull Requests Authored")
            for pr in self.prs_authored:
                status = f"MERGED ({pr.merged_at.date()})" if pr.merged_at else pr.state.upper()
                sections.append(
                    f"- [{pr.repo}#{pr.number}]({pr.url}) {pr.title} — {status} "
                    f"(+{pr.additions}/-{pr.deletions}, {pr.changed_files} files)"
                )
                if pr.body:
                    body_preview = pr.body[:500].replace("\n", " ")
                    sections.append(f"  Description: {body_preview}")
            sections.append("")

        if self.prs_reviewed:
            sections.append("### Pull Requests Reviewed")
            for r in self.prs_reviewed:
                sections.append(f"- [{r.repo}#{r.pr_number}]({r.pr_url}) {r.pr_title} — {r.state}")
                if r.body:
                    body_preview = r.body[:300].replace("\n", " ")
                    sections.append(f"  Review comment: {body_preview}")
            sections.append("")

        if self.issues_created:
            sections.append("### Issues Created")
            for issue in self.issues_created:
                labels = f" [{', '.join(issue.labels)}]" if issue.labels else ""
                sections.append(
                    f"- [{issue.repo}#{issue.number}]({issue.url}) {issue.title} "
                    f"— {issue.state.upper()}{labels}"
                )
                if issue.body:
                    body_preview = issue.body[:300].replace("\n", " ")
                    sections.append(f"  Description: {body_preview}")
            sections.append("")

        if self.issue_comments:
            sections.append("### Issue Comments")
            for c in self.issue_comments:
                body_preview = c.body[:300].replace("\n", " ")
                sections.append(f"- [{c.repo}#{c.issue_number}]({c.issue_url}) {c.issue_title}")
                sections.append(f"  Comment: {body_preview}")
            sections.append("")

        if self.discussions_created:
            sections.append("### Discussions Created")
            for d in self.discussions_created:
                cat = f" ({d.category})" if d.category else ""
                sections.append(f"- [{d.repo}#{d.number}]({d.url}) {d.title}{cat}")
                if d.body:
                    body_preview = d.body[:300].replace("\n", " ")
                    sections.append(f"  Body: {body_preview}")
            sections.append("")

        if self.discussion_comments:
            sections.append("### Discussion Comments")
            for c in self.discussion_comments:
                body_preview = c.body[:300].replace("\n", " ")
                sections.append(
                    f"- [{c.repo}#{c.discussion_number}]({c.discussion_url}) {c.discussion_title}"
                )
                sections.append(f"  Comment: {body_preview}")
            sections.append("")

        return "\n".join(sections)
