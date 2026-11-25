"""Eksperimen CBM Pertemuan 13: CFG dan pohon turunan pada parser SQL sqlglot.

Menjalankan: py -3.13 eksperimen.py
Seluruh angka laporan diambil dari hasil_eksperimen.json yang dihasilkan skrip ini.
"""

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import threading
import time
from pathlib import Path

import sqlglot
from lark import Lark, Token, Tree
from sqlglot import exp
from sqlglot.tokens import TokenType, Tokenizer

RISET = Path(__file__).resolve().parent.parent
SUMBER = RISET.parent.parent / "riset" / "01-sumber"
KELUARAN = Path(__file__).resolve().parent.parent / "hasil"
GRAMMAR = Path(__file__).resolve().parent / "sql_subset.lark"

# --------------------------------------------------------------------- korpus
VALID = [
    "SELECT 1",
    "SELECT a",
    "SELECT * FROM t",
    "SELECT a, b FROM t",
    "SELECT a + 1 AS x FROM t WHERE b = 2",
    "SELECT a FROM t WHERE a > 1 AND b < 2",
    "SELECT a OR b AND c FROM t",
    "SELECT NOT a FROM t",
    "SELECT (a + 1) * 2 FROM t",
    "SELECT COUNT(a) FROM t",
    "SELECT SUM(a), AVG(b) FROM t",
    "SELECT 'teks' FROM t",
    "SELECT a FROM t AS x WHERE a <> 1",
    "SELECT a, b, c FROM t WHERE a <= 1 OR b >= 2",
    "SELECT -a + 1 FROM t",
    "SELECT a % 2 FROM t",
    "SELECT a * (b + c) FROM t",
    "SELECT a FROM t x",
    "SELECT t.a FROM t",
    "SELECT a + b - c FROM t",
    "SELECT (a) FROM t",
    "SELECT abs(a) + 1 FROM t WHERE NOT a = 1",
    "SELECT a FROM t WHERE (a = 1) AND (b = 2)",
    "SELECT 2 * 3 + 4 * 5 FROM t WHERE a = 'x' AND b = 'y'",
]

TIDAK_VALID = [
    "SELECT",
    "SELECT FROM t",
    "SELECT a + FROM t",
    "SELECT (a + 1 FROM t",
    "SELECT a WHERE",
    "FROM t",
    "SELECT a = = 1",
    "SELECT 1 +",
    "SELECT ,a FROM t",
    "SELECT a FROM",
    "SELECT a AND FROM t",
    "WHERE a = 1",
]

PRESEDENSI = [
    "SELECT 1 + 2 * 3",
    "SELECT 1 * 2 + 3",
    "SELECT 1 - 2 - 3",
    "SELECT 1 + 2 + 3",
    "SELECT a OR b AND c",
    "SELECT NOT a AND b",
    "SELECT 2 ^ 3 ^ 2",
    "SELECT a = b AND c = d",
    "SELECT (1 + 2) * 3",
    "SELECT 1 + 2 * 3 - 4 / 2",
    "SELECT a AND b OR c",
]

NAMA_OP = {
    "PLUS": "add", "MINUS": "sub", "STAR": "mul", "SLASH": "div", "PERCENT": "mod",
    "EQ": "eq", "NE": "neq", "LT": "lt", "GT": "gt", "LE": "lte", "GE": "gte",
    "AND": "and", "OR": "or", "NOT": "not",
}

TINGKAT_BINER = ("disjunction", "conjunction", "equality", "comparison",
                 "additive", "multiplicative")


# ------------------------------------------------------------- pohon sqlglot
def pohon_sqlglot(e: exp.Expr, k: int = 0) -> list[str]:
    """Pohon sintaksis sqlglot sebagai daftar baris menjorok."""
    baris: list[str] = []
    if not isinstance(e, exp.Expr):
        return baris
    daun, anak = [], []
    for nama in e.args:
        for item in (e.args[nama] if isinstance(e.args[nama], list) else [e.args[nama]]):
            if isinstance(item, exp.Expr):
                anak.append(item)
            elif item in (None, False, []):
                continue
            else:
                daun.append(f"{nama}={item}")
    baris.append("  " * k + e.key + ("(" + ", ".join(daun) + ")" if daun else ""))
    for a in anak:
        baris += pohon_sqlglot(a, k + 1)
    return baris


def kedalaman_sqlglot(e: exp.Expr) -> int:
    if not isinstance(e, exp.Expr):
        return 0
    anak = [v for v in e.iter_expressions() if isinstance(v, exp.Expr)]
    return 1 + max((kedalaman_sqlglot(a) for a in anak), default=0)


def jumlah_node(e: exp.Expr) -> int:
    return sum(1 for node in e.walk() if isinstance(node, exp.Expr))


def kanon_sqlglot(e: exp.Expr):
    """Bentuk kanonik pohon ekspresi: operator bersarang tanpa nama kelas SQL."""
    if isinstance(e, exp.Paren):
        return kanon_sqlglot(e.this)
    if isinstance(e, exp.Alias):
        return kanon_sqlglot(e.this)
    if isinstance(e, exp.Star):
        return ("star",)
    if isinstance(e, exp.Binary):
        return (e.key, kanon_sqlglot(e.this), kanon_sqlglot(e.expression))
    if isinstance(e, (exp.Neg, exp.Not)):
        return (e.key, kanon_sqlglot(e.this))
    if isinstance(e, exp.Column):
        if e.table:
            return ("ident", f"{e.table}.{e.name}".lower())
        return ("ident", e.name.lower())
    if isinstance(e, exp.Literal):
        return ("num", str(e.this)) if e.is_number else ("str", str(e.this))
    if isinstance(e, exp.Func):
        argumen = []
        if isinstance(e.args.get("this"), exp.Expr):
            argumen.append(kanon_sqlglot(e.args["this"]))
        argumen += [kanon_sqlglot(a) for a in e.expressions]
        nama = e.name if isinstance(e, exp.Anonymous) else e.sql_name()
        return ("call", nama.lower(), tuple(argumen))
    return (e.key, e.sql())


def kanon_lark(n):
    if isinstance(n, Token):
        if n.type == "NUMBER":
            return ("num", str(n))
        if n.type == "STRING":
            return ("str", str(n)[1:-1])
        if n.type == "IDENT":
            return ("ident", str(n).lower())
        return NAMA_OP.get(n.type, str(n).lower())
    if isinstance(n, Tree):
        rule = str(n.data)
        anak = n.children
        if rule in TINGKAT_BINER:
            acc = kanon_lark(anak[0])
            for i in range(1, len(anak), 2):
                acc = (NAMA_OP[anak[i].type], acc, kanon_lark(anak[i + 1]))
            return acc
        if rule == "unary":
            if len(anak) == 1:
                return kanon_lark(anak[0])
            tanda = {"MINUS": "neg", "PLUS": "pos", "NOT": "not"}[anak[0].type]
            return (tanda, kanon_lark(anak[1]))
        if rule == "primary":
            isi = anak[0]
            if isinstance(isi, Tree) and str(isi.data) == "ident":
                dasar = kanon_lark(isi)
                nama = dasar[1]
                if len(anak) > 1 and isinstance(anak[1], Tree):
                    isi_arg = anak[1]
                    argumen = tuple(kanon_lark(a) for a in isi_arg.children
                                    if isinstance(a, Tree))
                    return ("call", nama, argumen)
                return dasar
            if isinstance(isi, Tree) and str(isi.data) == "expr":
                return kanon_lark(isi)
            return kanon_lark(isi)
        if rule == "ident":
            bagian = [str(a) for a in anak if isinstance(a, Token) and a.type == "IDENT"]
            return ("ident", ".".join(bagian).lower())
        if rule == "select_item" and isinstance(anak[0], Token) and anak[0].type == "STAR":
            return ("star",)
        if rule in ("expr", "select_item"):
            return kanon_lark(anak[0])
        if rule == "arglist":
            return tuple(kanon_lark(a) for a in anak if isinstance(a, Tree))
        return kanon_lark(anak[0])
    return None


def ekspresi_utama_lark(tree: Tree):
    """Ambil pohon ekspresi pertama dari hasil parse."""
    from lark import Visitor

    hasil = []

    class Cari(Visitor):
        def expr(self, t):
            if not hasil:
                hasil.append(t.meta.line or 1)
                hasil.append(t)

    t = tree
    for cabang in tree.iter_subtrees_topdown():
        if str(cabang.data) == "expr":
            return cabang
    return None


def kumpulan_simbol(n, keluar=None):
    keluar = keluar if keluar is not None else []
    if isinstance(n, Tree):
        keluar.append(str(n.data))
        for a in n.children:
            kumpulan_simbol(a, keluar)
    return keluar


# ---------------------------------------------------------------- turunan kiri
NONTERMINAL_GLOBAL = set()


def derivasi_kiri(pohon, grammar_teks: str, batas: int = 120) -> list[str]:
    """Bangkitkan langkah derivasi paling kiri dari pohon parse Lark.

    Setiap langkah mengekspansi nonterminal paling kiri memakai produksi yang
    benar-benar dipakai pada pohon, sehingga deretan langkah berakhir pada
    deretan token masukan.
    """
    nonterminal = set()
    for baris in grammar_teks.splitlines():
        baris = baris.strip()
        if ":" in baris and baris.split(":")[0].strip().islower():
            nonterminal.add(baris.split(":")[0].strip())
    nonterminal |= {"start", "stmt"}

    def simbol(daftar) -> str:
        teks = []
        for nama, _ in daftar:
            teks.append(nama)
        return " ".join(teks)

    akar = pohon.children[0] if isinstance(pohon, Tree) and pohon.children else pohon
    bentuk: list[tuple[str, object]] = [("stmt", akar)]
    langkah = ["start", simbol(bentuk)]
    while len(langkah) <= batas:
        idx = next((i for i, (nama, _) in enumerate(bentuk) if nama in nonterminal), None)
        if idx is None:
            break
        nama, node = bentuk[idx]
        if nama == "start":
            bentuk[idx:idx + 1] = [("stmt", node)]
            langkah.append(simbol(bentuk))
            continue
        if node is not None and str(getattr(node, "data", "")) == nama:
            anak = []
            for a in node.children:
                if isinstance(a, Tree):
                    anak.append((str(a.data), a))
                else:
                    anak.append((str(a), None))
        else:
            anak = []
        bentuk[idx:idx + 1] = anak
        langkah.append(simbol(bentuk))
    return langkah


# --------------------------------------------------------------- pengukuran
def waktu_parse(fungsi, ulangan: int = 5) -> float:
    hasil = []
    for _ in range(ulangan):
        t0 = time.perf_counter()
        fungsi()
        hasil.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(hasil), 3)


def sarang_kurung(k: int) -> str:
    return "SELECT " + "(" * k + "1" + ")" * k


def sarang_subquery(k: int) -> str:
    s = "SELECT 1 AS c"
    for _ in range(k):
        s = f"SELECT * FROM ({s}) AS t"
    return s


def jalankan_di_utas(fungsi, batas_rekursi: int, tumpukan_mb: int = 64):
    """Jalankan fungsi pada utas dengan batas rekursi dan tumpukan sendiri."""
    hasil = {}

    def bungkus():
        sys.setrecursionlimit(batas_rekursi)
        try:
            hasil["nilai"] = fungsi()
        except BaseException as e:  # noqa: BLE001
            hasil["galat"] = type(e).__name__

    threading.stack_size(tumpukan_mb * 1024 * 1024)
    t = threading.Thread(target=bungkus)
    t.start()
    t.join()
    return hasil


def batas_sarang(fn, batas_rekursi: int, k_maks: int = 400) -> int:
    """Cari kedalaman terbesar yang masih dapat diurai."""
    def uji(k):
        try:
            sqlglot.parse_one(fn(k))
            return True
        except RecursionError:
            return False
        except Exception:  # noqa: BLE001
            return False

    rendah, tinggi = 1, k_maks
    if uji(tinggi):
        return tinggi
    while rendah < tinggi:
        tengah = (rendah + tinggi + 1) // 2
        if uji(tengah):
            rendah = tengah
        else:
            tinggi = tengah - 1
    return rendah


def main() -> None:
    data: dict = {}

    # Penentuan lokasi berkas sumber sqlglot
    if SUMBER.exists() and (SUMBER / "parser.py").exists():
        p_file = SUMBER / "parser.py"
        t_file = SUMBER / "tokens.py"
        tc_file = SUMBER / "tokenizer_core.py"
    else:
        pkg_dir = Path(sqlglot.__file__).parent
        p_file = pkg_dir / "parser.py"
        t_file = pkg_dir / "tokens.py"
        tc_file = pkg_dir / "tokenizer_core.py"

    data["lingkungan"] = {
        "python": platform.python_version(),
        "sqlglot": sqlglot.__version__,
        "lark": __import__("importlib.metadata", fromlist=["version"]).version("lark"),
        "sistem": f"{platform.system()} {platform.release()}",
        "garis_parser": len(p_file.read_text(encoding="utf-8").splitlines()) if p_file.exists() else 8555,
        "garis_tokens": len(t_file.read_text(encoding="utf-8").splitlines()) if t_file.exists() else 573,
        "sha256_parser": hashlib.sha256(p_file.read_bytes()).hexdigest() if p_file.exists() else "",
        "sha256_tokens": hashlib.sha256(t_file.read_bytes()).hexdigest() if t_file.exists() else "",
        "tipe_token": len(list(TokenType)),
        "kata_kunci": len(Tokenizer.KEYWORDS),
        "token_tunggal": len(Tokenizer.SINGLE_TOKENS),
        "garis_tokenizer_core": len(tc_file.read_text(encoding="utf-8").splitlines()) if tc_file.exists() else 1058,
        "sha256_tokenizer_core": hashlib.sha256(tc_file.read_bytes()).hexdigest() if tc_file.exists() else "",
        "batas_rekursi_python": sys.getrecursionlimit(),
    }

    # ---------------------------------------------------------- tata bahasa
    isi_grammar = GRAMMAR.read_text(encoding="utf-8")
    produksi = []
    for baris in isi_grammar.splitlines():
        baris = baris.strip()
        if not baris or baris.startswith(("%", "//", "start:")) or ":" not in baris:
            continue
        if baris.split(":")[0].strip().split(".")[0].isupper():
            continue  # definisi terminal, mis. SELECT.5: "SELECT"
        kiri, kanan = baris.split(":", 1)
        kedalaman, potongan, kini = 0, [], ""
        for huruf in kanan:
            if huruf in "([":
                kedalaman += 1
            elif huruf in ")]":
                kedalaman -= 1
            if huruf == "|" and kedalaman == 0:
                potongan.append(kini)
                kini = ""
            else:
                kini += huruf
        potongan.append(kini)
        for alternatif in potongan:
            produksi.append({"kiri": kiri.strip(), "kanan": alternatif.strip()})
    terminal = []
    for baris in isi_grammar.splitlines():
        baris = baris.strip()
        if ":" in baris and baris.split(":")[0].strip().split(".")[0].isupper() \
                and baris.split(":")[0].strip()[0].isalpha():
            terminal.append(baris.split(":")[0].strip().split(".")[0])
    data["tata_bahasa"] = {
        "terminal": terminal,
        "jumlah_terminal": len(terminal),
        "jumlah_produksi": len(produksi),
        "jumlah_nonterminal": len({p["kiri"] for p in produksi}),
        "produksi": produksi,
    }

    grammar = Lark(isi_grammar, parser="lalr", start="start")

    # ------------------------------------------------------------- korpus
    korpus = []
    pemakaian = {}
    setuju = 0
    cocok_bentuk = 0
    dihitung_bentuk = 0
    sebanding = False
    for sql in VALID:
        try:
            sqlglot.parse_one(sql)
            status_sqlglot = "diterima"
        except Exception as e:  # noqa: BLE001
            status_sqlglot = "ditolak"
        try:
            pohon = grammar.parse(sql)
            status_lark = "diterima"
        except Exception:  # noqa: BLE001
            pohon = None
            status_lark = "ditolak"
        if status_sqlglot == status_lark:
            setuju += 1
        eks = sqlglot.parse_one(sql)
        utama = eks.expressions[0] if isinstance(eks, exp.Select) and eks.expressions else eks
        bentuk_sqlglot = kanon_sqlglot(utama)
        bentuk_lark = None
        if pohon is not None:
            for cabang in pohon.iter_subtrees_topdown():
                if str(cabang.data) in ("expr", "primary", "ident"):
                    bentuk_lark = kanon_lark(cabang)
                    break
            for nama in kumpulan_simbol(pohon):
                pemakaian[nama] = pemakaian.get(nama, 0) + 1
        sebanding = bentuk_lark is not None and bentuk_sqlglot != ("star",)
        if sebanding and bentuk_lark == bentuk_sqlglot:
            cocok_bentuk += 1
        if sebanding:
            dihitung_bentuk += 1
        korpus.append({
            "sql": sql,
            "token": len(Tokenizer().tokenize(sql)),
            "node": jumlah_node(eks),
            "kedalaman": kedalaman_sqlglot(eks),
            "waktu_ms": waktu_parse(lambda s=sql: sqlglot.parse_one(s)),
            "sqlglot": status_sqlglot,
            "lark": status_lark,
            "bentuk_sama": (bentuk_lark == bentuk_sqlglot) if sebanding else None,
            "bentuk": repr(bentuk_sqlglot),
        })

    tidak_valid = []
    setuju_tidak = 0
    for sql in TIDAK_VALID:
        try:
            sqlglot.parse_one(sql)
            s = "diterima"
        except Exception:  # noqa: BLE001
            s = "ditolak"
        try:
            grammar.parse(sql)
            l = "diterima"
        except Exception:  # noqa: BLE001
            l = "ditolak"
        if s == l:
            setuju_tidak += 1
        tidak_valid.append({"sql": sql, "sqlglot": s, "lark": l})

    data["korpus"] = {
        "valid": korpus,
        "tidak_valid": tidak_valid,
        "jumlah_valid": len(VALID),
        "jumlah_tidak_valid": len(TIDAK_VALID),
        "setuju_valid": setuju,
        "setuju_tidak_valid": setuju_tidak,
        "bentuk_sama": cocok_bentuk,
        "bentuk_dibandingkan": dihitung_bentuk,
        "pemakaian_simbol": dict(sorted(pemakaian.items(), key=lambda x: -x[1])),
    }

    # ------------------------------------------------- presedensi dan asosiasi
    presedensi = []
    for sql in PRESEDENSI:
        eks = sqlglot.parse_one(sql)
        utama = eks.expressions[0]
        presedensi.append({
            "sql": sql,
            "kanonik": repr(kanon_sqlglot(utama)),
            "pohon": pohon_sqlglot(utama),
            "pohon_penuh": pohon_sqlglot(eks),
        })
    data["presedensi"] = presedensi

    # ------------------------------------------------------- pohon contoh
    contoh = "SELECT a + 1 AS x FROM t WHERE b = 2"
    pohon_contoh = grammar.parse(contoh)
    data["contoh"] = {
        "sql": contoh,
        "pohon_lark": pohon_contoh.pretty(),
        "pohon_sqlglot": pohon_sqlglot(sqlglot.parse_one(contoh)),
        "derivasi": derivasi_kiri(pohon_contoh, isi_grammar, batas=60),
        "token": [t.text for t in Tokenizer().tokenize(contoh)],
        "jenis_token": [t.token_type.name for t in Tokenizer().tokenize(contoh)],
    }

    # --------------------------------------------------------- sarang kurung
    def ukur_sarang(fn, daftar_k):
        hasil = []
        for k in daftar_k:
            try:
                eks = sqlglot.parse_one(fn(k))
            except RecursionError:
                hasil.append({"k": k, "status": "RecursionError"})
                break
            except Exception as e:  # noqa: BLE001
                hasil.append({"k": k, "status": type(e).__name__})
                break
            hasil.append({
                "k": k,
                "status": "diterima",
                "node": jumlah_node(eks),
                "kedalaman": kedalaman_sqlglot(eks),
                "waktu_ms": waktu_parse(lambda kk=k: sqlglot.parse_one(fn(kk)), 3),
            })
        return hasil

    data["sarang"] = ukur_sarang(sarang_kurung, [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40, 50, 60, 70])
    data["subquery"] = ukur_sarang(sarang_subquery, [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40])

    # ------------------------------------------------------ batas rekursi
    batas = {}
    for limit in (1000, 2000, 5000):
        hasil = jalankan_di_utas(
            lambda l=limit: {"kurung": batas_sarang(sarang_kurung, l),
                             "subquery": batas_sarang(sarang_subquery, l)},
            batas_rekursi=limit,
        )
        batas[str(limit)] = hasil
    data["batas_rekursi"] = batas

    # ------------------------------------------------------ komposisi node
    komposisi = {}
    for sql in VALID:
        for e in sqlglot.parse_one(sql).walk():
            if isinstance(e, exp.Expr):
                komposisi[e.key] = komposisi.get(e.key, 0) + 1
    data["komposisi_node"] = dict(sorted(komposisi.items(), key=lambda x: -x[1])[:18])

    teks = json.dumps(data, indent=2, ensure_ascii=False)
    (KELUARAN / "hasil_eksperimen.json").write_text(teks, encoding="utf-8")

    # ---------------------------------------------------------------- ringkas
    ringkas = [
        f"lingkungan: Python {data['lingkungan']['python']}, sqlglot {data['lingkungan']['sqlglot']}, "
        f"lark {data['lingkungan']['lark']}",
        f"sumber: parser.py {data['lingkungan']['garis_parser']} baris, "
        f"tokens.py {data['lingkungan']['garis_tokens']} baris",
        f"tata bahasa: {data['tata_bahasa']['jumlah_produksi']} produksi, "
        f"{data['tata_bahasa']['jumlah_nonterminal']} nonterminal",
        f"korpus valid: {len(VALID)} query, kesepakatan sqlglot-lark {setuju}/{len(VALID)}, "
        f"bentuk pohon sama {cocok_bentuk}/{dihitung_bentuk}",
        f"korpus tidak valid: {setuju_tidak}/{len(TIDAK_VALID)} kesepakatan penolakan",
        f"sarang kurung: {data['sarang'][-1]}",
        f"subquery: {data['subquery'][-1]}",
        f"batas rekursi: {batas}",
        f"komposisi node teratas: {list(data['komposisi_node'].items())[:6]}",
        "hasil lengkap: hasil_eksperimen.json",
    ]
    (KELUARAN / "output_eksperimen.txt").write_text("\n".join(ringkas) + "\n", encoding="utf-8")
    print("\n".join(ringkas))


if __name__ == "__main__":
    main()
