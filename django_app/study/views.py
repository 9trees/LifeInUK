from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from content.models import StudyPage, Topic

from .models import UserStudyProgress


@login_required
def study_plan_view(request):
    return render(request, "study/plan.html", {})


@login_required
def study_index(request):
    topics = Topic.objects.prefetch_related("pages").all()
    progress = {
        p.study_page_id: p
        for p in UserStudyProgress.objects.filter(user=request.user)
    }

    topic_blocks = []
    for topic in topics:
        pages = []
        for page in topic.pages.all():
            prog = progress.get(page.id)
            pages.append({"page": page, "status": prog.status if prog else "not_started"})
        completed = sum(1 for p in pages if p["status"] == "completed")
        total = len(pages)
        topic_blocks.append({
            "topic": topic,
            "pages": pages,
            "completed": completed,
            "total": total,
            "percent": round((completed / total) * 100) if total else 0,
        })

    last = (
        UserStudyProgress.objects.filter(user=request.user)
        .order_by("-last_viewed_at")
        .first()
    )
    return render(request, "study/index.html", {"topics": topic_blocks, "last": last})


@login_required
def study_page_view(request, slug):
    topic_code, _, seq = slug.partition("_")
    page = get_object_or_404(StudyPage, topic__code=int(topic_code), sequence_no=int(seq))

    progress, _ = UserStudyProgress.objects.get_or_create(user=request.user, study_page=page)
    progress.visits += 1
    progress.last_viewed_at = timezone.now()
    if progress.status == UserStudyProgress.NOT_STARTED:
        progress.status = UserStudyProgress.IN_PROGRESS
    progress.save()

    prev_page = (
        StudyPage.objects.filter(
            models.Q(topic__code__lt=page.topic.code)
            | models.Q(topic__code=page.topic.code, sequence_no__lt=page.sequence_no)
        ).order_by("-topic__code", "-sequence_no").first()
    )
    next_page = (
        StudyPage.objects.filter(
            models.Q(topic__code__gt=page.topic.code)
            | models.Q(topic__code=page.topic.code, sequence_no__gt=page.sequence_no)
        ).order_by("topic__code", "sequence_no").first()
    )

    return render(request, "study/page.html", {
        "page": page,
        "progress": progress,
        "prev_page": prev_page,
        "next_page": next_page,
    })


@require_POST
@login_required
def complete_page(request, slug):
    topic_code, _, seq = slug.partition("_")
    page = get_object_or_404(StudyPage, topic__code=int(topic_code), sequence_no=int(seq))
    progress, _ = UserStudyProgress.objects.get_or_create(user=request.user, study_page=page)
    progress.status = UserStudyProgress.COMPLETED
    progress.completed_at = timezone.now()
    seconds = int(request.POST.get("seconds", 0) or 0)
    progress.time_spent_seconds += max(0, seconds)
    progress.save()
    return redirect("study:page", slug=slug)
