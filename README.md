# ITS Cinema

Web app di un cinema realizzata con Django, Bootstrap 5 e JavaScript vanilla.
I dati (film, spettacoli, prenotazioni) arrivano dall'API [its-cinema](https://its-cinema.vercel.app/api/doc).

## Cosa fa il programma

Il sito permette di consultare la programmazione del cinema e di prenotare un posto per uno spettacolo.
Il percorso dell'utente è: **programmazione → dettaglio del film → prenotazione → conferma**.

### 1. Programmazione (homepage)

Indirizzo: `/` · API usata: `GET /films`

- Mostra tutti i film in programmazione in una griglia di schede.
- Ogni scheda riporta locandina, genere, divieto di visione (es. `T`, `VM14`), anno, durata, regista
  e un estratto della trama.
- La durata è mostrata in ore e minuti (es. "2 h 46 min").
- Ogni scheda ha il pulsante **"Scopri di più"**, che apre il dettaglio del film.

### 2. Dettaglio del film

Indirizzo: `/film/?id=<id del film>` · API usate: `GET /films/{id}` e `GET /films/{id}/screenings`

- Mostra le informazioni complete del film: titolo, anno, durata, regista, genere, divieto e trama.
- Elenca i **prossimi spettacoli**:
  - solo quelli non ancora iniziati, in ordine cronologico;
  - raggruppati per giorno (es. "Domenica 11 Ottobre 2026");
  - con orario (convertito nel fuso orario italiano), sala e posti disponibili sulla capienza totale.
- Ogni spettacolo ha un'etichetta di disponibilità:
  - **Disponibile**;
  - **Ultimi posti**, quando resta libero il 10% della capienza o meno;
  - **Esaurito**, quando non ci sono più posti.
- Gli spettacoli con posti liberi hanno il pulsante **"Prenota"**; quelli esauriti no.
- Se il film non ha spettacoli in programma viene mostrato un avviso.

### 3. Prenotazione

Indirizzo: `/prenota/<id dello spettacolo>/` · API usate: `GET /screenings/{id}` e `POST /screenings/{id}/bookings`

- Mostra il riepilogo dello spettacolo scelto: film, data, orario, sala e posti disponibili.
- Chiede **Nome, Cognome ed Email** e invia la prenotazione all'API.
- I dati vengono controllati due volte:
  - **nel browser**, prima dell'invio: i campi mancanti o l'email non valida vengono evidenziati in rosso;
  - **sul server**, prima di chiamare l'API.
- Gli errori restituiti dall'API (es. "Formato email non valido", "Nessun posto disponibile")
  vengono mostrati accanto al campo interessato o in cima al form.
- Dopo il clic su "Conferma prenotazione" il pulsante si disattiva, così la prenotazione non può essere
  inviata due volte.
- Uno spettacolo esaurito o già iniziato non è prenotabile: il form non viene mostrato.

### 4. Conferma della prenotazione

Indirizzo: `/prenota/conferma/`

- Mostra il **codice della prenotazione** e il riepilogo: film, data, orario, sala, intestatario ed email.
- Ricaricare la pagina non crea una seconda prenotazione.
- Se la pagina viene aperta senza aver prenotato, l'utente viene riportato alla programmazione.

### Aspetti generali

- **Responsive**: il layout, basato su Bootstrap 5, si adatta a smartphone, tablet e desktop
  (su schermi piccoli il menu diventa a scomparsa e le schede si dispongono in colonna).
- **Gestione degli errori**:
  - se l'API non è raggiungibile, le pagine mostrano un messaggio invece di bloccarsi;
  - un film o uno spettacolo inesistente, o un indirizzo non valido, portano alla pagina "Pagina non trovata";
  - se una locandina non si carica, al suo posto compare un'icona.
- **Test automatici**: le funzionalità sono coperte da test che simulano l'API, quindi si possono eseguire
  anche senza connessione.

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
