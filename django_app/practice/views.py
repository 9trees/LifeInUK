import random

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from content.models import Topic

from .models import AnswerOption, PracticeResponse, PracticeSession, Question

MODE_COUNTS = {"random_10": 10, "random_20": 20, "random_30": 30}


@login_required
def practice_setup(request):
    topics = Topic.objects.all()
    if request.method == "POST":
        topic_codes = request.POST.getlist("topics")
        mode = request.POST.get("mode", "random_10")
        if not topic_codes:
            return render(request, "practice/setup.html", {"topics": topics, "error": "Select at least one topic."})

        question_qs = Question.objects.filter(topic__code__in=topic_codes)
        question_ids = list(question_qs.values_list("id", flat=True))

        if mode == "unanswered":
            answered_ids = set(
                PracticeResponse.objects.filter(session__user=request.user, question_id__in=question_ids)
                .values_list("question_id", flat=True)
            )
            question_ids = [qid for qid in question_ids if qid not in answered_ids]
        elif mode in MODE_COUNTS:
            random.shuffle(question_ids)
            question_ids = question_ids[: MODE_COUNTS[mode]]
        # mode == "all" keeps all question_ids

        if not question_ids:
            return render(request, "practice/setup.html", {"topics": topics, "error": "No questions match that selection."})

        random.shuffle(question_ids)
        session = PracticeSession.objects.create(
            user=request.user,
            mode=mode,
            selected_topics=[int(c) for c in topic_codes],
            question_ids=question_ids,
            total_questions=len(question_ids),
        )
        return redirect("practice:question", session_id=session.id, index=0)

    return render(request, "practice/setup.html", {"topics": topics})


@login_required
def practice_question(request, session_id, index):
    session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
    ids = session.question_ids
    if index < 0 or index >= len(ids):
        return redirect("practice:result", session_id=session.id)

    question = get_object_or_404(Question, id=ids[index])
    response = PracticeResponse.objects.filter(session=session, question=question).first()

    return render(request, "practice/question.html", {
        "session": session,
        "question": question,
        "options": question.options.all(),
        "index": index,
        "total": len(ids),
        "response": response,
        "has_prev": index > 0,
        "has_next": index < len(ids) - 1,
    })


@require_POST
@login_required
def practice_answer(request, session_id, index):
    session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
    ids = session.question_ids
    question = get_object_or_404(Question, id=ids[index])

    option_id = request.POST.get("option")
    selected = AnswerOption.objects.filter(id=option_id, question=question).first() if option_id else None
    is_correct = bool(selected and selected.is_correct)

    PracticeResponse.objects.update_or_create(
        session=session,
        question=question,
        defaults={
            "selected_option": selected,
            "is_correct": is_correct,
            "explanation_viewed": True,
            "response_time_ms": int(request.POST.get("elapsed_ms", 0) or 0),
        },
    )
    return redirect("practice:question", session_id=session.id, index=index)


@login_required
def practice_result(request, session_id):
    session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
    responses = session.responses.select_related("question__topic", "selected_option")

    correct = sum(1 for r in responses if r.is_correct)
    total = session.total_questions
    session.correct_answers = correct
    session.score_percent = round((correct / total) * 100) if total else 0
    session.ended_at = timezone.now()
    session.save()

    topic_stats = {}
    for r in responses:
        name = r.question.topic.name
        bucket = topic_stats.setdefault(name, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if r.is_correct:
            bucket["correct"] += 1

    return render(request, "practice/result.html", {
        "session": session,
        "correct": correct,
        "total": total,
        "responses": responses,
        "topic_stats": topic_stats,
    })
