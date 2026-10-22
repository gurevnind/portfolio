# Сборка и деплой

## Сборка

Нужен Python 3.9+ и Pillow (конвертация PNG → WebP, favicon, OG-картинка).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
SITE_URL=https://gurevnind.ru .venv/bin/python build.py   # этот домен и так стоит по умолчанию
```

`SITE_URL` (по умолчанию `https://gurevnind.ru`) используется в `canonical`, `og:url`, ссылке на OG-картинку и `sitemap.xml`.

Результат — папка `dist/`:

| Маршрут | Файл |
|---|---|
| `/` | `dist/index.html` |
| `/cases/sber-platform/` | `dist/cases/sber-platform/index.html` |
| `/cases/sberbusiness-consents/` | `dist/cases/sberbusiness-consents/index.html` |
| `/cases/sber-platform/client-form/` | `dist/cases/sber-platform/client-form/index.html` |
| `/cases/sber-platform/data-domains/` | `dist/cases/sber-platform/data-domains/index.html` |
| `/cases/sber-platform/bulk-operations/` | `dist/cases/sber-platform/bulk-operations/index.html` |
| 404 | `dist/404.html` |

Локальный просмотр: `python3 -m http.server 4321 -d dist` → http://127.0.0.1:4321/

## Как устроено

- `build.py` берёт разметку из `design/*.dc.html` как есть. Привязки `{{ … }}` в стилях становятся CSS-переменными, `style-hover` / `style-after` — сгенерированными CSS-правилами, `sc-if` / `sc-for` — элементами `dc-if` / `dc-for`. Класс `Component` каждой страницы переносится без изменений, только ссылки на `*.dc.html` заменяются ЧПУ-маршрутами.
- `src/site.js` (~5 КБ) — замена `support.js`: `setState` / `renderVals`, карусели, лайтбокс и хлебные крошки работают на той же логике, что в референсах, без React.
- Картинки: WebP, `srcset` на 960 / 1600 / исходную ширину, `width/height`, `loading="lazy"` для всего, кроме первой картинки. 55 МБ PNG превращаются в ~10 МБ WebP.

Чтобы поправить текст или вёрстку, редактируйте `design/*.dc.html` и пересобирайте.

## Деплой

Папка `dist/` уже собрана, поэтому команда сборки на хостинге не нужна: залейте `dist/` целиком.

**Netlify.** Конфиг лежит в `netlify.toml` (`publish = "dist"`). Можно перетащить `dist/` в Netlify Drop или подключить репозиторий с закоммиченной `dist/`.
Домен: Site configuration → Domain management → Add a domain. У регистратора пропишите `A @ 75.2.60.5` и `CNAME www <сайт>.netlify.app` либо делегируйте домен на NS Netlify. HTTPS выпускается автоматически.

**Vercel.** Конфиг лежит в `vercel.json` (`outputDirectory: dist`). Команда `npx vercel --prod` из корня проекта.
Домен: Project → Settings → Domains → Add. Пропишите `A @ 76.76.21.21` и `CNAME www cname.vercel-dns.com`.

**Cloudflare Pages.** Workers & Pages → Create → Pages → Upload assets, загрузите `dist/`. Заголовки кэша берутся из `dist/_headers`.
Домен: Custom domains → Set up a domain. Если домен уже в Cloudflare, DNS-записи создадутся сами.

Домен `gurevnind.ru` уже вшит в сборку. Привяжите и апекс `gurevnind.ru`, и `www.gurevnind.ru`; основным сделайте `gurevnind.ru`, чтобы www перенаправлялся на него.
