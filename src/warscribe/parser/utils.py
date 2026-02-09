"""Shared utility functions for the Warscribe system."""

import os
import glob


def find_audio(input_dir, video_id):
    """Find audio file for a video_id regardless of extension.
    
    Searches the input directory for common audio/video extensions,
    falling back to a glob pattern match.
    
    Returns the path if found, else None.
    """
    for ext in ['wav', 'm4a', 'webm', 'opus', 'mp3', 'ogg', 'mp4', 'mkv']:
        path = os.path.join(input_dir, f"{video_id}.{ext}")
        if os.path.exists(path):
            return path
    # Last resort: glob
    pattern = os.path.join(input_dir, f"{video_id}.*")
    matches = [f for f in glob.glob(pattern) if not f.endswith('.json')]
    return matches[0] if matches else None
