DEFAULT_CONFIG = {
  "app_config": {
    "video_defaults": {
      "private": True
    },
    "allow_public_upload": False,
    "public_upload_folder_name": "public uploads",
    "admin_upload_folder_name": "uploads"
  },
  "ui_config": {
    "shareable_link_domain": "",
    "show_public_upload": False,
    "show_admin_upload": True,
  }
}

SUPPORTED_FILE_TYPES = ['video/mp4', 'video/mov', 'video/webm', 'video/flv', 'video/H264', 'video/H265']
SUPPORTED_FILE_EXTENSIONS = ['.mp4', '.mov', '.webm', '.flv', '.mkv']