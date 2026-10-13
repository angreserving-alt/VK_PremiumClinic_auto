#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка поста ВК — Premium Clinic (premium-clinic.com)
Запуск: python3 check.py post_N.md

Параметры этой клиники (должны совпадать с файлом стиля на Google Drive):
  объём до 1000 знаков без пробелов, считается ВЕСЬ пост: заголовок + текст + подпись
  формат: чистый текст, без * # > ` _ ~ и таблиц; единственная разметка — строка картинки ![описание](ссылка)
  структура: первая строка - заголовок, последняя строка - подпись только с должностью (без стажа)
  абзац: не длиннее 3 строк
  картинка: ровно одна, с реальной ссылкой http, БЕЗ подписи под ней
  стаж врача, ссылки на сайт, плашка 18+/противопоказания: запрещены

Блок «ИИ-ядро» идентичен во всех пяти клиниках проекта ВК. Не меняй его
в одном репозитории, не поменяв в остальных.
Только стандартная библиотека Python.
"""
import re, sys

CLINIC = "Premium Clinic (premium-clinic.com)"
VMIN, VMAX = 1, 1000
PARA_LINES = 3
TITLE_MAX = 90
QUOTE_IN_GUILLEMETS = False   # True только у Нарколог Клиник: цитата комментария целиком в «ёлочках» отдельной строкой
CHECK_STORY_PRIVACY = False  # True только у Гармонии: истории без имён, возраста и профессий

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

# слово "лечение" рядом (в пределах ~40 символов) со словом зависимости -
# запрещённая по закону конструкция для частной клиники
LECHENIE_PATTERN = re.compile(
    r'лечени\w*[^.!?\n]{0,40}?(алкоголизм\w*|наркоман\w*|запо\w*|зависимост\w*)'
    r'|(алкоголизм\w*|наркоман\w*|запо\w*|зависимост\w*)[^.!?\n]{0,40}?лечени\w*',
    re.IGNORECASE
)

FEAR_MONGERING = ["без помощи он умрёт", "он умрёт", "она умрёт", "они умрут"]

# ============================================================
# СТАЖ ВРАЧА — запрещён везде: в тексте, в голосе, в подписи
# ============================================================

EXPERIENCE_DIRECT = [
    (r'стаж\w*', 'слово «стаж»'),
    (r'лет\s+(?:опыта|практики|работы)\b', '«N лет опыта/практики/работы»'),
    (r'многолетн\w+', '«многолетний»'),
    (r'опытн\w+\s+(?:врач|нарколог|психиатр|специалист)\w*', '«опытный врач»'),
    (r'годы\s+практики|годы\s+работы', '«годы практики/работы»'),
    (r'\bопыт\w*\s+(?:работы|практики)', '«опыт работы/практики»'),
]
YEARS_RE = re.compile(
    r'\b(?:\d{1,2}|один|одиннадцать|двенадцать|тринадцать|четырнадцать|пятнадцать|шестнадцать|семнадцать|'
    r'восемнадцать|девятнадцать|двадцать|тридцать|сорок|десять|много|несколько|более\s+\w+|свыше\s+\w+)'
    r'\s+(?:лет|года|год)\b', re.I)
DOCTOR_CONTEXT_RE = re.compile(
    r'\b(?:врач\w*|нарколог\w*|психиатр\w*|психотерапевт\w*|работаю|работаем|практик\w*|принимаю|'
    r'опыт\w*|выезжа\w*|вижу\s+такое)\b', re.I)

# ============================================================
# ИСТОРИИ БЕЗ ИМЁН, ВОЗРАСТА И ПРОФЕССИЙ (включается только у Гармонии)
# ============================================================

NAME_STEMS = [
    'Ирин', 'Светлан', 'Наталь', 'Ольг', 'Елен', 'Татьян', 'Людмил', 'Галин', 'Марин', 'Анн',
    'Мари', 'Екатерин', 'Оксан', 'Лидия', 'Лидии', 'Тамар', 'Ларис', 'Валентин', 'Нин', 'Любов',
    'Юли', 'Вер', 'Надежд', 'Алл', 'Тан', 'Лен', 'Свет', 'Наташ', 'Оль', 'Ир',
    'Иван', 'Сергей', 'Алексей', 'Дмитри', 'Андре', 'Михаил', 'Николай', 'Владимир', 'Александр',
    'Евгени', 'Виктор', 'Павел', 'Олег', 'Игор', 'Максим', 'Артём', 'Денис', 'Антон', 'Кирилл', 'Борис',
    'Серёж', 'Коля', 'Кол', 'Саш', 'Вит', 'Дим', 'Андрюш', 'Игорёк',
]
AGE_PATTERNS = [
    r'\b\d{2}[\s-]*(?:лет|летн\w*|года)\b',
    r'\b(?:ей|ему)\s+(?:было\s+)?[а-яё]+(?:\s+[а-яё]+)?\s+(?:лет|года|год)\b',
    r'\b(?:двадцати|тридцати|сорока|пятидесяти|шестидесяти)\w*летн\w*',
    r'\b(?:сорокалетн|пятидесятилетн|шестидесятилетн|тридцатилетн|двадцатилетн)\w*',
]
PROFESSIONS = [
    'экономист', 'бухгалтер', 'учител', 'медсестр', 'инженер', 'менеджер', 'продав',
    'юрист', 'программист', 'преподавател', 'парикмахер', 'повар', 'директор', 'дизайнер',
    'водител', 'строител', 'архитектор', 'журналист',
]

# ============================================================
# ПОМОЩНИКИ
# ============================================================

IMG_LINE_RE = re.compile(r'^\s*!\[[^\]]*\]\([^)]*\)\s*$')
SERVICE_PREFIXES = ('тема:', 'статья:', 'пост:', 'заголовок:', 'title:')


def is_img_line(line):
    return bool(IMG_LINE_RE.match(line))


def strip_markup(text):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    return t


def in_quote(text, pos):
    """Внутри ли позиция в цитате придуманного комментария (только Нарколог Клиник)."""
    if not QUOTE_IN_GUILLEMETS:
        return False
    ls = text.rfind('\n', 0, pos) + 1
    nl = text.find('\n', pos)
    line = text[ls:nl if nl > 0 else len(text)].strip()
    return line.startswith('«') and line.endswith('»')


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]


def main(path):
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    lines = raw.split('\n')
    body = strip_markup(raw)
    low = body.lower()
    problems = []

    print("=" * 64)
    print("ПРОВЕРКА: " + CLINIC + " - пост ВК (до 1000 зн.) | файл: " + path)
    print("=" * 64)

    # --- заголовок и подпись ---
    nonempty = [(i, l.strip()) for i, l in enumerate(lines) if l.strip()]
    print("\n[ЗАГОЛОВОК И ПОДПИСЬ]")
    if len(nonempty) < 3:
        print(" !! в файле меньше трёх непустых строк: нужны заголовок, текст и подпись")
        problems.append("нет структуры заголовок/текст/подпись")
    else:
        title = nonempty[0][1]
        sign = nonempty[-1][1]
        print(f" заголовок: {title}")
        if is_img_line(title):
            print(" !! первая строка - картинка, а должна быть заголовок")
            problems.append("первая строка не заголовок")
        if len(title) > TITLE_MAX:
            print(f" ! заголовок длиннее {TITLE_MAX} знаков ({len(title)}): желательно короче, это предупреждение")
        if title.endswith('.'):
            print(" !! заголовок заканчивается точкой")
            problems.append("точка в конце заголовка")
        for pr in SERVICE_PREFIXES:
            if title.lower().startswith(pr):
                print(f" !! служебный префикс в заголовке: {pr}")
                problems.append("служебный префикс в заголовке")
        print(f" подпись: {sign}")
        sign_low = sign.lower()
        if is_img_line(sign) or 'врач' not in sign_low or re.search(r'\d', sign) or len(sign.split()) > 6:
            print(" !! последняя строка должна быть подписью: только должность («Врач-нарколог»), без цифр и стажа")
            problems.append("нет подписи-должности последней строкой")
        elif title == sign:
            print(" !! заголовок и подпись совпали")
            problems.append("нет подписи")
        else:
            print(" OK")

    # --- объём ---
    no_spaces = len(re.sub(r'\s', '', body))
    ok_vol = VMIN <= no_spaces <= VMAX
    print(f"\n[ОБЪЁМ] знаков без пробелов (заголовок + текст + подпись): {no_spaces} (норма {VMIN}-{VMAX})" + ("" if ok_vol else " !!"))
    if not ok_vol:
        problems.append("объём вне диапазона")

    # --- чистый текст ---
    print("\n[ЧИСТЫЙ ТЕКСТ] разметки быть не должно (кроме строки картинки)")
    markup_hits = []
    for i, l in enumerate(lines, 1):
        if is_img_line(l):
            continue
        s = l.strip()
        if '*' in l:
            markup_hits.append((i, '*', s))
        if '#' in l:
            markup_hits.append((i, '#', s))
        if s.startswith('>'):
            markup_hits.append((i, '> (цитата)', s))
        if '`' in l:
            markup_hits.append((i, '`', s))
        if '~~' in l:
            markup_hits.append((i, '~~', s))
        if re.search(r'(^|\s)_[^_\n]+_(\s|$|[.,!?])', l):
            markup_hits.append((i, '_курсив_', s))
        if re.match(r'^\|.*\|\s*$', s):
            markup_hits.append((i, 'таблица', s))
        if re.match(r'^\s*\[[^\]]+\]\([^)]*\)', s) or re.search(r'\[[^\]]+\]\(https?://', l):
            markup_hits.append((i, '[ссылка](url)', s))
    if markup_hits:
        for i, kind, s in markup_hits:
            print(f" !! строка {i}: {kind}: {s[:70]}")
        problems.append("в тексте есть разметка")
    else:
        print(" 0 - OK")
    if re.search(r'подпись\s*:', low):
        print(" !! в тексте осталось слово «Подпись:»")
        problems.append("слово «Подпись:» в тексте")

    # ====== ИИ-ЯДРО ======
    print("\n[ИИ-ЯДРО] противопоставление через отрицание:")
    total_crit = 0
    for pat, name in CRIT_PATTERNS:
        for h in re.finditer(pat, low):
            s = max(0, h.start() - 35); e = min(len(body), h.end() + 35)
            if in_quote(body, h.start()):
                print(f" (в цитате, править не нужно): ...{body[s:e].strip()}...")
                continue
            total_crit += 1
            print(f" !! {name}: ...{body[s:e].strip()}...")
    print(" 0 - OK" if not total_crit else f" ВСЕГО: {total_crit} - должно быть 0")
    if total_crit:
        problems.append("конструкции-маркеры")

    print("\n[ИИ-ЯДРО] ряды отрицаний:")
    rows_found = 0
    for pat, name in ROWS:
        n = len(re.findall(pat, low))
        if n:
            rows_found += n
            print(f" !! {name}: {n}")
    print(" 0 - OK" if not rows_found else "")
    if rows_found:
        problems.append("ряды отрицаний")

    print("\n[ИИ-ЯДРО] символы:")
    dash_long = body.count(chr(8212)); dash_short = body.count(chr(8211))
    print(f" длинное тире: {dash_long}" + (" !!" if dash_long else " - OK"))
    print(f" короткое тире: {dash_short}" + (" !!" if dash_short else " - OK"))
    print(f" стрелки: {body.count(chr(8594))} точка с запятой: {body.count(';')} двоеточия: {body.count(':')}")
    if dash_long or dash_short:
        problems.append("тире")

    yol, straight = body.count('«'), body.count('"')
    if yol and straight:
        print(f" !! кавычки смешаны: ёлочки {yol}, прямые {straight}")
        problems.append("смешаны кавычки")
    else:
        print(f" кавычки: ёлочки {yol}, прямые {straight} - единообразно")

    print("\n[ИИ-ЯДРО] лексика:")
    sw = [(w, low.count(w)) for w in STOP_WORDS if w in low]
    print(" стоп-слова: " + (", ".join(f"{w} x{n}" for w, n in sw) + " !!" if sw else "0 - OK"))
    fe = [w for w in FAKE_EMPATHY if w in low]
    print(" фальшивая эмпатия: " + (", ".join(fe) + " !!" if fe else "0 - OK"))
    gu = [w for w in GUARANTEES if w in low]
    print(" гарантии: " + (", ".join(gu) + " !!" if gu else "0 - OK"))
    ca = [w for w in CHAT_ARTIFACTS if w in low]
    print(" артефакты чата: " + (", ".join(ca) + " !!" if ca else "0 - OK"))
    if sw or fe or gu or ca:
        problems.append("лексика")

    print("\n[ИИ-ЯДРО] частицы же/ведь/вот/-то, >2 на абзац:")
    bad_p = 0
    for i, p in enumerate(body.split('\n\n'), 1):
        n = len(re.findall(r'\b(же|ведь|вот)\b|\w+-то\b', p.lower()))
        if n > 2:
            bad_p += 1
            print(f" !! абзац {i}: {n}")
    print(" OK" if not bad_p else "")
    if bad_p:
        problems.append("частицы")

    print("\n[ИИ-ЯДРО] смешение кириллицы и латиницы внутри слова:")
    mix = [w for w in re.findall(r'\b(?=\w*[а-яё])(?=\w*[a-z])\w+\b', body, re.I) if not w.startswith('http')]
    print(" " + (", ".join(sorted(set(mix))) + " !!" if mix else "0 - OK"))
    if mix:
        problems.append("раскладка")

    # ====== ЮРИДИЧЕСКИЙ ЧЕК-ЛИСТ ======
    print("\n[ЮРИДИЧЕСКОЕ]")
    legal_hits = [w for w in LEGAL_BANNED if w in low]
    lechenie_hits = LECHENIE_PATTERN.findall(body)
    if lechenie_hits:
        legal_hits.append(f'"лечение" рядом со словом зависимости x{len(lechenie_hits)}')
    print(" запрещённые формулировки: " + (", ".join(legal_hits) + " !!" if legal_hits else "0 - OK"))
    fear_hits = [w for w in FEAR_MONGERING if w in low]
    print(" нагнетание страха: " + (", ".join(fear_hits) + " !!" if fear_hits else "0 - OK"))
    if legal_hits or fear_hits:
        problems.append("юридический чек-лист")

    # ====== СТАЖ ВРАЧА ======
    print("\n[СТАЖ ВРАЧА] (запрещён в тексте и в подписи)")
    exp_hits = []
    for pat, name in EXPERIENCE_DIRECT:
        for h in re.finditer(pat, low):
            s = max(0, h.start() - 30); e = min(len(body), h.end() + 30)
            exp_hits.append(f"{name}: ...{body[s:e].strip()}...")
    for sent in sentences(body):
        if YEARS_RE.search(sent) and DOCTOR_CONTEXT_RE.search(sent):
            exp_hits.append(f"годы рядом с врачом/работой: {sent[:90]}")
    if exp_hits:
        for h in exp_hits:
            print(" !! " + h)
        problems.append("упоминание стажа врача")
    else:
        print(" 0 - OK")

    # ====== ИСТОРИИ БЕЗ ИМЁН (только Гармония) ======
    if CHECK_STORY_PRIVACY:
        print("\n[ИСТОРИИ БЕЗ ИМЁН, ВОЗРАСТА И ПРОФЕССИЙ]")
        age_hits = []
        for pat in AGE_PATTERNS:
            for h in re.finditer(pat, low):
                s = max(0, h.start() - 25); e = min(len(body), h.end() + 25)
                age_hits.append(body[s:e].strip())
        if age_hits:
            for h in age_hits:
                print(" !! возраст героя: ..." + h + "...")
            problems.append("возраст героя истории")
        name_hits = []
        for st in NAME_STEMS:
            for m in re.finditer(r'(?<![А-Яа-яЁё])' + st + r'[а-яё]{0,4}(?![А-Яа-яЁё])', body):
                name_hits.append(m.group(0))
        name_hits = sorted(set(name_hits))
        if name_hits:
            print(" ! возможные имена (предупреждение, смотрите глазами): " + ", ".join(name_hits))
        prof_hits = sorted({p for p in PROFESSIONS if p in low})
        if prof_hits:
            print(" ! возможные профессии героев (предупреждение): " + ", ".join(prof_hits))
        if not (age_hits or name_hits or prof_hits):
            print(" 0 - OK")

    # ====== параметры клиники / формата ======
    print("\n[ФОРМАТ]")
    long_p = 0
    for i, p in enumerate(body.split('\n\n'), 1):
        p = p.strip()
        if not p:
            continue
        if len(p) / 40 > PARA_LINES + 0.5:
            long_p += 1
            print(f" !! абзац {i}: ~{round(len(p)/40)} строк (лимит {PARA_LINES})")
    if not long_p:
        print(f" абзацы в пределах {PARA_LINES} строк - OK")
    else:
        problems.append("длинные абзацы")

    print("\n[ССЫЛКИ]")
    raw_no_img = '\n'.join(l for l in lines if not is_img_line(l))
    links = sorted(set(re.findall(r'https?://[^\s)]+', raw_no_img)))
    if links:
        for l in links:
            print(" !! " + l)
        problems.append("найдены ссылки - по новым правилам их быть не должно")
    else:
        print(" 0 - OK (ссылок на сайт быть не должно; ссылка внутри строки картинки не считается)")

    print("\n[ПЛАШКА 18+/ПРОТИВОПОКАЗАНИЯ]")
    disclaimer_hits = re.findall(r'18\+|противопоказани\w*', low)
    if disclaimer_hits:
        print(f" !! найдено: {', '.join(set(disclaimer_hits))} - по новым правилам плашки быть не должно")
        problems.append("плашка 18+/противопоказания найдена")
    else:
        print(" 0 - OK (плашки быть не должно)")

    # ====== КАРТИНКА ======
    print("\n[КАРТИНКА] норма для ВК: ровно одна ![описание](http...), без подписи под ней")
    n_all = len(re.findall(r'!\[', raw))
    img_lines = [(i, l) for i, l in enumerate(lines) if is_img_line(l)]
    print(f" найдено конструкций ![: {n_all}, строк-картинок: {len(img_lines)}" + ("" if n_all == 1 and len(img_lines) == 1 else " !!"))
    if n_all != 1 or len(img_lines) != 1:
        problems.append("картинок не одна или строка картинки оформлена неверно")
    for i, l in img_lines:
        m = re.match(r'^\s*!\[([^\]]*)\]\(([^)]*)\)\s*$', l)
        alt, url = m.group(1).strip(), m.group(2).strip()
        if not alt:
            print(" !! пустое описание ![]()")
            problems.append("у картинки пустое описание")
        if not url.startswith('http'):
            print(f" !! вместо ссылки заглушка: {url[:60]}")
            problems.append("вместо ссылки на картинку заглушка")
        elif re.search(r'\.\.\.|…|example\.com|placeholder', url, re.I):
            print(f" !! похоже на выдуманную ссылку: {url[:60]}")
            problems.append("выдуманная ссылка на картинку")
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        if nxt.strip():
            print(f" !! сразу под картинкой стоит текст-подпись: {nxt.strip()[:60]}")
            problems.append("подпись под картинкой")
        else:
            print(" OK: под картинкой подписи нет")
    if re.search(r'\[\s*изображение', low):
        print(" !! осталась текстовая метка [ИЗОБРАЖЕНИЕ ...] вместо картинки")
        problems.append("текстовая метка вместо картинки")

    print("\n" + "=" * 64)
    print("ИТОГ: ГОТОВО К СДАЧЕ" if not problems else "ИТОГ: ЕСТЬ ЗАМЕЧАНИЯ - " + ", ".join(sorted(set(problems))))
    print("=" * 64)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'post.md')
