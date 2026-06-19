from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import render

from content.models import StudyPage
from mocktest.models import MockTestResponse, MockTestSession
from practice.models import PracticeResponse
from study.models import UserStudyProgress


@login_required
def dashboard(request):
    user = request.user

    total_pages = StudyPage.objects.count()
    completed_pages = UserStudyProgress.objects.filter(
        user=user, status=UserStudyProgress.COMPLETED
    ).count()
    study_percent = round((completed_pages / total_pages) * 100) if total_pages else 0

    mock_sessions = MockTestSession.objects.filter(user=user, submitted_at__isnull=False).order_by("started_at")
    best_score = max((m.correct_answers for m in mock_sessions), default=None)
    last_mock = mock_sessions.last()

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

    topic_rows = [
        {"name": name, "percent": round((v["correct"] / v["total"]) * 100) if v["total"] else 0, **v}
        for name, v in topic_accuracy.items()
    ]
    weakest = min(topic_rows, key=lambda r: r["percent"], default=None)

    mock_trend = [{"label": m.started_at.strftime("%d %b"), "score": m.correct_answers} for m in mock_sessions]

    context = {
        "study_percent": study_percent,
        "completed_pages": completed_pages,
        "total_pages": total_pages,
        "best_score": best_score,
        "last_mock": last_mock,
        "mock_count": mock_sessions.count(),
        "practice_accuracy": practice_accuracy,
        "practice_total": practice_total,
        "topic_rows": topic_rows,
        "weakest": weakest,
        "mock_trend": mock_trend,
    }
    return render(request, "analytics/dashboard.html", context)
