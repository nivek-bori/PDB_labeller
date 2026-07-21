import os
import shutil
import numpy as np
import matplotlib.pyplot as plt

bin_dir = "/Users/kevinboriboonsomsin/Downloads/2026-03-05_153720/lidar"
tmp_dir = "tmp"
file_extension = "png"  # Change to 'jpg', 'svg', etc. if needed

# 1. Setup tmp folder & delete existing files inside it
if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)  # Delete folder and all contents
os.makedirs(tmp_dir)        # Recreate fresh empty folder

# List all files in the directory and sort them
filenames = sorted(os.listdir(bin_dir))

print(f"Total files found: {len(filenames)}")

plot_counter = 1

for i in range(0, len(filenames), 10):
    filename = filenames[i]
    if not filename.endswith('.bin'):
        continue  # skip non-bin files

    bin_path = os.path.join(bin_dir, filename)

    # Load LiDAR points
    try:
        points = np.fromfile(bin_path, dtype=np.float32).reshape(-1, 4)[:, :3]
    except Exception as e:
        print(f"Failed to read {bin_path}: {e}")
        continue

    # Flip axis (if necessary)
    # points[:, 0] = -points[:, 0]
    # points[:, 1] = -points[:, 1]

    # Filter points (keep within 40m radius and strip high ceiling/ground noise)
    mask = (np.abs(points[:, 0]) < 40) & (np.abs(points[:, 1]) < 40) & (points[:, 2] > -2) & (points[:, 2] < 2)
    points = points[mask]

    # Create 2D Top-Down Plot (BEV)
    fig, ax = plt.subplots(figsize=(8, 8))

    # Scatter X vs Y
    ax.scatter(points[:, 0], points[:, 1], s=0.1, c=points[:, 2], cmap='viridis', alpha=0.6)

    # Draw Coordinate Origin and Direction Arrows
    ax.annotate(
        '', xy=(10, 0), xytext=(0, 0),
        arrowprops=dict(facecolor='red', edgecolor='red', width=2, headwidth=8)
    )

    ax.annotate(
        '', xy=(0, 10), xytext=(0, 0),
        arrowprops=dict(facecolor='green', edgecolor='green', width=2, headwidth=8)
    )

    ax.set_aspect('equal')
    ax.set_xlabel("X coordinate (meters, flipped)")
    ax.set_ylabel("Y coordinate (meters)")
    ax.set_title(f"Top-Down LiDAR View (Origin at Sensor, X Flipped) - {filename}")
    ax.grid(True)

    # Save file sequentially (tmp/plot1.png, tmp/plot2.png, etc.)
    save_path = os.path.join(tmp_dir, f"plot{plot_counter}.{file_extension}")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the plot to free RAM

    print(f"Saved: {save_path}")
    plot_counter += 1