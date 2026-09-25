# Messaggi anonimi

Piccola web app per gruppi: ogni partecipante scrive un messaggio; l'organizzatore chiude il gruppo e il sistema assegna casualmente ogni messaggio a una persona diversa dall'autore.

## Come funziona
1. L'organizzatore crea il gruppo.
2. Condivide il link del gruppo.
3. Ogni partecipante inserisce nome + messaggio e salva il proprio link personale.
4. L'organizzatore vede chi ha partecipato e preme **Chiudi e fai il sorteggio**.
5. Ogni partecipante riapre il proprio link e vede un solo messaggio anonimo.

Il nome dell'autore non viene mostrato al destinatario. L'area organizzatore mostra i nomi dei partecipanti, ma non i loro messaggi.

## Avvio sul computer
Richiede Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Apri `http://127.0.0.1:5000`.

## Pubblicazione online con Render
1. Carica questa cartella in un repository GitHub.
2. Su Render crea un nuovo **Blueprint** collegando il repository.
3. Render leggerà `render.yaml` e creerà il servizio con disco persistente.
4. Apri l'indirizzo HTTPS fornito da Render.

Nota: il piano/disco disponibile su Render può cambiare; verifica le condizioni correnti prima della pubblicazione.

## Privacy
Questa è una piccola app, non un sistema di anonimato forte. Il server conserva nome e messaggio nello stesso database. Per gruppi informali va bene; per dati sensibili servirebbero autenticazione, cifratura e una policy di cancellazione.
