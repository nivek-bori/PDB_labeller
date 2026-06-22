import numpy as np
import os
from PIL import Image

def load_image_dataset(img_dir_path: str) -> list[dict[str, any]]:
	"""
	Load all images from a directory.
	Returns a list of dictionaries of {'timestamp': str, 'img': np.ndarray}
	Reshapes all images into first image's shape.
	"""
	IMAGE_EXTENSIONS = {
		".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp", ".ppm",
		".pgm", ".pbm", ".pnm", ".ico", ".jfif", ".heic", ".heif"
	}

	image_file_names = [
		f for f in os.listdir(img_dir_path)
		if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
	]

	if not image_file_names:
		raise ValueError(f"No image files found in directory {img_dir_path}")

	images = []
	base_size = None

	for file_name in sorted(image_file_names):
		file_path = os.path.join(img_dir_path, file_name)
		
		with Image.open(file_path) as img:
			img = img.convert("RGB")
			if base_size is None:
				base_size = img.size
			if img.size != base_size:
				img = img.resize(base_size)
				images.append({ 'timestamp': os.path.splitext(file_name)[0], 'img': np.array(img) })
				
	return images