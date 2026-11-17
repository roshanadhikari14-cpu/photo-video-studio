"""Cinematic per-frame grade (numpy): dehaze levels, S-curve contrast, vibrance, teal/orange split-tone,
golden sky gradient on the sky side, soft vignette."""
import numpy as np

class Grade:
    def __init__(self, W, H, sky_side="top", sky=(1.0, 0.72, 0.45), sky_amt=0.35, contrast=0.55, vib=0.45,
                 warm=0.05, teal=0.05, black=0.06, white=0.97, vignette=0.28, gamma=1.0, dehaze=0.0, air=(0.86, 0.89, 0.93), clarity=0.0):
        self.dehaze, self.air, self.clarity = dehaze, np.array(air, np.float32), clarity
        self.black, self.white, self.contrast, self.vib, self.gamma = black, white, contrast, vib, gamma
        self.warm, self.teal = warm, teal
        # sky gradient mask: 1 at the sky edge, fading to 0 by ~60% of the frame
        if sky_side == "top":
            t = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
        else:  # "right": footage turned sideways, sky is on the right
            t = (1 - np.linspace(0, 1, W))[None, :] * np.ones((H, 1))
        m = np.clip(1 - t / 0.6, 0, 1) ** 1.4
        self.sky = (m[..., None] * sky_amt).astype(np.float32)
        self.skycol = np.array(sky, np.float32)
        y = np.linspace(-1, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
        self.vig = (1 - vignette * np.clip(x ** 2 * 0.55 + y ** 2 * 0.4 - 0.15, 0, 1))[..., None].astype(np.float32)

    def __call__(self, buf, W, H):
        a = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        if self.dehaze:  # dark-channel-prior dehaze, computed at 1/8 res for speed
            from PIL import Image, ImageFilter
            dc = Image.fromarray((a.min(2) * 255).astype(np.uint8)).resize((W // 8, H // 8), Image.BILINEAR)
            dc = dc.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR)
            dc = np.asarray(dc, np.float32)[..., None] / 255
            # protect the sky (very hazy, flat, full of compression blocks): dehaze it only lightly
            strength = self.dehaze * np.clip((0.84 - dc) / 0.16, 0.2, 1)
            t = np.maximum(1 - strength * dc / self.air.min(), 0.35)
            a = np.clip((a - self.air) / t + self.air, 0, 1)
        if self.clarity:  # local contrast
            from PIL import Image, ImageFilter
            bl = Image.fromarray((a * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
            a = np.clip(a + (a - np.asarray(bl, np.float32) / 255) * self.clarity, 0, 1)
        # 1. dehaze: set black/white points
        a = np.clip((a - self.black) / (self.white - self.black), 0, 1)
        if self.gamma != 1:
            a = a ** self.gamma
        # 2. golden sky: multiply a warm colour into the bright sky side (soft, luminance-weighted)
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        k = self.sky * np.clip((lum[..., None] - 0.3) / 0.5, 0, 1)
        a = a * (1 - k) + a * self.skycol * k * 1.12
        # 3. S-curve contrast
        s = a * a * (3 - 2 * a)
        a = a + (s - a) * self.contrast
        # 4. vibrance (boost less-saturated colours more)
        lum = (a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        sat = a.max(2, keepdims=True) - a.min(2, keepdims=True)
        a = lum + (a - lum) * (1 + self.vib * (1 - sat))
        # 5. split-tone: teal shadows, warm highlights
        lum = np.clip((a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None], 0, 1)
        a = a + (1 - lum) ** 2 * np.array([-self.teal, self.teal * 0.3, self.teal], np.float32) \
              + lum ** 2 * np.array([self.warm, self.warm * 0.35, -self.warm], np.float32)
        # 6. vignette
        a = a * self.vig
        return (np.clip(a, 0, 1) * 255).astype(np.uint8).tobytes()
