# Setting Up the NEU Calendar MCP Server in Claude Desktop

This guide will walk you through setting up the Northeastern University Calendar MCP server to work with Claude Desktop.

## Prerequisites

- Claude Desktop (latest version)
- Python 3.9 or higher
- Required Python packages: `icalendar`, `httpx`, `mcp`

## Installation Steps

### 1. Install Required Python Packages

Open a terminal or command prompt and run:

```bash
pip install icalendar httpx mcp
```

Or use the provided requirements.txt file:

```bash
pip install -r requirements.txt
```

### 2. Find Your Python Path

Claude Desktop needs to know the exact location of your Python executable. To find it:

- On macOS/Linux, open Terminal and run:
  ```bash
  which python
  ```
  
- On Windows, open Command Prompt and run:
  ```bash
  where python
  ```

Take note of the full path that is displayed (e.g., `/usr/bin/python` or `C:\Users\YourName\AppData\Local\Programs\Python\Python39\python.exe`).

### 3. Locate the Claude Desktop Configuration Directory

The Claude Desktop configuration file is located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 4. Configure Claude Desktop

You have two options for configuring Claude Desktop:

#### Option 1: Edit Configuration Through Claude Desktop UI

1. Open Claude Desktop
2. Open the main menu (Claude logo in the top left on Mac, or from taskbar on Windows)
3. Select "Settings..."
4. Go to the "Developer" tab
5. Click "Edit Config"
6. Replace or merge the content with the following:

```json
{
  "mcpServers": {
    "neu-calendar": {
      "command": "/full/path/to/python",
      "args": [
        "/full/path/to/neu_calendar_mcp/neu_calendar_server.py"
      ],
      "env": {}
    }
  }
}
```

**IMPORTANT**: 
- Replace `/full/path/to/python` with the actual Python path you found in step 2
- Replace `/full/path/to/neu_calendar_mcp` with the actual full path to where you have saved the NEU Calendar MCP files

#### Option 2: Manual Configuration

1. Edit the configuration file directly using any text editor
2. If the file doesn't exist, create it with the following content:

```json
{
  "mcpServers": {
    "neu-calendar": {
      "command": "/full/path/to/python",
      "args": [
        "/full/path/to/neu_calendar_mcp/neu_calendar_server.py"
      ],
      "env": {}
    }
  }
}
```

**IMPORTANT**: 
- Replace `/full/path/to/python` with the actual Python path you found in step 2
- Replace `/full/path/to/neu_calendar_mcp` with the actual full path to where you have saved the NEU Calendar MCP files

### 5. Restart Claude Desktop

After configuring, fully close and restart Claude Desktop to load the changes.

## Verifying the Setup

1. After restarting Claude Desktop, you should see a small hammer icon in the chat interface, which indicates that MCP tools are available.
2. Test the server by asking Claude:
   - "What events are happening today at Northeastern University?"
   - "Show me upcoming events for the next week"

If Claude responds with calendar information, your setup is working correctly!

## Troubleshooting

If the server doesn't work, try the following:

### "spawn python ENOENT" Error

This error means Claude Desktop cannot find the Python executable. Make sure:

1. You're using the full absolute path to Python in your configuration
2. The Python path is correct and the executable exists
3. The path has no typos or extra spaces

You can find your Python path by running:
- macOS/Linux: `which python`
- Windows: `where python`

### Check the logs

Claude Desktop writes logs to:
- **macOS**: `~/Library/Logs/Claude/`
- **Windows**: `%APPDATA%\Claude\logs\`

Look for files named:
- `mcp.log`
- `mcp-server-neu-calendar.log`

### Verify the server runs on its own

Try running the server manually to check for errors:

```bash
python /path/to/neu_calendar_mcp/neu_calendar_server.py
```

### Common issues

1. **Python path issue**: Make sure the path to Python is correct. You must use the full absolute path.

2. **File permissions**: Ensure the server file is executable.

3. **Dependency issues**: Verify all required packages are installed correctly.

4. **Path issues**: Make sure all paths in the configuration file are absolute and correct.

5. **Virtual environment**: If using a virtual environment, you might need to specify the Python executable from within that environment.

## Getting Support

If you encounter issues not covered in this guide, please:

1. Check the main README.md file for additional troubleshooting tips
2. Run the test client to verify the server works independently of Claude Desktop
3. Review the server logs for specific error messages 