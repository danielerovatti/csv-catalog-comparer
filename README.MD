# 🧩 CSV Catalog Comparer

Un tool Python flessibile e configurabile per confrontare due file CSV (ad esempio cataloghi di prodotti) e generare un report delle differenze.  
Progettato per gestire anche colonne complesse come `additional_attributes`, dove più coppie `key=value` possono essere concatenate in un'unica cella.

---

## 🚀 Funzionalità principali

- Confronto tra due file CSV basato su un campo chiave configurabile (es. `sku`)
- Gestione di campi con valori complessi: `key=value§key=value`
- Supporto per valori contenenti HTML, caratteri speciali e più `=`
- Possibilità di escludere colonne o attributi specifici dal confronto
- Report CSV dettagliato con tutte le differenze
- Totalmente configurabile tramite file `config.json`
- Output strutturato e leggibile (CSV aggregato per prodotto)

---

## 🧱 Struttura del progetto

```
csv-comparer/
│
├─ compare_catalogs.py      # Script principale
├─ config.json              # File di configurazione
├─ requirements.txt         # (opzionale, se usi solo la standard library può restare vuoto)
├─ README.md
│
├─ examples/
│   ├─ staging.csv
│   └─ production.csv
│
└─ output/
    └─ diff_report.csv      # Report generato
```

---

## ⚙️ Configurazione (`config.json`)

Tutti i parametri del tool si gestiscono da qui.  
Ecco un esempio di file completo:

```json
{
  "master_file": "examples/staging.csv",
  "comparison_file": "examples/production.csv",
  "csv_delimiter": ",",
  "attr_separator": "§",
  "special_field": "additional_attributes",
  "exclude_columns": ["created_at", "updated_at"],
  "exclude_additional_attributes": ["internal_note", "last_sync"],
  "html_fields": ["description", "additional_attributes"],
  "output_file": "output/diff_report.csv",
  "key_field": "sku"
}
```

### 🔍 Significato dei campi

| Chiave | Descrizione |
|--------|-------------|
| **master_file** | CSV principale (es. ambiente *staging*) |
| **comparison_file** | CSV da confrontare (es. ambiente *production*) |
| **csv_delimiter** | Separatore delle colonne (es. `,` o `;`) |
| **attr_separator** | Separatore interno delle coppie `key=value` (default: `§`) |
| **special_field** | Nome del campo che contiene gli attributi concatenati |
| **exclude_columns** | Colonne da ignorare durante il confronto |
| **exclude_additional_attributes** | Attributi specifici da ignorare nel campo `special_field` |
| **html_fields** | Campi che contengono HTML, verranno escapati nel report |
| **output_file** | Percorso dove salvare il CSV del report |
| **key_field** | Campo chiave univoco per identificare le righe (es. `sku`, `id`, ecc.) |

---

## ▶️ Utilizzo

1. **Clona il repository**

   ```bash
   git clone https://github.com/danielerovatti/csv-catalog-comparer
   cd csv-comparer
   ```

2. **(Opzionale) Crea un ambiente virtuale**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Installa le dipendenze**

   (Se usi solo la standard library, questo passaggio può essere saltato)

   ```bash
   pip install -r requirements.txt
   ```

4. **Esegui il confronto**

   ```bash
   python compare_catalogs.py --config config.json
   ```

   Verrà generato un file di output nella cartella `output/` (configurabile).

---

## 📄 Output del report

Il file risultante (`diff_report.csv`) conterrà tre colonne principali:

| Campo | Descrizione |
|-------|-------------|
| **sku** | Chiave del prodotto |
| **product_websites** | Informazione aggiuntiva (presa dal CSV master) |
| **differences** | Elenco differenze in formato leggibile |

Esempio:

```csv
sku,product_websites,differences
P001,base,description [<p>Vecchio testo</p> → <p>Nuovo testo</p>]; price [10 → 12]
P002,base,missing_in_production
P003,base,additional_attributes:material [cotone → lana]
```

---

## 🧩 Funzionamento tecnico

1. I file CSV vengono letti con attenzione alle celle che contengono `,`, `§`, `=` o HTML.
2. I campi speciali (es. `additional_attributes`) vengono decomposti in coppie chiave/valore.
3. Il confronto tiene conto solo delle chiavi e attributi non esclusi.
4. Tutte le differenze vengono aggregate per prodotto e salvate in un unico file CSV.

---

## 💡 Suggerimenti

- Usa sempre il delimitatore giusto nel `config.json` (`,` o `;`) in base al CSV.
- Se alcuni campi contengono HTML o tag `<p>`, aggiungili in `html_fields` per evitare problemi di encoding nel report.
- Se vuoi confrontare campi diversi da `additional_attributes`, basta cambiare `special_field` nel config.
