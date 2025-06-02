# Ollama Specific Model Backup Script

This Python script provides a convenient way to backup specific Ollama language models installed on your Linux system. It intelligently identifies the model files (blobs and manifests) associated with your chosen models and archives them into a single zip file.

## Features

* **Automatic Ollama Directory Detection:** Automatically locates your Ollama models directory, supporting default paths and the `OLLAMA_MODELS` environment variable.

* **Interactive Model Selection:** Lists all available Ollama models and allows you to select specific ones or backup all.

* **Dependency Resolution:** Identifies and copies all necessary blob (model weight) and manifest (metadata) files for the selected models.

* **Progress Bar:** Utilizes `rsync` to display a progress bar during large file (blob) copying operations.

* **Zip Archiving:** Compresses the selected models and their dependencies into a timestamped zip file.

* **Temporary Directory Cleanup:** Automatically removes the temporary directory created during the backup process.

## Requirements

* **Python 3:** Ensure Python 3 is installed on your system.

* **Ollama:** Ollama must be installed and have models pulled.

* **`rsync`:** The `rsync` utility must be installed on your system for the progress bar feature. If `rsync` is not found, the script will fall back to `cp` without a progress bar.

    * To install `rsync` on Debian/Ubuntu-based systems (like Linux Mint):

        ```bash
        sudo apt update
        sudo apt install rsync
        ```

## How to Use

1.  **Save the script:** Save the provided Python code into a file, for example, `backup_ollama.py`.

2.  **Open your terminal.**

3.  **Navigate to the directory** where you saved the script.

4.  **Run the script with `sudo`:**
    Since Ollama models are often stored in system-owned directories (`/usr/share/ollama/.ollama/models`), the script requires root privileges to read and copy these files.

    ```bash
    sudo python3 backup_ollama.py
    ```

5.  **Follow the prompts:**

    * The script will first detect your Ollama models directory and list all available models.

    * You will then be prompted to enter the numbers of the models you wish to backup (e.g., `1 3 5`) or type `all` to backup every model.

    * The script will display progress as it copies model files and then create a zip archive.

## Output

A zip file named similar to `models_YYYYMMDD_HHMMSS.zip` will be created in the directory that you would specify. This zip file contains the selected models and their dependencies, preserving the necessary directory structure for potential restoration.

## Important Considerations

* **`sudo` Requirement:** Always run this script with `sudo` to ensure it has the necessary permissions to access Ollama's model storage.

* **Shared Blobs:** Ollama models often share underlying "blob" files (the large model weights). This script handles this by only copying each unique blob file once, even if multiple selected models depend on it.

* **Restoration:** To restore models from this backup, you would extract the zip file and copy the contents (the `blobs` and `manifests` folders) into your Ollama models base directory (e.g., `/usr/share/ollama/.ollama/models/`). After copying, you might need to restart the Ollama service or run `ollama list` to ensure Ollama recognizes the restored models.

* **Disk Space:** Ensure you have enough free disk space in your home directory for the temporary backup files and the final zip archive, especially if backing up large models.