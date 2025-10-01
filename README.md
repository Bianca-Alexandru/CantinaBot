# Cantina Bot

A Discord bot that fetches daily menus for multiple cantinas, caches PDFs, converts them to images, and posts them automatically or on demand via slash commands.

## Environment Variables

| Name | Description |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Your Discord bot token. Keep this secret and never commit it to source control. |
| `DISCORD_CHANNEL_ID` | The ID of the Discord text channel where the bot should post menus by default. |

You can copy `.env.example` to `.env` and fill in your own values for local development (PowerShell example below).

## Local Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env  # update the token + channel ID
python CantinaBot.py
```

Alternatively, export the environment variables directly in your shell before running the bot:

```powershell
$env:DISCORD_BOT_TOKEN = "your-token"
$env:DISCORD_CHANNEL_ID = "123456789012345678"
python CantinaBot.py
```

## Creating the Git Repository

1. Sign in to GitHub and create a **new empty repository** (no README/LICENSE/ignore files).
2. In this project folder, initialise Git and make the first commit:

```powershell
git init
git add .
git commit -m "Initial commit"
```

3. Add the GitHub remote and push:

```powershell
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

## Deploying to Railway

1. Create an account at [railway.app](https://railway.app/) and install the CLI if you prefer using it locally (`npm i -g @railway/cli`).
2. In the Railway dashboard, create a **New Project** and select **Deploy from GitHub Repo**.
3. Connect your GitHub account, choose the repository you created above, and deploy it.
4. Railway will detect `requirements.txt` and install dependencies automatically.
5. Set the two required environment variables (`DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`) in the project’s **Variables** tab.
6. Ensure the service is marked as a **Worker** (not a web service). Railway will honour the `Procfile` and run `python CantinaBot.py`.
7. Deploy the latest commit. The bot should come online once Railway finishes building the image. Check the **Logs** tab for confirmation that the bot connected to Discord successfully.

### Updating the Deployment

Push new commits to the `main` branch (or the branch configured in Railway). Railway will rebuild and redeploy automatically. You can also trigger redeploys from the dashboard.

### Useful Railway CLI Commands (Optional)

```powershell
railway login
railway link
railway variables set DISCORD_BOT_TOKEN="your-token" DISCORD_CHANNEL_ID="123456789012345678"
railway up
```

## Contributing / Maintenance Tips

- Avoid committing secrets by keeping the `.env` file listed in `.gitignore`.
- Run `python -m compileall CantinaBot.py` or start the bot locally to check for syntax issues before pushing.
- Review the Railway logs periodically to ensure scheduled posts succeed and to catch SSL or permission errors early.
