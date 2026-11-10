# Сборка и деплой

## Сборка

Нужен Python 3.9+ и Pillow (конвертация PNG → WebP, favicon, OG-картинка). Для выкладки в Yandex Cloud — ещё boto3; оба ставятся из `requirements.txt`.

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

## Yandex Cloud (Object Storage)

Сайт лежит в бакете Object Storage с включённым хостингом. Загружает его `deploy_yc.py`: он отправляет только изменившиеся файлы, выставляет `Content-Type` и `Cache-Control` и удаляет из бакета то, чего больше нет в `dist/`.

Отличия от Vercel:
- Object Storage не отдаёт произвольные заголовки, поэтому резюме закрыто от поиска через `robots.txt` (`Disallow: /assets/*.pdf`), а не через `X-Robots-Tag`.
- Для адреса без www нужна запись **ANAME**. В DNS-панели Timeweb такого типа нет, поэтому DNS переезжает в Yandex Cloud DNS, а Timeweb остаётся только регистратором домена.
- HTTP перенаправляется на HTTPS автоматически, как только к бакету подключён сертификат.

Порядок шагов выбран так, чтобы сайт не пропадал во время переезда: пока DNS смотрит на Vercel, всё готовится в Yandex Cloud, а переключение — последний шаг.

### 1. Бакет и загрузка

1. В https://console.yandex.cloud создайте облако и платёжный аккаунт (статус ACTIVE или TRIAL_ACTIVE).
2. Object Storage → Создать бакет:
   - **Имя:** `gurevnind.ru` — должно в точности совпадать с доменом;
   - **Чтение объектов** и **Чтение списка объектов:** «Для всех» (без списка вместо страницы 404 будет ошибка 403).
3. В бакете: Настройки → **Веб-сайт** → режим «Хостинг»: **Главная страница** `index.html`, **Страница ошибки** `404.html` → Сохранить.
4. Сервисный аккаунт: Identity and Access Management → Сервисные аккаунты → Создать, роль `storage.editor`. В нём: Создать новый ключ → **Создать статический ключ доступа**. Сохраните идентификатор и секрет — секрет показывается один раз.
5. Загрузите сайт. Ключи вводите сами, в свой терминал, и никуда не пересылайте:

```bash
cd ~/Downloads/design_handoff_portfolio
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export AWS_ACCESS_KEY_ID=<идентификатор ключа>
export AWS_SECRET_ACCESS_KEY=<секретный ключ>
.venv/bin/python deploy_yc.py --dry-run   # что будет загружено
.venv/bin/python deploy_yc.py
```

6. Проверьте сайт по техническому адресу: http://gurevnind.ru.website.yandexcloud.net/ и http://gurevnind.ru.website.yandexcloud.net/cases/sber-platform/ — должны открыться главная и кейс, а http://gurevnind.ru.website.yandexcloud.net/nope — страница 404.

### 2. Перенаправление www

Создайте второй бакет `www.gurevnind.ru` (доступ можно оставить ограниченным). Настройки → Веб-сайт → режим **«Переадресация»**: **Доменное имя** `gurevnind.ru`, **Протокол** `HTTPS` → Сохранить.

### 3. Сертификат (пока DNS ещё на Timeweb)

1. Certificate Manager → Добавить сертификат → **Сертификат от Let's Encrypt**. Домены: `gurevnind.ru` и `www.gurevnind.ru`. Тип проверки: **DNS**, тип записи **CNAME**.
2. Откройте сертификат: для каждого домена Yandex Cloud покажет CNAME-запись вида `_acme-challenge.gurevnind.ru` → `<…>.cm.yandexcloud.net`. Добавьте обе записи в DNS Timeweb (тип CNAME, хост `_acme-challenge` и `_acme-challenge.www`).
3. Дождитесь статуса **Issued** (обычно до часа).
4. Подключите сертификат к обоим бакетам: бакет → Безопасность → **HTTPS** → Настроить → Источник «Certificate Manager» → выберите сертификат → Сохранить. HTTPS заработает в течение получаса.

### 4. DNS-зона в Yandex Cloud

Cloud DNS → Создать зону: **Зона** `gurevnind.ru.` (с точкой в конце), **Тип** «Публичная». Создайте записи:

| Имя | Тип | Значение |
|---|---|---|
| `@` | ANAME | `gurevnind.ru.website.yandexcloud.net` |
| `www` | ANAME | `www.gurevnind.ru.website.yandexcloud.net` |
| `_acme-challenge` | CNAME | то же значение, что в шаге 3 |
| `_acme-challenge.www` | CNAME | то же значение, что в шаге 3 |
| `@` | MX | скопируйте из Timeweb (`mx1.timeweb.ru`, `mx2.timeweb.ru` с теми же приоритетами) |
| `@` | TXT | скопируйте SPF из Timeweb целиком (`v=spf1 include:_spf.timeweb.ru …`) |

`_acme-challenge` нужны и после переезда — по ним сертификат будет продлеваться сам. MX и TXT — почта на домене: если их не перенести, она перестанет работать.

### 5. Переключение

1. В Timeweb: Домены → `gurevnind.ru` → **NS-серверы** → укажите `ns1.yandexcloud.net` и `ns2.yandexcloud.net`.
2. Делегирование занимает до 24 часов. Проверка: `dig +short NS gurevnind.ru` должен вернуть серверы `yandexcloud.net`.
3. Когда https://gurevnind.ru открывается из Yandex Cloud (`curl -sI https://gurevnind.ru | grep -i server` покажет не Vercel), удалите домены в Vercel → Settings → Domains. Проект Vercel после этого можно удалить; репозиторий на GitHub остаётся хранилищем кода.

### Обновление сайта

```bash
.venv/bin/python build.py && .venv/bin/python deploy_yc.py
git add -A && git commit -m "Обновление" && git push   # чтобы код на GitHub не отставал
```
