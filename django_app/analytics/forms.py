from django import forms

from .models import Feedback


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["category", "rating", "message"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "rating": forms.RadioSelect(),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Tell us what you think…"}),
        }
