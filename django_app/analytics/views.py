from django.contrib.auth.decorators import login_required
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
    }
    return render(request, "analytics/dashboard.html", context)
