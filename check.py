#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка поста ВК — Premium Clinic (premium-clinic.com)
Запуск: python3 check.py post_N.md

Параметры этой клиники (должны совпадать с файлом стиля на Google Drive —
при изменении объёма или лимитов правь ОБА места):
  объём до 1000 знаков без пробелов (весь пост целиком)
  жирных фрагментов: не больше 2 (сдержанный тон, минимум акцентов)
  абзац: не длиннее 3 строк
  структура: свободная, формат подбирается под тему (сжатый аналитический
    обзор / новость-повод / экспертное наблюдение / заголовок+суть+призыв
    и др. — см. файл стиля), не проверяется скриптом. Полное сравнение всех
    вариантов метода в 1000 знаков не помещается — сравнение должно быть
    сужено до 1-2 вариантов (проверяется вручную по чек-листу файла стиля,
    скрипт этого не отслеживает)

Блок «ИИ-паттерны» идентичен во всех пяти клиниках проекта. Не меняй его
в одном репозитории, не поменяв в остальных.
Только стандартная библиотека Python.
"""
import re, sys

VMIN, VMAX = 1, 1000
BOLD_LIMIT = 2
PARA_LINES = 3

# ============================================================
# ЕДИНОЕ ИИ-ЯДРО — одинаковое для всех пяти клиник
# ============================================================

CRIT_PATTERNS = [
    (r'\bне\s+[^.!?\n]{1,60}?,\s+а\s+', 'не X, а Y'),
    (r',\s+а\s+не\s+', 'Y, а не X'),
    (r'\bэто\s+не\s+[^.!?\n]{1,50}?[,.]\s*это\s+', 'это не X, это Y'),
    (r'\bне\s+просто\s+[^.!?\n]{1,50}?,\s*а\s+', 'не просто X, а Y'),
    (r'\bне\s+только\s+[^.!?\n]{1,50}?,\s*но\s+и\s+', 'не только X, но и Y'),
    (r'\bдело\s+не\s+в\s+', 'дело не в X'),
]

ROWS = [
    (r'без\s+\w+[.,]\s*без\s+', 'ряд «без... без...»'),
    (r'через\s+\w+[.,]\s*через\s+', 'ряд «через... через...»'),
    (r'\bне\s+\w+,\s*не\s+\w+,\s*не\s+', 'ряд «не... не... не...»'),
]

STOP_WORDS = [
    "кроме того", "в контексте", "ключевой", "углубиться", "подчёркивая",
    "способствуя", "нюансы", "знаковый", "продемонстрировать", "акцентировать",
    "поистине", "по-настоящему", "в самом сердце", "ландшафт", "свидетельство",
    "в современном мире", "в наше время", "не секрет что", "как известно",
    "стоит отметить", "важно отметить", "важно понимать", "следует учитывать",
    "нельзя не упомянуть", "более того", "таким образом", "в свою очередь",
    "играет ключевую роль", "играет важную роль", "подводя итог", "в заключение",
    "можно сделать вывод", "комплексный подход", "идеально подходит для",
    "раскрыть потенциал", "выйти на новый уровень", "открывает новые горизонты",
    "инновационное решение", "и вот почему", "и вот тут начинается",
    "данный", "данная", "данное", "в рамках", "в целях", "на данный момент",
    "в настоящее время", "представляет собой", "может похвастаться",
]

FAKE_EMPATHY = [
    "вы не одиноки", "вы сильнее, чем думаете", "каждый шаг имеет значение",
    "позвольте себе быть уязвимой", "вы справитесь", "всё будет хорошо",
    "вы делаете всё правильно", "главное - не сдаваться",
]

GUARANTEES = ["излечим", "100%", "навсегда", "гарантируем излечение", "гарантированный результат"]

CHAT_ARTIFACTS = [
    "отличный вопрос", "хороший вопрос", "надеюсь это поможет", "надеюсь, это поможет",
    "давайте рассмотрим", "давайте разберём", "конечно!", "безусловно!",
]

# ============================================================
# ЮРИДИЧЕСКИЙ ЧЕК-ЛИСТ — общий для проекта ВК (см. файлы стиля)
# ============================================================

LEGAL_BANNED = [
    "вылечим", "излечим",
    "лучшие", "первая", "передовая", "непревзойдённые", "профессиональная команда",
    "самая низкая цена",
]

# слово "лечение" рядом (в пределах ~40 символов) со словом зависимости —
# запрещённая по закону конструкция для частной клиники
LECHENIE_PATTERN = re.compile(
    r'лечени\w*[^.!?\n]{0,40}?(алкоголизм\w*|наркоман\w*|запо\w*|зависимост\w*)'
    r'|(алкоголизм\w*|наркоман\w*|запо\w*|зависимост\w*)[^.!?\n]{0,40}?лечени\w*',
    re.IGNORECASE
)

FEAR_MONGERING = ["без помощи он умрёт", "он умрёт", "она умрёт", "они умрут"]


def strip_markup(text):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    return t


def main(path):
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    body = strip_markup(raw)
    low = body.lower()
    problems = []

    print("=" * 64)
    print("ПРОВЕРКА: Premium Clinic (premium-clinic.com) — пост ВК (до 1000 зн.)  |  файл: " + path)
    print("=" * 64)

    # --- объём (параметр клиники) ---
    no_spaces = len(re.sub(r'\s', '', body))
    ok_vol = VMIN <= no_spaces <= VMAX
    print(f"\n[ОБЪЁМ] знаков без пробелов: {no_spaces} (норма {VMIN}-{VMAX})" + ("" if ok_vol else "  !!"))
    if not ok_vol:
        problems.append("объём вне диапазона")

    # ====== ИИ-ЯДРО ======
    print("\n[ИИ-ЯДРО] противопоставление через отрицание:")
    total_crit = 0
    for pat, name in CRIT_PATTERNS:
        for h in re.finditer(pat, low):
            s = max(0, h.start() - 35); e = min(len(body), h.end() + 35)
            total_crit += 1
            print(f"  !! {name}: ...{body[s:e].strip()}...")
    print("  0 - OK" if not total_crit else f"  ВСЕГО: {total_crit} - должно быть 0")
    if total_crit:
        problems.append("конструкции-маркеры")

    print("\n[ИИ-ЯДРО] ряды отрицаний:")
    rows_found = 0
    for pat, name in ROWS:
        n = len(re.findall(pat, low))
        if n:
            rows_found += n
            print(f"  !! {name}: {n}")
    print("  0 - OK" if not rows_found else "")
    if rows_found:
        problems.append("ряды отрицаний")

    print("\n[ИИ-ЯДРО] символы:")
    dash_long = body.count(chr(8212)); dash_short = body.count(chr(8211))
    print(f"  длинное тире: {dash_long}" + ("  !!" if dash_long else " - OK"))
    print(f"  короткое тире: {dash_short}" + ("  !!" if dash_short else " - OK"))
    print(f"  стрелки: {body.count(chr(8594))}   точка с запятой: {body.count(';')}   двоеточия: {body.count(':')}")
    if dash_long or dash_short:
        problems.append("тире")

    yol, straight = body.count('«'), body.count('"')
    if yol and straight:
        print(f"  !! кавычки смешаны: ёлочки {yol}, прямые {straight}")
        problems.append("смешаны кавычки")
    else:
        print(f"  кавычки: ёлочки {yol}, прямые {straight} - единообразно")

    print("\n[ИИ-ЯДРО] лексика:")
    sw = [(w, low.count(w)) for w in STOP_WORDS if w in low]
    print("  стоп-слова: " + (", ".join(f"{w} x{n}" for w, n in sw) + "  !!" if sw else "0 - OK"))
    fe = [w for w in FAKE_EMPATHY if w in low]
    print("  фальшивая эмпатия: " + (", ".join(fe) + "  !!" if fe else "0 - OK"))
    gu = [w for w in GUARANTEES if w in low]
    print("  гарантии: " + (", ".join(gu) + "  !!" if gu else "0 - OK"))
    ca = [w for w in CHAT_ARTIFACTS if w in low]
    print("  артефакты чата: " + (", ".join(ca) + "  !!" if ca else "0 - OK"))
    if sw or fe or gu or ca:
        problems.append("лексика")

    print("\n[ИИ-ЯДРО] частицы же/ведь/вот/-то, >2 на абзац:")
    bad_p = 0
    for i, p in enumerate(body.split('\n\n'), 1):
        n = len(re.findall(r'\b(же|ведь|вот)\b|\w+-то\b', p.lower()))
        if n > 2:
            bad_p += 1
            print(f"  !! абзац {i}: {n}")
    print("  OK" if not bad_p else "")
    if bad_p:
        problems.append("частицы")

    print("\n[ИИ-ЯДРО] смешение кириллицы и латиницы внутри слова:")
    mix = [w for w in re.findall(r'\b(?=\w*[а-яё])(?=\w*[a-z])\w+\b', body, re.I) if not w.startswith('http')]
    print("  " + (", ".join(sorted(set(mix))) + "  !!" if mix else "0 - OK"))
    if mix:
        problems.append("раскладка")

    # ====== ЮРИДИЧЕСКИЙ ЧЕК-ЛИСТ ======
    print("\n[ЮРИДИЧЕСКОЕ]")
    legal_hits = [w for w in LEGAL_BANNED if w in low]
    lechenie_hits = LECHENIE_PATTERN.findall(body)
    if lechenie_hits:
        legal_hits.append(f'"лечение" рядом со словом зависимости x{len(lechenie_hits)}')
    print("  запрещённые формулировки: " + (", ".join(legal_hits) + "  !!" if legal_hits else "0 - OK"))
    fear_hits = [w for w in FEAR_MONGERING if w in low]
    print("  нагнетание страха: " + (", ".join(fear_hits) + "  !!" if fear_hits else "0 - OK"))
    if legal_hits or fear_hits:
        problems.append("юридический чек-лист")

    # ====== параметры клиники / формата ======
    print("\n[ФОРМАТ]")
    bold = len(re.findall(r'\*\*[^*]+\*\*', raw))
    print(f"  жирных фрагментов: {bold} (лимит {BOLD_LIMIT})" + ("  !!" if bold > BOLD_LIMIT else " - OK"))
    if bold > BOLD_LIMIT:
        problems.append("жирного больше лимита")

    long_p = 0
    for i, p in enumerate(body.split('\n\n'), 1):
        p = p.strip()
        if p.startswith('#') or not p:
            continue
        if len(p) / 40 > PARA_LINES + 0.5:
            long_p += 1
            print(f"  !! абзац {i}: ~{round(len(p)/40)} строк (лимит {PARA_LINES})")
    if not long_p:
        print(f"  абзацы в пределах {PARA_LINES} строк - OK")
    else:
        problems.append("длинные абзацы")

    tables = len(re.findall(r'^\|.*\|\s*$', raw, re.M))
    print(f"  markdown-таблиц (строк): {tables}" + ("  !! в тексте запрещены" if tables else " - OK"))
    if tables:
        problems.append("таблицы в тексте")

    print("\n[ССЫЛКИ]")
    links = sorted(set(re.findall(r'https?://[^\s)]+', raw)))
    if links:
        for l in links:
            print("  !! " + l)
        problems.append("найдены ссылки — по новым правилам их быть не должно")
    else:
        print("  0 - OK (ссылок быть не должно)")

    print("\n[ПЛАШКА 18+/ПРОТИВОПОКАЗАНИЯ]")
    disclaimer_hits = re.findall(r'18\+|противопоказани\w*', low)
    if disclaimer_hits:
        print(f"  !! найдено: {', '.join(set(disclaimer_hits))} — по новым правилам плашки быть не должно")
        problems.append("плашка 18+/противопоказания найдена")
    else:
        print("  0 - OK (плашки быть не должно)")

    n_images = len(re.findall(r'!\[', raw))
    print(f"\n[КАРТИНКИ] найдено: {n_images} (норма для ВК: 1)" + ("" if n_images == 1 else "  !!"))
    if n_images != 1:
        problems.append("число картинок не равно 1")

    print("\n" + "=" * 64)
    print("ИТОГ: ГОТОВО К СДАЧЕ" if not problems else "ИТОГ: ЕСТЬ ЗАМЕЧАНИЯ - " + ", ".join(problems))
    print("=" * 64)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'post.md')
