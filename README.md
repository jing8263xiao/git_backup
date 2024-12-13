# GitHub Projects Backup Tool

This tool automatically backs up GitHub repositories from a specified user's starred list.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have Git installed on your system

## Usage

Simply run the script:
```bash
python github_backup.py
```

The script will:
1. Fetch all starred repositories from the specified user
2. Clone new repositories or update existing ones in the `backups` directory
3. Create a metadata file with backup information

## Output

- All repositories will be backed up in the `backups` directory
- A `backup_metadata.json` file will be created with the timestamp of the last backup
