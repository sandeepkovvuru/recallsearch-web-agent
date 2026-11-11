# Publish RecallSearch to GitHub

The source tree is ready to upload. Create a **new public repository** on GitHub named `recallsearch-web-agent` (or another name you prefer), and leave it empty.

**Upload in the browser:** open the new repository, choose **Add file → Upload files**, drag the contents of the extracted `web-search-agent` folder into the page (including `design.md`), then choose **Commit changes**. Make sure `README.md` and `design.md` are visible at the top level.

**Or use Git from Windows PowerShell:** run these commands from the extracted project folder:

```powershell
git init
git add .
git commit -m "Build RecallSearch web search chat agent"
git branch -M main
git remote add origin https://github.com/<your-username>/recallsearch-web-agent.git
git push -u origin main
```

Replace `<your-username>` with your GitHub username. After the push, open the repository page and confirm that both `README.md` and `design.md` are visible at the top level. Copy that repository URL into the challenge form.

Do not upload `.env`, API keys, or the SQLite database. The included `.gitignore` excludes them.
