"""Membuat gambar diagram dan grafik laporan CBM Pertemuan 13.

Semua gambar datar: latar putih, garis hitam, isian abu muda.
Menjalankan: py -3.13 buat_gambar.py
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sqlglot
from sqlglot import exp
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
GAMBAR = ROOT / "gambar"
DATA = json.loads((ROOT / "hasil" / "hasil_eksperimen.json").read_text(encoding="utf-8"))
GRAMMAR = (ROOT / "src" / "sql_subset.lark").read_text(encoding="utf-8")

HITAM = "#1a1a1a"
ABU = "#444444"
ABU_MUDA = "#efefef"
ABU_SEDANG = "#bdbdbd"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": HITAM,
    "axes.labelcolor": HITAM,
    "text.color": HITAM,
    "xtick.color": ABU,
    "ytick.color": ABU,
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def kotak(ax, x, y, lebar, tinggi, teks, ukuran=9, tebal=False, isi=ABU_MUDA):
    ax.add_patch(FancyBboxPatch(
        (x - lebar / 2, y - tinggi / 2), lebar, tinggi,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.0, edgecolor=HITAM, facecolor=isi, zorder=2,
    ))
    ax.text(x, y, teks, ha="center", va="center", fontsize=ukuran,
            color=HITAM, zorder=3, fontweight="bold" if tebal else "normal",
            linespacing=1.35)


def panah(ax, x1, y1, x2, y2, teks=None, gaya="-|>", ukuran=8, lekuk=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=gaya, mutation_scale=12,
        linewidth=1.0, color=HITAM, zorder=1,
        connectionstyle=f"arc3,rad={lekuk}",
    ))
    if teks:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.03, teks, ha="center", va="bottom",
                fontsize=ukuran, color=ABU)


def simpan(fig, nama):
    fig.savefig(GAMBAR / nama, dpi=220, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("gambar", nama)


# ---------------------------------------------------------------- 1 arsitektur
def arsitektur():
    fig, ax = plt.subplots(figsize=(7.4, 3.1))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])
    kotak(ax, 1.0, 2.0, 1.7, 1.0, "Teks SQL\n(SELECT ...)", ukuran=9)
    kotak(ax, 3.5, 2.0, 2.0, 1.35, "Tokenizer\nlapisan reguler\n_tokenizer_core", ukuran=8)
    kotak(ax, 6.1, 2.0, 1.5, 1.0, "Deretan\ntoken", ukuran=9)
    kotak(ax, 8.6, 2.0, 2.2, 1.35, "Parser\nCFG turunan\nrekursif", ukuran=8)
    panah(ax, 1.85, 2.0, 2.5, 2.0)
    panah(ax, 4.5, 2.0, 5.35, 2.0)
    panah(ax, 6.85, 2.0, 7.5, 2.0)
    ax.text(8.6, 0.9, "Pohon sintaksis (AST)\nsetiap simpul = satu produksi",
            ha="center", va="center", fontsize=8.5, color=ABU)
    panah(ax, 8.6, 1.3, 8.6, 1.32, gaya="-")
    ax.text(3.5, 3.3, "DFA: state = posisi karakter", ha="center", fontsize=8.5, color=ABU)
    ax.text(8.6, 3.3, "CFG: rekursi = sarang", ha="center", fontsize=8.5, color=ABU)
    simpan(fig, "arsitektur.png")


# --------------------------------------------------------- 2 pemindai token
def pemindai_token():
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])

    kotak(ax, 1.2, 2.5, 1.5, 0.9, "q0\nawal", ukuran=9, tebal=True)
    kotak(ax, 5.0, 4.1, 2.4, 0.9, "angka\n_scan_number", ukuran=8.5)
    kotak(ax, 5.0, 2.5, 2.4, 0.9, "identifier\n_scan_identifier", ukuran=8.5)
    kotak(ax, 5.0, 0.9, 2.4, 0.9, "kata kunci/operator\n_scan_keywords", ukuran=8.5)
    kotak(ax, 8.6, 2.5, 1.9, 1.6, "Token\n(jenis, teks,\nbaris, kolom)", ukuran=8.5)

    panah(ax, 1.95, 2.75, 3.8, 4.05, "digit", lekuk=-0.15, ukuran=8)
    panah(ax, 1.95, 2.5, 3.8, 2.5, "huruf/kutip", ukuran=8)
    panah(ax, 1.95, 2.25, 3.8, 0.95, "simbol", lekuk=0.15, ukuran=8)
    for y in (4.1, 2.5, 0.9):
        panah(ax, 6.2, y, 7.65, 2.5, ukuran=8)

    ax.add_patch(FancyBboxPatch((0.55, 3.25), 1.3, 0.55,
                                boxstyle="round,pad=0.01,rounding_size=0.15",
                                linewidth=1.0, edgecolor=HITAM, facecolor="white"))
    ax.text(1.2, 3.52, "karakter", ha="center", va="center", fontsize=8)
    panah(ax, 1.2, 3.2, 1.2, 3.0, ukuran=7)
    panah(ax, 1.2, 2.95, 1.2, 3.25, ukuran=7, lekuk=0.6)

    simpan(fig, "pemindai_token.png")


# ------------------------------------------------------- 3 tangga presedensi
def tangga_presedensi():
    tingkat = [
        ("expression", "_parse_expression", "alias"),
        ("assignment", "_parse_assignment", ":="),
        ("disjunction", "_parse_disjunction", "OR"),
        ("conjunction", "_parse_conjunction", "AND"),
        ("equality", "_parse_equality", "= <>"),
        ("comparison", "_parse_comparison", "< > <= >="),
        ("additive", "_parse_term", "+ -"),
        ("multiplicative", "_parse_factor", "* / %"),
        ("unary", "_parse_unary", "NOT -"),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.4)
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])

    for i, (nama, fungsi, op) in enumerate(tingkat):
        y = 9.6 - i * 1.05
        kotak(ax, 2.25, y, 3.1, 0.75, nama, ukuran=9, tebal=True)
        ax.text(3.95, y, fungsi, ha="left", va="center", fontsize=8.5, color=ABU,
                family="monospace")
        ax.text(6.6, y, op, ha="left", va="center", fontsize=8.5, color=HITAM)
        if i < len(tingkat) - 1:
            panah(ax, 2.25, y - 0.38, 2.25, y - 0.67, ukuran=7)
    ax.text(2.25, 0.35, "operan paling kiri diturunkan lebih dulu", ha="center",
            fontsize=8.5, color=ABU)
    ax.text(6.6, 10.05, "operator pada tingkat itu", ha="left", fontsize=8.5, color=ABU)
    simpan(fig, "tangga_presedensi.png")


# ------------------------------------------------------------ 4 pohon contoh
GAP = 1.1
CH = 0.86
PAD = 0.5


def _lebar(node):
    label, anak = node
    if not anak:
        return len(label)
    total = sum(_lebar(a) for a in anak) + GAP * (len(anak) - 1)
    return max(len(label), total)


def _tata(node, kiri, depth, simpul, garis):
    """Tempatkan simpul; kembalikan posisi mendatar pusat simpul."""
    label, anak = node
    lebar = _lebar(node)
    if not anak:
        x = kiri + lebar / 2
        simpul.append((label, False, x, depth))
        return x
    total = sum(_lebar(a) for a in anak) + GAP * (len(anak) - 1)
    x0 = kiri + (lebar - total) / 2
    posisi_anak = []
    for a in anak:
        posisi_anak.append(_tata(a, x0, depth + 1, simpul, garis))
        x0 += _lebar(a) + GAP
    x = (posisi_anak[0] + posisi_anak[-1]) / 2
    simpul.append((label, True, x, depth))
    for cx in posisi_anak:
        garis.append((x, cx, depth))
    return x


def gambar_pohon(ax, akar, ukuran=8.0):
    simpul, garis = [], []
    _tata(akar, 0.0, 0, simpul, garis)
    for (x1, x2, depth) in garis:
        ax.plot([x1, x2], [-depth - 0.31, -(depth + 1) + 0.31],
                color=ABU_SEDANG, linewidth=0.9, zorder=1)
    for (label, punya_anak, x, depth) in simpul:
        kotak(ax, x, -depth, len(label) * CH + PAD, 0.62, label, ukuran=ukuran,
              tebal=punya_anak, isi=ABU_MUDA if punya_anak else "white")
    kedalaman = max(d for (_, _, _, d) in simpul)
    ax.set_xlim(-1.2, _lebar(akar) + 1.2)
    ax.set_ylim(-kedalaman - 0.8, 0.8)
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])


def pohon_ekspresi(e):
    """Ubah simpul sqlglot menjadi pohon (label, anak) yang ringkas."""
    if isinstance(e, exp.Alias):
        return (f"alias {e.alias}", [pohon_ekspresi(e.this)])
    if isinstance(e, exp.Paren):
        return ("paren", [pohon_ekspresi(e.this)])
    if isinstance(e, exp.Column):
        return (f"kolom {e.sql()}", [])
    if isinstance(e, exp.Literal):
        return (f"literal {e.this}", [])
    if isinstance(e, exp.Table):
        return (f"tabel {e.name}", [])
    if isinstance(e, exp.From):
        return ("from", [pohon_ekspresi(e.this)])
    if isinstance(e, exp.Where):
        return ("where", [pohon_ekspresi(e.this)])
    if isinstance(e, exp.Select):
        anak = [pohon_ekspresi(x) for x in e.expressions]
        for nama in ("from_", "where"):
            v = e.args.get(nama)
            if isinstance(v, exp.Expr):
                anak.append(pohon_ekspresi(v))
        return ("select", anak)
    if isinstance(e, exp.Binary):
        return (e.key, [pohon_ekspresi(e.this), pohon_ekspresi(e.expression)])
    if isinstance(e, (exp.Neg, exp.Not)):
        return (e.key, [pohon_ekspresi(e.this)])
    return (e.key, [pohon_ekspresi(a) for a in e.iter_expressions()])


def pohon_contoh():
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    gambar_pohon(ax, pohon_ekspresi(sqlglot.parse_one(DATA["contoh"]["sql"])), ukuran=8.5)
    simpan(fig, "pohon_contoh.png")


def pohon_dari_kanonik(bentuk):
    if isinstance(bentuk, tuple) and len(bentuk) == 3 and isinstance(bentuk[0], str):
        return (bentuk[0], [pohon_dari_kanonik(bentuk[1]), pohon_dari_kanonik(bentuk[2])])
    if isinstance(bentuk, tuple) and len(bentuk) == 2:
        return (bentuk[0], [pohon_dari_kanonik(bentuk[1])])
    if isinstance(bentuk, tuple):
        return (bentuk[0], [])
    return (str(bentuk), [])


def pohon_presedensi():
    contoh = DATA["presedensi"][:3]
    judul = ["1 + 2 * 3", "1 * 2 + 3", "1 - 2 - 3"]
    fig, sumbu = plt.subplots(1, 3, figsize=(7.8, 3.0))
    for ax, item, j in zip(sumbu, contoh, judul):
        bentuk = ast.literal_eval(item["kanonik"])
        gambar_pohon(ax, pohon_dari_kanonik(bentuk), ukuran=7.5)
        ax.set_title(j, fontsize=9, color=HITAM, pad=4)
    fig.subplots_adjust(wspace=0.08)
    simpan(fig, "pohon_presedensi.png")


# ------------------------------------------------------------------ 5 grafik
def grafik_sarang():
    baris = [b for b in DATA["sarang"] if b.get("status") == "diterima"]
    k = [b["k"] for b in baris]
    kedalaman = [b["kedalaman"] for b in baris]
    node = [b["node"] for b in baris]

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot(k, kedalaman, color=HITAM, marker="o", markersize=4, linewidth=1.4,
            label="kedalaman pohon")
    ax.plot(k, node, color=ABU, marker="s", markersize=4, linewidth=1.2,
            linestyle="--", label="jumlah simpul")
    ax.set_xlabel("kedalaman sarang kurung (k)")
    ax.set_ylabel("jumlah simpul atau kedalaman")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("Pohon tumbuh linear terhadap kedalaman sarang", fontsize=10, pad=8)
    simpan(fig, "grafik_sarang.png")


def grafik_rekursi():
    batas = ["1000", "2000", "5000"]
    kurung = [DATA["batas_rekursi"][b]["nilai"]["kurung"] for b in batas]
    subq = [DATA["batas_rekursi"][b]["nilai"]["subquery"] for b in batas]
    x = [int(b) for b in batas]

    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    ax.plot(x, kurung, color=HITAM, marker="o", linewidth=1.4, label="sarang kurung")
    ax.plot(x, subq, color=ABU, marker="s", linewidth=1.2, linestyle="--",
            label="sarang subquery")
    for xi, yi in zip(x, kurung):
        ax.annotate(str(yi), (xi, yi), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8.5, color=HITAM)
    for xi, yi in zip(x, subq):
        ax.annotate(str(yi), (xi, yi), textcoords="offset points", xytext=(0, -14),
                    ha="center", fontsize=8.5, color=ABU)
    ax.set_xlabel("batas rekursi Python (sys.setrecursionlimit)")
    ax.set_ylabel("kedalaman sarang terbesar yang diterima")
    ax.set_xticks(x)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("Batas kedalaman naik sebanding dengan batas rekursi", fontsize=10, pad=8)
    simpan(fig, "grafik_rekursi.png")


if __name__ == "__main__":
    GAMBAR.mkdir(parents=True, exist_ok=True)
    arsitektur()
    pemindai_token()
    tangga_presedensi()
    pohon_contoh()
    pohon_presedensi()
    grafik_sarang()
    grafik_rekursi()
