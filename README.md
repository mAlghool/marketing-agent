# Marketing Agent — وكيل التسويق

وكيل يولّد محتوى السوشيال ميديا، يجدوله، ثم ينشره تلقائيًا على **Facebook Page** و**Instagram** و**TikTok**، مع لوحة تحكم بسيطة للمراجعة والاعتماد قبل النشر.

## المكوّنات

| الملف | الوظيفة |
| --- | --- |
| `app/agent.py` | توليد المحتوى بالـ LLM حسب هدف الحملة والجمهور ونبرة العلامة، مع إرشادات مخصّصة لكل منصة |
| `app/publishers/meta.py` | النشر على صفحة فيسبوك (feed/photos) وإنستجرام (media container ثم media_publish، مع دعم Reels) |
| `app/publishers/tiktok.py` | النشر عبر TikTok Content Posting API بأسلوب `PULL_FROM_URL` |
| `app/scheduler.py` | APScheduler يفحص المنشورات المستحقة كل فترة وينشرها مع إعادة محاولة محدودة |
| `app/main.py` | واجهة REST + لوحة التحكم |

دورة حياة المنشور: `draft → approved → publishing → published` (أو `failed` بعد استنفاد المحاولات، أو `cancelled`).

## التشغيل

```bash
cp .env.example .env   # املأ المفاتيح
uv venv && uv pip install -e ".[dev]"
uvicorn app.main:app --reload
```

افتح http://localhost:8000 للوحة التحكم، و`/docs` لتوثيق الـ API.

> النشر الفعلي معطّل افتراضيًا. فعّله بـ `PUBLISHING_ENABLED=true` بعد ضبط التوكنات.

## المفاتيح المطلوبة

- `OPENAI_API_KEY` — لتوليد المحتوى.
- `META_ACCESS_TOKEN` + `FACEBOOK_PAGE_ID` + `INSTAGRAM_USER_ID` — توكن Page طويل الأجل بصلاحيات `pages_manage_posts`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`. حساب إنستجرام يجب أن يكون Business/Creator ومربوطًا بالصفحة.
- `TIKTOK_ACCESS_TOKEN` — توكن بصلاحية `video.publish`. النطاق المستضيف للفيديو يجب أن يكون موثّقًا (verified domain) في تطبيق TikTok.

إنستجرام وتيك توك يتطلبان `media_url` عام يمكن للمنصة تحميله؛ فيسبوك يقبل نصًا فقط.

## الـ API

| Endpoint | الوصف |
| --- | --- |
| `POST /api/campaigns` | إنشاء حملة (هدف، جمهور، نبرة، هاشتاجات) |
| `POST /api/campaigns/{id}/generate` | توليد منشورات وجدولتها بفاصل زمني |
| `GET /api/posts` | عرض المنشورات مع فلترة بالحالة/المنصة |
| `PATCH /api/posts/{id}` | تعديل النص أو الميديا أو الموعد |
| `POST /api/posts/{id}/approve` | اعتماد المنشور ليدخل جدول النشر |
| `POST /api/posts/{id}/publish` | نشر فوري |
| `DELETE /api/posts/{id}` | إلغاء المنشور |

## الاختبارات

```bash
pytest && ruff check .
```

الاختبارات تحاكي الـ APIs عبر `httpx.MockTransport` فلا تُرسل أي طلب حقيقي.
