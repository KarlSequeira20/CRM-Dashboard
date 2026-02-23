# 🟢 Git Repository Setup

## 1. Create a `.gitignore` File
First, create a `.gitignore` in the project root to prevent sensitive data from leaking:

```bash
# Dependencies
node_modules/
venv/
.venv/
__pycache__/
*.pyc

# Sensitive Environment Variables
.env
backend/.env

# OS / IDE files
.DS_Store
.vscode/

# Build artifacts
dist/
build/
```

## 2. Initialize and Commit
Run these commands in your terminal:

```bash
# Initialize the repo
git init

# Add all files (the .gitignore will automatically skip node_modules and .env)
git add .

# Create the initial commit
git commit -m "Initial commit: AHA Smart Home CRM Intelligence Platform"
```

## 3. Connect to GitHub/GitLab
Create a new blank repository on GitHub. Then, run the following commands (replace the URL with your actual repo link):

```bash
# Link to your remote repository
git remote add origin https://github.com/YOUR_USERNAME/crm-intelligence-agent.git

# Set the main branch
git branch -M main

# Push to the cloud
git push -u origin main
```
