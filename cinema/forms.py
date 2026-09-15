from django import forms


class BookingForm(forms.Form):
    first_name = forms.CharField(
        label='Nome', max_length=100, widget=forms.TextInput(attrs={'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        label='Cognome', max_length=100, widget=forms.TextInput(attrs={'autocomplete': 'family-name'})
    )
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def add_error(self, field, error):
        super().add_error(field, error)
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs['class'] = 'form-control is-invalid'
