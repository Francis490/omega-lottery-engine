# 🧠 Omega Engine

Bot automatico per l'analisi statistica, il calcolo dell'Expected Value (EV) e la generazione di numeri per **Eurojackpot**, **Superenalotto** e **Super Win for Life**.

## ⚙️ Come funziona
1. **Scraping & Fetching**: Scarica le ultime estrazioni e i montepremi aggiornati dai siti ufficiali.
2. **Database (SQLite)**: Salva lo storico in `omega.db` e mantiene i file CSV sincronizzati per la consultazione.
3. **Hacker Mode**: Calcola lo Z-Score di ogni numero per individuare anomalie statistiche (numeri "rotti" o statisticamente deviati).
4. **Modalità Caos (20%)**: Per evitare bias cognitivi, il 20% delle generazioni ignora i filtri logici e gioca numeri totalmente casuali.
5. **Invio Telegram**: Invia i risultati calcolati con tanto di EV (Expected Value) su Telegram.
6. **PWA**: Aggiorna la dashboard (`docs/latest.json`) per la visualizzazione lato utente.

## 🧬 Architettura
- `main.py`: Entry point, orchestratore e invio messaggi Telegram.
- `fetcher.py`: Modulo di scraping e fetch dei dati.
- `omega_brain.py`: Cuore del bot (Z-Score, filtri, generazione sestine e EV).
- `jackpot_fetcher.py`: Recupero e parsing dei jackpot correnti.
- `database.py`: Gestione del DB SQLite con logica `UPSERT` per la correzione dei dati.
- `hack_the_system.py`: Analisi profonda (Chi-Quadro, Z-Score) dello storico completo.
- `report_generator.py`: Report testuale delle frequenze e dei ritardi.
- `export_csv.py`: Esportazione dal DB ai CSV.
- `test_smoke.py`: Test automatici eseguiti in CI prima del deploy.

## 🚀 Automazione
Il bot gira da solo ogni giorno alle **08:00 (Europe/Rome)** grazie a **GitHub Actions** (`omega.yml`). Il workflow:
- Scarica il DB e i CSV precedenti.
- Esegue il bot e i test (se i test falliscono, il DB non viene pubblicato).
- Aggiorna i file ed effettua il commit per la PWA.

## 🛠️ Tecnologie
Python 3.10+, SQLite, GitHub Actions, HTML/JS (PWA), Pydantic (validazione dati), SciPy (analisi statistica), BeautifulSoup (scraping).

## ⚠️ Disclaimer
Questo bot è un progetto a scopo puramente statistico e informativo. Il gioco d'azzardo è vietato ai minori e può causare dipendenza. Gioca responsabilmente.
