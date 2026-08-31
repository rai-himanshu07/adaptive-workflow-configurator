"""State and persistence boundary for review-gated upstream updates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping

from workflow_configurator.upstream import (
    UpstreamAssetReview,
    UpstreamError,
    UpstreamReport,
    UpstreamReviewItem,
    UpstreamReviewLedger,
    UpstreamReviewRecord,
    advance_review_baseline,
    asset_request_urls,
    build_asset_review,
    build_upstream_report,
    default_cache_path,
    default_review_ledger_path,
    load_cached_report,
    load_review_ledger,
    outstanding_review_items,
    record_upstream_review,
    request_urls,
    review_decision_for,
    review_items,
    save_cached_report,
    save_review_ledger,
    update_check_due,
)


class UpstreamUpdateService:
    """Own upstream cache, review ledger, and transitions without UI code."""

    def __init__(
        self,
        *,
        cache_path: Path | str | None = None,
        ledger_path: Path | str | None = None,
    ) -> None:
        self.cache_path = (
            Path(cache_path).expanduser()
            if cache_path is not None
            else default_cache_path()
        )
        self.ledger_path = (
            Path(ledger_path).expanduser()
            if ledger_path is not None
            else default_review_ledger_path()
        )
        self.ledger: UpstreamReviewLedger | None = None
        self.report: UpstreamReport | None = None
        self.error = ""

        try:
            self.ledger = load_review_ledger(self.ledger_path)
        except UpstreamError as error:
            self.error = str(error)
            return

        try:
            cached = load_cached_report(self.cache_path)
        except UpstreamError as error:
            self.error = str(error)
            return
        if (
            cached is not None
            and cached.reviewed_revision != self.ledger.baseline_revision
        ):
            self.error = (
                "cached update report uses an older reviewed baseline; "
                "run a new upstream check"
            )
            return
        self.report = cached

    def _require_ledger(self) -> UpstreamReviewLedger:
        if self.ledger is None:
            raise UpstreamError(
                self.error or "the upstream review ledger is unavailable"
            )
        return self.ledger

    @property
    def baseline_revision(self) -> str:
        return self._require_ledger().baseline_revision

    def catalog_request_urls(self) -> dict[str, str]:
        return request_urls(self.baseline_revision)

    def check_due(self, *, now: datetime | None = None) -> bool:
        return update_check_due(self.report, now=now)

    def accept_catalog_payloads(
        self,
        payloads: Mapping[str, bytes],
        *,
        checked_at: datetime | None = None,
    ) -> UpstreamReport:
        report = build_upstream_report(
            payloads,
            checked_at=checked_at,
            reviewed_revision=self.baseline_revision,
        )
        save_cached_report(report, self.cache_path)
        self.report = report
        self.error = ""
        return report

    def review_items(
        self,
        *,
        outstanding_only: bool = False,
    ) -> tuple[UpstreamReviewItem, ...]:
        if self.report is None:
            return ()
        ledger = self._require_ledger()
        if outstanding_only:
            return outstanding_review_items(self.report, ledger)
        return review_items(self.report)

    def decision_for(
        self,
        item: UpstreamReviewItem,
    ) -> UpstreamReviewRecord | None:
        return review_decision_for(self._require_ledger(), item)

    def asset_request_urls(self, item: UpstreamReviewItem) -> dict[str, str]:
        if self.report is None or item not in self.review_items():
            raise UpstreamError("the selected item is not in the active review report")
        return asset_request_urls(item)

    def build_asset_review(
        self,
        item: UpstreamReviewItem,
        payloads: Mapping[str, bytes],
    ) -> UpstreamAssetReview:
        if self.report is None or item not in self.review_items():
            raise UpstreamError("the selected item is not in the active review report")
        return build_asset_review(item, payloads)

    def record_review(
        self,
        review: UpstreamAssetReview,
        disposition: str,
        note: str,
        *,
        reviewed_at: datetime | None = None,
    ) -> UpstreamReviewRecord:
        if self.report is None or review.item not in self.review_items():
            raise UpstreamError("the inspected item is no longer in the active report")
        updated = record_upstream_review(
            self._require_ledger(),
            review,
            disposition,
            note,
            reviewed_at=reviewed_at,
        )
        save_review_ledger(updated, self.ledger_path)
        self.ledger = updated
        decision = review_decision_for(updated, review.item)
        if decision is None:
            raise UpstreamError("the review decision was not persisted")
        return decision

    def can_advance_baseline(self) -> bool:
        return (
            self.report is not None
            and self.report.current_revision != self.baseline_revision
            and not self.review_items(outstanding_only=True)
        )

    def advance_baseline(self) -> str:
        if self.report is None:
            raise UpstreamError("there is no active update report")
        updated = advance_review_baseline(self._require_ledger(), self.report)
        save_review_ledger(updated, self.ledger_path)
        self.ledger = updated
        self.report = None
        self.error = ""
        return updated.baseline_revision


__all__ = ["UpstreamUpdateService"]
