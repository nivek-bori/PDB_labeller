import os
import shutil

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# Configuration
# ============================================================

bin_dir = "/home/tsr-sim/kevin/PDB_labeller/data/raw/reduced/lidar"
tmp_dir = "tools/visualize_lidar"
file_extension = "png"

# Perspective-specific output directories
xy_dir = os.path.join(tmp_dir, "xy")
xz_dir = os.path.join(tmp_dir, "xz")
three_d_dir = os.path.join(tmp_dir, "3d")

# Plot every Nth frame
frame_step = 10

# Simple XYZ translation applied to every point, in meters.
XYZ_TRANSLATION = np.array(
    [0.0, 0.0, 0.0],
    dtype=np.float32,
)

# Viewing/filter limits
x_limit = 40
y_limit = 40
z_min = -4
z_max = 4


# ============================================================
# Setup output directories
# ============================================================

if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)

os.makedirs(xy_dir)
os.makedirs(xz_dir)
os.makedirs(three_d_dir)


# ============================================================
# Find LiDAR files
# ============================================================

filenames = sorted(filename for filename in os.listdir(bin_dir) if filename.endswith(".bin"))

print(f"Total .bin files found: {len(filenames)}")
print(f"XYZ translation: {XYZ_TRANSLATION.tolist()} meters")


# ============================================================
# Process frames
# ============================================================

plot_counter = 1

for i in range(0, len(filenames), frame_step):
    filename = filenames[i]
    bin_path = os.path.join(bin_dir, filename)

    # --------------------------------------------------------
    # Load LiDAR
    # --------------------------------------------------------

    try:
        points = np.fromfile(
            bin_path,
            dtype=np.float32,
        ).reshape(-1, 4)

    except Exception as e:
        print(f"Failed to read {bin_path}: {e}")
        continue

    # Keep XYZ only
    points = points[:, :3]

    # --------------------------------------------------------
    # Optional axis transformations
    # --------------------------------------------------------

    # points[:, 0] = -points[:, 0]
    # points[:, 1] = -points[:, 1]
    # points[:, 2] = -points[:, 2]

    # --------------------------------------------------------
    # Apply XYZ translation
    # --------------------------------------------------------

    points += XYZ_TRANSLATION

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------

    mask = (np.abs(points[:, 0]) < x_limit) & (np.abs(points[:, 1]) < y_limit) & (points[:, 2] > z_min) & (points[:, 2] < z_max)

    points = points[mask]

    if len(points) == 0:
        print(f"No points remaining after filtering: {filename}")
        continue

    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    print(f"{filename}: Z min={z.min():.2f}, Z median={np.median(z):.2f}, Z max={z.max():.2f}")

    # ========================================================
    # 1. TOP-DOWN VIEW: X vs Y
    # ========================================================

    fig, ax = plt.subplots(figsize=(8, 8))

    scatter = ax.scatter(
        x,
        y,
        s=0.1,
        c=z,
        cmap="viridis",
        alpha=0.6,
    )

    ax.annotate(
        "+X",
        xy=(10, 0),
        xytext=(0, 0),
        arrowprops=dict(
            facecolor="red",
            edgecolor="red",
            width=2,
            headwidth=8,
        ),
    )

    ax.annotate(
        "+Y",
        xy=(0, 10),
        xytext=(0, 0),
        arrowprops=dict(
            facecolor="green",
            edgecolor="green",
            width=2,
            headwidth=8,
        ),
    )

    ax.scatter(
        0,
        0,
        marker="x",
        s=100,
        linewidths=2,
        label="Coordinate origin",
    )

    ax.set_xlim(-x_limit, x_limit)
    ax.set_ylim(-y_limit, y_limit)

    ax.set_aspect("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"Top-Down View (X-Y)\n{filename}")

    ax.grid(True)
    ax.legend()

    colorbar = plt.colorbar(scatter, ax=ax)
    colorbar.set_label("Z height (m)")

    save_path = os.path.join(
        xy_dir,
        f"plot{plot_counter}.{file_extension}",
    )

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved: {save_path}")

    # ========================================================
    # 2. SIDE VIEW: X vs Z
    # ========================================================

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.scatter(
        x,
        z,
        s=0.2,
        alpha=0.6,
    )

    ax.annotate(
        "+X",
        xy=(10, 0),
        xytext=(0, 0),
        arrowprops=dict(
            facecolor="red",
            edgecolor="red",
            width=2,
            headwidth=8,
        ),
    )

    ax.annotate(
        "+Z",
        xy=(0, min(3, z_max)),
        xytext=(0, 0),
        arrowprops=dict(
            facecolor="blue",
            edgecolor="blue",
            width=2,
            headwidth=8,
        ),
    )

    ax.scatter(
        0,
        0,
        marker="x",
        s=100,
        linewidths=2,
        label="Coordinate origin",
    )

    ax.axhline(
        0,
        linewidth=1,
        linestyle="--",
    )

    ax.set_xlim(-x_limit, x_limit)
    ax.set_ylim(z_min, z_max)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_title(f"Side View (X-Z)\n{filename}")

    ax.grid(True)
    ax.legend()

    save_path = os.path.join(
        xz_dir,
        f"plot{plot_counter}.{file_extension}",
    )

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved: {save_path}")

    # ========================================================
    # 3. 3D VIEW
    # ========================================================

    fig = plt.figure(figsize=(10, 8))

    ax = fig.add_subplot(
        111,
        projection="3d",
    )

    max_plot_points = 100_000

    if len(points) > max_plot_points:
        indices = np.random.choice(
            len(points),
            max_plot_points,
            replace=False,
        )

        plot_points = points[indices]

    else:
        plot_points = points

    px = plot_points[:, 0]
    py = plot_points[:, 1]
    pz = plot_points[:, 2]

    ax.scatter(
        px,
        py,
        pz,
        s=0.1,
        c=pz,
        cmap="viridis",
        alpha=0.5,
    )

    arrow_length_xy = 8
    arrow_length_z = 3

    # +X
    ax.quiver(
        0,
        0,
        0,
        arrow_length_xy,
        0,
        0,
        linewidth=3,
        arrow_length_ratio=0.15,
    )

    # +Y
    ax.quiver(
        0,
        0,
        0,
        0,
        arrow_length_xy,
        0,
        linewidth=3,
        arrow_length_ratio=0.15,
    )

    # +Z
    ax.quiver(
        0,
        0,
        0,
        0,
        0,
        arrow_length_z,
        linewidth=3,
        arrow_length_ratio=0.15,
    )

    ax.text(
        arrow_length_xy,
        0,
        0,
        "+X",
        fontsize=12,
    )

    ax.text(
        0,
        arrow_length_xy,
        0,
        "+Y",
        fontsize=12,
    )

    ax.text(
        0,
        0,
        arrow_length_z,
        "+Z",
        fontsize=12,
    )

    ax.set_xlim(-x_limit, x_limit)
    ax.set_ylim(-y_limit, y_limit)
    ax.set_zlim(z_min, z_max)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")

    ax.set_title(f"3D LiDAR View — Coordinate Axes\n{filename}")

    ax.view_init(
        elev=20,
        azim=-60,
    )

    save_path = os.path.join(
        three_d_dir,
        f"plot{plot_counter}.{file_extension}",
    )

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved: {save_path}")

    plot_counter += 1


print(f"\nDone. Generated plots for {plot_counter - 1} LiDAR frames.")
