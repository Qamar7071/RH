# RH Labs Website + Backend

```
rh-labs/
  frontend/            website (index.html + images/)
  backend/
    app.py             API: /api/contact, /api/chat, /admin
    chat.py            AI chatbot (Gemini / Groq / OpenAI / Claude)
    knowledge.md       everything the chatbot knows (edit this!)
    storage.py         database (SQLite locally, Postgres live)
    mailer.py          Gmail alerts for new project requests
    check_ai.py        test your AI key
    tests/             26 automated tests
  render.yaml          one-click deploy of the backend on Render
```

---

## 1. Local chalana (apne laptop pe)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
python app.py
```
Browser mein kholo: http://127.0.0.1:5000  (website + backend dono yahin chalenge)

Tests: `python -m pytest -q`

## 2. Chatbot ko real AI dena

1. https://aistudio.google.com pe Google account se login karo, **Get API key** se key banao.
2. `.env` mein: `LLM_PROVIDER=gemini` aur `LLM_API_KEY=apni-key`
3. Check karo: `python check_ai.py "Aap kya services dete ho?"`
   Agar model ka error aaye to AI Studio se current free model ka naam copy karke `LLM_MODEL=` mein daal do.

Chatbot sirf `knowledge.md` se jawab deta hai. Prices, team members, naye FAQs wahin likho. File save karte hi naya jawab shuru (restart ki zaroorat nahi).

Note: Gemini free tier mein Google prompts ko apni services behtar karne ke liye use kar sakta hai, is liye knowledge.md mein koi private info mat likhna.
Agar AI band ho ya key na ho, website khud built-in jawabon pe chali jati hai, chatbot kabhi "dead" nahi hota.

## 3. Gmail alerts (har naye client request ki email)

1. Google Account > Security > 2-Step Verification ON karo.
2. "App passwords" mein naya password banao (16 letters).
3. `.env`: `SMTP_USER=tumhari@gmail.com`, `SMTP_PASSWORD=app-password`, `NOTIFY_EMAIL=tumhari@gmail.com`
4. Email pe "Reply" karoge to seedha client ko jayega.

## 4. Admin panel

`.env` mein `ADMIN_PASSWORD=mazboot-password` rakho, phir `/admin` kholo (user: admin).
Wahan saare project requests aur chatbot ke sawal dikhte hain. `/admin/leads.csv` se Excel download.

## 5. Live karna (free)

**Website (GitHub Pages, hamesha fast):** `frontend` folder ko GitHub repo mein upload karo > Settings > Pages.

**Backend (Render):** poora repo GitHub pe daalo > render.com > New > Blueprint > repo select karo.
Phir Render pe values bharo: `LLM_API_KEY`, `SMTP_*`, `NOTIFY_EMAIL`, `ADMIN_PASSWORD`, `DATABASE_URL`,
aur `ALLOWED_ORIGINS=https://tumhara-username.github.io`

Phir `frontend/index.html` mein: `apiBase: "https://rh-labs-api.onrender.com"` (apna Render URL).

Zaroori baatein (Render free plan):
- 15 minute koi visit na ho to server so jata hai, pehli request pe ~1 minute lagta hai. Website page khulte hi server ko jaga deti hai, aur tab tak chatbot built-in jawab deta hai.
- Free server pe SQLite file restart pe mit jati hai. Leads hamesha mehfooz rakhne ke liye `DATABASE_URL` mein free hosted Postgres (jaise Neon ya Supabase, unka current free plan check kar lena) ka URL daalo. Gmail alerts on hon to har request email mein bhi aa jati hai.

## 6. Website edit karna

`frontend/index.html` ke end mein:
- `SITE`: WhatsApp, email, location, `apiBase`
- `PROJECTS`: project ka title, category, description, links
- `TEAM`: naam, titles (typing effect), bio, skills, links (linkedin, email, portfolio, github, fiverr)

Images `frontend/images/` mein in naamon se daalo (.png / .jpg / .jpeg / .webp sab chalta hai):
`logo`, `team`, `member-1`, `member-2`, `member-3`, `project-1` ... `project-6`
Team photos ke liye background-remove ki hui PNG (cut-out) sab se professional lagti hai.

## Security (jo already laga hai)

- Rate limits: form 5/minute, chat 20/minute har visitor
- Spam trap (hidden field), input validation, 64 KB request limit
- API key sirf backend pe, browser mein kabhi nahi jati
- Admin password-protected, Excel formula injection se bachao, HTML escaping
- `.env` GitHub pe kabhi upload mat karna (`.gitignore` mein already hai)
