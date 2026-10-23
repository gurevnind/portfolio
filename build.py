#!/usr/bin/env python3
"""Сборка статического сайта из дизайн-референсов design/*.dc.html в dist/.

  python3 -m pip install -r requirements.txt
  SITE_URL=https://example.ru python3 build.py

Каждый референс — шаблон с привязками {{ ... }}, style-hover / style-after,
<sc-if>/<sc-for> и классом Component. Сборщик переносит разметку как есть,
превращая привязки в CSS-переменные и data-атрибуты, которые обслуживает
src/site.js. Картинки конвертируются в WebP с несколькими ширинами.
"""
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DESIGN = ROOT / 'design'
ASSETS = DESIGN / 'assets'
SRC = ROOT / 'src'
DIST = ROOT / 'dist'
SITE_URL = os.environ.get('SITE_URL', 'https://gurevnind.ru').rstrip('/')

ACCENT = '#1B44E0'
SITE_JS = 'site.js'  # имя с хэшем содержимого задаётся в main()

# Метатеги подтверждения прав для панелей вебмастера; выводятся только на главной.
VERIFICATION = {
    'yandex-verification': '20485b39baa75f5a',
}
# Ключ IndexNow: файл /<ключ>.txt подтверждает, что уведомления шлёт владелец сайта.
INDEXNOW_KEY = 'd0c705f09210197d3875f06d88c2709b'

PAGES = {
    'Portfolio.dc.html': {
        'route': '/',
        'title': 'Дмитрий Гуревнин — продуктовый дизайнер',
        'desc': 'Портфолио продуктового дизайнера Дмитрия Гуревнина: внутренние data-heavy продукты, высоконагруженные системы, сложные данные и enterprise-сценарии.',
    },
    'Case Sber Platform v3.dc.html': {
        'route': '/cases/sber-platform/',
        'title': 'Корпоративная платформа клиентских данных — кейс · Дмитрий Гуревнин',
        'desc': 'Кейс: корпоративная банковская платформа для работы с данными корпоративных клиентов Сбера — 30 000+ пользователей ежедневно.',
    },
    'Case SberBusiness Consents.dc.html': {
        'route': '/cases/sberbusiness-consents/',
        'title': 'Раздел согласий в СберБизнес — кейс · Дмитрий Гуревнин',
        'desc': 'Кейс: раздел работы с согласиями в СберБизнес для 120 000+ активных пользователей с учётом требований регуляции.',
    },
    'Feature Client Form.dc.html': {
        'route': '/cases/sber-platform/client-form/',
        'title': 'Форма создания клиента — фича · Дмитрий Гуревнин',
        'desc': 'Фича корпоративной платформы: пошаговая форма создания клиента.',
    },
    'Feature Data Domains.dc.html': {
        'route': '/cases/sber-platform/data-domains/',
        'title': 'Домены данных и AI-пространство — фича · Дмитрий Гуревнин',
        'desc': 'Фича корпоративной платформы: управление доменами данных и AI-пространство.',
    },
    'Feature Bulk Operations.dc.html': {
        'route': '/cases/sber-platform/bulk-operations/',
        'title': 'Массовые операции по филиальной сети — фича · Дмитрий Гуревнин',
        'desc': 'Фича корпоративной платформы: автоматизация массовых операций по филиальной сети.',
    },
}
# Старые имена референсов, на которые ещё ссылается код.
ALIASES = {'Case Sber Platform v2.dc.html': 'Case Sber Platform v3.dc.html'}
FEATURE_SLUGS = {
    'Feature Client Form': 'client-form',
    'Feature Data Domains': 'data-domains',
    'Feature Bulk Operations': 'bulk-operations',
}

# Ширины для srcset; оригинал (не шире MAX_W) всегда идёт в src — его же открывает лайтбокс.
MAX_W = 2900
WIDTHS = (960, 1600)
# sizes для картинок, которые на экране заметно уже вьюпорта.
SIZES = {
    'avatar-full': '200px',
    **{n: '(max-width: 640px) 100vw, 420px' for n in ('istanbul', 'dnd', 'mushrooms', 'travel', 'altai', 'altai-nose', 'podcast')},
}
DEFAULT_SIZES = '(min-width: 1792px) 1632px, 100vw'


# ---------------------------------------------------------------- images

image_info = {}


def build_images():
    out = DIST / 'assets'
    out.mkdir(parents=True, exist_ok=True)
    for p in sorted(ASSETS.iterdir()):
        if p.suffix.lower() != '.png':
            if p.is_file():
                shutil.copy2(p, out / p.name)
            continue
        with Image.open(p) as im:
            im.load()
            w, h = im.size
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGBA')
            variants = []
            full_w = min(w, MAX_W)
            for tw in sorted({x for x in WIDTHS if x < full_w} | {full_w}):
                name = p.stem + ('.webp' if tw == full_w else f'-{tw}.webp')
                dst = out / name
                if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
                    th = round(h * tw / w)
                    (im if tw == w else im.resize((tw, th), Image.LANCZOS)).save(dst, 'WEBP', quality=82, method=6)
                variants.append((tw, name))
        image_info[p.stem] = {'w': full_w, 'h': round(h * full_w / w), 'variants': variants}
    print(f'images: {len(image_info)}')


def asset_url(name):
    stem, ext = os.path.splitext(name)
    if ext.lower() == '.png' and stem in image_info:
        return f'/assets/{stem}.webp'
    return f'/assets/{name}'


# ---------------------------------------------------------------- template conversion

TOKEN_RE = re.compile(r'<!--.*?-->|<(/?)([a-zA-Z][\w-]*)((?:\s+[^\s=/>]+(?:="[^"]*")?)*)\s*(/?)>', re.S)
ATTR_RE = re.compile(r'([^\s=/>]+)(?:="([^"]*)")?')
BIND_RE = re.compile(r'{{\s*([\w.]+)\s*}}')
EVENTS = {'onClick': 'click', 'onMouseEnter': 'mouseenter', 'onMouseLeave': 'mouseleave', 'onMouseDown': 'mousedown'}
VOID = {'img', 'br', 'meta', 'input', 'hr', 'source', 'link'}


def map_url(u):
    if u.startswith('./assets/'):
        return asset_url(u[len('./assets/'):])
    m = re.match(r'\./([^#?]+\.dc\.html)(.*)$', u)
    if m:
        name = ALIASES.get(m.group(1), m.group(1))
        if name in PAGES:
            return PAGES[name]['route'] + m.group(2)
    return u


class Converter:
    def __init__(self):
        self.css = []          # сгенерированные правила hover/after
        self.vars = set()      # имена переменных верхнего уровня
        self.for_alias = []    # стек имён переменных sc-for
        self.n = 0
        self.img_count = 0

    def css_value(self, s):
        def rep(m):
            expr = m.group(1)
            head, _, rest = expr.partition('.')
            if rest and head in self.for_alias:
                return f'var(--i-{rest})'
            self.vars.add(expr)
            return f'var(--v-{expr})'
        return BIND_RE.sub(rep, s)

    def rule(self, sel, body, important):
        decls = []
        for d in split_decls(self.css_value(body)):
            k, _, v = d.partition(':')
            decls.append(f'{k.strip()}:{v.strip()}{"!important" if important else ""}')
        self.css.append(f'{sel}{{{";".join(decls)}}}')

    def start_tag(self, tag, attrs):
        if tag == 'sc-if':
            expr = BIND_RE.search(attrs['value']).group(1)
            hint = BIND_RE.search(attrs.get('hint-placeholder-val', '{{ false }}')).group(1)
            return f'<dc-if data-if="{expr}"{"" if hint == "true" else " hidden"}>'
        if tag == 'sc-for':
            expr = BIND_RE.search(attrs['list']).group(1)
            alias = attrs.get('as', 'item')
            self.for_alias.append(alias)
            return f'<dc-for data-for="{expr}" data-as="{alias}"><template>'

        out, classes, data_on, data_a = [], [], [], []
        for k, v in attrs.items():
            if v is None:
                out.append(k)
                continue
            if k == 'style-hover':
                self.n += 1
                classes.append(f'h{self.n}')
                self.rule(f'.h{self.n}:hover', v, True)
                continue
            if k == 'style-after':
                self.n += 1
                classes.append(f'a{self.n}')
                self.rule(f'.a{self.n}::after', v, False)
                continue
            if k in EVENTS:
                data_on.append(f'{EVENTS[k]}:{BIND_RE.search(v).group(1)}')
                continue
            if k == 'ref':
                out.append(f'data-ref="{BIND_RE.search(v).group(1)}"')
                continue
            if k == 'style':
                if 'translate3d({{' in v:
                    out.append('data-track')
                out.append(f'style="{self.css_value(v)}"')
                continue
            m = BIND_RE.fullmatch(v.strip())
            if m:
                data_a.append(f'{k}:{m.group(1)}')
                continue
            if k in ('href', 'src', 'data-full'):
                v = map_url(html.unescape(v))
                v = html.escape(v, quote=True)
            out.append(f'{k}="{v}"')

        if tag == 'img':
            out = self.img_attrs(out)
        if classes:
            out.insert(0, f'class="{" ".join(classes)}"')
        if data_on:
            out.append(f'data-on="{";".join(data_on)}"')
        if data_a:
            out.append(f'data-a="{";".join(data_a)}"')
        return f'<{tag}{"".join(" " + a for a in out)}>'

    def img_attrs(self, out):
        src = next((a for a in out if a.startswith('src="')), None)
        if not src:
            return out
        stem = os.path.splitext(os.path.basename(src[5:-1]))[0]
        info = image_info.get(stem)
        self.img_count += 1
        extra = []
        if info:
            extra.append(f'width="{info["w"]}" height="{info["h"]}"')
            if len(info['variants']) > 1:
                srcset = ', '.join(f'/assets/{n} {w}w' for w, n in info['variants'])
                extra.append(f'srcset="{srcset}" sizes="{SIZES.get(stem, DEFAULT_SIZES)}"')
        # Первая картинка страницы — в первом экране, остальные грузим лениво.
        if self.img_count == 1:
            extra.append('fetchpriority="high"')
        else:
            extra.append('loading="lazy"')
        extra.append('decoding="async"')
        return out + extra

    def text(self, s):
        def rep(m):
            return f'<span data-t="{m.group(1)}" style="display:contents"></span>'
        return BIND_RE.sub(rep, s)

    def convert(self, src):
        res, pos = [], 0
        for m in TOKEN_RE.finditer(src):
            res.append(self.text(src[pos:m.start()]))
            pos = m.end()
            if m.group(0).startswith('<!--'):
                continue
            closing, tag, rawattrs, _ = m.groups()
            tag_l = tag.lower()
            if closing:
                if tag_l == 'img':
                    continue
                if tag_l == 'sc-if':
                    res.append('</dc-if>')
                elif tag_l == 'sc-for':
                    self.for_alias.pop()
                    res.append('</template></dc-for>')
                else:
                    res.append(f'</{tag}>')
                continue
            attrs = {}
            for am in ATTR_RE.finditer(rawattrs):
                attrs[am.group(1)] = am.group(2)
            res.append(self.start_tag(tag, attrs))
        res.append(self.text(src[pos:]))
        return ''.join(res)


def split_decls(s):
    """Делит CSS-декларации по ';' вне скобок и кавычек."""
    out, depth, q, cur = [], 0, None, ''
    for ch in s:
        if q:
            if ch == q:
                q = None
        elif ch in '\'"':
            q = ch
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ';' and depth == 0:
            if cur.strip():
                out.append(cur)
            cur = ''
            continue
        cur += ch
    if cur.strip():
        out.append(cur)
    return out


# ---------------------------------------------------------------- pages

BASE_CSS = (
    'dc-if,dc-for{display:contents}dc-if[hidden]{display:none!important}'
    ':focus-visible{outline:2px solid ' + ACCENT + ';outline-offset:2px}'
    # Точки карусели 6px — расширяем зону нажатия без изменения вида.
    'button[aria-label="Слайд"]{position:relative}'
    'button[aria-label="Слайд"]::before{content:"";position:absolute;inset:-9px -3px}'
)


def abs_url(path):
    return (SITE_URL + path) if SITE_URL else path


def head(meta, css):
    t = html.escape(meta['title'])
    d = html.escape(meta['desc'])
    og_img = abs_url('/og.png')
    canonical = f'<link rel="canonical" href="{abs_url(meta["route"])}">\n' if SITE_URL else ''
    og_url = f'<meta property="og:url" content="{abs_url(meta["route"])}">\n' if SITE_URL else ''
    verify = ''.join(f'<meta name="{k}" content="{v}">\n' for k, v in VERIFICATION.items()) if meta['route'] == '/' else ''
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
{canonical}{verify}<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="Дмитрий Гуревнин">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
{og_url}<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{og_img}">
<style>{css}</style>
</head>
'''


def fix_script(js):
    """Адаптирует логику компонента к ЧПУ-маршрутам."""
    for name, slug in FEATURE_SLUGS.items():
        js = js.replace(f"'{name}'", f"'{slug}'")
    js = js.replace(r"/(Feature [^/?#]+)\.dc\.html/", r"/\/cases\/sber-platform\/([\w-]+)\/?(?:[?#]|$)/")
    js = js.replace("prevHref: './' + m[1] + '.dc.html'", "prevHref: '/cases/sber-platform/' + m[1] + '/'")
    js = re.sub(r"'(\./[^']+?\.dc\.html)'", lambda m: repr(map_url(m.group(1))), js)
    js = re.sub(r"'\./assets/([^']+)'", lambda m: repr(asset_url(m.group(1))), js)
    if '.dc.html' in js:
        raise SystemExit('unmapped .dc.html reference left in script')
    return js


def build_page(fname, meta):
    src = (DESIGN / fname).read_text(encoding='utf-8')
    body = re.search(r'<x-dc>(.*)</x-dc>', src, re.S).group(1)
    helmet_css = ''.join(re.findall(r'<style>(.*?)</style>', re.search(r'<helmet>(.*?)</helmet>', body, re.S).group(1), re.S))
    body = re.sub(r'<helmet>.*?</helmet>', '', body, flags=re.S)

    sm = re.search(r'<script type="text/x-dc"[^>]*data-props="([^"]*)"[^>]*>(.*?)</script>', src, re.S)
    props_spec = json.loads(html.unescape(sm.group(1)))
    props = {k: v.get('default') for k, v in props_spec.items()}
    for k, v in props.items():
        if isinstance(v, str) and v.endswith('.dc.html'):
            props[k] = map_url(v)
    script = fix_script(sm.group(2).strip())

    conv = Converter()
    out_body = conv.convert(body)
    if '{{' in out_body:
        raise SystemExit(f'{fname}: unconverted binding')

    css = minify_css(helmet_css) + BASE_CSS + ''.join(conv.css)
    page = head(meta, css) + '<body>\n' + out_body.strip() + '\n' + f'''<script src="/assets/{SITE_JS}"></script>
<script>window.DC_VARS={json.dumps(sorted(conv.vars))};
{script}
DC.mount(Component,{json.dumps(props, ensure_ascii=False)});</script>
</body>
</html>
'''
    dst = DIST / meta['route'].lstrip('/') / 'index.html'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(page, encoding='utf-8')
    print(f'{meta["route"]:42} {len(page) // 1024} KB, {len(conv.vars)} vars, {conv.n} rules')


def minify_css(s):
    return re.sub(r'\s*\n\s*', '', s).strip()


def build_404():
    meta = {'route': '/404.html', 'title': 'Страница не найдена · Дмитрий Гуревнин', 'desc': 'Такой страницы нет. Вернитесь на главную портфолио Дмитрия Гуревнина.'}
    css = ('body{margin:0;background:#fff;color:#111113;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue","Noto Sans",Arial,sans-serif;-webkit-font-smoothing:antialiased}'
           'a{color:inherit;text-decoration:none}.btn:hover{transform:translateY(-2px);box-shadow:0 2px 4px rgba(17,17,19,.06),0 20px 56px rgba(17,17,19,.12)}'
           '.ghost:hover{border-color:#111113!important}' + BASE_CSS)
    page = head(meta, css).replace('<meta name="description"', '<meta name="robots" content="noindex">\n<meta name="description"') + f'''<body>
<div style="min-height:100vh;display:flex;flex-direction:column">
  <header style="max-width:1792px;width:100%;box-sizing:border-box;margin:0 auto;padding-inline:clamp(20px,4vw,80px);min-height:72px;display:flex;align-items:center">
    <a href="/" style="display:inline-flex;align-items:center;gap:8px;font-size:15px;color:#6c6c74;white-space:nowrap"><i style="width:7px;height:7px;border-radius:50%;background:{ACCENT};display:inline-block"></i>Дмитрий Гуревнин</a>
  </header>
  <main style="flex:1;max-width:1792px;width:100%;box-sizing:border-box;margin:0 auto;padding:clamp(56px,9vw,140px) clamp(20px,4vw,80px) clamp(56px,8vw,120px);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
    <p style="margin:0 0 14px;font-size:clamp(14px,1.1vw,17px);color:{ACCENT};font-weight:500">Ошибка 404</p>
    <h1 style="margin:0;font-size:clamp(30px,5.6vw,68px);line-height:1.04;letter-spacing:-.035em;font-weight:700">Такой страницы нет</h1>
    <p style="margin:clamp(20px,2.4vw,32px) auto 0;max-width:52ch;font-size:clamp(16px,1.25vw,20px);line-height:1.5;color:#6c6c74;text-wrap:pretty">Возможно, ссылка устарела. Кейсы и контакты — на главной.</p>
    <div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;margin-top:clamp(28px,3.4vw,48px)">
      <a class="btn" href="/" style="display:inline-flex;align-items:center;justify-content:center;gap:9px;height:52px;padding:0 26px;border-radius:999px;color:#fff;font-size:16px;font-weight:500;background:{ACCENT};transition:transform .3s cubic-bezier(.22,.61,.36,1),box-shadow .3s">На главную</a>
      <a class="ghost" href="https://t.me/gurevnind" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;justify-content:center;height:52px;padding:0 26px;border-radius:999px;border:1px solid #e4e4e8;font-size:16px;font-weight:500;color:#111113;transition:border-color .25s">Написать в TG</a>
    </div>
  </main>
</div>
</body>
</html>
'''
    (DIST / '404.html').write_text(page, encoding='utf-8')


# ---------------------------------------------------------------- icons, og, seo files

FLOWER_SVG = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><g fill="{ACCENT}"><circle cx="16" cy="4.5" r="4.4"/><circle cx="27.5" cy="16" r="4.4"/><circle cx="16" cy="27.5" r="4.4"/><circle cx="4.5" cy="16" r="4.4"/><circle cx="16" cy="16" r="8"/></g><circle cx="16" cy="16" r="4.2" fill="#fff"/></svg>
'''


def draw_flower(size, color=ACCENT, center='#ffffff'):
    k = 8
    s = size * k
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = s / 32
    for cx, cy, r in ((16, 4.5, 4.4), (27.5, 16, 4.4), (16, 27.5, 4.4), (4.5, 16, 4.4), (16, 16, 8)):
        d.ellipse([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], fill=color)
    d.ellipse([(16 - 4.2) * u, (16 - 4.2) * u, (16 + 4.2) * u, (16 + 4.2) * u], fill=center)
    return im.resize((size, size), Image.LANCZOS)


def find_font(bold):
    cands = (['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
             if bold else
             ['/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def font(bold, size):
    f = find_font(bold)
    return ImageFont.truetype(f, size) if f else ImageFont.load_default()


def build_icons_and_og():
    (DIST / 'favicon.svg').write_text(FLOWER_SVG, encoding='utf-8')
    draw_flower(32).save(DIST / 'favicon.ico', sizes=[(32, 32), (16, 16)])
    touch = Image.new('RGBA', (180, 180), '#ffffff')
    fl = draw_flower(124)
    touch.alpha_composite(fl, (28, 28))
    touch.convert('RGB').save(DIST / 'apple-touch-icon.png')

    # OG 1200×630 в стиле hero: аватар, имя, роль, цветочки.
    W, H = 1200, 630
    og = Image.new('RGBA', (W, H), '#ffffff')
    for x, y, s, o in ((90, 80, 56, 1), (170, 380, 28, .55), (60, 500, 40, .8), (1040, 70, 34, .7), (1090, 280, 64, 1), (980, 500, 24, .5), (900, 170, 18, .4)):
        f = draw_flower(s)
        if o < 1:
            a = f.getchannel('A').point(lambda v, o=o: int(v * o))
            f.putalpha(a)
        og.alpha_composite(f, (x, y))
    with Image.open(ASSETS / 'avatar-full.png') as av:
        av = av.convert('RGBA').resize((190, 190), Image.LANCZOS)
    mask = Image.new('L', (190 * 4, 190 * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 190 * 4 - 1, 190 * 4 - 1], radius=24 * 4, fill=255)
    av.putalpha(mask.resize((190, 190), Image.LANCZOS))
    og.alpha_composite(av, ((W - 190) // 2, 92))
    d = ImageDraw.Draw(og)

    def center(text, y, fnt, fill):
        w = d.textlength(text, font=fnt)
        d.text(((W - w) / 2, y), text, font=fnt, fill=fill)

    center('Дмитрий Гуревнин', 318, font(True, 68), '#111113')
    center('Продуктовый дизайнер, 3 года опыта', 410, font(False, 30), '#111113')
    center('Внутренние data-heavy продукты: высоконагруженные', 478, font(False, 26), '#6c6c74')
    center('системы, сложные данные, enterprise-сценарии', 514, font(False, 26), '#6c6c74')
    og.convert('RGB').save(DIST / 'og.png', optimize=True)


def build_seo_files():
    lines = ['User-agent: *', 'Allow: /']
    if SITE_URL:
        lines.append(f'Sitemap: {SITE_URL}/sitemap.xml')
        urls = ''.join(f'<url><loc>{SITE_URL}{m["route"]}</loc></url>' for m in PAGES.values())
        (DIST / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding='utf-8')
    (DIST / 'robots.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (DIST / f'{INDEXNOW_KEY}.txt').write_text(INDEXNOW_KEY, encoding='utf-8')


def main():
    if DIST.exists():
        for p in DIST.iterdir():
            if p.name != 'assets':
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    DIST.mkdir(exist_ok=True)
    build_images()
    global SITE_JS
    js = (SRC / 'site.js').read_bytes()
    SITE_JS = f'site.{hashlib.sha1(js).hexdigest()[:8]}.js'
    for old in (DIST / 'assets').glob('site.*.js'):
        old.unlink()
    (DIST / 'assets' / SITE_JS).write_bytes(js)
    shutil.copy2(SRC / '_headers', DIST / '_headers')
    for fname, meta in PAGES.items():
        build_page(fname, meta)
    build_404()
    build_icons_and_og()
    build_seo_files()
    if not SITE_URL:
        print('note: SITE_URL не задан — canonical, og:url и sitemap.xml пропущены', file=sys.stderr)


if __name__ == '__main__':
    main()
