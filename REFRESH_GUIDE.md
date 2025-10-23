# Auto-Refresh Setup Guide

## How to Use the Auto-Refresh Feature

The site now has a **"Refresh Data"** button that automatically runs the scraper and updates the leaderboard!

### Quick Start

1. **Start the refresh server** (only needs to run once):
   ```powershell
   cd conversion
   python refresh_server.py
   ```
   
   You should see:
   ```
   Starting refresh server on https://gdg-refresh-server.onrender.com
   Make sure to keep this running while using the site!
   ```

2. **Open the site** in your browser:
   - Open `main/index.html` in your browser, or
   - Run a local server: `python -m http.server 8000` from the `main/` folder

3. **Click "Refresh Data"** button on the site whenever you want to update badge counts!

### What Happens When You Click Refresh?

1. 🔄 The button triggers the scraper (`scrape_profiles.py`)
2. 🌐 The scraper fetches latest badge data from Google Cloud Skills Boost profiles
3. 💾 Updates `main/data.json` with new counts
4. ✅ The site automatically reloads the updated data
5. 📊 You see the refreshed leaderboard!

### Important Notes

- ⚠️ Keep the refresh server (`refresh_server.py`) running in a terminal while using the site
- ⏱️ The refresh takes 1-3 minutes depending on how many profiles need updating
- 🔒 The server only runs locally on your machine (localhost:5001)
- 💾 Backups are automatically created before updating

### Troubleshooting

**"Could not connect to refresh server"**
- Make sure `refresh_server.py` is running in a terminal
- Check that port 5001 is not being used by another application

**Refresh is slow**
- The scraper is polite and adds delays between requests (default: 10 concurrent requests)
- You can adjust concurrency in `scrape_profiles.py` if needed

**Changes not showing**
- Hard refresh the browser (Ctrl+F5 or Cmd+Shift+R)
- Check the browser console for errors (F12)

### Manual Scraper Run (Alternative)

If you prefer to run the scraper manually without the button:

```powershell
cd conversion
python scrape_profiles.py ../main/data.json
```

Or with options:
```powershell
# Dry run (doesn't save changes)
python scrape_profiles.py ../main/data.json --dry-run

# Adjust concurrency
python scrape_profiles.py ../main/data.json --concurrency 5

# With retries
python scrape_profiles.py ../main/data.json --retries 2
```
