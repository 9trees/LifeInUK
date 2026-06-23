import json
from collections import Counter
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from content.models import StudyPage
from mocktest.models import MockTestQuestionEvent, MockTestResponse, MockTestSession
from practice.models import PracticeResponse
from study.models import UserStudyProgress

from .forms import FeedbackForm
from .models import Feedback


@login_required
def dashboard(request):
    user = request.user

    total_pages = StudyPage.objects.count()
    completed_pages = UserStudyProgress.objects.filter(
        user=user, status=UserStudyProgress.COMPLETED
    ).count()
    study_percent = round((completed_pages / total_pages) * 100) if total_pages else 0

    mock_sessions = list(MockTestSession.objects.filter(user=user, submitted_at__isnull=False).order_by("started_at"))
    last_mock = mock_sessions[-1] if mock_sessions else None
    best_mock = max(mock_sessions, key=lambda m: m.correct_answers, default=None)
    best_score = best_mock.correct_answers if best_mock else None
    best_mock_date = best_mock.started_at.strftime("%d %b %Y") if best_mock else None
    average_mock = round(sum(m.correct_answers for m in mock_sessions) / len(mock_sessions)) if mock_sessions else None
    previous_mock = mock_sessions[-2] if len(mock_sessions) > 1 else None
    mock_delta = last_mock.correct_answers - previous_mock.correct_answers if previous_mock and last_mock else None

    practice_total = PracticeResponse.objects.filter(session__user=user).count()
    practice_correct = PracticeResponse.objects.filter(session__user=user, is_correct=True).count()
    practice_accuracy = round((practice_correct / practice_total) * 100) if practice_total else 0

    # Topic-wise accuracy across practice + mock.
    topic_accuracy = {}
    for r in PracticeResponse.objects.filter(session__user=user).select_related("question__topic"):
        b = topic_accuracy.setdefault(r.question.topic.name, {"correct": 0, "total": 0})
        b["total"] += 1
        b["correct"] += 1 if r.is_correct else 0
    for r in MockTestResponse.objects.filter(mock_session__user=user).select_related("question__topic"):
        b = topic_accuracy.setdefault(r.question.topic.name, {"correct": 0, "total": 0})
        b["total"] += 1
        b["correct"] += 1 if r.is_correct else 0

    topic_rows = sorted([
        {"name": name, "percent": round((v["correct"] / v["total"]) * 100) if v["total"] else 0, **v}
        for name, v in topic_accuracy.items()
    ], key=lambda r: (r["percent"], r["name"]))
    weakest = min(topic_rows, key=lambda r: r["percent"], default=None)

    mock_trend = [{"label": m.started_at.strftime("%d %b"), "score": m.correct_answers} for m in mock_sessions]

    weak_topics = [row for row in topic_rows if row["total"] >= 2 and row["percent"] < 70][:3]

    recommendations = []
    if study_percent < 50:
        recommendations.append(f"Push study progress to at least 50% by finishing {max(total_pages - completed_pages, 0)} more page(s).")
    elif study_percent < 80:
        recommendations.append("Keep study momentum going and close the remaining content gaps before more mock attempts.")

    if weakest:
        recommendations.append(f"Focus practice on {weakest['name']} first; it is currently your weakest topic.")
    if practice_total < 20:
        recommendations.append("Do more practice questions to make the accuracy metric more reliable.")
    if best_score is not None and best_score < 18:
        recommendations.append("Aim to move your best mock score above the pass mark of 18/24.")
    elif mock_delta is not None and mock_delta > 0:
        recommendations.append(f"Your latest mock improved by {mock_delta} point(s); keep that pattern going.")

    if not recommendations:
        recommendations.append("You are in a strong place. Keep rotating between study, practice, and mock tests.")

    context = {
        "days_left": user.get_remaining_days(),
        "study_percent": study_percent,
        "completed_pages": completed_pages,
        "total_pages": total_pages,
        "best_score": best_score,
        "best_mock_date": best_mock_date,
        "last_mock": last_mock,
        "mock_count": len(mock_sessions),
        "mock_average": average_mock,
        "mock_delta": mock_delta,
        "practice_accuracy": practice_accuracy,
        "practice_total": practice_total,
        "topic_rows": topic_rows,
        "weakest": weakest,
        "weak_topics": weak_topics,
        "recommendations": recommendations,
        "mock_trend": mock_trend,
        "pace_metrics": _compute_pace_metrics(mock_sessions),
    }
    return render(request, "analytics/dashboard.html", context)


def _compute_pace_metrics(mock_sessions):
    """Compute pace analytics across all submitted mock sessions."""
    if not mock_sessions:
        return None

    TOTAL_SECONDS = 45 * 60  # 45 minutes
    TOTAL_Q = 24

    durations = [m.duration_seconds for m in mock_sessions if m.duration_seconds > 0]
    if not durations:
        return None

    latest = mock_sessions[-1]
    avg_duration = sum(durations) / len(durations)
    avg_per_q = avg_duration / TOTAL_Q

    # Classify pace: fast (<60s/q), normal (60-90s/q), slow (>90s/q)
    if avg_per_q < 60:
        pace_label = "Fast"
        pace_class = "text-warning"
        pace_tip = "You're rushing — slow down and read carefully."
    elif avg_per_q <= 90:
        pace_label = "Normal"
        pace_class = "text-success"
        pace_tip = "Good pace — balanced between speed and care."
    else:
        pace_label = "Slow"
        pace_class = "text-danger"
        pace_tip = "You're using a lot of time — practise to build speed."

    # Per-question dwell from the latest session
    latest_events = list(
        MockTestQuestionEvent.objects.filter(mock_session=latest).order_by("question_order")
    )
    question_times = [
        {"order": e.question_order + 1, "dwell_s": round(e.dwell_time_ms / 1000, 1)}
        for e in latest_events if e.dwell_time_ms > 0
    ]

    # Skipped count (answered questions with no selected option)
    skipped = MockTestResponse.objects.filter(
        mock_session=latest, selected_option__isnull=True
    ).count()
    answer_changes = sum(e.answer_changed_count for e in latest_events)
    revisits = sum(e.revisit_count for e in latest_events)

    return {
        "avg_seconds": round(avg_duration),
        "avg_per_question": round(avg_per_q, 1),
        "pace_label": pace_label,
        "pace_class": pace_class,
        "pace_tip": pace_tip,
        "latest_duration": latest.duration_seconds,
        "latest_pct_used": round((latest.duration_seconds / TOTAL_SECONDS) * 100) if latest.duration_seconds else 0,
        "skipped": skipped,
        "answer_changes": answer_changes,
        "revisits": revisits,
        "question_times": question_times,
    }


@login_required
def feedback_view(request):
    form = FeedbackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        fb = form.save(commit=False)
        fb.user = request.user
        fb.save()
        messages.success(request, "Thank you for your feedback!")
        return redirect("analytics:feedback")

    return render(request, "analytics/feedback.html", {"form": form})


@login_required
def infographics_view(request):
    infographics = [
        {"title": "Democracy Timeline", "file": "infographics/democracy-timeline.pdf"},
        {"title": "Inventions", "file": "infographics/inventions.pdf"},
        {"title": "Society and Values", "file": "infographics/society-and-values.pdf"},
        {"title": "The British Constitution", "file": "infographics/the-british-constitution.pdf"},
        {"title": "UK Sport", "file": "infographics/uk-sport.pdf"},
        {"title": "Writers", "file": "infographics/writers.pdf"},
    ]
    return render(request, "analytics/infographics.html", {"infographics": infographics})


# ── Superuser Feedback Dashboard ──────────────────────────────


def _superuser_required(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(_superuser_required)
def feedback_admin(request):
    """Superuser dashboard: view all feedback with charts and filters."""
    qs = Feedback.objects.select_related("user").order_by("-created_at")

    # Optional query-string filters
    category = request.GET.get("category", "")
    rating = request.GET.get("rating", "")
    status = request.GET.get("status", "")  # "unread" or "read"

    if category:
        qs = qs.filter(category=category)
    if rating:
        qs = qs.filter(rating=int(rating))
    if status == "unread":
        qs = qs.filter(is_read=False)
    elif status == "read":
        qs = qs.filter(is_read=True)

    all_feedback = list(qs)
    all_unfiltered = Feedback.objects.all()

    # ── Summary stats ──
    total = all_unfiltered.count()
    unread = all_unfiltered.filter(is_read=False).count()
    avg_rating = all_unfiltered.aggregate(avg=Avg("rating"))["avg"] or 0

    # ── Category breakdown (for doughnut chart) ──
    cat_counts = dict(all_unfiltered.values_list("category").annotate(c=Count("id")).order_by("category"))
    category_labels = [label for _, label in Feedback.CATEGORY_CHOICES]
    category_data = [cat_counts.get(code, 0) for code, _ in Feedback.CATEGORY_CHOICES]

    # ── Rating distribution (for bar chart) ──
    rating_counts = dict(all_unfiltered.values_list("rating").annotate(c=Count("id")))
    rating_labels = ["1 ★", "2 ★", "3 ★", "4 ★", "5 ★"]
    rating_data = [rating_counts.get(i, 0) for i in range(1, 6)]

    # ── Feedback over time — last 30 days (for line chart) ──
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_qs = (
        all_unfiltered.filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    daily_map = {row["day"]: row["count"] for row in daily_qs}
    timeline_labels = []
    timeline_data = []
    for i in range(30):
        day = (timezone.now() - timedelta(days=29 - i)).date()
        timeline_labels.append(day.strftime("%d %b"))
        timeline_data.append(daily_map.get(day, 0))

    # ── Average rating over time (for line chart overlay) ──
    daily_avg_qs = (
        all_unfiltered.filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(avg_r=Avg("rating"))
        .order_by("day")
    )
    daily_avg_map = {row["day"]: round(float(row["avg_r"]), 1) for row in daily_avg_qs}
    avg_rating_data = [daily_avg_map.get((timezone.now() - timedelta(days=29 - i)).date(), None) for i in range(30)]

    context = {
        "feedbacks": all_feedback,
        "total": total,
        "unread": unread,
        "avg_rating": round(avg_rating, 1),
        "category_labels": json.dumps(category_labels),
        "category_data": json.dumps(category_data),
        "rating_labels": json.dumps(rating_labels),
        "rating_data": json.dumps(rating_data),
        "timeline_labels": json.dumps(timeline_labels),
        "timeline_data": json.dumps(timeline_data),
        "avg_rating_data": json.dumps(avg_rating_data),
        "filter_category": category,
        "filter_rating": rating,
        "filter_status": status,
        "categories": Feedback.CATEGORY_CHOICES,
    }
    return render(request, "analytics/feedback_admin.html", context)


@require_POST
@login_required
@user_passes_test(_superuser_required)
def feedback_mark_read(request, pk):
    """AJAX: toggle read status of a single feedback."""
    fb = get_object_or_404(Feedback, pk=pk)
    fb.is_read = not fb.is_read
    fb.save(update_fields=["is_read"])
    unread = Feedback.objects.filter(is_read=False).count()
    return JsonResponse({"ok": True, "is_read": fb.is_read, "unread": unread})


@require_POST
@login_required
@user_passes_test(_superuser_required)
def feedback_mark_all_read(request):
    """AJAX: mark all feedback as read."""
    Feedback.objects.filter(is_read=False).update(is_read=True)
    return JsonResponse({"ok": True, "unread": 0})
