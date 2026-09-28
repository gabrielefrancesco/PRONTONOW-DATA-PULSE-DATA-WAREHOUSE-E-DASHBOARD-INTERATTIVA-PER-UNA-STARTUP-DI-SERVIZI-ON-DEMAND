prototipo_dw.py - Data warehouse a schema stella per una startup on-demand
Esecuzione:  python prototipo_dw_fixed.py        (richiede: pip install matplotlib)
Produce:     ondemand.db (archivio dati) + dashboard.png (grafici)
"""
import sqlite3
import random
import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

random.seed(42)  # risultati riproducibili
DB = "ondemand.db"

# ---------------------------------------------------------------------------
# 1. GENERAZIONE DATI SORGENTE (piccolo insieme realistico, nessun dato personale)
# ---------------------------------------------------------------------------
CITTA_AREA = {
    "Milano": "Nord", "Torino": "Nord", "Bergamo": "Nord", "Verona": "Nord",
    "Bologna": "Nord", "Roma": "Centro", "Firenze": "Centro", "Pisa": "Centro",
    "Perugia": "Centro", "Napoli": "Sud", "Bari": "Sud", "Salerno": "Sud",
    "Palermo": "Isole", "Catania": "Isole", "Cagliari": "Isole",
}
NOMI_CLIENTI = [
    ("Marco Rossi", "Milano"), ("Giulia Bianchi", "Roma"), ("Luca Ferrari", "Napoli"),
    ("Anna Esposito", "Palermo"), ("Francesco Romano", "Torino"), ("Sofia Greco", "Catania"),
    ("Alessandro Conti", "Bergamo"), ("Martina Russo", "Bari"), ("Giovanni Colombo", "Firenze"),
    ("Chiara Moretti", "Cagliari"), ("Davide Barbieri", "Verona"), ("Elena Marini", "Salerno"),
    ("Stefano Lombardi", "Bologna"), ("Francesca Costa", "Perugia"), ("Matteo Galli", "Milano"),
    ("Valentina Fontana", "Roma"), ("Andrea Marchetti", "Napoli"), ("Sara De Luca", "Palermo"),
    ("Federico Santoro", "Torino"), ("Roberta Ferri", "Catania"), ("Simone Rinaldi", "Bergamo"),
    ("Alice Monti", "Bari"), ("Paolo Ferrari", "Firenze"), ("Beatrice Caputo", "Cagliari"),
    ("Diego Morelli", "Verona"),
]
OPERATORI = [
    ("Luca Marchetti", "Nord", "expert"), ("Elena Pozzi", "Nord", "senior"),
    ("Marco Bellini", "Centro", "senior"), ("Giulia Santoro", "Centro", "junior"),
    ("Davide Greco", "Sud", "expert"), ("Anna Romano", "Sud", "senior"),
    ("Stefano Costa", "Isole", "junior"), ("Chiara Greco", "Isole", "senior"),
]
FORNITORI = [
    ("Pulizie Express", "Pulizie", "Milano"), ("Sparkle Clean", "Pulizie", "Roma"),
    ("Elettro Pronto", "Riparazione elettrica", "Torino"), ("Volt Service", "Riparazione elettrica", "Napoli"),
    ("Idraulica 24", "Idraulico", "Bologna"), ("Tubi e Affini", "Idraulico", "Palermo"),
    ("FastDelivery", "Consegna", "Bergamo"), ("QuickPost", "Consegna", "Firenze"),
    ("TechAssist", "Assistenza informatica", "Verona"), ("PC SOS", "Assistenza informatica", "Catania"),
    ("MontaBene", "Montaggio mobili", "Bari"), ("GreenGarden", "Giardinaggio", "Cagliari"),
]
# durata del servizio in minuti, per categoria: (minimo, massimo)
CAT_MINUTI = {
    "Pulizie": (60, 120), "Riparazione elettrica": (45, 90), "Idraulico": (30, 120),
    "Consegna": (15, 45), "Assistenza informatica": (30, 90),
    "Montaggio mobili": (60, 180), "Giardinaggio": (45, 150),
}
MESI = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
GIORNI = ["Lunedi", "Martedi", "Mercoledi", "Giovedi", "Venerdi", "Sabato", "Domenica"]


def genera_dati():
    """Restituisce i quattro dataset sorgente pronti per il caricamento."""
    clienti = [(i + 1, n, c, CITTA_AREA[c]) for i, (n, c) in enumerate(NOMI_CLIENTI)]
    operatori = [(i + 1, o[0], o[1], o[2]) for i, o in enumerate(OPERATORI)]
    fornitori = [(i + 1, f[0], f[1], f[2]) for i, f in enumerate(FORNITORI)]
    # 150 richieste: 10 clienti "nuovi" con 1 richiesta, 15 "ricorrenti" con piu richieste
    per_cliente = [1] * 10 + [4, 5, 6, 7, 7, 8, 9, 9, 10, 10, 11, 11, 12, 13, 18]
    inizio = datetime.date(2026, 1, 1)
    richieste = []
    for cl in clienti:
        for _ in range(per_cliente[cl[0] - 1]):
            # scegli un operatore assegnato all'area del cliente
            possibili_op = [o for o in operatori if o[2] == cl[3]]
            if not possibili_op:
                op = random.choice(operatori)
            else:
                op = random.choice(possibili_op)
            fo = random.choice(fornitori)
            lo, hi = CAT_MINUTI.get(fo[2], (30, 60))
            durata = random.randint(lo, hi)
            importo = round(durata * random.uniform(0.9, 1.5) + random.uniform(10, 30), 2)
            data = inizio + datetime.timedelta(days=random.randint(0, 178))
            stato = "annullata" if random.random() < 0.10 else "completata"
            richieste.append((cl[0], op[0], fo[0], data.isoformat(), durata, importo, stato))
    return clienti, operatori, fornitori, richieste


# ---------------------------------------------------------------------------
# 2. CREAZIONE DATABASE: sorgenti operative + data warehouse a schema stella
# ---------------------------------------------------------------------------
def crea_database(clienti, operatori, fornitori, richieste):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS richieste; DROP TABLE IF EXISTS clienti;
    DROP TABLE IF EXISTS operatori; DROP TABLE IF EXISTS fornitori;
    DROP TABLE IF EXISTS dim_data; DROP TABLE IF EXISTS dim_cliente;
    DROP TABLE IF EXISTS dim_operatore; DROP TABLE IF EXISTS dim_fornitore;
    DROP TABLE IF EXISTS fatto_richiesta;
    -- tabelle operative (sorgenti)
    CREATE TABLE clienti (id INTEGER PRIMARY KEY, nome TEXT, citta TEXT, area_geografica TEXT);
    CREATE TABLE operatori (id INTEGER PRIMARY KEY, nome TEXT, area_assegnata TEXT, livello TEXT);
    CREATE TABLE fornitori (id INTEGER PRIMARY KEY, nome TEXT, categoria TEXT, citta TEXT);
    CREATE TABLE richieste (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER, operatore_id INTEGER, fornitore_id INTEGER,
        data_richiesta TEXT, durata_minuti INTEGER, importo REAL, stato TEXT);
    -- data warehouse: tabella dei fatti al centro, dimensioni intorno (schema a stella)
    CREATE TABLE dim_data (data_id TEXT PRIMARY KEY, anno INTEGER, mese INTEGER,
        mese_nome TEXT, trimestre INTEGER, giorno_settimana TEXT);
    CREATE TABLE dim_cliente (cliente_id INTEGER PRIMARY KEY, nome TEXT,
        area_geografica TEXT, citta TEXT, segmento TEXT);
    CREATE TABLE dim_operatore (operatore_id INTEGER PRIMARY KEY, nome TEXT,
        area_assegnata TEXT, livello TEXT);
    CREATE TABLE dim_fornitore (fornitore_id INTEGER PRIMARY KEY, nome TEXT,
        categoria TEXT, citta TEXT);
    CREATE TABLE fatto_richiesta (
        data_id TEXT, cliente_id INTEGER, operatore_id INTEGER, fornitore_id INTEGER,
        durata_minuti INTEGER, importo REAL, conteggio INTEGER, stato TEXT);
    """)
    cur.executemany("INSERT INTO clienti VALUES (?,?,?,?)", clienti)
    cur.executemany("INSERT INTO operatori VALUES (?,?,?,?)", operatori)
    cur.executemany("INSERT INTO fornitori VALUES (?,?,?,?)", fornitori)
    cur.executemany(
        "INSERT INTO richieste (cliente_id, operatore_id, fornitore_id, "
        "data_richiesta, durata_minuti, importo, stato) VALUES (?,?,?,?,?,?,?)",
        richieste)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# 3. ETL: Estrazione -> Trasformazione -> Caricamento
# ---------------------------------------------------------------------------
def etl(conn):
    cur = conn.cursor()

    # E - Estrazione dalle sorgenti operative
    clienti = cur.execute("SELECT id, nome, citta, area_geografica FROM clienti").fetchall()
    operatori = cur.execute("SELECT id, nome, area_assegnata, livello FROM operatori").fetchall()
    fornitori = cur.execute("SELECT id, nome, categoria, citta FROM fornitori").fetchall()
    richieste = cur.execute(
        "SELECT cliente_id, operatore_id, fornitore_id, data_richiesta, "
        "durata_minuti, importo, stato FROM richieste").fetchall()

    # T - Trasformazione
    dim_data = {}
    for r in richieste:
        data_iso = r[3]
        if data_iso not in dim_data:
            d = datetime.date.fromisoformat(data_iso)
            dim_data[data_iso] = (data_iso, d.year, d.month, MESI[d.month - 1],
                                  (d.month - 1) // 3 + 1, GIORNI[d.weekday()])
    n_richieste_cliente = {}
    for r in richieste:
        n_richieste_cliente[r[0]] = n_richieste_cliente.get(r[0], 0) + 1
    dim_cliente = [(c[0], c[1], c[3], c[2],
                    "ricorrente" if n_richieste_cliente.get(c[0], 0) > 1 else "nuovo")
                   for c in clienti]
    fatti = [(r[3], r[0], r[1], r[2], r[4], r[5], 1, r[6]) for r in richieste]

    # L - Caricamento nel data warehouse
    cur.executemany("INSERT OR REPLACE INTO dim_data VALUES (?,?,?,?,?,?)", list(dim_data.values()))
    cur.executemany("INSERT OR REPLACE INTO dim_cliente VALUES (?,?,?,?,?)", dim_cliente)
    cur.executemany("INSERT OR REPLACE INTO dim_operatore VALUES (?,?,?,?)", operatori)
    cur.executemany("INSERT OR REPLACE INTO dim_fornitore VALUES (?,?,?,?)", fornitori)
    cur.executemany("INSERT INTO fatto_richiesta VALUES (?,?,?,?,?,?,?,?)", fatti)
    conn.commit()
    print("ETL completato: {} fatti, {} clienti, {} date, {} operatori, {} fornitori".format(
        len(fatti), len(dim_cliente), len(dim_data), len(operatori), len(fornitori)))


# ---------------------------------------------------------------------------
# 4. DASHBOARD: KPI e grafici (aggregazioni con join fatti <-> dimensioni)
# ---------------------------------------------------------------------------
def dashboard(conn):
    cur = conn.cursor()

    totale_richieste = cur.execute("SELECT SUM(conteggio) FROM fatto_richiesta").fetchone()[0]
    tempo_medio = cur.execute(
        "SELECT AVG(durata_minuti) FROM fatto_richiesta WHERE stato = 'completata'").fetchone()[0]
    incassi = cur.execute(
        "SELECT SUM(importo) FROM fatto_richiesta WHERE stato = 'completata'").fetchone()[0]
    ricorrenti = cur.execute(
        "SELECT COUNT(*) FROM dim_cliente WHERE segmento = 'ricorrente'").fetchone()[0]
    totale_clienti = cur.execute("SELECT COUNT(*) FROM dim_cliente").fetchone()[0]

    # protezioni contro valori None
    totale_richieste = int(totale_richieste or 0)
    tempo_medio = float(tempo_medio) if tempo_medio is not None else 0.0
    incassi = float(incassi or 0.0)
    totale_clienti = int(totale_clienti or 0)
    ricorrenti = int(ricorrenti or 0)

    print()
    print("=== INDICATORI PRINCIPALI ===")
    print("Richieste gestite:        {}".format(totale_richieste))
    print("Tempo medio erogazione:  {:.0f} minuti".format(tempo_medio))
    print("Incassi totali:          {:.2f} EUR".format(incassi))
    if totale_clienti > 0:
        print("Tasso clienti ricorrenti: {:.0%}".format(ricorrenti / totale_clienti))
    else:
        print("Tasso clienti ricorrenti: N/A (nessun cliente)")

    area = cur.execute("""
        SELECT dc.area_geografica, SUM(f.importo)
        FROM fatto_richiesta f JOIN dim_cliente dc ON f.cliente_id = dc.cliente_id
        WHERE f.stato = 'completata'
        GROUP BY dc.area_geografica ORDER BY 2 DESC""").fetchall()
    mesi = cur.execute("""
        SELECT dd.mese, dd.mese_nome, SUM(f.conteggio)
        FROM fatto_richiesta f JOIN dim_data dd ON f.data_id = dd.data_id
        GROUP BY dd.mese, dd.mese_nome ORDER BY dd.mese""").fetchall()
    categorie = cur.execute("""
        SELECT df.categoria, SUM(f.importo)
        FROM fatto_richiesta f JOIN dim_fornitore df ON f.fornitore_id = df.fornitore_id
        WHERE f.stato = 'completata'
        GROUP BY df.categoria ORDER BY 2 DESC""").fetchall()
    segmenti = cur.execute(
        "SELECT segmento, COUNT(*) FROM dim_cliente GROUP BY segmento").fetchall()

    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Dashboard - Data warehouse OnDemand")

    # Incassi per area geografica
    aree = [r[0] for r in area]
    incassi_area = [r[1] or 0 for r in area]
    ax[0, 0].bar(aree, incassi_area, color="#6366f1")
    ax[0, 0].set_title("Incassi per area geografica (EUR)")
    ax[0, 0].tick_params(axis='x', rotation=10)

    # Richieste per mese (x = mese numerico, etichetta = nome mese)
    mesi_nums = [r[0] for r in mesi]
    mesi_count = [r[2] for r in mesi]
    ax[0, 1].plot(mesi_nums, mesi_count, marker="o", color="#10b981")
    ax[0, 1].set_xticks(mesi_nums)
    ax[0, 1].set_xticklabels([r[1] for r in mesi], rotation=45)
    ax[0, 1].set_title("Richieste per mese")
    ax[0, 1].set_xlabel("Mese")

    # Incassi per categoria
    nomi = [r[0] for r in categorie]
    valori = [r[1] or 0 for r in categorie]
    ax[1, 0].barh(nomi[::-1], valori[::-1], color="#8b5cf6")
    ax[1, 0].set_title("Incassi per categoria (EUR)")

    # Clienti nuovi vs ricorrenti
    seg_labels = [r[0] for r in segmenti]
    seg_values = [r[1] for r in segmenti]
    if sum(seg_values) == 0:
        seg_values = [1]  # evita errore pie con somma 0
        seg_labels = ["Nessun cliente"]
    ax[1, 1].pie(seg_values, labels=seg_labels, colors=["#6366f1", "#f59e0b"][:len(seg_values)],
                 autopct="%1.0f%%")
    ax[1, 1].set_title("Clienti nuovi vs ricorrenti")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig("dashboard.png", dpi=150)
    print()
    print("Grafici salvati in dashboard.png")


if _name_ == "_main_":
    clienti, operatori, fornitori, richieste = genera_dati()
    conn = crea_database(clienti, operatori, fornitori, richieste)
    etl(conn)
    dashboard(conn)
    conn.close()
    print("Prototipo completato.")
