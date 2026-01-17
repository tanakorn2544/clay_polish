# Clay Polish - Blender Addon

ZBrush-style Clay Polish for Blender. Smooths curved areas while preserving flat/planar surfaces.

## Features

- **Curvature-based smoothing** - Only smooths curved areas, preserves flat planes
- **Pinch Tips** - Sharpen pointy areas like horns, fingers
- **Non-destructive** - Works as Geometry Nodes modifier
- **Multires compatible** - Doesn't destroy modifier stack

## Installation

1. Download `clay_polish.zip`
2. Blender → Edit → Preferences → Add-ons → Install
3. Select the ZIP file
4. Enable "Clay Polish"

## Usage

1. Select mesh object
2. N-Panel → **Clay Polish** tab
3. Click **"Add Clay Polish Modifier"**
4. Adjust parameters in Modifier panel

## Parameters

| Parameter | Description |
|-----------|-------------|
| **Strength** | Smoothing intensity (0-5) |
| **Iterations** | Smoothing passes (1-50) |
| **Curvature Threshold** | Lower = smooth more, Higher = only very curved |
| **Pinch Tips** | Positive = sharpen tips, Negative = round tips |
| **Keep Volume** | Blend with original to prevent shrinkage |

## Tips

- Start with **Curvature Threshold = 0.1** and adjust
- Use **Pinch Tips** on meshes with pointy features
- Lower **Keep Volume** for stronger effect

## Requirements

- Blender 4.0+

## License

MIT
