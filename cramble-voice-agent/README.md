# Cramble Voice Agent — "Emma"

Emma is an AI phone host for **Cramble Restaurant**. Guests talk to her (in the browser, or by
calling a real phone number), and she:

- **books tables**: checks if there's space, repeats the booking back, and saves it
- **takes event bookings**: birthdays, anniversaries, corporate dinners, big groups
- **answers menu questions**: describes dishes like a waiter who loves the food
- **takes callback requests**: complaints and questions she can't answer

Every booking goes into a **Google Sheet**, and the owner gets an **email** for each one.
A copy of all bookings is saved to local CSV files once a day.

```
Guest speaks ─► Groq Whisper (hears) ─► Groq Llama 3.3 (thinks) ─► Cartesia (speaks)
                                              │
                                              ├─► Google Sheet  (bookings)
                                              └─► Gmail         (alert to owner)
```

---

## What's in this folder

| File / folder | What it is | Will you edit it? |
|---|---|---|
| `restaurant_data.json` | Name, hours, menu, prices, event packages, table limits | **Yes**, your real details go here |
| `system_prompt.txt` | Emma's personality and rules | Optional |
| `.env.example` | A list of every key needed | Copy it to `.env` and fill it in |
| `server.py` | Starts everything | No |
| `cramble/` | The code (booking logic, sheets, email, voice) | No |
| `static/index.html` | The "Start Call" test page | No |
| `scripts/check_setup.py` | Tests all your keys | No, just run it |
| `scripts/chat_test.py` | Chat with Emma by typing (no mic needed) | No, just run it |
| `Dockerfile`, `railway.json` | Settings for running 24/7 on Railway | No |
| `tests/` | Automatic checks of the booking rules | No |

---

## Step 1: Get your free API keys

You need **2 keys to start**. Everything else can come later.

### 1a. Groq (Emma's ears and brain): free

1. Go to **https://console.groq.com** and sign up (Google sign-in works).
2. On the left, click **API Keys**, then **Create API Key**.
3. Name it `cramble` and click **Submit**.
4. **Copy the key now.** It starts with `gsk_`, and Groq only shows it once.
5. Keep it somewhere safe for Step 3.

### 1b. Cartesia (Emma's voice): free tier

1. Go to **https://play.cartesia.ai** and sign up.
2. Click **API Keys** (in the left menu or under your profile), then **New key**.
3. Name it `cramble`, create it, and **copy the key**.
4. *(Optional)* Want a different voice? Open **Voices**, play a few, and when you find one you like,
   copy its **Voice ID**. You'll paste it as `CARTESIA_VOICE_ID` in Step 3.

---

## Step 2: Install on your computer

1. **Install Python 3.12** from https://www.python.org/downloads/
   *Windows:* on the first install screen, **tick "Add python.exe to PATH"**.
2. **Download this project.** On GitHub, open the repository, click the green **Code** button, then
   **Download ZIP**, and unzip it. (If the code is still on a branch, pick that branch in the branch
   menu first.)
3. **Open a terminal in the `cramble-voice-agent` folder.**
   *Windows:* open the folder in File Explorer, click the address bar, type `cmd`, and press Enter.
   *Mac:* right-click the folder and choose **New Terminal at Folder**.
4. Copy and paste these commands one at a time:

   **Windows**
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
   **Mac**
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   The install takes a few minutes. Next time you only need the middle line (`activate`).

---

## Step 3: Create your `.env` file (where the keys go)

1. In the project folder, **copy** `.env.example` and name the copy exactly `.env`.
   *Windows tip:* if you can't see file extensions, open File Explorer and turn on
   **View → Show → File name extensions** first.
2. Open `.env` with Notepad (Windows) or TextEdit (Mac).
3. Paste your keys after the `=` signs, with no spaces and no quotes:
   ```
   GROQ_API_KEY=gsk_abc123...
   CARTESIA_API_KEY=sk_car_...
   ```
4. Save.

> `.env` is on the project's ignore list, so it will **never** be uploaded to GitHub. Never email it
> or paste it anywhere.

---

## Step 4: Test it

```
python scripts/check_setup.py
```
You should see `[OK]` next to Groq and Cartesia. `[--]` just means "not set up yet", which is fine.

**Test by typing (quickest):**
```
python scripts/chat_test.py
```
Try: *"Hi, can I book a table for 4 this Friday at 8pm?"*

**Test by talking:**
```
python server.py
```
Then open **http://localhost:7860** in **Chrome**, click **Start Call**, allow the microphone,
and talk. Headphones work best, because otherwise Emma can hear herself through your speakers. Press
`Ctrl + C` in the terminal to stop the server.

Until Google Sheets is set up, bookings are saved in `data/bookings/` as CSV files, which you can
open with Excel.

---

## Step 5: Connect Google Sheets (free)

This part has the most clicks. Take it slowly.

**A. Create a "robot" Google account (a service account)**
1. Go to **https://console.cloud.google.com** and sign in with your Gmail.
2. At the top, click the project picker, then **New Project**. Name it `Cramble` and click **Create**.
   Make sure `Cramble` is selected at the top afterwards.
3. In the search bar at the top, type **Google Sheets API**, open it, and click **Enable**.
4. Search **Google Drive API**, open it, and click **Enable**.
5. Search **Service Accounts**, open it, and click **+ Create service account**.
   Name it `cramble-bot`, then click **Create and continue**, then **Done** (skip the optional steps).
6. Click the new `cramble-bot` account, open the **Keys** tab, then
   **Add key → Create new key → JSON → Create**. A file downloads.
7. **Rename that file to `google-credentials.json`** and move it into the project folder (next to
   `server.py`). It's a password, so never share it. It's already on the ignore list.

**B. Create the sheet and share it with the robot**
1. Go to **https://sheets.google.com** and create a blank sheet named `Cramble Bookings`.
2. Open `google-credentials.json` with Notepad and find the line `"client_email": "cramble-bot@...iam.gserviceaccount.com"`.
   Copy that email address.
3. In your sheet, click **Share**, paste that email, set it to **Editor**, untick "Notify", and click **Share**.
4. Look at the sheet's web address:
   `https://docs.google.com/spreadsheets/d/`**`1AbCdEf...xyz`**`/edit`
   Copy the bold part (the long ID) and add it to `.env`:
   ```
   GOOGLE_SHEET_ID=1AbCdEf...xyz
   ```
5. Run `python scripts/check_setup.py`. It creates the **Table Bookings**, **Event Bookings** and
   **Callbacks** tabs with headers automatically.

The **Status** column has a dropdown (Pending / Ready / Done / Cancelled). New bookings start as
*Pending*, and your team updates the status by hand. Rows marked **Cancelled** free up the table again.

---

## Step 6: Email alerts to the owner (free, using Gmail)

1. Use a Gmail account that will **send** the alerts (it can be your own).
2. Turn on 2-Step Verification: https://myaccount.google.com/signinoptions/twosv
3. Go to **https://myaccount.google.com/apppasswords**, type the name `Cramble`, and click **Create**.
4. Copy the 16-letter password (the spaces don't matter).
5. In `.env`:
   ```
   OWNER_EMAIL=owner@example.com       (who receives the alerts)
   GMAIL_ADDRESS=yourname@gmail.com    (the Gmail that sends them)
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   ```
6. Test it: `python scripts/check_setup.py --email`

Each booking sends an email such as **"New Table Booking — Sarah, 4 guests, Fri 9 Oct 8 PM"**.
If Google Sheets is ever down during a call, the booking is written to
`data/unsaved_bookings_failsafe.csv` and the owner gets an **"ACTION NEEDED"** email, so nothing is lost.

---

## How to edit the restaurant details (no coding)

Open `restaurant_data.json` in Notepad or TextEdit and change the text **between the quotes**.

- **Hours:** `"tuesday": { "open": "12:00", "close": "22:00" }` uses the 24-hour clock. Write `"closed"` for days off.
- **Holidays:** add dates to `"closed_dates": ["2026-12-25"]`.
- **Table limits:** `"tables_per_time_slot": 10` means 10 bookings per hour. `"max_group_size": 8` means
  bigger groups become event bookings.
- **Menu:** copy a whole dish line (from `{` to `},`) and change the name, price, description and tags.
- **Timezone:** `"timezone": "America/New_York"`. Pick yours from
  https://en.wikipedia.org/wiki/List_of_tz_database_time_zones (TZ identifier column).

**Rules so the file keeps working:** keep every quote `"` and every comma `,` between items, and
**no comma after the last item** in a list. If something breaks, paste the file into
**https://jsonlint.com** and it will point to the mistake. `python scripts/check_setup.py` checks it too.

Changes apply on the **next call**, with no restart needed. (On Railway, you edit the file on GitHub and
Railway redeploys by itself.)

---

## Step 7: Run it 24/7 on Railway

Railway costs about **$5 a month** (Hobby plan, and new accounts get trial credit). It keeps Emma
online all the time.

1. Go to **https://railway.com** and sign in with GitHub.
2. Click **New Project**, then **Deploy from GitHub repo**, and pick this repository.
   *If this project sits inside a bigger repository*, open the service's **Settings**, set
   **Root Directory** to `/cramble-voice-agent`, and save.
3. Open the service, go to the **Variables** tab, and click **Raw Editor**. Paste everything from your
   `.env`, with **one change**: Railway can't see your `google-credentials.json` file, so delete
   the `GOOGLE_SERVICE_ACCOUNT_FILE` line, and add
   `GOOGLE_SERVICE_ACCOUNT_JSON=` followed by the **entire contents** of the credentials file pasted
   on the same line. Remove the `PORT` line, because Railway sets the port itself.
4. Go to **Settings → Networking** and click **Generate Domain**. You get an address like
   `https://cramble-voice-agent-production.up.railway.app`.
5. Add one more variable: `PUBLIC_URL=` followed by that address.
6. Wait for the deploy to turn green. Visiting `https://YOUR-ADDRESS/health` should show `{"ok":true,...}`.
7. *(Recommended)* So the daily CSV backups survive redeploys, right-click the service, choose
   **Attach Volume**, and set the mount path to `/app/data`.

> **Note:** the browser "Start Call" page is meant for **testing on your own computer**. Railway's
> network can block the direct browser audio connection (WebRTC). Phone calls through Twilio work fine
> on Railway.

---

## Step 8: Connect a real phone number (Twilio, optional)

1. Sign up at **https://www.twilio.com/try-twilio**. The free trial gives you credit and a number,
   but during the trial callers hear a short Twilio message first, and only phone numbers you have
   verified can call. Upgrading (about $1–2 a month for a number, plus about 1–2 cents a minute)
   removes both limits.
2. In the Twilio Console, go to **Phone Numbers → Manage → Buy a number**, pick one with **Voice**, and buy it.
3. Go to **Phone Numbers → Manage → Active numbers** and click your number.
4. Under **Voice Configuration**, find **"A call comes in"** and set:
   - **Webhook**: `https://YOUR-RAILWAY-ADDRESS/twilio/incoming`
   - **HTTP POST**
   Click **Save configuration**.
5. On the Twilio Console home page, copy your **Account SID** and **Auth Token** into Railway
   **Variables** as `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` (this lets Emma hang up cleanly).
6. Call the number. Emma answers!

*Testing phone calls before deploying:* install **ngrok** (https://ngrok.com), run `ngrok http 7860`
while `python server.py` is running, and use the `https://....ngrok-free.app/twilio/incoming` address
in step 4 instead.

---

## Costs (cheapest setup)

| Service | Cost |
|---|---|
| Groq (speech recognition and AI) | Free tier (rate-limited, plenty for testing and a small restaurant) |
| Cartesia (voice) | Free monthly allowance, then a paid plan if you need more |
| Google Sheets and Gmail | Free |
| Railway (24/7 hosting) | About $5 a month |
| Twilio phone number | About $1–2 a month plus about 1–2 cents a minute (optional) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognised | Reinstall Python and tick **Add to PATH**. On Mac, use `python3`. |
| The page says "Microphone blocked" | Click the lock icon in Chrome's address bar and allow the microphone. |
| Emma interrupts herself or repeats | Use headphones. |
| Google Sheets says 403 / permission | Share the sheet with the `client_email` as **Editor** (Step 5B). |
| Email fails | Use the 16-letter **app password**, not your normal Gmail password. |
| Groq "rate limit" error | The free tier is busy. Wait a minute, or add billing on console.groq.com. |
| Something else | Copy the red error text from the terminal and ask for help. |

## For developers

- Run the tests: `python -m unittest discover tests`
- Booking IDs: `CR-T-0001` (tables), `CR-E-0001` (events), `CR-C-0001` (callbacks)
- Capacity: bookings are counted per `time_slot_minutes` bucket (default 1 hour), so 20:00 and 20:30
  share the 20:00 slot.
- Pipecat moved some modules between versions. `requirements.txt` pins `<0.1` and the code tries both
  the old and new import paths.
