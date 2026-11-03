# users/forms.py
from django import forms
from .models import Employee, User
from django.contrib.auth.password_validation import validate_password

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'cuit_dni', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. Juan'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. Pérez'}),
            'cuit_dni': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. 20384958674'}),
            'email': forms.EmailInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'correo@ejemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. +5491123456789'}),
        }

        
class UserAccessForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_deleted=False),
        required=False,
        label='Empleado Asociado',
        empty_label='-- Sin empleado vinculado --',
        widget=forms.Select(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Dejar en blanco para mantener la contraseña actual'
        }),
        required=False,
        label='Contraseña'
    )

    class Meta:
        model = User
        fields = ['username', 'employee', 'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: jperez'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500'}),
        }
        labels = {
            'username': 'Nombre de Usuario',
            'is_active': 'Cuenta Activa (Permitir ingreso)',
            'is_staff': 'Es Staff (Requiere 2FA)',
            'is_superuser': 'Superusuario',
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user