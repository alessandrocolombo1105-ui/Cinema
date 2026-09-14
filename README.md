# ITS Cinema

Web app di un cinema realizzata con Django, Bootstrap 5 e JavaScript vanilla.
I dati (film, spettacoli, prenotazioni) arrivano dall'API [its-cinema](https://its-cinema.vercel.app/api/doc).

## Funzionalità

- **Programmazione** (`/`): elenco dei film in programmazione (`GET /films`), ognuno con il pulsante "Scopri di più".
- **Dettaglio film** (`/film/?id=<id>`): titolo, anno, durata, regista, genere e trama (`GET /films/{id}`)
  e i prossimi spettacoli raggruppati per giorno, con orario, sala e posti disponibili (`GET /films/{id}/screenings`).
- **Prenotazione** (`/prenota/<id spettacolo>/`): riepilogo dello spettacolo e form con Nome, Cognome ed Email
  (`POST /screenings/{id}/bookings`), con validazione lato browser e lato server.
- **Conferma** (`/prenota/conferma/`): codice e riepilogo della prenotazione appena effettuata.

L'interfaccia è responsive e gestisce gli errori dell'API (film o spettacolo inesistente, posti esauriti,
dati non validi, servizio non raggiungibile) mostrando messaggi comprensibili all'utente.

## Struttura

```
config/                 impostazioni e URL del progetto Django
cinema/
  services.py           client dell'API esterna
  views.py              viste delle pagine
  forms.py              form di prenotazione
  templatetags/         filtri per i template (es. durata "2 h 46 min")
  templates/cinema/     template delle pagine
  tests.py              test automatici (l'API è simulata)
templates/              layout base e pagina 404
static/                 CSS, JavaScript e immagini
```

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

## Configurazione

| Variabile              | Default                  | Descrizione                                   |
| ---------------------- | ------------------------ | --------------------------------------------- |
| `DJANGO_SECRET_KEY`    | chiave di sviluppo       | Chiave segreta, obbligatoria in produzione    |
| `DJANGO_DEBUG`         | `1`                      | `0` per disattivare la modalità debug         |
| `DJANGO_ALLOWED_HOSTS` | vuoto                    | Host consentiti, separati da virgola          |

Con `DJANGO_DEBUG=1` sono sempre consentiti `127.0.0.1` e `localhost`.
La pagina 404 personalizzata è visibile solo con il debug disattivato, ad esempio:

```powershell
$env:DJANGO_DEBUG = "0"; $env:DJANGO_ALLOWED_HOSTS = "127.0.0.1"
python manage.py collectstatic --noinput
python manage.py runserver --insecure
```

## Test

```powershell
python manage.py test
```
