"""Utilities for downloading and uploading probe models to/from HuggingFace Hub."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union

import torch
from huggingface_hub import HfApi, hf_hub_download, login
from huggingface_hub.utils import validate_repo_id

# Default directory for saving probes locally
LOCAL_PROBES_DIR = Path(__file__).parent.parent / "value_head_probes"

def download_probe_from_hf(
    repo_id: str,
    probe_id: Optional[str] = None,
    local_folder: Optional[Union[str, Path]] = None,
    hf_repo_subfolder_prefix: str = "value_head_probes",
    token: Optional[str] = None
) -> None:
    """Simplified probe download function for Modal."""
    api = HfApi()

    if local_folder is None:
        local_folder = LOCAL_PROBES_DIR / probe_id
    elif isinstance(local_folder, str):
        local_folder = Path(local_folder)

    local_folder.mkdir(parents=True, exist_ok=True)
    
    # List files in the repository subfolder
    repo_files = api.list_repo_files(
        repo_id=repo_id,
        repo_type="model",
        revision="main"
    )
    
    # Filter files by subfolder
    path_in_repo = f"{hf_repo_subfolder_prefix}/{probe_id}"
    subfolder_files = [f for f in repo_files if f.startswith(f"{path_in_repo}/")]
    
    # Download each file
    for file_path in subfolder_files:
        # Get relative path within subfolder
        relative_path = file_path[len(path_in_repo):].lstrip('/')
        
        # Create subdirectory if needed
        local_file_path = local_folder / relative_path
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download file
        downloaded_file = hf_hub_download(
            repo_id=repo_id,
            filename=file_path,
            token=token
        )
        
        # Copy to destination
        shutil.copy(downloaded_file, local_file_path)
    
    print(f"Downloaded probe to {local_folder}")


def upload_probe_to_hf(
    repo_id: str,
    probe_id: Optional[str] = None,
    local_folder: Optional[Union[str, Path]] = None,
    hf_repo_subfolder_prefix: str = "value_head_probes",
    token: Optional[str] = None,
    private: bool = False,
    commit_message: str = "Upload probe model"
) -> str:
    """
    Uploads a probe (LoRA adapters + value head) to HuggingFace Hub.
    
    Args:
        probe_dir: Local directory containing the probe files
        repo_id: Destination repository ID in the format 'username/repo_name'
        repo_subfolder: Optional subfolder within the repo to upload to
        token: HF API token (required for uploading)
        private: Whether to make the repository private
        commit_message: Message for the commit
        
    Returns:
        URL of the uploaded model on Hugging Face Hub
    """
    # Validate inputs
    validate_repo_id(repo_id)

    if local_folder is None:
        local_folder = LOCAL_PROBES_DIR / probe_id
    elif isinstance(local_folder, str):
        local_folder = Path(local_folder)
    
    if not local_folder.exists():
        raise ValueError(f"Probe directory {probe_dir} does not exist")

    path_in_repo = f"{hf_repo_subfolder_prefix}/{probe_id}"
    
    # Login if token is provided
    if token:
        login(token=token)
    
    api = HfApi()
    
    # Create repo if it doesn't exist
    api.create_repo(
        repo_id=repo_id,
        exist_ok=True,
        private=private,
        token=token
    )
    
    print(f"Uploading folder {local_folder} to {repo_id}...")
    api.upload_folder(
        folder_path=str(local_folder),
        repo_id=repo_id,
        repo_type="model",
        path_in_repo=path_in_repo,
        commit_message=commit_message,
        token=token,
    )
    
    # Return the URL
    url = f"https://huggingface.co/{repo_id}"
    if repo_subfolder:
        url += f"/tree/main/{repo_subfolder}"
    
    print(f"Successfully uploaded probe to {url}")
    return url

