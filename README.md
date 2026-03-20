# Blindy2 - Discord Blind Test Bot

A Discord bot for running blind test (music quiz) games in your server. Players guess songs by typing artist names and titles, earning points for correct answers.

## What It Does

- You (the admin) play music manually (Spotify, YouTube, etc.)
- Players type their guesses in a dedicated Discord channel
- The bot validates answers and awards points automatically
- First correct answer locks the question (prevents spam)
- Tracks scores and shows a leaderboard

## What It Doesn't Do

- Does NOT play music automatically
- Does NOT search for songs
- Does NOT host multiple games simultaneously

---

## Setup Guide

### Step 1: Create Discord Bot Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it "Blindy2"
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot" to create the bot user
5. **Enable Privileged Intents** (CRITICAL!):
   - Under "Privileged Gateway Intents"
   - Enable **MESSAGE CONTENT INTENT** ✅
   - Enable **SERVER MEMBERS INTENT** ✅
   - Click "Save Changes"
6. Copy your bot token:
   - Click "Reset Token" (or "Copy" if first time)
   - Save this token somewhere safe - you'll need it soon!

### Step 2: Invite Bot to Your Server

1. Go to "OAuth2" → "URL Generator" in the left sidebar
2. Select these scopes:
   - `bot` ✅
   - `applications.commands` ✅
3. Select these bot permissions:
   - Read Messages/View Channels ✅
   - Send Messages ✅
   - Embed Links ✅
   - Read Message History ✅
4. Copy the generated URL at the bottom
5. Open the URL in your browser
6. Select your Discord server and authorize the bot

### Step 3: Install Python Dependencies

1. Make sure you have Python 3.9 or higher installed:
   ```bash
   python3 --version
   ```

2. Navigate to the project directory:
   ```bash
   cd /path/to/blindbot
   ```

3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```

4. Activate the virtual environment:
   
   **On Linux/Mac:**
   ```bash
   source venv/bin/activate
   ```
   
   **On Windows:**
   ```bash
   venv\Scripts\activate
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 4: Configure the Bot

1. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your bot token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```
   
   Replace `your_actual_bot_token_here` with the token you copied in Step 1.

### Step 5: Run the Bot

1. Make sure your virtual environment is activated (you should see `(venv)` in your terminal)

2. Start the bot:
   ```bash
   python bot.py
   ```

3. You should see:
   ```
   Loaded cog: admin
   Loaded cog: game
   Blindy2 is online!
   Connected to 1 server(s)
   Synced 6 command(s)
   ```

4. Check Discord - your bot should now show as "Online" (green circle)

### Step 6: First-Time Setup in Discord

1. In Discord, go to the channel where you want to play the game (e.g., `#blind-test`)

2. Set the game channel:
   ```
   /set_channel
   ```
   The bot will confirm: "✅ Game channel set to #blind-test"

3. Test your first round:
   ```
   /start_round artist:queen title:bohemian rhapsody
   ```
   The bot announces: "🎵 Round 1 started! Start guessing!"

4. Test guessing by typing in the game channel:
   ```
   queen
   ```
   The bot responds: "✅ [Your Name] got the artist! (+1 point) 🔒 Question locked!"

5. End the round:
   ```
   /end_round
   ```

6. Check scores:
   ```
   /scores
   ```

**Success!** Your bot is working! 🎉

---

## Commands Reference

### Admin Commands (Require "Manage Channels" Permission)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `/set_channel` | None | Set current channel as game channel |
| `/start_round` | `artist`, `title` | Start a new round with the correct answer |
| `/end_round` | None | End the current round and show results |
| `/set_answer` | `artist`, `title` | Fix the answer if you made a typo |
| `/show_answer` | None | Reveal the answer without ending the round |
| `/reset_scores` | `user` (optional) | Reset all scores or a specific user's score |

### User Commands (Available to Everyone)

| Command | Description |
|---------|-------------|
| `/scores` | View top 10 leaderboard |
| `/current` | Show current round status |

### Guessing (Regular Messages)

Just type your guess in the game channel! No command needed.

**Rules:**
- Must be lowercase only (`queen` ✅, `Queen` ❌)
- Must be exact match (no extra words: `queen` ✅, `i think queen` ❌)
- Can guess artist, title, or both
- First correct answer wins and locks the question

**Examples:**
- `queen` → 1 point if correct artist
- `bohemian rhapsody` → 1 point if correct title
- `queen bohemian rhapsody` → 2 points (both correct)
- `bohemian rhapsody queen` → 2 points (order doesn't matter)

---

## How to Play

### For Admins:

1. Set up your music (Spotify, YouTube, etc.)
2. Start a round: `/start_round artist:the beatles title:hey jude`
3. Play the song manually
4. Wait for players to guess
5. When someone guesses correctly (or time runs out), end the round: `/end_round`
6. Repeat!

### For Players:

1. Listen to the song
2. Type your guess in the game channel (lowercase, no extra words)
3. First correct answer wins!
4. Check your score: `/scores`

---

## Scoring System

| What You Type | Points | Example |
|---------------|--------|---------|
| Artist name only | 1 point | `queen` |
| Song title only | 1 point | `bohemian rhapsody` |
| Both (any order) | 2 points | `queen bohemian rhapsody` |

---

## Answer Validation

The bot uses **STRICT** validation to prevent spam:

- ✅ Lowercase only: `queen` accepted, `Queen` rejected
- ✅ Exact match: `queen` accepted, `queen!` rejected
- ✅ No extra words: `queen` accepted, `i think queen` rejected
- ✅ Flexible word order for both: `queen bohemian rhapsody` OR `bohemian rhapsody queen` both work
- ✅ Whitespace normalized: `queen  bohemian  rhapsody` becomes `queen bohemian rhapsody`

**Why silent rejection?**
When a guess is invalid (uppercase, extra words, etc.), the bot doesn't respond at all. This keeps the chat clean and the game moving fast.

---

## Troubleshooting

### Bot doesn't come online

- Check that your `.env` file has the correct token
- Make sure you enabled "Message Content Intent" in the Developer Portal
- Check your internet connection
- Look for error messages in the terminal

### Bot doesn't respond to slash commands

- Wait 1-2 minutes for Discord to cache the commands
- Make sure the bot is online (check terminal)
- Ensure the bot has "Send Messages" permission in that channel
- Try restarting the bot

### Bot doesn't read guesses

- Make sure you set the game channel with `/set_channel` first
- Check that "Message Content Intent" is enabled in the Developer Portal
- Ensure a round is active (use `/start_round`)
- Check that the round isn't locked (someone already answered)

### "Missing Permissions" error

- You need "Manage Channels" permission in Discord
- Ask your server owner to give you a role with this permission
- Server owners always have all permissions

### Scores not saving

- Check that the `data/` directory exists and is writable
- Look for error messages in the terminal
- Make sure there's enough disk space

---

## Stopping the Bot

To stop the bot:
1. Go to the terminal where `bot.py` is running
2. Press `Ctrl+C`
3. The bot goes offline

To start again:
1. Activate virtual environment: `source venv/bin/activate`
2. Run: `python bot.py`

---

## Project Structure

```
blindbot/
├── bot.py                    # Main entry point
├── cogs/                     # Command modules
│   ├── __init__.py
│   ├── game.py              # Game logic & user commands
│   └── admin.py             # Admin commands
├── utils/                    # Helper functions
│   ├── __init__.py
│   ├── answer_checker.py    # Answer validation
│   ├── data_manager.py      # JSON file operations
│   └── checks.py            # Permission checking
├── data/                     # Persistent storage
│   ├── config.json          # Bot settings
│   └── scores.json          # Player scores
├── .env                      # Bot token (secret!)
├── .env.example             # Template for .env
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## Credits

Created for running blind test games in Discord servers.

## License

Free to use and modify for your own Discord server.

---

## Need Help?

If you encounter issues:
1. Check the troubleshooting section above
2. Look at the error messages in the terminal
3. Make sure all setup steps were completed correctly
4. Verify that the bot has the correct permissions in Discord

Have fun with your blind test games! 🎵
