# GitHub Projects Backup Tool

This tool automatically backs up GitHub repositories from a specified user's starred list. It includes features like repository size checking, retry mechanisms for large repositories, and detailed backup status reporting.

## Features

- Backs up repositories from a user's GitHub starred list
- Shows repository sizes before downloading
- Handles large repositories with optimized Git settings
- Provides detailed backup status and error reporting
- Supports shallow cloning for faster initial backups
- Automatic retry mechanism for failed downloads
- Detailed backup metadata tracking

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have Git installed on your system

3. You need a GitHub token to run the script. You can obtain one by visiting https://github.com/settings/tokens and creating a new token with the `repo` permission.

4. Create a `.env` file in the project directory and add your GitHub token:
```
GITHUB_TOKEN=your_token_here
```

## Usage

Run the script with default settings:
```bash
python github_backup.py
```

Or specify a different user and list name:
```bash
python github_backup.py username listname
```

### Default Values
- Username: "jing8263xiao"
- List name: "backup"

## Output

The script will:
1. Configure Git settings for optimal performance
2. Display repository sizes before downloading
3. Create or update repositories in the `backups` directory
4. Show a detailed summary of successful and failed backups
5. Generate a `backup_metadata.json` file containing:
   - Timestamp of the last backup
   - List of successfully backed up repositories
   - List of failed repositories with error messages
   - Total number of processed repositories
   - Success and failure counts

## Error Handling

The script includes several features to handle common issues:
- Automatic retries for network-related failures
- Exponential backoff between retry attempts
- Shallow cloning for large repositories
- Optimized Git settings for better performance
- Detailed error reporting for troubleshooting

## Backup Directory Structure

```
backups/
├── repository1.git/
├── repository2.git/
├── ...
└── backup_metadata.json
