import os
import subprocess
from datetime import datetime
import requests
import json

def get_list_repos(username, list_name):
    # GitHub API endpoint for getting repositories in a list
    url = f"https://api.github.com/users/{username}/starred"
    
    # You'll need to add your GitHub token here
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching repositories: {e}")
        return []

def backup_repository(repo_url, backup_dir):
    repo_name = repo_url.split('/')[-1]
    repo_path = os.path.join(backup_dir, repo_name)
    
    if os.path.exists(repo_path):
        print(f"Updating existing repository: {repo_name}")
        try:
            subprocess.run(['git', '-C', repo_path, 'pull'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error updating repository {repo_name}: {e}")
    else:
        print(f"Cloning new repository: {repo_name}")
        try:
            subprocess.run(['git', 'clone', repo_url, repo_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository {repo_name}: {e}")

def main():
    # Configuration
    username = "jing8263xiao"
    list_name = "backup"
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Get repositories from the list
    repos = get_list_repos(username, list_name)
    
    # Backup each repository
    for repo in repos:
        backup_repository(repo['clone_url'], backup_dir)
    
    # Save backup metadata
    metadata = {
        "last_backup": datetime.now().isoformat(),
        "repos_backed_up": len(repos)
    }
    
    with open(os.path.join(backup_dir, "backup_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

if __name__ == "__main__":
    main()
