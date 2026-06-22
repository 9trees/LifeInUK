import random

from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from content.models import Topic
from practice.models import AnswerOption, Question

from .models import MockTestQuestionEvent, MockTestResponse, MockTestSession

PASS_MARK = 18
DURATION_SECONDS = 45 * 60
# topic_code → number of questions to sample
BLUEPRINT = {
    1: 1,  # The values and principles of the UK
    2: 1,  # What is the UK?
    3: 8,  # A long and illustrious history
    4: 7,  # A modern, thriving society
    5: 7,  # The UK government, the law and your role
}


@login_required
def mock_intro(request):
    """Intro page explaining how the mock test works."""
    return render(request, "mocktest/intro.html", {"pass_mark": PASS_MARK, "duration": DURATION_SECONDS // 60})


@login_required
def mock_start(request):
    """Generate a blueprint-based mock session and redirect to first question."""
    selected = []
    for topic_code, count in BLUEPRINT.items():
        topic = Topic.objects.filter(code=topic_code).first()
        if not topic:
            return render(request, "mocktest/intro.html", {
                "pass_mark": PASS_MARK, "duration": DURATION_SECONDS // 60,
                "error": f"Questions not yet imported for topic code {topic_code}. Run import_questions."
            })
        pool = list(Question.objects.filter(topic=topic).values_list("id", flat=True))
        if len(pool) < count:
            return render(request, "mocktest/intro.html", {
                "pass_mark": PASS_MARK, "duration": DURATION_SECONDS // 60,
                "error": f"Not enough questions for '{topic.name}'."
            })
        selected.extend(random.sample(pool, count))

    random.shuffle(selected)
    session = MockTestSession.objects.create(
        user=request.user,
        question_ids=selected,
        total_questions=len(selected),
    )
    return redirect("mocktest:question", session_id=session.id, index=0)


@login_required
def mock_question(request, session_id, index):
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)

    if session.submitted_at:
        return redirect("mocktest:result", session_id=session.id)

    ids = session.question_ids
    if index < 0 or index >= len(ids):
        return redirect("mocktest:question", session_id=session.id, index=0)

    question = get_object_or_404(Question, id=ids[index])
    response = MockTestResponse.objects.filter(mock_session=session, question=question).first()

    answered_ids = set(MockTestResponse.objects.filter(mock_session=session, selected_option__isnull=False).values_list("question_id", flat=True))
    flagged_ids = set(MockTestResponse.objects.filter(mock_session=session, flagged=True).values_list("question_id", flat=True))

    progress = []
    for i, qid in enumerate(ids):
        progress.append({
            "index": i,
            "answered": qid in answered_ids,
            "flagged": qid in flagged_ids,
            "current": i == index,
        })

    return render(request, "mocktest/question.html", {
        "session": session,
        "question": question,
        "options": question.options.all(),
        "index": index,
        "total": len(ids),
        "response": response,
        "has_prev": index > 0,
        "has_next": index < len(ids) - 1,
        "answered_count": len(answered_ids),
        "flagged_ids": list(flagged_ids),
        "progress": progress,
        "duration": DURATION_SECONDS,
    })


@require_POST
@login_required
def mock_save_answer(request, session_id, index):
    """AJAX: save selected option without submitting the test."""
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)
    if session.submitted_at:
        return JsonResponse({"ok": False, "reason": "already submitted"})

    ids = session.question_ids
    if index < 0 or index >= len(ids):
        return JsonResponse({"ok": False, "reason": "invalid index"})

    question = get_object_or_404(Question, id=ids[index])
    option_id = request.POST.get("option")
    selected = AnswerOption.objects.filter(id=option_id, question=question).first() if option_id else None

    obj, _ = MockTestResponse.objects.get_or_create(mock_session=session, question=question)
    old_option = obj.selected_option_id
    obj.selected_option = selected
    obj.save()

    if old_option and old_option != (selected.id if selected else None):
        MockTestQuestionEvent.objects.filter(mock_session=session, question=question).update(
            answer_changed_count=F("answer_changed_count") + 1
        )

    answered_count = MockTestResponse.objects.filter(mock_session=session, selected_option__isnull=False).count()
    return JsonResponse({"ok": True, "answered_count": answered_count})


@require_POST
@login_required
def mock_toggle_flag(request, session_id, index):
    """AJAX: toggle the flagged status for a question."""
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)
    if session.submitted_at:
        return JsonResponse({"ok": False})

    ids = session.question_ids
    question = get_object_or_404(Question, id=ids[index])
    obj, _ = MockTestResponse.objects.get_or_create(mock_session=session, question=question)
    obj.flagged = not obj.flagged
    obj.save()
    return JsonResponse({"ok": True, "flagged": obj.flagged})


@require_POST
@login_required
def mock_submit(request, session_id):
    session = get_object_or_404(MockTestSession, id=session_id, user=request.user)
    if session.submitted_at:
        return redirect("mocktest:result", session_id=session.id)

    correct = 0
    for order, qid in enumerate(session.question_ids):
        question = Question.objects.get(id=qid)
        resp = MockTestResponse.objects.filter(mock_session=session, question=question).first()
        selected = resp.selected_option if resp else None
        is_correct = bool(selected and selected.is_correct)
        if is_correct:
            correct += 1
        MockTestResponse.objects.update_or_create(
            mock_session=session, question=question,
            defaults={"selected_option": selected, "is_correct": is_correct},
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
    responses = (
        session.responses
        .select_related("question__topic", "selected_option")
        .prefetch_related("question__options")
        .order_by("id")
    )

    # Build ordered review with correct answer, selected, explanation
    review = []
    for order, qid in enumerate(session.question_ids):
        resp = next((r for r in responses if r.question_id == qid), None)
        question = resp.question if resp else Question.objects.prefetch_related("options").get(id=qid)
        correct_opt = question.options.filter(is_correct=True).first()
        review.append({
            "order": order + 1,
            "question": question,
            "options": list(question.options.all()),
            "selected": resp.selected_option if resp else None,
            "correct_option": correct_opt,
            "is_correct": resp.is_correct if resp else False,
            "flagged": resp.flagged if resp else False,
        })

    topic_stats = {}
    for item in review:
        name = item["question"].topic.name
        bucket = topic_stats.setdefault(name, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if item["is_correct"]:
            bucket["correct"] += 1

    incorrect_answers = max(session.total_questions - session.correct_answers, 0)

    return render(request, "mocktest/result.html", {
        "session": session,
        "review": review,
        "topic_stats": topic_stats,
        "pass_mark": PASS_MARK,
        "incorrect_answers": incorrect_answers,
    })

