from django import forms


class FacePhotoForm(forms.Form):
    """
    A plain Form, not a ModelForm -- FaceProfile intentionally has no
    ImageField (see its docstring: only the derived embedding is stored,
    never the photo). This field exists solely to get bytes from the
    browser into the view; the uploaded file is read, sent to the face
    engine, and discarded -- never saved to disk or the database.
    """

    photo = forms.ImageField(label="Photo")
