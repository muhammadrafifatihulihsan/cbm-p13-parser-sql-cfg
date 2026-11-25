# Parser SQL sqlglot dan Pohon Turunan Context-Free Grammar (CFG)

> **Studi Kasus Case-Based Method (CBM) Pertemuan ke-13**  
> **Mata Kuliah:** Teori Bahasa dan Automata  
> **Program Studi:** S1 Informatika, Departemen Teknik Elektronika, Fakultas Teknik, Universitas Negeri Padang  
> **Tahun Akademik:** 2026/2027  
> **Dosen Pengampu:** Dr. Resmi Darni, S.Kom., M.Kom.  
> **Penyusun:** Muhammad Rafi Fatihul Ihsan (NIM: 24343016)

---

## 1. Gambaran Proyek

Proyek ini membedah implementasi nyata parser SQL pada pustaka **sqlglot** (versi 30.34.0) dan memetakannya secara formal ke dalam konsep **Context-Free Grammar (CFG)** serta **Pohon Turunan (Parse Tree / Derivation Tree)**.

Pada perkuliahan Teori Bahasa dan Automata, tata bahasa bebas konteks sering kali dipelajari sebagai sekumpulan aturan produksi formal di atas kertas (misalnya $A \to \alpha B \beta$). Dalam sistem perangkat lunak industri, parser jarang sekali ditulis dalam bentuk formal murni; melainkan diimplementasikan sebagai **Recursive Descent Parser** dengan teknik **Precedence Climbing**, di mana aturan produksi diwujudkan sebagai fungsi-fungsi Python yang saling memanggil secara hierarkis.

Proyek ini menjembatani kesenjangan antara teori formal dan kode nyata dengan:
1. Menganalisis kode sumber resmi `sqlglot/parser.py`, `sqlglot/tokens.py`, dan `sqlglot/tokenizer_core.py`.
2. Mengekstrak aturan tata bahasa tersirat (implisit) pada kode menjadi Context-Free Grammar formal (`sql_subset.lark`).
3. Menguji kesetaraan semantik dan struktural antara parser sqlglot dengan parser CFG pembanding (Lark LALR) pada 24 kueri valid dan 12 kueri tidak valid.
4. Mengukur batasan empiris kedalaman struktur bersarang (*nested parenthesis* dan *nested subqueries*) terhadap batas rekursi runtime Python (*call stack*).

---

## 2. Ringkasan Hasil Eksperimen

Seluruh angka dan metrik dalam repositori ini diperoleh secara deterministik melalui eksekusi `src/eksperimen.py` dan tersimpan di `hasil/hasil_eksperimen.json`:

| Kategori Pengujian | Parameter / Korpus | Hasil Empiris | Status Kesepakatan |
|---|---|---|---|
| **Korpus Kueri Sah (Valid)** | 24 kueri SQL variatif (SELECT, WHERE, aritmetika, logika) | 24 / 24 Diterima | 100% Sepakat (sqlglot & Lark) |
| **Bentuk Kanonik Pohon** | 24 kueri valid (struktur operator pohon) | 23 / 24 Identik Struktural | Sesuai (1 variasi representasi Unary Negation) |
| **Korpus Tidak Sah (Invalid)** | 12 kueri mutasi sintaksis cacat | 8 / 12 Ditolak Bersama | 4 diterima parsial oleh toleransi parser sqlglot |
| **Uji Presedensi Operator** | 11 variasi kueri bertingkat | 11 / 11 Urutan Simpul Benar | Hierarki operator aritmetika & logika valid |
| **Batas Rekursi Kurung ($k$)** | Default Python limit (1.000) | $k = 48$ kurung bersarang | Dibatasi oleh kedalaman call stack |
| **Batas Rekursi Subquery ($k$)** | Default Python limit (1.000) | $k = 120$ subquery bersarang | Dibatasi oleh call stack runtime |
| **Skalabilitas Limit Rekursi** | Limit 1.000 $\to$ 2.000 $\to$ 5.000 | $k$ kurung naik: 48 $\to$ 98 $\to$ 248 | Linear terhadap `sys.setrecursionlimit` |

---

## 3. Latar Belakang Teoretis

### 3.1 Keterbatasan Finite Automata (Chomsky Tipe 3)
Pada Pertemuan ke-11 dan ke-12, telah dibuktikan melalui **Pumping Lemma untuk Bahasa Reguler** bahwa *Deterministic Finite Automata* (DFA) dan Ekspresi Reguler (Regex) memiliki keterbatasan fundamental: model berhingga tidak memiliki memori tambahan (stack) sehingga **tidak mampu mengenali tanda kurung seimbang bersarang bebas tanpa batas** ($L = \{a^n b^n \mid n \ge 0\}$).

### 3.2 Context-Free Grammar (Chomsky Tipe 2)
Untuk memproses bahasa berstruktur hierarki seperti SQL, kompilator memerlukan **Context-Free Grammar (CFG)**, yang secara formal didefinisikan sebagai 4-tuple:
$$G = (V, \Sigma, R, S)$$
- $V$: Himpunan berhingga simbol nonterminal (variabel sintaksis).
- $\Sigma$: Himpunan berhingga simbol terminal (token alfabet).
- $R$: Himpunan aturan produksi berformat $A \to \alpha$, di mana $A \in V$ dan $\alpha \in (V \cup \Sigma)^*$.
- $S \in V$: Simbol awal (*start symbol*).

Mesin pengenal bahasa bebas konteks adalah **Pushdown Automata (PDA)** yang dilengkapi memori tumpukan (*stack memory*). Pada parser recursive descent di perangkat lunak nyata, peran memori tumpukan ini diemban langsung oleh *Call Stack* pemanggilan fungsi pada memori program.

---

## 4. Pemetaan Konsep Teori ke Kode Sumber `sqlglot`

Implementasi parser pada `sqlglot/parser.py` (terdiri dari 11.071 baris kode) memetakan elemen-elemen formal CFG ke dalam konstruksi bahasa pemrograman Python sebagai berikut:

| Elemen Teori CFG | Konstruksi Formal | Padanan pada Kode `sqlglot` | Penjelasan Implementasi |
|---|---|---|---|
| **Simbol Nonterminal ($V$)** | Variabel abstrak tata bahasa | Metode Parser: `_parse_statement()`, `_parse_select()`, `_parse_disjunction()` | Setiap nonterminal diwakili oleh satu fungsi/metode yang bertugas mengurai satu unit tata bahasa. |
| **Simbol Terminal ($\Sigma$)** | Token leksikal dasar | Enumerasi `TokenType` pada `sqlglot/tokens.py` (`TokenType.SELECT`, `TokenType.FROM`, dll.) | Dihasilkan oleh tokenizer reguler sebelum parser mulai bekerja. |
| **Aturan Produksi ($R$)** | $A \to \alpha_1 \mid \alpha_2$ | Badan fungsi, percabangan `if/elif`, dan pemanggilan fungsi anak | Pemilihan cabang produksi ditentukan oleh token saat ini (*lookahead token*). |
| **Simbol Awal ($S$)** | Titik mula derivasi | Metode `_parse_statement(self)` | Titik masuk utama parser yang memanggil produksi pernyataan kueri. |
| **Pohon Turunan (Parse Tree)** | Struktur pohon graf | Objek turunan `sqlglot.exp.Expression` | Setiap simpul pohon menyimpan tipe operasi (`exp.Select`, `exp.Add`) beserta anak (*children*). |
| **Derivasi Paling Kiri** | Urutan penggantian simbol | Urutan eksekusi rekursif mendalam (*depth-first*) | Simbol nonterminal paling kiri selalu dipanggil dan dievaluasi lebih dahulu. |

---

## 5. Arsitektur Parser Dua Lapis

```
[ Teks Kueri SQL ]
       │
       ▼
┌──────────────────────────────┐
│       Lapisan Reguler        │
│    (Tokenizer / Scanner)     │  DFA berbasis tabel karakter & keyword
│   sqlglot/tokenizer_core.py  │  Memecah string menjadi token-token diskrit
└──────────────────────────────┘
       │
       ▼ [ Sekuens Token: TokenType ]
┌──────────────────────────────┐
│     Lapisan Bebas Konteks    │
│  (Recursive Descent Parser)  │  Hierarki fungsi presedensi rekursif
│     sqlglot/parser.py        │  Membangun pohon sintaksis bertingkat
└──────────────────────────────┘
       │
       ▼
[ Abstract Syntax Tree (AST) ]
 (exp.Select, exp.Add, exp.Column, ...)
```

1. **Lapisan Reguler (Tokenizer):** Menggunakan finite state machine dan tabel pemetaan karakter tunggal (`SINGLE_TOKENS`) serta kamus kata kunci (`KEYWORDS`) untuk mengubah teks mentah menjadi sekuens token tanpa memahami struktur bersarang.
2. **Lapisan Bebas Konteks (Parser):** Mengambil sekuens token dan menyusunnya menjadi pohon ekspresi melalui pemanggilan fungsi rekursif yang merefleksikan hierarki CFG.

---

## 6. Tangga Presedensi Operator dan Eliminasi Rekursi Kiri

### 6.1 Masalah Rekursi Kiri pada CFG
Tata bahasa alami untuk operator asosiatif kiri sering kali berbentuk rekursif kiri:
$$E \to E + T \mid T$$
Jika diimplementasikan secara langsung pada parser recursive descent tanpa modifikasi, pemanggilan fungsi `E()` akan langsung memanggil `E()` kembali di baris pertama tanpa mengonsumsi token apa pun, mengakibatkan loop tak hingga (*infinite recursion crash*).

### 6.2 Solusi Praktis sqlglot: Precedence Climbing
`sqlglot` mengatasi hal ini dengan mentransformasikan rekursi kiri menjadi perulangan `while`:
```python
def _parse_additive(self):
    return self._parse_tokens(self._parse_multiplicative, self.ADDITIVE)
```
Metode pembantu `_parse_tokens` membaca operand pertama secara rekursif, lalu menggunakan loop `while` untuk mengonsumsi operator biner berikutnya selama token yang cocok ditemukan.

### 6.3 Tangga Presedensi Operator (Rendah ke Tinggi)
Hierarki nonterminal pada `sqlglot/parser.py` dan `src/sql_subset.lark`:

```
┌──────────────────────────────────────────────┐  Prioritas Terendah
│  1. Disjunction       (OR)                   │
├──────────────────────────────────────────────┤
│  2. Conjunction       (AND)                  │
├──────────────────────────────────────────────┤
│  3. Equality          (=, <>, !=)            │
├──────────────────────────────────────────────┤
│  4. Comparison        (<, <=, >, >=)         │
├──────────────────────────────────────────────┤
│  5. Additive          (+, -)                 │
├──────────────────────────────────────────────┤
│  6. Multiplicative    (*, /, %)              │
├──────────────────────────────────────────────┤
│  7. Unary             (NOT, -, +)            │
├──────────────────────────────────────────────┤
│  8. Primary / Atom    (Literal, Kolom, (E))  │  Prioritas Tertinggi
└──────────────────────────────────────────────┘
```

---

## 7. Spesifikasi Grammar yang Diekstrak (`sql_subset.lark`)

Aturan tata bahasa formal yang diekstrak dari `sqlglot/parser.py` ditulis dalam notasi EBNF untuk parser Lark LALR:

```ebnf
start: select_stmt

select_stmt: SELECT [DISTINCT] select_list [from_clause] [where_clause]

select_list: select_item ("," select_item)*
select_item: expression [AS alias] | STAR

from_clause: FROM table_ref ("," table_ref)*
table_ref: IDENT [AS alias] | IDENT IDENT

where_clause: WHERE expression

expression: disjunction
disjunction: conjunction (OR conjunction)*
conjunction: equality (AND equality)*
equality: comparison ((EQ | NEQ) comparison)*
comparison: additive ((LT | LTE | GT | GTE) additive)*
additive: multiplicative ((PLUS | MINUS) multiplicative)*
multiplicative: unary ((STAR | SLASH | PERCENT) unary)*
unary: NOT unary | MINUS unary | PLUS unary | primary
primary: literal | column_ref | func_call | "(" expression ")"

literal: NUMBER | STRING
column_ref: [IDENT "."] IDENT
func_call: IDENT "(" [select_list] ")"
alias: IDENT
```

---

## 8. Struktur Berkas Repositori

```
cbm-p13-parser-sql-cfg/
├── .gitignore                  # Konfigurasi pengabaian berkas sementara git
├── README.md                   # Dokumentasi teknis dan akademik lengkap
├── requirements.txt            # Daftar pustaka dependensi proyek
├── data/                       # Berkas kueri SQL eksperimen
│   ├── valid.sql               # 24 kueri SQL sah
│   ├── tidak_valid.sql         # 12 kueri SQL mutasi tidak sah
│   └── presedensi.sql          # 11 kueri uji hierarki operator
├── gambar/                     # Diagram dan grafik visualisasi (300 DPI)
│   ├── arsitektur.png          # Diagram arsitektur 2 lapis
│   ├── pemindai_token.png      # Alur pemindaian token leksikal
│   ├── tangga_presedensi.png   # Bagan hierarki tangga presedensi operator
│   ├── pohon_presedensi.png    # Pohon turunan SELECT 1 + 2 * 3
│   ├── pohon_contoh.png        # Pohon turunan kueri SELECT lengkap
│   ├── grafik_sarang.png       # Grafik pertumbuhan simpul terhadap kedalaman
│   ├── grafik_rekursi.png      # Grafik batas kedalaman vs sys.setrecursionlimit
│   ├── output_eksperimen.png   # Cuplikan log eksekusi eksperimen
│   ├── lampiran_1_bentuk.png   # Kode pembanding bentuk kanonik
│   └── lampiran_2_derivasi.png # Kode generator derivasi paling kiri
├── hasil/                      # Rekaman luaran eksperimen
│   ├── hasil_eksperimen.json   # Data numerik mentah seluruh pengujian
│   └── output_eksperimen.txt   # Ringkasan keluaran eksekusi konsol
├── src/                        # Kode sumber implementasi eksperimen
│   ├── eksperimen.py           # Skrip pengujian utama (menghasilkan JSON)
│   ├── gambar_hasil.py         # Skrip pembuatan grafik dan diagram visual
│   └── sql_subset.lark         # Spesifikasi Context-Free Grammar formal
└── tests/                      # Pengujian unit otomatis (unittest / pytest)
    ├── test_grammar.py         # Uji parsing CFG Lark pada korpus SQL
    └── test_parser.py          # Uji kesepakatan parser sqlglot vs Lark
```

---

## 9. Panduan Menjalankan dan Reproduksi

### 9.1 Prasyarat Sistem
- Python versi 3.10 atau yang lebih baru (disarankan Python 3.13).
- Lingkungan OS: Windows, Linux, atau macOS.

### 9.2 Instalasi Dependensi
Buka terminal / PowerShell dan pasang dependensi yang diperlukan:
```bash
pip install -r requirements.txt
```

### 9.3 Menjalankan Pengujian Eksperimen Utama
Perintah ini mengeksekusi pengujian korpus, menguji kesepakatan parser, mengukur kedalaman sarang kurung dan subquery, serta memperbarui berkas `hasil/hasil_eksperimen.json`:
```bash
python src/eksperimen.py
```

### 9.4 Menghasilkan Grafik dan Diagram Hasil
Perintah ini membaca `hasil/hasil_eksperimen.json` dan merender ulang seluruh gambar beresolusi tinggi ke dalam folder `gambar/`:
```bash
python src/gambar_hasil.py
```

### 9.5 Menjalankan Pengujian Unit Otomatis
Seluruh pengujian unit dapat dijalankan menggunakan runner `unittest` bawaan Python:
```bash
python -m unittest discover tests -v
```
Atau jika menggunakan `pytest`:
```bash
pytest tests/ -v
```

---

## 10. Referensi Akademik

1. **Aho, A. V., Lam, M. S., Sethi, R., & Ullman, J. D. (2006).** *Compilers: Principles, Techniques, and Tools* (2nd ed.). Boston, MA: Pearson Education / Addison-Wesley.
2. **Hopcroft, J. E., Motwani, R., & Ullman, J. D. (2006).** *Introduction to Automata Theory, Languages, and Computation* (3rd ed.). Boston, MA: Pearson Education / Addison-Wesley.
3. **Sipser, M. (2012).** *Introduction to the Theory of Computation* (3rd ed.). Boston, MA: Cengage Learning.
4. **Tobiko Data. (2026).** *sqlglot: An extremely fast Python SQL parser and transpiler (v30.34.0)*. Dokumentasi resmi dan repositori kode sumber terbuka: [https://github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot).
5. **Shinan, E. (2026).** *Lark: A modern parsing library for Python (v1.3.1)*. Dokumentasi resmi: [https://github.com/lark-parser/lark](https://github.com/lark-parser/lark).
6. **Python Software Foundation. (2026).** *sys — System-specific parameters and functions: sys.getrecursionlimit & sys.setrecursionlimit*. Dokumentasi resmi Python 3.13: [https://docs.python.org/3/library/sys.html](https://docs.python.org/3/library/sys.html).
