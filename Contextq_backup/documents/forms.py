from django import forms
from .models import Document

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']

class AskQuestionForm(forms.Form):
    question = forms.CharField(widget=forms.Textarea, label='Ask a question about the document')
    
    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('document', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        if not self.document:
            raise forms.ValidationError("Document is required to ask a question.")
        return cleaned_data