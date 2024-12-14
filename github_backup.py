import os
import subprocess
from datetime import datetime
import requests
import json
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import codecs
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set console to use UTF-8 encoding
if sys.platform.startswith('win'):
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

def create_session():
    """Create a requests session with retry strategy and SSL verification disabled"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.verify = False  # Disable SSL verification
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return session

def format_size(size_bytes):
    """Convert size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_github_token():
    """Get GitHub token from environment variable or user input"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("\nGitHub token not found in environment variables.")
        print("You can create a token at: https://github.com/settings/tokens")
        print("The token needs 'repo' and 'read:user' scopes.")
        print("Please set the GITHUB_TOKEN environment variable and try again.")
        sys.exit(1)
    return token

def get_list_repos(username, list_name):
    session = create_session()
    token = get_github_token()
    
    try:
        # Get the list page
        list_url = f"https://github.com/stars/{username}/lists/{list_name}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = session.get(list_url, headers=headers)
        response.raise_for_status()
        
        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all repository divs using the structure you provided
        repo_items = soup.find_all('div', {'class': 'd-inline-block mb-1'})
        
        if not repo_items:
            print(f"No repositories found in list '{list_name}'")
            return []
        
        print(f"\nFound {len(repo_items)} repositories in list '{list_name}'")
        
        # Get detailed information for each repository
        detailed_repos = []
        total_size = 0
        
        # Add token to headers for API requests
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        print("\nFetching repository sizes...")
        for item in repo_items:
            try:
                # Find the repository link using the exact structure
                repo_link = item.find('h3').find('a')
                if not repo_link:
                    print("Could not find repository link in item")
                    continue
                
                # Get the href which contains the repo path
                repo_path = repo_link.get('href', '').strip('/')
                if not repo_path:
                    print("Could not find repository path")
                    continue
                
                # The repo path should be in format "owner/repo"
                owner, repo_name = repo_path.split('/')
                print(f"\nProcessing repository: {owner}/{repo_name}")
                
                # Get repository details from GitHub API
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                repo_response = session.get(api_url, headers=api_headers)
                
                # Handle rate limiting
                if repo_response.status_code == 403 and 'rate limit exceeded' in repo_response.text:
                    print(f"\nRate limit exceeded. Waiting 60 seconds before retrying...")
                    time.sleep(60)
                    repo_response = session.get(api_url, headers=api_headers)
                
                repo_response.raise_for_status()
                repo_details = repo_response.json()
                
                size_bytes = repo_details.get('size', 0) * 1024  # Convert KB to bytes
                total_size += size_bytes
                
                print(f"Repository: {repo_details['full_name']}")
                print(f"Size: {format_size(size_bytes)}")
                
                # Handle description that might contain emojis
                description = repo_details.get('description', 'No description')
                if description:
                    try:
                        print(f"Description: {description}")
                    except UnicodeEncodeError:
                        print("Description: [Contains special characters that cannot be displayed]")
                print("-" * 50)
                
                detailed_repos.append({
                    'name': repo_details['name'],
                    'clone_url': repo_details['clone_url'],
                    'size': size_bytes
                })
                
                # Add a small delay between requests to avoid hitting rate limits
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing repository {owner}/{repo_name if 'repo_name' in locals() else 'unknown'}: {e}")
        
        print(f"\nTotal repositories: {len(detailed_repos)}")
        print(f"Total size: {format_size(total_size)}")
        
        while True:
            try:
                proceed = input("\nDo you want to proceed with the backup? (y/n): ").strip().lower()
                if proceed in ['y', 'n']:
                    break
                print("Please enter 'y' for yes or 'n' for no.")
            except EOFError:
                print("\nInvalid input. Defaulting to 'n'")
                proceed = 'n'
        
        if proceed != 'y':
            print("Backup cancelled")
            return []
            
        return detailed_repos
        
    except requests.RequestException as e:
        print(f"Error fetching repositories: {e}")
        return []

def configure_git():
    """Configure git with optimal settings for large repositories"""
    git_configs = [
        # Increase buffer sizes
        ['http.postBuffer', '524288000'],  # 500MB buffer
        ['core.compression', '0'],         # Less compression, faster cloning
        ['http.lowSpeedLimit', '1000'],    # Lower threshold for slow connections
        ['http.lowSpeedTime', '60'],       # Wait longer for slow connections
        # Disable some features for better performance
        ['gc.auto', '0'],                  # Disable auto garbage collection
        ['core.preloadIndex', 'true'],     # Preload index for better performance
        # Configure larger packet size
        ['protocol.version', '2'],         # Use Git protocol v2
        ['core.packedGitLimit', '512m'],   # Increase packed git limit
        ['core.packedGitWindowSize', '512m'], # Increase window size
        ['pack.windowMemory', '512m'],     # Increase pack memory
        ['pack.packSizeLimit', '512m'],    # Increase pack size limit
        ['pack.threads', '1'],             # Single thread to avoid memory issues
    ]
    
    print("Configuring git for large repositories...")
    for config in git_configs:
        try:
            subprocess.run(['git', 'config', '--global'] + config, 
                         check=True, 
                         capture_output=True)
            print(f"Set git config {config[0]}={config[1]}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not set git config {config[0]}: {e.stderr}")

def run_git_command(command, retries=3, delay=5):
    """Run a git command with retries"""
    for attempt in range(retries):
        try:
            if attempt > 0:
                print(f"Retry attempt {attempt + 1}/{retries}")
            
            # Add environment variables for this specific command
            env = os.environ.copy()
            env['GIT_TRACE_PACKET'] = '1'
            env['GIT_TRACE'] = '1'
            env['GIT_CURL_VERBOSE'] = '1'
            
            result = subprocess.run(command,
                                 check=True,
                                 capture_output=True,
                                 text=True,
                                 env=env)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Attempt {attempt + 1} failed: {e.stderr}")
            if any(err in e.stderr for err in [
                "unable to access",
                "Couldn't connect to server",
                "RPC failed",
                "early EOF",
                "index-pack failed"
            ]):
                if attempt < retries - 1:
                    print(f"Network/transfer issue detected. Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            return False, e.stderr
        except Exception as e:
            return False, str(e)
    return False, "Max retries reached"

def backup_repository(repo_url, backup_dir):
    """Backup a repository by cloning or pulling if it already exists"""
    repo_name = repo_url.split('/')[-1]
    try:
        repo_path = os.path.join(backup_dir, repo_name)

        # Add --depth 1 for initial clone to speed up
        clone_command = ['git', 'clone', '--depth', '1', repo_url, repo_path]
        
        if os.path.exists(repo_path):
            print(f"\nRepository exists, updating: {repo_name}")
            try:
                # Try to pull updates
                success, output = run_git_command(['git', '-C', repo_path, 'pull'])
                if success:
                    print(f"Successfully updated {repo_name}")
                    print(f"Git output: {output}")
                    return True, "Updated successfully"
                else:
                    print(f"Error updating repository {repo_name}: {output}")
                    # If pull fails, try to remove and clone again
                    print(f"Attempting to re-clone {repo_name}")
                    import shutil
                    shutil.rmtree(repo_path, ignore_errors=True)
                    success, output = run_git_command(clone_command)
                    if success:
                        print(f"Successfully re-cloned {repo_name}")
                        print(f"Git output: {output}")
                        return True, "Re-cloned successfully"
                    else:
                        return False, f"Failed to re-clone: {output}"
            except Exception as e:
                return False, str(e)
        else:
            print(f"\nCloning new repository: {repo_name}")
            success, output = run_git_command(clone_command)
            if success:
                print(f"Successfully cloned {repo_name}")
                print(f"Git output: {output}")
                return True, "Cloned successfully"
            else:
                return False, f"Failed to clone: {output}"
            
    except Exception as e:
        error_msg = str(e)
        print(f"Unexpected error with repository {repo_name}: {error_msg}")
        return False, error_msg

def main():
    # Create backups directory if it doesn't exist
    backup_dir = os.path.join(os.getcwd(), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    # Configure git settings
    configure_git()

    # Get username and list name from command line arguments or use defaults
    username = sys.argv[1] if len(sys.argv) > 1 else "jing8263xiao"
    list_name = sys.argv[2] if len(sys.argv) > 2 else "backup"

    # Configure git to use system proxy if available
    try:
        # Try to get system proxy settings
        import urllib.request
        proxy_handler = urllib.request.ProxyHandler({})
        if proxy_handler.proxies:
            print("System proxy detected, configuring git...")
            for protocol, proxy in proxy_handler.proxies.items():
                if protocol in ('http', 'https'):
                    subprocess.run(['git', 'config', '--global', f'{protocol}.proxy', proxy])
                    print(f"Set {protocol} proxy to: {proxy}")
    except Exception as e:
        print(f"Warning: Could not configure proxy: {e}")

    # Get repositories from the list
    repos = get_list_repos(username, list_name)

    # Initialize counters and lists for summary
    successful_repos = []
    failed_repos = []
    
    # Backup each repository
    if repos:
        print("\nStarting backup process...")
        for repo in repos:
            success, message = backup_repository(repo['clone_url'], backup_dir)
            if success:
                successful_repos.append(repo['name'])
            else:
                failed_repos.append((repo['name'], message))
        
        # Print summary
        print("\n" + "="*50)
        print("BACKUP SUMMARY")
        print("="*50)
        print(f"Total repositories processed: {len(repos)}")
        print(f"Successful: {len(successful_repos)}")
        print(f"Failed: {len(failed_repos)}")
        
        if successful_repos:
            print("\nSuccessfully backed up repositories:")
            for repo in successful_repos:
                print(f"✓ {repo}")
        
        if failed_repos:
            print("\nFailed repositories:")
            for repo, error in failed_repos:
                print(f"✗ {repo}")
                print(f"  Error: {error}")
        
        print("\nBackup process completed!")
    else:
        print("No repositories to backup.")

    # Save backup metadata
    metadata = {
        "last_backup": datetime.now().isoformat(),
        "successful_repos": successful_repos,
        "failed_repos": [(name, str(error)) for name, error in failed_repos],
        "total_repos": len(repos),
        "success_count": len(successful_repos),
        "fail_count": len(failed_repos)
    }
    
    # Save metadata to file
    metadata_file = os.path.join(backup_dir, "backup_metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"\nBackup metadata saved to {metadata_file}")

if __name__ == "__main__":
    main()
