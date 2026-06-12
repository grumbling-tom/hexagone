# Design resources

Low-fidelity wireframing assets for designing Hexagone screens.

## Files

| File | What it is |
| --- | --- |
| `hexagone-wireframe-kit.excalidraw` | A reusable, greyscale wireframe component kit at **1:1 scale** (real UI dimensions). Atoms → molecules → organisms, plus design tokens (spacing / type / grey scales) and 1:1 device artboards (Desktop 1440×900, Mobile 390×844). Includes an extended set: states (empty / loading / error / success), form controls, feedback & data-viz, and navigation. |
| `hexagone-dashboard-example.excalidraw` | A worked example — the Hexagone dashboard composed inside the desktop artboard using the kit's components. Reference for "the kit in use". |
| `gen_kit.py` | Generator for the kit file. |
| `gen_example.py` | Generator for the worked example. |

## Opening

Open [excalidraw.com](https://excalidraw.com) (or the VS Code Excalidraw extension) and **File → Open** the `.excalidraw` file, or drag it onto the canvas.

Each component is **grouped**, so a single click-drag selects the whole thing. Select one and **Add to library** to reuse it across drawings.

## Conventions

- **Greyscale only.** Wireframing in greyscale forces hierarchy to come from size, weight, and spacing rather than colour — the core lesson from [Refactoring UI](https://www.refactoringui.com/).
- **1:1 dimensions.** Buttons ~120×40, inputs ~290×40, 14px body text, 40px avatars — so kit components drop straight into the device artboards without rescaling.
- **Tokens:** spacing `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`; type `30 / 24 / 20 / 18 / 16 / 14 / 13 / 12` (body 14, caption 12); a 6-step grey ramp with roles.

## Regenerating

The `.excalidraw` files are generated, not hand-authored. To change them, edit the generator and re-run it (writes the `.excalidraw` into the current directory):

```sh
python3 gen_kit.py        # -> hexagone-wireframe-kit.excalidraw
python3 gen_example.py     # -> hexagone-dashboard-example.excalidraw
```

No dependencies beyond the Python standard library.
