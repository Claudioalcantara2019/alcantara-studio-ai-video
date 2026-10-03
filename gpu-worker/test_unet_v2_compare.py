"""
Fast isolated validation of the MuseTalk v1.5 UNet OpenVINO v2 export.

Runs ONE forward pass in PyTorch and ONE in OpenVINO on the same inputs.
It does not process video, audio, landmarks, or VAE.
Run with the dedicated openvino-converter environment.
"""
from pathlib import Path
import gc
import json
import numpy as np
import torch
import openvino as ov
from diffusers import UNet2DConditionModel

MUSE_DIR = Path(r"C:\Users\minim\MuseTalk")
CONFIG_PATH = MUSE_DIR / "models" / "musetalkV15" / "musetalk.json"
WEIGHTS_PATH = MUSE_DIR / "models" / "musetalkV15" / "unet.pth"
OV_PATH = MUSE_DIR / "models" / "openvino_unet_v2_fp16.xml"

def main():
    print("=== UNET V2 ISOLATED COMPARISON ===")
    print("PyTorch:", torch.__version__)
    print("OpenVINO:", ov.__version__)
    print("OpenVINO model:", OV_PATH)
    if not OV_PATH.is_file():
        raise FileNotFoundError(f"Missing: {OV_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    print("Loading original MuseTalk v1.5 UNet...")
    model = UNet2DConditionModel(**config)
    state = torch.load(WEIGHTS_PATH, map_location="cpu")
    model.load_state_dict(state, strict=True)
    del state
    gc.collect()
    model.eval()

    torch.manual_seed(1234)
    sample = torch.randn(1, 8, 32, 32, dtype=torch.float32)
    timestep = torch.tensor([0], dtype=torch.int64)
    hidden = torch.randn(1, 50, 384, dtype=torch.float32)

    print("Running PyTorch forward...")
    with torch.no_grad():
        pt = model(
            sample,
            timestep,
            encoder_hidden_states=hidden,
            return_dict=False,
        )[0].cpu().numpy()

    print("Loading OpenVINO v2...")
    core = ov.Core()
    compiled = core.compile_model(str(OV_PATH), "CPU")
    result = compiled({
        "sample": sample.numpy(),
        "timestep": timestep.numpy(),
        "encoder_hidden_states": hidden.numpy(),
    })
    ov_out = next(iter(result.values()))
    ov_out = np.asarray(ov_out)

    if pt.shape != ov_out.shape:
        print("RESULT: FAIL")
        print("Shape mismatch:", pt.shape, ov_out.shape)
        return

    diff = np.abs(pt - ov_out)
    print("PyTorch shape:", pt.shape)
    print("OpenVINO shape:", ov_out.shape)
    print("max_abs_diff:", float(diff.max()))
    print("mean_abs_diff:", float(diff.mean()))
    print("pt_mean:", float(pt.mean()), "ov_mean:", float(ov_out.mean()))
    print("pt_std:", float(pt.std()), "ov_std:", float(ov_out.std()))

    # FP16 export should be numerically close, not bit-identical.
    if float(diff.mean()) < 0.02 and float(diff.max()) < 0.5:
        print("RESULT: PASS — OpenVINO v2 matches the PyTorch UNet within the FP16 tolerance used here.")
    else:
        print("RESULT: FAIL — OpenVINO v2 differs too much from PyTorch.")
    
if __name__ == "__main__":
    main()
