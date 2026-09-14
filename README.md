# ITS Cinema

Web app di un cinema realizzata con Django, Bootstrap 5 e JavaScript vanilla.
I dati (film, spettacoli, prenotazioni) arrivano dall'API [its-cinema](https://its-cinema.vercel.app/api/doc).

## Requisiti

- Python 3.12 o superiore

## Avvio in locale (Windows / PowerShell)

```powershell
# 1. Crea il virtualenv (solo la prima volta)
python -m venv .venv

# 2. Attiva il virtualenv
.\.venv\Scripts\Activate.ps1

# 3. Installa le dipendenze (solo la prima volta o se cambia requirements.txt)
pip install -r requirements.txt

# 4. Crea il database SQLite (solo la prima volta)
python manage.py migrate

# 5. Avvia il server di sviluppo
python manage.py runserver
```

Poi apri <http://127.0.0.1:8000/> nel browser.

Se PowerShell blocca l'attivazione del virtualenv, esegui una volta:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Test

```powershell
python manage.py test
```
