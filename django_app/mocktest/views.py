import random

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from content.models import Topic
from practice.models import AnswerOption, Question

from .models import MockTestQuestionEvent, MockTestResponse, MockTestSession

PASS_MARK = 18
DURATION_SECONDS = 45 * 60
BLUEPRINT = {
    "The values and principles of the UK": 1,
    "What is the UK?": 1,
    "A long and illustrious history": 8,
    "A modern, thriving society": 7,
    "The UK government, the law and your role": 7,
}


@login_required
def mock_start(request):
    selected = []
    for topic_name, count in BLUEPRINT.items():
        topic = Topic.objects.filter(name=topic_name).first()
        if not topic:
            continue
        pool = list(Question.objects.filter(topic=topic).values_list("id", flat=True))
        if len(pool) < count:
            return render(request, "mocktest/start.html", {"error": f"Not enough questions for '{topic_name}'."})
        selected.extend(random.sample(pool, count))

    random.shuffle(selected)
    session = MockTestSession.objects.create(
        user=request.user,
        question_ids=selected,
        total_questions=len(selected),
    )
    return redirect("mocktest:run", session_id=session.id)


@login_required
def mock_run(request, session_id):
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)
    questions = []
    for order, qid in enumerate(session.question_ids):
        q = Question.objects.prefetch_related("options").get(id=qid)
        questions.append({"order": order, "question": q, "options": list(q.options.all())})

    return render(request, "mocktest/run.html", {
        "session": session,
        "questions": questions,
        "duration": DURATION_SECONDS,
        "pass_mark": PASS_MARK,
    })


@require_POST
@login_required
def mock_submit(request, session_id):
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)
    correct = 0

    for order, qid in enumerate(session.question_ids):
        question = Question.objects.get(id=qid)
        option_id = request.POST.get(f"q_{qid}")
        selected = AnswerOption.objects.filter(id=option_id, question=question).first() if option_id else None
        is_correct = bool(selected and selected.is_correct)
        if is_correct:
            correct += 1

        MockTestResponse.objects.update_or_create(
            mock_session=session,
            question=question,
            defaults={"selected_option": selected, "is_correct": is_correct},
        )

        MockTestQuestionEvent.objects.update_or_create(
            mock_session=session,
            question=question,
            defaults={
                "question_order": order,
                "dwell_time_ms": int(request.POST.get(f"dwell_{qid}", 0) or 0),
                "revisit_count": int(request.POST.get(f"revisit_{qid}", 0) or 0),
                "answer_changed_count": int(request.POST.get(f"changed_{qid}", 0) or 0),
            },
        )

    session.correct_answers = correct
    session.score_percent = round((correct / session.total_questions) * 100) if session.total_questions else 0
    session.pass_status = correct >= PASS_MARK
    session.submitted_at = timezone.now()
    session.duration_seconds = int(request.POST.get("elapsed_seconds", 0) or 0)
    session.save()

    return redirect("mocktest:result", session_id=session.id)


@login_required
def mock_result(request, session_id):
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)
    responses = session.responses.select_related("question__topic", "selected_option")

    topic_stats = {}
    for r in responses:
        name = r.question.topic.name
        bucket = topic_stats.setdefault(name, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if r.is_correct:
            bucket["correct"] += 1

    return render(request, "mocktest/result.html", {
        "session": session,
        "responses": responses,
        "topic_stats": topic_stats,
        "pass_mark": PASS_MARK,
    })
