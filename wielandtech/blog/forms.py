from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and self.user.is_authenticated:
            self.fields['body'].widget.attrs.update({'placeholder': 'Write your comment here...'})
        else:
            self.fields['name'] = forms.CharField(max_length=80)
            self.fields['email'] = forms.EmailField()
            self.fields['body'].widget.attrs.update({'placeholder': 'Write your comment here...'})

    def save(self, commit=True):
        comment = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            comment.user = self.user
            comment.name = self.user.username
            comment.email = self.user.email
        if commit:
            comment.save()
        return comment


class EmailPostForm(forms.Form):
    name = forms.CharField(max_length=25)
    email = forms.EmailField()
    to = forms.EmailField()
    comments = forms.CharField(required=False, widget=forms.Textarea)


class SearchForm(forms.Form):
    query = forms.CharField()
