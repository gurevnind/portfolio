# Handoff: Портфолио продуктового дизайнера (Дмитрий Гуревнин)

## Overview
Персональный сайт-портфолио: главная, 2 кейса и 3 страницы фичей (вложены в кейс «Корпоративная платформа»). Цель — **статический сайт**, который деплоится на Netlify / Vercel / Cloudflare Pages и привязывается к собственному домену. Язык контента — русский.

## About the Design Files
Файлы в `design/` — **дизайн-референсы, сделанные в HTML** (`*.dc.html` + рантайм `support.js`). Это прототипы, показывающие точный вид и поведение, а не продакшн-код. Задача — **воссоздать их как обычный статический сайт**. Рекомендуемый стек: **Astro** (статическая сборка, ноль JS по умолчанию, острова для каруселей/лайтбокса) или чистые HTML + CSS + небольшой vanilla JS. React не обязателен.

Открыть референс: запустить любой локальный сервер в `design/` (`npx serve design`) и открыть `Portfolio.dc.html`. Вся разметка и стили — инлайн в шаблоне каждого файла; логика — в `class Component` внизу файла.

## Fidelity
**High-fidelity.** Цвета, типографика, отступы, тексты и взаимодействия — финальные. Воспроизводить пиксель-в-пиксель.

## Pages / Routes
| Референс | Маршрут | Содержание |
|---|---|---|
| `Portfolio.dc.html` | `/` | Hero с фото и контактами, 2 кейса с каруселями, «Немного о моих навыках» (плавающие «цветочки»), «Вне работы» (фото-плитки), CV |
| `Case Sber Platform v3.dc.html` | `/cases/sber-platform` | Кейс: корпоративная платформа клиентских данных. Карусель 9 скринов, боковая навигация по секциям, ссылки на 3 фичи |
| `Case SberBusiness Consents.dc.html` | `/cases/sberbusiness-consents` | Кейс: раздел согласий в СберБизнес |
| `Feature Client Form.dc.html` | `/cases/sber-platform/client-form` | Фича: форма создания клиента (карусель 4 шагов) |
| `Feature Data Domains.dc.html` | `/cases/sber-platform/data-domains` | Фича: домены данных и AI-пространство |
| `Feature Bulk Operations.dc.html` | `/cases/sber-platform/bulk-operations` | Фича: массовые операции (карусель 7 скринов, раскрывающиеся детали) |

Все тексты брать дословно из референсов.

## Global layout
- Контейнер: `max-width:1792px; margin:0 auto; padding-inline:clamp(20px,4vw,80px)`.
- Вертикальный ритм секций: `padding-top:clamp(56px,9vw,140px)`, `padding-bottom:clamp(56px,8vw,120px)`.
- Полностью «резиновый» адаптив, брейкпоинт мобильного поведения JS — `window.innerWidth < 640`. Сетки — `repeat(auto-fit,minmax(min(100%,340px),1fr))`.
- Блоки при масштабе браузера 150%+ не должны раздуваться (используются `clamp()` с верхними границами).

## Components & Interactions

### Header (sticky, все страницы)
`position:sticky; top:0; z-index:100`. В покое — прозрачный. После `scrollY > 12` — «стеклянный»: полупрозрачный белый фон, `backdrop-filter: saturate(190%) brightness(1.06) blur(12px)`, тонкая нижняя граница и тень. Переход `.45s ease` по background / backdrop-filter / box-shadow / border-color. Точные значения — `headerBg/headerBlur/headerShadow/headerBorder` в `renderVals()`.

### Хлебные крошки (фичи)
На страницах фичей: `Главная / Кейс / [Предыдущая фича] / Текущая`. Сегмент «предыдущая фича» показывается, только если `document.referrer` — другая страница фичи (см. `componentDidMount`). Всегда есть путь на главную.

### Карусель скринов
- Трек `display:flex`, слайды `flex:0 0 100%`, сдвиг `transform: translate3d(-i*100%,0,0)`, `transition: transform .6s cubic-bezier(.22,.61,.36,1)`.
- Рамка: `border-radius:32px; overflow:hidden; background:#fff; box-shadow:0 0 0 1px rgba(17,17,19,.06),0 12px 40px rgba(17,17,19,.06)`. Соотношение слайда — из `aspect-ratio` в разметке (обычно `2560/1282` или `16/10`).
- Слева сверху — счётчик `01 / 07` (tabular-nums, 14px). Справа сверху — кнопки ← → 45×45, круглые. Обе — «стеклянные», как header: `background:linear-gradient(180deg,rgba(255,255,255,.42),rgba(255,255,255,.22)); backdrop-filter:saturate(190%) brightness(1.06) blur(12px); border:1px solid rgba(255,255,255,.5); box-shadow: inset 0 1px 0 rgba(255,255,255,.7), 0 4px 16px rgba(17,17,19,.08)`.
- Под каруселью — точки: 6px высота, активная 24px шириной `#111113`, неактивные 6px `#d4d4d8`, переход `.3s`.
- **Зациклена**: с последнего → на первый, с первого «влево» → на последний. Кнопки никогда не дизейблятся.
- **Автопрокрутка** каждые 5 с. Пауза: при наведении курсора, пока открыт лайтбокс, когда вкладка скрыта, и 5 с после ручного переключения.

### Лайтбокс (просмотр скрина)
- Клик по любому скрину интерфейса (`cursor: zoom-in`) открывает его на весь экран поверх затемнения. Если у `<img>` есть `data-full`, открывается полная версия (превью в карусели обрезаны по высоте, полная — нет); `data-ratio` — её пропорция.
- Зум 100–300% шагом 50% (кнопки − / +, индикатор %), при зуме >100% — перетаскивание мышью (grab/grabbing).
- Закрытие: Esc, крестик, клик по фону.
- Окно: горизонтальные скрины — `min(1440px, 100%, 78vh × ratio)`; вертикальные (ratio < 1) — ширина `min(1200px,100%)`, высота `100vh − 140px`, скролл внутри.
- **Мобильная версия**: окно почти на весь экран (`calc(100dvh − 120px)`), горизонтальный скрин поворачивается на 90° и показывается вертикально.
- Фото из «Вне работы» и аватар — НЕ открываются.

### Кнопка «наверх» (все страницы)
Круглая кнопка со стрелкой вверх, fixed в правом нижнем углу; появляется после `scrollY > 600`, плавный скролл к началу.

### «Цветочки»
Декоративные плавающие элементы разного размера на главной (hero и «навыки»). Анимация `flowerFloat` (см. `@keyframes` в helmet). Отключаются при `prefers-reduced-motion: reduce`.

### Прочее
- Бейдж «кейс на проде» с зелёной пульсирующей точкой `#1FA855` (`@keyframes pulse`).
- NDA-оговорка в кейсах (флаг `showNdaNote`, по умолчанию включена).
- «Массовые операции»: блок деталей раскрывается/сворачивается (по умолчанию свёрнут).
- Кнопка «Скачать CV» → `/assets/Gurevnin-CV.pdf`.
- Контакты: `mailto:gurevnind@gmail.com`, Telegram `https://t.me/gurevnind`. LinkedIn убран.

## Design Tokens
**Цвета**
- Текст основной `#111113`, вторичный `#6c6c74`, третичный `#8b8b94` / `#9a9aa3`
- Акцент `#1B44E0` (варианты в тюнинге: `#0B2FA8`, `#2E5BFF`) — ссылки hover, лейблы «Решение N», маркеры
- Фон страницы `#FFFFFF`; поверхности карточек `#F4F4F5`; вторичные `#EFEFF1`, `#E9E9EC`
- Границы/разделители `#E4E4E8`, `#E6E6EA`, `#DEDEDF`; неактивные точки/маркеры `#D4D4D8`, `#C9C9D0`
- Успех/«на проде» `#1FA855`

**Типографика** — системный стек: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", "Noto Sans", Arial, sans-serif`, `-webkit-font-smoothing: antialiased`. Веб-шрифтов нет.
- H1: `clamp(30px,5.6vw,68px)` / 1.04 / `-.035em` / 700
- H1 страниц кейсов/фичей: до ~`clamp(…,…,72px)` / ~0.99–1.04 / 600–700 (см. файлы)
- H2: `clamp(26px,3.2vw,46px)` / 1.1 / `-.028em` / 600
- H3: `clamp(24px,2.6vw,40px)` / 1.08 / `-.026em` / 600
- Body: `clamp(16px,1.25vw,20px)` / 1.5, `max-width:52ch`, `text-wrap:pretty`
- Подписи: 14–15px `#6c6c74`; метрики — `clamp(28px,3vw,46px)` / 600 / tabular-nums, цвет акцента

**Радиусы**: 999px (пилюли, круглые кнопки), 32px (карусели, крупные карточки), 24px (фигуры), 20px (мелкие карточки).
**Тени**: `0 0 0 1px rgba(17,17,19,.06), 0 12px 40px rgba(17,17,19,.06)` (рамки скринов); стеклянная — см. карусель.

## State (на страницу, всё клиентское)
`scrolled` (header), `showTop` (кнопка наверх), `mob` (<640px), `ci` (индекс карусели) + hover/touch-таймеры, `zoom` / `zratio` / `zscale` (лайтбокс), `fromFeature` / `prevLabel` / `prevHref` (крошки), `open` (детали на «Массовых операциях»). Данные не загружаются.

## Assets (`design/assets/`, 50 файлов)
Все скрины уже очищены (замазаны телефоны, заменены названия компаний — на скринах тестовые данные) и подготовлены в 2× разрешении.
- `avatar-full.png` — фото в hero
- Главная, кейс 1: `platform-main, client-card, product-search, consents-search, gov-update, counterparties-search, counterparty-express, counterparty-tenders, quick-search`
- Главная, кейс 2 / кейс СберБизнес: `sb-consents-list, sb-consent-form, sb-consent-recipients, sb-consent-sign, sb-consent-view, sb-consent-states, sb-consent-preview`
- «Вне работы»: `altai, altai-nose, travel, podcast, dnd`
- Кейс платформы: `domains-nav, form-before, form-after, domain-graph, ai-space, design-system`
- Форма клиента: `form-step1..4.png` (превью) + `form-step1..4-full.png` (лайтбокс)
- Домены: `domain-manage, domain-doc, domain-graph, ai-space`
- Массовые операции: `bulk-search, bulk-cover, bulk-spread, bulk-step4..7.png` + `bulk-step4..7-full.png`
- `Gurevnin-CV.pdf` — резюме

При сборке конвертировать PNG в **WebP/AVIF** (например, `astro:assets` или `sharp`), задать `width/height`, `loading="lazy"` для всего ниже первого экрана.

## Deliverables для деплоя
1. Статическая сборка (`dist/`) с ЧПУ-маршрутами из таблицы выше; 404-страница в стиле сайта.
2. `<title>`, `meta description`, Open Graph/Twitter-превью (картинка 1200×630 из hero), favicon.
3. `lang="ru"`, семантические заголовки, `alt` у всех картинок (взять из референсов).
4. Lighthouse ≥ 95 по Performance / Accessibility / SEO.
5. Конфиг для выбранного хостинга (`netlify.toml` или `vercel.json`) и инструкция привязки домена.

## Files
- `design/Portfolio.dc.html` — главная
- `design/Case Sber Platform v3.dc.html`, `design/Case SberBusiness Consents.dc.html` — кейсы
- `design/Feature Client Form.dc.html`, `design/Feature Data Domains.dc.html`, `design/Feature Bulk Operations.dc.html` — фичи
- `design/support.js` — рантайм для просмотра референсов (в продакшн не переносить)
- `design/assets/` — все изображения и CV
- `screenshots/` — эталонные скриншоты страниц сверху вниз для сверки (`NN-home`, `NN-case-platform`, `NN-case-consents`, `NN-feature-client-form`, `NN-feature-domains`, `NN-feature-bulk`). Сравнивать сборку с ними и с живыми референсами.
