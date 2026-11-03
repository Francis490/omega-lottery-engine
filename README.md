# 🧠 Omega Engine

Bot automatico per l'analisi statistica e la generazione di numeri per Eurojackpot, Superenalotto e Super Win for Life.

## ⚙️ Come funziona
1. Scarica le ultime estrazioni dai siti ufficiali.
2. Salva lo storico in un database SQLite (`omega.db`).
3. Calcola i numeri basandosi su frequenze (caldi/freddi).
4. Invia i risultati su Telegram.
5. Aggiorna la PWA (`index.html`) tramite il file `docs/latest.json`.

## 🚀 Automazione
Il bot gira da solo ogni giorno grazie a **GitHub Actions** (workflow `omega.yml`).

## 🛠️ Tecnologie
Python, SQLite, GitHub Actions, HTML/JS (PWA).
