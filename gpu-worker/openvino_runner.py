import os
from pathlib import Path

import numpy as np
import torch
import openvino as ov

MUSE_DIR = Path(os.getenv("MUSETALK_DIR", r"C:\Users\minim\MuseTalk"))
MODELS_DIR = MUSE_DIR / "models"
UNET_XML = MODELS_DIR / "openvino_unet_fp16.xml"
VAE_ENCODER_XML = MODELS_DIR / "openvino_vae_encoder.xml"
VAE_DECODER_XML = MODELS_DIR / "openvino_vae_decoder.xml"
VAE_WEIGHTS = MODELS_DIR / "sd-vae" / "diffusion_pytorch_model.bin"
SCALING_FACTOR = 0.18215

class OpenVINOBackend:
    """Low-level OpenVINO layer for the existing MuseTalk exports."""
    def __init__(self, device=None):
        self.core = ov.Core()
        self.device = device or os.getenv("OPENVINO_DEVICE", "GPU")
        if self.device not in self.core.available_devices:
            raise RuntimeError(
                f"OpenVINO device {self.device!r} is unavailable. "
                f"Available devices: {self.core.available_devices}"
            )
        missing = [str(p) for p in (UNET_XML, VAE_ENCODER_XML, VAE_DECODER_XML) if not p.is_file()]
        if missing:
            raise RuntimeError("OpenVINO model files are missing:\n" + "\n".join(missing))
        self.unet = self.core.compile_model(UNET_XML, self.device)
        self.vae_encoder = self.core.compile_model(VAE_ENCODER_XML, self.device)
        self.vae_decoder = self.core.compile_model(VAE_DECODER_XML, self.device)
        self._unet_inputs = {self._input_name(p): p for p in self.unet.inputs}
        self._load_vae_1x1_convs()

    @staticmethod
    def _input_name(port):
        names = list(port.get_names())
        return names[0] if names else port.get_any_name()

    def info(self):
        return {
            "device": self.device,
            "available_devices": list(self.core.available_devices),
            "unet_inputs": [
                {"name": self._input_name(p), "shape": str(p.get_partial_shape()), "type": str(p.get_element_type())}
                for p in self.unet.inputs
            ],
            "unet_outputs": [
                {"shape": str(p.get_partial_shape()), "type": str(p.get_element_type())}
                for p in self.unet.outputs
            ],
            "vae_encoder_output": str(self.vae_encoder.output(0).get_partial_shape()),
            "vae_decoder_input": str(self.vae_decoder.input(0).get_partial_shape()),
            "vae_decoder_output": str(self.vae_decoder.output(0).get_partial_shape()),
        }

    def _load_vae_1x1_convs(self):
        """Load only Diffusers AutoencoderKL quant/post-quant 1x1 conv weights."""
        if not VAE_WEIGHTS.is_file():
            raise RuntimeError(f"VAE weights not found: {VAE_WEIGHTS}")
        state = torch.load(VAE_WEIGHTS, map_location="cpu")
        def get(name):
            value = state.get(name)
            if value is None:
                raise RuntimeError(f"Missing VAE weight: {name}")
            return value.detach().cpu().numpy().astype(np.float32)
        self.quant_w = get("quant_conv.weight")
        self.quant_b = get("quant_conv.bias")
        self.post_quant_w = get("post_quant_conv.weight")
        self.post_quant_b = get("post_quant_conv.bias")
        del state

    @staticmethod
    def _conv1x1(x, weight, bias):
        return np.einsum("oc,bchw->bohw", weight[:, :, 0, 0], x) + bias[None, :, None, None]

    def encode(self, image):
        image = np.asarray(image, dtype=np.float32)
        output = self.vae_encoder({self.vae_encoder.input(0): image})[self.vae_encoder.output(0)]
        if output.ndim != 4 or output.shape[1] != 8:
            raise RuntimeError(f"Unexpected VAE encoder output shape: {output.shape}")
        return self._conv1x1(output, self.quant_w, self.quant_b)

    @staticmethod
    def posterior_sample(encoder_output, rng=None):
        encoder_output = np.asarray(encoder_output, dtype=np.float32)
        if encoder_output.ndim != 4 or encoder_output.shape[1] != 8:
            raise ValueError(f"Expected [B,8,H,W] encoder output, got {encoder_output.shape}")
        mean = encoder_output[:, :4]
        logvar = np.clip(encoder_output[:, 4:], -30.0, 20.0)
        std = np.exp(0.5 * logvar)
        noise = (rng.standard_normal(mean.shape).astype(np.float32)
                 if rng is not None else np.random.randn(*mean.shape).astype(np.float32))
        return mean + std * noise

    def encode_latents(self, image, sample=True, rng=None):
        encoded = self.encode(image)
        latent = self.posterior_sample(encoded, rng) if sample else encoded[:, :4]
        return latent * SCALING_FACTOR

    def decode_latents(self, latents):
        latents = np.asarray(latents, dtype=np.float32)
        if latents.ndim != 4 or latents.shape[1] != 4:
            raise ValueError(f"Expected [B,4,H,W] latents, got {latents.shape}")
        unscaled = latents / SCALING_FACTOR
        unscaled = self._conv1x1(unscaled, self.post_quant_w, self.post_quant_b)
        decoded = self.vae_decoder({self.vae_decoder.input(0): unscaled})[self.vae_decoder.output(0)]
        # MuseTalk blending expects uint8 BGR images in HWC layout.
        # The OpenVINO export returns float RGB tensors in NCHW layout.
        if decoded.ndim != 4 or decoded.shape[1] != 3:
            raise RuntimeError(f"Unexpected VAE decoder output shape: {decoded.shape}")
        decoded = np.transpose(decoded, (0, 2, 3, 1))
        decoded = np.clip((decoded + 1.0) * 127.5, 0, 255).astype(np.uint8)
        decoded = decoded[:, :, :, ::-1]
        return decoded

    def unet_inference(self, latent_model_input, timestep, encoder_hidden_states):
        feed = {}
        # The exported OpenVINO UNet names its timestep input "33".
        # Prefer the semantic name when available, otherwise use the second
        # input by position, which is how the current export was produced.
        timestep_port = self._unet_inputs.get("timestep")
        if timestep_port is None:
            timestep_port = self.unet.inputs[1]

        feed = {
            self._unet_inputs["sample"]: np.asarray(latent_model_input),
            timestep_port: np.asarray(timestep),
            self._unet_inputs["encoder_hidden_states"]: np.asarray(encoder_hidden_states),
        }
        return self.unet(feed)[self.unet.output(0)]

if __name__ == "__main__":
    backend = OpenVINOBackend()
    print("OpenVINO backend carregado.")
    for key, value in backend.info().items():
        print(f"{key}: {value}")
