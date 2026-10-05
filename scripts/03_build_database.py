"""
03_build_database.py
Creates data/recruitment.db (SQLite) from the clean CSVs:
  sql/01_schema.sql -> load tables -> sql/02_views.sql
then runs every query in sql/03_analysis_queries.sql and saves each result
to sql/query_results/Qnn_<name>.csv.
"""
import re
import sqlite3
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CLEAN, SQL = BASE / "data" / "clean", BASE / "sql"
DB = BASE / "data" / "recruitment.db"
RES = SQL / "query_results"
RES.mkdir(exist_ok=True)
for f in RES.glob("*.csv"):
    f.unlink()
DB.unlink(missing_ok=True)

con = sqlite3.connect(DB)
con.executescript((SQL / "01_schema.sql").read_text())
for table in ["departments", "recruiters", "requisitions", "candidates", "applications",
              "stage_events", "offers", "hires", "source_spend"]:
    df = pd.read_csv(CLEAN / f"{table}.csv")
    if "days_in_stage" in df:
        df["days_in_stage"] = df.days_in_stage.astype("Int64")
    df.to_sql(table, con, if_exists="append", index=False)
    print(f"loaded {table:<14} {len(df):>7,} rows")
con.executescript((SQL / "02_views.sql").read_text())
con.commit()

text = (SQL / "03_analysis_queries.sql").read_text()
for block in re.split(r"\n(?=-- Q\d\d:)", text)[1:]:
    title = block.splitlines()[0].replace("-- ", "")
    qid = title.split(":")[0]
    slug = re.sub(r"[^a-z0-9]+", "_", title.split(":", 1)[1].lower()).strip("_")[:45]
    df = pd.read_sql(block, con)
    df.to_csv(RES / f"{qid}_{slug}.csv", index=False)
    print(f"\n{title}\n{df.to_string(index=False)}")
con.close()
