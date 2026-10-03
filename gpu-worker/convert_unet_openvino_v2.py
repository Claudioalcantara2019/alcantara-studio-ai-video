"""
Re-export MuseTalk v1.5 UNet for OpenVINO.

Run this script with the dedicated openvino-converter Python environment.
The MuseTalk runtime environment is intentionally not modified.

This script builds the UNet from the official MuseTalk v1.5 config +
checkpoint instead of converting a previously exported OpenVINO file.
"""

from pathlib import Path
import gc
import json
import shutil

import torch
import openvino as ov
from diffusers import UNet2DConditionModel


MUSE_DIR = Path(r"C:\Users\minim\MuseTalk")
CONFIG_PATH = MUSE_DIR / "models" / "musetalkV15" / "musetalk.json"
WEIGHTS_PATH = MUSE_DIR / "models" / "musetalkV15" / "unet.pth"
OUTPUT_PATH = MUSE_DIR / "models" / "openvino_unet_v2_fp16.xml"


class MuseTalkUNetWrapper(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, sample, timestep, encoder_hidden_states):
        # MuseTalk uses the Diffusers .sample tensor exactly.
        return self.model(
            sample,
            timestep,
            encoder_hidden_states=encoder_hidden_states,
            return_dict=False,
        )[0]


def main():
    print("=== MuseTalk v1.5 -> OpenVINO UNet v2 ===")
    print(f"PyTorch: {torch.__version__}")
    print(f"OpenVINO: {ov.__version__}")
    print(f"Config : {CONFIG_PATH}")
    print(f"Weights: {WEIGHTS_PATH}")
    print(f"Output : {OUTPUT_PATH}")

    if not hasattr(torch, "float8_e4m3fn"):
        raise RuntimeError(
            "This converter requires a newer PyTorch with float8_e4m3fn. "
            "Run it with the dedicated openvino-converter environment."
        )

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(CONFIG_PATH)
    if not WEIGHTS_PATH.exists():
        raise FileNotFoundError(WEIGHTS_PATH)

    free_gb = shutil.disk_usage(OUTPUT_PATH.parent).free / (1024 ** 3)
    print(f"Free disk before conversion: {free_gb:.2f} GB")
    if free_gb < 6:
        raise RuntimeError(
            "Less than 6 GB free on the MuseTalk drive. "
            "Free some space before creating the new UNet."
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    print("Loading official Diffusers UNet2DConditionModel...")
    model = UNet2DConditionModel(**config)

    print("Loading MuseTalk v1.5 checkpoint...")
    state = torch.load(WEIGHTS_PATH, map_location="cpu")
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]

    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        raise RuntimeError(f"Missing checkpoint keys: {missing[:10]}")
    if unexpected:
        raise RuntimeError(f"Unexpected checkpoint keys: {unexpected[:10]}")

    # The checkpoint is several GB. Release the second copy before conversion
    # so the 8 GB Windows machine does not keep both checkpoint + model in RAM.
    del state
    gc.collect()

    model.eval()
    wrapper = MuseTalkUNetWrapper(model).eval()

    # MuseTalk's inference path uses batches of 8 by default.
    sample = torch.randn(8, 8, 32, 32, dtype=torch.float32)
    timestep = torch.zeros(8, dtype=torch.int64)
    encoder_hidden_states = torch.randn(8, 50, 384, dtype=torch.float32)

    print("Converting the exact PyTorch graph to OpenVINO...")
    with torch.no_grad():
        ov_model = ov.convert_model(
            wrapper,
            example_input=(sample, timestep, encoder_hidden_states),
        )

    print("OpenVINO inputs:")
    for inp in ov_model.inputs:
        print(" ", inp.any_name, inp.partial_shape, inp.element_type)

    print("OpenVINO outputs:")
    for out in ov_model.outputs:
        print(" ", out.any_name, out.partial_shape, out.element_type)

    # Save as FP16 weights for Intel GPU execution.
    print("Saving FP16 OpenVINO model...")
    ov.save_model(
        ov_model,
        str(OUTPUT_PATH),
        compress_to_fp16=True,
    )

    print("DONE")
    print(f"XML: {OUTPUT_PATH}")
    print(f"BIN: {OUTPUT_PATH.with_suffix('.bin')}")


if __name__ == "__main__":
    main()
