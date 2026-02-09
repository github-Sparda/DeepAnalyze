# DeepAnalyze CLI

A command-line interface for DeepAnalyze, powered by the Rich library. Provides an intuitive way to interact with DeepAnalyze for data docs/analysis tasks with file upload support and real-time streaming responses.

## 🚀 Quick Start

### Prerequisites

Please ensure that an OpenAI-compatible LLM endpoint is configured in `src/api/config.py` or `.env` before starting the CLI.

1. **Start the DeepAnalyze src/api Server**:
   ```bash
   cd ../../src/api
   python start_server.py
   ```

2. **Launch the CLI**: 
   
   ```bash
   # In another terminal
   # English version
   python api_cli.py
   # Chinese version
   python api_cli_ZH.py
   ```

## 📋 Commands

### Basic Commands
- `help` - Display help information
- `quit` / `exit` - Exit the program
- `clear` - Clear conversation history 
- `clear-all` - Clear all content including uploaded files

### File Management
- `files` - View uploaded files
- `upload <file_path>` - Upload new file
- `delete <file_id>` - Delete specified file
- `download <file_id> [save_path]` - Download file

### System & History
- `status` - Display system status
- `history` - Display conversation history
- `fid` - Display all file names and complete IDs

## 💬 Usage Examples

### Basic Chat
   ```
> Analyze this dataset and generate insights
```

### File Upload and Analysis
```
> upload data.csv
✅ File uploaded: file-abc123...

> Analyze the uploaded data and create visualizations
📊 Generating docs/analysis...
📈 Created charts: docs/analysis.png, trends.png
📝 Generated report: report.md
```

### Streaming Responses
The CLI automatically streams responses, showing real-time progress as DeepAnalyze analyzes your data and generates insights.

## 🔧 Configuration

The CLI connects to the DeepAnalyze src/api server at `http://localhost:48200/v1` by default. You can change this in `src/api/config.py` (see `src/api_PUBLIC_BASE_V1`).

Command history is saved to `~/.deeppanalyze_history_en` (English) or `~/.deeppanalyze_history_zh` (Chinese).
