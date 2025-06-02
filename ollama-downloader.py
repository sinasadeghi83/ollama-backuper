import os
import json
import shutil
import subprocess
from datetime import datetime

# Global flag to indicate if rsync is available for progress
RSYNC_AVAILABLE = False

def check_tools_installed():
    """Checks if necessary commands (rsync, pv) are available in the system's PATH."""
    tools = {
        'rsync': shutil.which('rsync') is not None,
    }
    return tools

def get_ollama_models_base_dir():
    """
    Determines the base directory where Ollama stores its models.
    Prioritizes the OLLAMA_MODELS environment variable, then checks common Linux paths.
    """
    ollama_env_dir = os.environ.get('OLLAMA_MODELS')
    if ollama_env_dir:
        # If OLLAMA_MODELS is set, use it directly.
        # It's expected to point to the directory *containing* 'blobs' and 'manifests'.
        if os.path.isdir(os.path.join(ollama_env_dir, 'blobs')) and \
           os.path.isdir(os.path.join(ollama_env_dir, 'manifests')):
            return ollama_env_dir
        else:
            print(f"Warning: OLLAMA_MODELS is set to '{ollama_env_dir}', but 'blobs' or 'manifests' subdirectories are not found there.")

    # Common default paths for Linux
    default_paths = [
        os.path.expanduser('~/.ollama/models'),
        '/usr/share/ollama/.ollama/models',
        '/var/lib/ollama/.ollama/models' # Less common but possible
    ]

    for path in default_paths:
        if os.path.isdir(os.path.join(path, 'blobs')) and \
           os.path.isdir(os.path.join(path, 'manifests')):
            return path

    return None

def list_available_models(ollama_models_base_dir):
    """
    Lists all available Ollama models (name:tag) by scanning the manifests directory.
    """
    models = []
    manifests_dir = os.path.join(ollama_models_base_dir, 'manifests', 'registry.ollama.ai', 'library')

    if not os.path.isdir(manifests_dir):
        print(f"Error: Manifests directory not found at {manifests_dir}")
        return []

    try:
        for model_name in os.listdir(manifests_dir):
            model_path = os.path.join(manifests_dir, model_name)
            if os.path.isdir(model_path):
                for tag in os.listdir(model_path):
                    if os.path.isfile(os.path.join(model_path, tag)):
                        models.append(f"{model_name}:{tag}")
    except PermissionError:
        print(f"Permission denied when accessing {manifests_dir}. Please run the script with 'sudo'.")
        return []
    except Exception as e:
        print(f"An error occurred while listing models: {e}")
        return []

    return sorted(models)

def get_model_dependencies(ollama_models_base_dir, model_name, tag):
    """
    Reads the manifest file for a given model:tag and returns the manifest path
    and a list of associated blob file paths.
    """
    manifest_path = os.path.join(
        ollama_models_base_dir, 'manifests', 'registry.ollama.ai', 'library', model_name, tag
    )
    blobs_dir = os.path.join(ollama_models_base_dir, 'blobs')
    
    if not os.path.isfile(manifest_path):
        print(f"Error: Manifest file not found for {model_name}:{tag} at {manifest_path}")
        return None, []

    blob_paths = []
    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)

        # Add config digest
        if 'config' in manifest_data and 'digest' in manifest_data['config']:
            blob_paths.append(os.path.join(blobs_dir, f"sha256-{manifest_data['config']['digest'][7:]}"))
        
        # Add layer digests
        if 'layers' in manifest_data:
            for layer in manifest_data['layers']:
                if 'digest' in layer:
                    blob_paths.append(os.path.join(blobs_dir, f"sha256-{layer['digest'][7:]}"))

    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from manifest file: {manifest_path}")
        return None, []
    except PermissionError:
        print(f"Permission denied when reading manifest: {manifest_path}. Please run the script with 'sudo'.")
        return None, []
    except Exception as e:
        print(f"An error occurred while reading model dependencies: {e}")
        return None, []

    return manifest_path, blob_paths

def copy_with_sudo(source, destination):
    """
    Copies a file or directory using 'sudo cp'.
    """
    try:
        if RSYNC_AVAILABLE:
            # Use subprocess.run for better error handling and command execution
            # -a for archive mode if source is a directory
            # -h for output to be human readable
            # -P to show progress
            cmd = ['sudo', 'rsync', '-ah', '-P', source, destination]
                
            print(f"  Copying (with progress): {os.path.basename(source)}")
            # Execute rsync
            # We don't capture_output here so rsync's progress output goes directly to stdout
            result = subprocess.run(cmd, check=True, text=True)
            print(f"  Finished copying: {os.path.basename(source)}")
        else:
            # Fallback to standard cp if rsync is not available
            cmd = ['sudo', 'cp', '-rp', source, destination]
            
            # If source is a directory, ensure -r is used
            if os.path.isdir(source) and '-r' not in cmd:
                cmd.insert(2, '-r') # Insert -r after 'cp'
            
            print(f"  Copying: {os.path.basename(source)} (no progress bar)")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error copying {source} to {destination}: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: 'sudo' or 'cp' command not found. Ensure they are in your PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during copy: {e}")
        return False

def main():
    global RSYNC_AVAILABLE
    tools = check_tools_installed()
    RSYNC_AVAILABLE = tools['rsync']

    if not RSYNC_AVAILABLE:
        print("Warning: 'rsync' command not found. Copying large files will proceed without a progress bar.")
        print("You can install 'rsync' using: sudo apt install rsync")
        
    ollama_models_base_dir = get_ollama_models_base_dir()

    if not ollama_models_base_dir:
        print("Error: Could not find Ollama models directory. Please ensure Ollama is installed and models are pulled.")
        print("If you've set a custom OLLAMA_MODELS environment variable, ensure it's correct.")
        return

    print(f"Ollama models base directory detected: {ollama_models_base_dir}")
    print("\nListing available Ollama models...")
    available_models = list_available_models(ollama_models_base_dir)

    if not available_models:
        print("No Ollama models found or permission denied. Ensure models are pulled and run with 'sudo'.")
        return

    print("Available models:")
    for i, model in enumerate(available_models):
        print(f"{i+1}. {model}")

    selected_indices = input("\nEnter the numbers of the models you want to backup (e.g., 1 3 5), or 'all' for all: ")

    models_to_backup = []
    if selected_indices.lower() == 'all':
        models_to_backup = available_models
    else:
        try:
            indices = [int(x.strip()) for x in selected_indices.split()]
            for idx in indices:
                if 1 <= idx <= len(available_models):
                    models_to_backup.append(available_models[idx-1])
                else:
                    print(f"Warning: Invalid model number '{idx}' skipped.")
        except ValueError:
            print("Invalid input. Please enter numbers separated by spaces or 'all'.")
            return

    if not models_to_backup:
        print("No models selected for backup. Exiting.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_dir = input("Specify backup directory path: ")
    backup_dir = os.path.expanduser(backup_dir)
    if not os.path.exists(backup_dir) and not os.path.isdir(backup_dir):
        print("Backup directory is invalid. Exiting.")
        return
    
    backup_root_dir = os.path.join(backup_dir, "models")
    os.makedirs(backup_root_dir, exist_ok=True)
        
    # Create the necessary subdirectories for blobs and manifests within the backup root
    backup_blobs_dir = os.path.join(backup_root_dir, 'blobs')
    backup_manifests_library_dir = os.path.join(backup_root_dir, 'manifests', 'registry.ollama.ai', 'library')

    os.makedirs(backup_blobs_dir, exist_ok=True)
    os.makedirs(backup_manifests_library_dir, exist_ok=True)

    print(f"\nStarting backup to: {backup_root_dir}")

    copied_blobs = set() # To avoid copying the same blob multiple times if shared

    for model_str in models_to_backup:
        print(f"\nProcessing model: {model_str}")
        model_name, tag = model_str.split(':')

        manifest_source_path, blob_source_paths = get_model_dependencies(ollama_models_base_dir, model_name, tag)

        if not manifest_source_path:
            print(f"Skipping {model_str} due to missing manifest or error.")
            continue

        # Copy manifest
        manifest_dest_dir = os.path.join(backup_manifests_library_dir, model_name)
        os.makedirs(manifest_dest_dir, exist_ok=True)
        manifest_dest_path = os.path.join(manifest_dest_dir, tag)
        print(f"  Copying manifest: {os.path.basename(manifest_source_path)}")
        if not copy_with_sudo(manifest_source_path, manifest_dest_path):
            print(f"  Failed to copy manifest for {model_str}. Skipping blobs for this model.")
            continue

        # Copy blobs
        total_blobs = len(blob_source_paths)
        for i, blob_source_path in enumerate(blob_source_paths):
            blob_filename = os.path.basename(blob_source_path)
            if blob_filename in copied_blobs:
                print(f"  Blob {blob_filename} already copied. Skipping.")
                continue

            blob_dest_path = os.path.join(backup_blobs_dir, blob_filename)
            print(f"  Copying blob {i+1}/{total_blobs}: {blob_filename}")
            if copy_with_sudo(blob_source_path, blob_dest_path):
                copied_blobs.add(blob_filename)
            else:
                print(f"  Failed to copy blob {blob_filename}. Backup might be incomplete for {model_str}.")

    print("\nAll selected models and their dependencies copied to temporary directory.")
    print(f"Creating zip archive of {backup_root_dir}...")

    zip_filename = f"models_{timestamp}"
    zip_path = os.path.join(backup_dir, zip_filename)

    try:
        # shutil.make_archive does not support sudo, so we use subprocess for zip
        # Change directory to the parent of backup_root_dir to zip it correctly
        parent_backup_root_dir = os.path.dirname(backup_root_dir)
        base_backup_root_dir_name = os.path.basename(backup_root_dir)
        
        # Use 'zip -r' command with sudo
        zip_cmd = ['sudo', 'zip', '-r', f"{zip_path}.zip", base_backup_root_dir_name]
        
        print(f"Executing: {' '.join(zip_cmd)} from {parent_backup_root_dir}")
        
        # Execute the zip command from the parent directory
        subprocess.run(zip_cmd, cwd=parent_backup_root_dir, check=True, capture_output=True, text=True)
        
        print(f"\nBackup complete! Zip file created at: {zip_path}.zip")
    except subprocess.CalledProcessError as e:
        print(f"Error creating zip archive: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred during zipping: {e}")
    finally:
        print(f"Cleaning up temporary directory: {backup_root_dir}")
        try:
            # Remove the temporary directory using sudo
            subprocess.run(['sudo', 'rm', '-rf', backup_root_dir], check=True, capture_output=True, text=True)
            print("Temporary directory cleaned up.")
        except subprocess.CalledProcessError as e:
            print(f"Error cleaning up temporary directory: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred during cleanup: {e}")

if __name__ == "__main__":
    # IMPORTANT: Run this script with sudo, e.g., `sudo python3 your_script_name.py`
    # This is necessary because Ollama models are often stored in system-owned directories
    # that require root privileges to read and copy.
    print("--- Ollama Specific Model Backup Script ---")
    print("WARNING: This script requires 'sudo' privileges to access Ollama's model directory.")
    print("Please run it as: sudo python3 <script_name.py>")
    print("------------------------------------------")
    main()

