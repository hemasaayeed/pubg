# موقع يعرض قناة تليجرام لحظة بلحظة

## الخطوات

### 1) اعمل بوت
- افتح تليجرام وكلم [@BotFather](https://t.me/BotFather)
- ابعتله `/newbot` واتبع التعليمات
- هيديك **Token** زي كده: `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- احتفظ بيه، هتحطه في متغير `BOT_TOKEN`

### 2) ضيف البوت أدمن في القناة
- روح إعدادات القناة (goudzl) → Administrators → Add Admin
- دور على اسم البوت وضيفه (مش لازم صلاحيات كتير، يكفي إنه يشوف الرسايل)

### 3) شغل السيرفر
```bash
pip install -r requirements.txt
export BOT_TOKEN="التوكن بتاعك"
export WEBHOOK_SECRET="اي كلمة سر انت تختارها"
python app.py
```
ده هيشغل السيرفر محليًا على البورت 5000. لكن عشان تليجرام يقدر يوصلك، لازم يكون عندك **رابط عام (public URL)**، يعني محتاج تنشره على استضافة زي:
- [Render](https://render.com) (فيه خطة مجانية)
- [Railway](https://railway.app)
- أي VPS

### 4) قول لتليجرام يبعتلك على السيرفر بتاعك (فعّل الـ Webhook)
بعد ما ترفع السيرفر ويبقى ليه دومين زي `https://your-app.onrender.com`، شغل السطر ده مرة واحدة بس (من أي جهاز فيه إنترنت):

```bash
curl "https://api.telegram.org/bot<التوكن>/setWebhook?url=https://your-app.onrender.com/webhook/<WEBHOOK_SECRET>"
```

استبدل `<التوكن>` و `<WEBHOOK_SECRET>` بنفس القيم اللي حطيتها في env variables.

### 5) خلاص
افتح `https://your-app.onrender.com` في المتصفح، وأي بوست ينزل في القناة هيظهر في الصفحة تلقائيًا خلال ثواني.

## ملاحظات
- الملف `posts.db` هو قاعدة بيانات بسيطة (SQLite) بتتخزن فيها البوستات القديمة، مفيش داعي تلمسها.
- لو غيرت الاستضافة أو الدومين، لازم تعيد الخطوة 4 (setWebhook) بالدومين الجديد.
- لو حبيت تتأكد إن الـ webhook شغال صح: `https://api.telegram.org/bot<التوكن>/getWebhookInfo`
