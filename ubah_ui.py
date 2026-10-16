import re
from pathlib import Path

T = Path("templates")


def baca(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def tulis(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def edit(path, pairs, regex=()):
    p = T / path
    s = baca(p)
    for lama, baru in pairs:
        if lama not in s:
            print(f"  [lewat] {path}: tidak ketemu -> {lama[:50]}...")
            continue
        s = s.replace(lama, baru)
    for pola, baru in regex:
        s, n = re.subn(pola, baru, s)
        if not n:
            print(f"  [lewat] {path}: pola tidak ketemu -> {pola[:50]}...")
    tulis(p, s)


# 1. Semua template: hapus label huruf kapital, perkuat ring fokus input
for f in T.rglob("*.html"):
    if f.name in ("base.html", "login.html"):
        continue
    s = baca(f)
    s = s.replace(" uppercase tracking-wide", "").replace("focus:ring-blue-100", "focus:ring-blue-200")
    tulis(f, s)

# 2. Tabel: header bergaya buku register, angka rata
edit("arsip/_tabel.html", [
    ('<thead class="bg-slate-50 text-xs font-semibold text-slate-600">',
     '<thead class="border-b-2 border-blue-900 bg-white text-xs font-semibold text-slate-700">'),
    ('<table class="min-w-full text-sm">', '<table class="min-w-full text-sm tabular-nums">'),
])

# 3. Dashboard: dua kartu statistik jadi satu strip
edit("dashboard.html", [
    ('<div class="grid gap-4 sm:grid-cols-2 lg:max-w-xl">',
     '<dl class="flex w-fit max-w-full divide-x divide-slate-200 overflow-x-auto rounded-xl border border-slate-200 bg-white">'),
    ('<div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">', '<div class="px-6 py-4">'),
    ('<p class="text-sm text-slate-500">{{ label }}</p>', '<dt class="text-sm text-slate-500">{{ label }}</dt>'),
    ('<p class="mt-2 text-3xl font-bold text-slate-900">{{ value }}</p>',
     '<dd class="mt-1 font-display text-3xl font-semibold text-slate-900">{{ value }}</dd>'),
], regex=[(r'(\{% endfor %\}\s*)</div>(\s*<h2 class="mb-3 mt-10)', r'\1</dl>\2')])

# 4. Modal: semantik dialog dan label tombol tutup
tutup_lama = '<button type="button" @click="close()" class="text-2xl leading-none text-slate-400 hover:text-slate-600">'
tutup_baru = '<button type="button" @click="close()" aria-label="Tutup" class="text-2xl leading-none text-slate-400 hover:text-slate-600">'
edit("arsip/_modal_form.html", [
    ('<form method="post" hx-post="{{ request.path }}"', '<form method="post" role="dialog" aria-modal="true" aria-labelledby="judul-modal" hx-post="{{ request.path }}"'),
    ('<h2 class="text-lg font-semibold text-slate-900">{{ judul }}</h2>', '<h2 id="judul-modal" class="text-lg font-semibold text-slate-900">{{ judul }}</h2>'),
    (tutup_lama, tutup_baru),
])
edit("arsip/_modal_import.html", [
    ('<form method="post" enctype="multipart/form-data" hx-post="{% url \'arsip_import\' %}"', '<form method="post" role="dialog" aria-modal="true" aria-labelledby="judul-modal" enctype="multipart/form-data" hx-post="{% url \'arsip_import\' %}"'),
    ('<h2 class="text-lg font-semibold text-slate-900">Import dari Excel</h2>', '<h2 id="judul-modal" class="text-lg font-semibold text-slate-900">Import dari Excel</h2>'),
    (tutup_lama, tutup_baru),
])

# 5. Panel export di Django admin: samakan warna tombol
edit("admin/arsip/export_panel.html", [
    ("background: #2563eb;", "background: #1f4496;"),
    (".exp-form button:hover { background: #1d4ed8; }", ".exp-form button:hover { background: #183a82; }"),
])
print("Selesai.")