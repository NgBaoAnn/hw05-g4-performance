"""Seed the disposable, freshly initialized SUT from the same CSV used in JMeter."""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = "slot,email,password,product_id,name,description,imageUrl,category_id,low,high".split(",")


def seed():
    backend = ROOT / ".work/eshop/backend"
    with sqlite3.connect(backend / "database.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 5, "Expected fresh demo DB"
        for row in csv.DictReader((ROOT / "data/admin-fixtures.csv").open()):
            db.execute("INSERT INTO users(name,email,password,role) VALUES (?,?,?,'admin')",
                       (row["name"], row["email"], row["password"]))
            db.execute("INSERT INTO products(id,name,price,description,imageUrl,category_id) VALUES (?,?,?,?,?,?)",
                       tuple(row[k] for k in ("product_id", "name", "low", "description", "imageUrl", "category_id")))
        db.execute("INSERT INTO orders(id,user_id,total_amount,status) VALUES(9001,2,100000,'pending')")


if __name__ == "__main__":
    if sys.argv[1:] == ["--generate"]:
        with (ROOT / "data/admin-fixtures.csv").open("w", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(FIELDS)
            for i in range(1, 81):
                writer.writerow([i, f"g4-{i}@example.test", "LocalDemo123!", 1000+i, f"G4-{i}",
                                 "Fixture G4", "", 1, 100000+i, 110000+i])
    elif not sys.argv[1:]:
        seed()
    else:
        raise SystemExit("Use --generate or run after a fresh local SUT start")
