"""
prototipo_dw.py - Data warehouse a schema stella per una startup on-demand.

Esecuzione:
    python prototipo_dw.py

Dipendenza:
    matplotlib

Produce:
    ondemand.db  - database SQLite ricreato a ogni esecuzione
    dashboard.png - dashboard con quattro grafici
"""

from __future__ import annotations

import datetime as dt
import random
import sqlite3
from pathlib import Path


DB_PATH = Path("ondemand.db")
DASHBOARD_PATH = Path("dashboard.png")
SEED = 42


CITTA_AREA = {
    "Milano": "Nord",
    "Torino": "Nord",
    "Bergamo": "Nord",
    "Verona": "Nord",
    "Bologna": "Nord",
    "Roma": "Centro",
    "Firenze": "Centro",
    "Pisa": "Centro",
    "Perugia": "Centro",
    "Napoli": "Sud",
    "Bari": "Sud",
    "Salerno": "Sud",
    "Palermo": "Isole",
    "Catania": "Isole",
    "Cagliari": "Isole",
}


NOMI_CLIENTI = [
    ("Marco Rossi", "Milano"),
    ("Giulia Bianchi", "Roma"),
    ("Luca Ferrari", "Napoli"),
    ("Anna Esposito", "Palermo"),
    ("Francesco Romano", "Torino"),
    ("Sofia Greco", "Catania"),
    ("Alessandro Conti", "Bergamo"),
    ("Martina Russo", "Bari"),
    ("Giovanni Colombo", "Firenze"),
    ("Chiara Moretti", "Cagliari"),
    ("Davide Barbieri", "Verona"),
    ("Elena Marini", "Salerno"),
    ("Stefano Lombardi", "Bologna"),
    ("Francesca Costa", "Perugia"),
    ("Matteo Galli", "Milano"),
    ("Valentina Fontana", "Roma"),
    ("Andrea Marchetti", "Napoli"),
    ("Sara De Luca", "Palermo"),
    ("Federico Santoro", "Torino"),
    ("Roberta Ferri", "Catania"),
    ("Simone Rinaldi", "Bergamo"),
    ("Alice Monti", "Bari"),
    ("Paolo Ferrari", "Firenze"),
    ("Beatrice Caputo", "Cagliari"),
    ("Diego Morelli", "Verona"),
]


OPERATORI = [
    ("Luca Marchetti", "Nord", "expert"),
    ("Elena Pozzi", "Nord", "senior"),
    ("Marco Bellini", "Centro", "senior"),
    ("Giulia Santoro", "Centro", "junior"),
    ("Davide Greco", "Sud", "expert"),
    ("Anna Romano", "Sud", "senior"),
    ("Stefano Costa", "Isole", "junior"),
    ("Chiara Greco", "Isole", "senior"),
]


FORNITORI = [
    ("Pulizie Express", "Pulizie", "Milano"),
    ("Sparkle Clean", "Pulizie", "Roma"),
    ("Elettro Pronto", "Riparazione elettrica", "Torino"),
    ("Volt Service", "Riparazione elettrica", "Napoli"),
    ("Idraulica 24", "Idraulico", "Bologna"),
    ("Tubi e Affini", "Idraulico", "Palermo"),
    ("FastDelivery", "Consegna", "Bergamo"),
    ("QuickPost", "Consegna", "Firenze"),
    ("TechAssist", "Assistenza informatica", "Verona"),
    ("PC SOS", "Assistenza informatica", "Catania"),
    ("MontaBene", "Montaggio mobili", "Bari"),
    ("GreenGarden", "Giardinaggio", "Cagliari"),
]


CAT_MINUTI = {
    "Pulizie": (60, 120),
    "Riparazione elettrica": (45, 90),
    "Idraulico": (30, 120),
    "Consegna": (15, 45),
    "Assistenza informatica": (30, 90),
    "Montaggio mobili": (60, 180),
    "Giardinaggio": (45, 150),
}


MESI = [
    "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic"
]

GIORNI = [
    "Lunedi",
    "Martedi",
    "Mercoledi",
    "Giovedi",
    "Venerdi",
    "Sabato",
    "Domenica",
]


def genera_dati():
    """
    Genera quattro dataset sorgente deterministici:
    clienti, operatori, fornitori e richieste.
    """

    rng = random.Random(SEED)

    clienti = [
        (i + 1, nome, citta, CITTA_AREA[citta])
        for i, (nome, citta) in enumerate(NOMI_CLIENTI)
    ]

    operatori = [
        (i + 1, nome, area, livello)
        for i, (nome, area, livello) in enumerate(OPERATORI)
    ]

    fornitori = [
        (i + 1, nome, categoria, citta)
        for i, (nome, categoria, citta) in enumerate(FORNITORI)
    ]

    # 150 richieste:
    # 10 clienti nuovi con una richiesta ciascuno
    # 15 clienti ricorrenti con più richieste
    per_cliente = [
        1
    ] * 10 + [
        4, 5, 6, 7, 7, 8, 9, 9, 10, 10, 11, 11, 12, 13, 18
    ]

    assert sum(per_cliente) == 150

    data_inizio = dt.date(2026, 1, 1)
    richieste = []

    for cliente in clienti:
        cliente_id = cliente[0]
        area_cliente = cliente[3]

        for _ in range(per_cliente[cliente_id - 1]):

            operatori_possibili = [
                operatore
                for operatore in operatori
                if operatore[2] == area_cliente
            ]

            operatore = rng.choice(operatori_possibili or operatori)
            fornitore = rng.choice(fornitori)

            categoria_fornitore = fornitore[2]
            minimo, massimo = CAT_MINUTI[categoria_fornitore]

            durata = rng.randint(minimo, massimo)

            importo = round(
                durata * rng.uniform(0.9, 1.5)
                + rng.uniform(10, 30),
                2
            )

            data_richiesta = data_inizio + dt.timedelta(
                days=rng.randint(0, 178)
            )

            stato = (
                "annullata"
                if rng.random() < 0.10
                else "completata"
            )

            richieste.append(
                (
                    cliente_id,
                    operatore[0],
                    fornitore[0],
                    data_richiesta.isoformat(),
                    durata,
                    importo,
                    stato,
                )
            )

    return clienti, operatori, fornitori, richieste


def crea_database(clienti, operatori, fornitori, richieste):
    """
    Crea le tabelle operative e le tabelle del data warehouse.
    Il database viene ricreato a ogni esecuzione.
    """

    conn = sqlite3.connect(DB_PATH)

    # Attivazione dei vincoli di integrità referenziale in SQLite
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        """
        DROP TABLE IF EXISTS fatto_richiesta;
        DROP TABLE IF EXISTS dim_data;
        DROP TABLE IF EXISTS dim_cliente;
        DROP TABLE IF EXISTS dim_operatore;
        DROP TABLE IF EXISTS dim_fornitore;

        DROP TABLE IF EXISTS richieste;
        DROP TABLE IF EXISTS clienti;
        DROP TABLE IF EXISTS operatori;
        DROP TABLE IF EXISTS fornitori;


        -- TABELLE OPERATIVE DI SORGENTE

        CREATE TABLE clienti (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            citta TEXT NOT NULL,
            area_geografica TEXT NOT NULL
        );

        CREATE TABLE operatori (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            area_assegnata TEXT NOT NULL,
            livello TEXT NOT NULL
        );

        CREATE TABLE fornitori (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            citta TEXT NOT NULL
        );

        CREATE TABLE richieste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            operatore_id INTEGER NOT NULL,
            fornitore_id INTEGER NOT NULL,
            data_richiesta TEXT NOT NULL,
            durata_minuti INTEGER NOT NULL CHECK (durata_minuti > 0),
            importo REAL NOT NULL CHECK (importo >= 0),
            stato TEXT NOT NULL
                CHECK (stato IN ('completata', 'annullata')),

            FOREIGN KEY (cliente_id)
                REFERENCES clienti(id),

            FOREIGN KEY (operatore_id)
                REFERENCES operatori(id),

            FOREIGN KEY (fornitore_id)
                REFERENCES fornitori(id)
        );


        -- DIMENSIONE DATA

        CREATE TABLE dim_data (
            data_id TEXT PRIMARY KEY,
            anno INTEGER NOT NULL,
            mese INTEGER NOT NULL
                CHECK (mese BETWEEN 1 AND 12),
            mese_nome TEXT NOT NULL,
            trimestre INTEGER NOT NULL
                CHECK (trimestre BETWEEN 1 AND 4),
            giorno_settimana TEXT NOT NULL
        );


        -- DIMENSIONE CLIENTE

        CREATE TABLE dim_cliente (
            cliente_id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            area_geografica TEXT NOT NULL,
            citta TEXT NOT NULL,
            segmento TEXT NOT NULL
                CHECK (segmento IN ('nuovo', 'ricorrente'))
        );


        -- DIMENSIONE OPERATORE

        CREATE TABLE dim_operatore (
            operatore_id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            area_assegnata TEXT NOT NULL,
            livello TEXT NOT NULL
        );


        -- DIMENSIONE FORNITORE

        CREATE TABLE dim_fornitore (
            fornitore_id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            citta TEXT NOT NULL
        );


        -- TABELLA DEI FATTI

        CREATE TABLE fatto_richiesta (
            fatto_id INTEGER PRIMARY KEY AUTOINCREMENT,

            data_id TEXT NOT NULL,
            cliente_id INTEGER NOT NULL,
            operatore_id INTEGER NOT NULL,
            fornitore_id INTEGER NOT NULL,

            durata_minuti INTEGER NOT NULL
                CHECK (durata_minuti > 0),

            importo REAL NOT NULL
                CHECK (importo >= 0),

            conteggio INTEGER NOT NULL DEFAULT 1
                CHECK (conteggio = 1),

            stato TEXT NOT NULL
                CHECK (stato IN ('completata', 'annullata')),

            FOREIGN KEY (data_id)
                REFERENCES dim_data(data_id),

            FOREIGN KEY (cliente_id)
                REFERENCES dim_cliente(cliente_id),

            FOREIGN KEY (operatore_id)
                REFERENCES dim_operatore(operatore_id),

            FOREIGN KEY (fornitore_id)
                REFERENCES dim_fornitore(fornitore_id)
        );
        """
    )

    conn.executemany(
        """
        INSERT INTO clienti
            (id, nome, citta, area_geografica)
        VALUES (?, ?, ?, ?)
        """,
        clienti,
    )

    conn.executemany(
        """
        INSERT INTO operatori
            (id, nome, area_assegnata, livello)
        VALUES (?, ?, ?, ?)
        """,
        operatori,
    )

    conn.executemany(
        """
        INSERT INTO fornitori
            (id, nome, categoria, citta)
        VALUES (?, ?, ?, ?)
        """,
        fornitori,
    )

    conn.executemany(
        """
        INSERT INTO richieste
            (
                cliente_id,
                operatore_id,
                fornitore_id,
                data_richiesta,
                durata_minuti,
                importo,
                stato
            )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        richieste,
    )

    conn.commit()

    return conn


def etl(conn):
    """
    Esegue il processo ETL:
    Estrazione, Trasformazione e Caricamento.
    """

    cur = conn.cursor()

    # -----------------------------------------------------
    # E - ESTRAZIONE
    # -----------------------------------------------------

    clienti = cur.execute(
        """
        SELECT id, nome, citta, area_geografica
        FROM clienti
        """
    ).fetchall()

    operatori = cur.execute(
        """
        SELECT id, nome, area_assegnata, livello
        FROM operatori
        """
    ).fetchall()

    fornitori = cur.execute(
        """
        SELECT id, nome, categoria, citta
        FROM fornitori
        """
    ).fetchall()

    richieste = cur.execute(
        """
        SELECT
            cliente_id,
            operatore_id,
            fornitore_id,
            data_richiesta,
            durata_minuti,
            importo,
            stato
        FROM richieste
        """
    ).fetchall()

    # -----------------------------------------------------
    # T - TRASFORMAZIONE
    # -----------------------------------------------------

    dim_data = {}

    for richiesta in richieste:
        data_iso = richiesta[3]

        if data_iso not in dim_data:
            data = dt.date.fromisoformat(data_iso)

            dim_data[data_iso] = (
                data_iso,
                data.year,
                data.month,
                MESI[data.month - 1],
                (data.month - 1) // 3 + 1,
                GIORNI[data.weekday()],
            )

    richieste_per_cliente = {}

    for richiesta in richieste:
        cliente_id = richiesta[0]

        richieste_per_cliente[cliente_id] = (
            richieste_per_cliente.get(cliente_id, 0) + 1
        )

    dim_cliente = [
        (
            cliente[0],
            cliente[1],
            cliente[3],
            cliente[2],
            (
                "ricorrente"
                if richieste_per_cliente.get(cliente[0], 0) > 1
                else "nuovo"
            ),
        )
        for cliente in clienti
    ]

    fatti = [
        (
            richiesta[3],  # data_id
            richiesta[0],  # cliente_id
            richiesta[1],  # operatore_id
            richiesta[2],  # fornitore_id
            richiesta[4],  # durata_minuti
            richiesta[5],  # importo
            1,             # conteggio
            richiesta[6],  # stato
        )
        for richiesta in richieste
    ]

    # -----------------------------------------------------
    # L - CARICAMENTO
    # -----------------------------------------------------

    cur.executemany(
        """
        INSERT INTO dim_data
            (
                data_id,
                anno,
                mese,
                mese_nome,
                trimestre,
                giorno_settimana
            )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        dim_data.values(),
    )

    cur.executemany(
        """
        INSERT INTO dim_cliente
            (
                cliente_id,
                nome,
                area_geografica,
                citta,
                segmento
            )
        VALUES (?, ?, ?, ?, ?)
        """,
        dim_cliente,
    )

    cur.executemany(
        """
        INSERT INTO dim_operatore
            (
                operatore_id,
                nome,
                area_assegnata,
                livello
            )
        VALUES (?, ?, ?, ?)
        """,
        operatori,
    )

    cur.executemany(
        """
        INSERT INTO dim_fornitore
            (
                fornitore_id,
                nome,
                categoria,
                citta
            )
        VALUES (?, ?, ?, ?)
        """,
        fornitori,
    )

    cur.executemany(
        """
        INSERT INTO fatto_richiesta
            (
                data_id,
                cliente_id,
                operatore_id,
                fornitore_id,
                durata_minuti,
                importo,
                conteggio,
                stato
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        fatti,
    )

    conn.commit()

    print(
        "ETL completato: {} fatti, {} clienti, {} date, "
        "{} operatori, {} fornitori".format(
            len(fatti),
            len(dim_cliente),
            len(dim_data),
            len(operatori),
            len(fornitori),
        )
    )


def dashboard(conn):
    """
    Calcola i KPI e genera la dashboard PNG.
    """

    import matplotlib

    # Necessario per eseguire il programma anche senza interfaccia grafica
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    cur = conn.cursor()

    totale_richieste = int(
        cur.execute(
            """
            SELECT COALESCE(SUM(conteggio), 0)
            FROM fatto_richiesta
            """
        ).fetchone()[0]
    )

    tempo_medio = cur.execute(
        """
        SELECT AVG(durata_minuti)
        FROM fatto_richiesta
        WHERE stato = 'completata'
        """
    ).fetchone()[0]

    incassi = cur.execute(
        """
        SELECT COALESCE(SUM(importo), 0)
        FROM fatto_richiesta
        WHERE stato = 'completata'
        """
    ).fetchone()[0]

    clienti_ricorrenti = int(
        cur.execute(
            """
            SELECT COUNT(*)
            FROM dim_cliente
            WHERE segmento = 'ricorrente'
            """
        ).fetchone()[0]
    )

    totale_clienti = int(
        cur.execute(
            """
            SELECT COUNT(*)
            FROM dim_cliente
            """
        ).fetchone()[0]
    )

    tempo_medio = float(tempo_medio or 0)
    incassi = float(incassi or 0)

    print()
    print("=== INDICATORI PRINCIPALI ===")
    print(f"Richieste gestite:        {totale_richieste}")
    print(f"Tempo medio erogazione:  {tempo_medio:.0f} minuti")
    print(f"Incassi totali:          {incassi:.2f} EUR")

    if totale_clienti > 0:
        tasso_ricorrenti = clienti_ricorrenti / totale_clienti
        print(
            "Tasso clienti ricorrenti: "
            f"{tasso_ricorrenti:.0%}"
        )
    else:
        print("Tasso clienti ricorrenti: N/A")

    # -----------------------------------------------------
    # QUERY PER I GRAFICI
    # -----------------------------------------------------

    incassi_area = cur.execute(
        """
        SELECT
            dc.area_geografica,
            SUM(f.importo)
        FROM fatto_richiesta AS f
        JOIN dim_cliente AS dc
            ON f.cliente_id = dc.cliente_id
        WHERE f.stato = 'completata'
        GROUP BY dc.area_geografica
        ORDER BY 2 DESC
        """
    ).fetchall()

    richieste_mese = cur.execute(
        """
        SELECT
            dd.mese,
            dd.mese_nome,
            SUM(f.conteggio)
        FROM fatto_richiesta AS f
        JOIN dim_data AS dd
            ON f.data_id = dd.data_id
        GROUP BY dd.mese, dd.mese_nome
        ORDER BY dd.mese
        """
    ).fetchall()

    incassi_categoria = cur.execute(
        """
        SELECT
            df.categoria,
            SUM(f.importo)
        FROM fatto_richiesta AS f
        JOIN dim_fornitore AS df
            ON f.fornitore_id = df.fornitore_id
        WHERE f.stato = 'completata'
        GROUP BY df.categoria
        ORDER BY 2 DESC
        """
    ).fetchall()

    segmenti_clienti = cur.execute(
        """
        SELECT
            segmento,
            COUNT(*)
        FROM dim_cliente
        GROUP BY segmento
        ORDER BY segmento
        """
    ).fetchall()

    # -----------------------------------------------------
    # CREAZIONE DASHBOARD
    # -----------------------------------------------------

    figura, assi = plt.subplots(2, 2, figsize=(12, 8))

    figura.suptitle(
        "Dashboard - Data warehouse OnDemand",
        fontsize=16,
        fontweight="bold",
    )

    # Grafico 1: incassi per area geografica

    aree = [riga[0] for riga in incassi_area]
    valori_aree = [riga[1] or 0 for riga in incassi_area]

    assi[0, 0].bar(
        aree,
        valori_aree,
        color="#6366f1",
    )

    assi[0, 0].set_title(
        "Incassi per area geografica"
    )

    assi[0, 0].set_ylabel("Euro")
    assi[0, 0].tick_params(axis="x", rotation=10)

    # Grafico 2: richieste per mese

    numeri_mesi = [riga[0] for riga in richieste_mese]
    valori_mesi = [riga[2] for riga in richieste_mese]
    nomi_mesi = [riga[1] for riga in richieste_mese]

    assi[0, 1].plot(
        numeri_mesi,
        valori_mesi,
        marker="o",
        color="#10b981",
        linewidth=2,
    )

    assi[0, 1].set_xticks(numeri_mesi)
    assi[0, 1].set_xticklabels(
        nomi_mesi,
        rotation=45,
    )

    assi[0, 1].set_title("Richieste per mese")
    assi[0, 1].set_xlabel("Mese")
    assi[0, 1].set_ylabel("Numero richieste")

    # Grafico 3: incassi per categoria

    categorie = [riga[0] for riga in incassi_categoria]
    valori_categorie = [riga[1] or 0 for riga in incassi_categoria]

    assi[1, 0].barh(
        categorie[::-1],
        valori_categorie[::-1],
        color="#8b5cf6",
    )

    assi[1, 0].set_title("Incassi per categoria")
    assi[1, 0].set_xlabel("Euro")

    # Grafico 4: clienti nuovi e ricorrenti

    etichette_segmenti = [riga[0] for riga in segmenti_clienti]
    valori_segmenti = [riga[1] for riga in segmenti_clienti]

    if not valori_segmenti:
        etichette_segmenti = ["Nessun cliente"]
        valori_segmenti = [1]

    assi[1, 1].pie(
        valori_segmenti,
        labels=etichette_segmenti,
        colors=["#6366f1", "#f59e0b"],
        autopct="%1.0f%%",
    )

    assi[1, 1].set_title(
        "Clienti nuovi vs ricorrenti"
    )

    figura.tight_layout(
        rect=[0, 0.03, 1, 0.95]
    )

    figura.savefig(
        DASHBOARD_PATH,
        dpi=150,
    )

    plt.close(figura)

    print()
    print(f"Grafici salvati in {DASHBOARD_PATH}")


def main():
    """
    Funzione principale del programma.
    """

    clienti, operatori, fornitori, richieste = genera_dati()

    conn = crea_database(
        clienti,
        operatori,
        fornitori,
        richieste,
    )

    try:
        etl(conn)
        dashboard(conn)
    finally:
        conn.close()

    print("Prototipo completato.")


if __name__ == "__main__":
    main()
