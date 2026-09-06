"""
================================================================================
MELODI PRO - HD MULTITRACK DAW WITH INTERACTIVE CLICKABLE INSTRUMENT WORKSTATIONS
================================================================================
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import math
import io
import wave
import struct
import os
import random

import pygame

# Initialize High-Definition Pygame Mixer (44.1 kHz, 16-bit, Low-Latency 512 Buffer)
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()

SAMPLE_RATE = 44100

# ==============================================================================
# 1. THEME CONFIGURATION
# ==============================================================================

THEMES = {
    "dark": {
        "bg": "#121212",
        "panel": "#1A1A1A",
        "card": "#242424",
        "card_hover": "#2F2F2F",
        "text": "#E0E0E0",
        "subtext": "#999999",
        "border": "#2E2E2E",
        "active_step": "#00D084",
        "inactive_step": "#1F1F1F",
        "accent": "#00D084",
        "accent_hover": "#00B070",
    },
    "light": {
        "bg": "#F4F5F7",
        "panel": "#FFFFFF",
        "card": "#EAECEF",
        "card_hover": "#DFE2E7",
        "text": "#2D3139",
        "subtext": "#757B86",
        "border": "#D1D5DB",
        "active_step": "#00985D",
        "inactive_step": "#E2E5EB",
        "accent": "#00985D",
        "accent_hover": "#007F4C",
    }
}

# ==============================================================================
# 2. CUSTOM ROUNDED BUTTON COMPONENT
# ==============================================================================

def create_rounded_rect(canvas, x1, y1, x2, y2, radius=10, **kwargs):
    points = [
        x1 + radius, y1, x1 + radius, y1, x2 - radius, y1, x2 - radius, y1,
        x2, y1, x2, y1 + radius, x2, y1 + radius, x2, y2 - radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x2 - radius, y2,
        x1 + radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius,
        x1, y2 - radius, x1, y1 + radius, x1, y1 + radius, x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, bg="#00985D", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), radius=10, width=90, height=30, hover_bg=None):
        parent_bg = parent.cget("bg") if "bg" in parent.keys() else "#FFFFFF"
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=parent_bg)
        self.command = command
        self.text = text
        self.bg = bg
        self.fg = fg
        self.font = font
        self.radius = radius
        self.width = width
        self.height = height
        self.hover_bg = hover_bg or bg
        
        self.draw(self.bg)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def draw(self, bg_color):
        self.delete("all")
        create_rounded_rect(self, 1, 1, self.width - 1, self.height - 1, radius=self.radius, fill=bg_color, outline="")
        self.create_text(self.width / 2, self.height / 2, text=self.text, fill=self.fg, font=self.font)

    def on_enter(self, event):
        self.draw(self.hover_bg)

    def on_leave(self, event):
        self.draw(self.bg)

    def on_click(self, event):
        if self.command:
            self.command()

    def update_style(self, bg, fg, hover_bg=None, parent_bg=None):
        self.bg = bg
        self.fg = fg
        if hover_bg:
            self.hover_bg = hover_bg
        if parent_bg:
            self.configure(bg=parent_bg)
        self.draw(self.bg)


# ==============================================================================
# 3. HD HARMONIC AUDIO ENGINE & INSTRUMENT LIBRARY
# ==============================================================================

class AudioEngine:
    def __init__(self):
        self.is_playing = False
        self.is_recording = False
        self.bpm = 110
        self.playback_speed = 1.0
        self.current_step = 0
        self.smooth_progress = 0.0
        self.master_volume = 0.8
        self.target_voice_filename = "ElevenLabs_2026-08-18T18_27_26_Laura - a top narration voice_pvc_s50_m2.mp3"
        self.loaded_filename = self.target_voice_filename
        self.running = True

        self.sound_cache = {}
        self.piano_frequencies = {}
        for midi_note in range(48, 73):
            freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
            self.piano_frequencies[midi_note] = freq

        self._init_instrument_cache()
        self._load_ai_voice_sample()

        self.channels = [
            {
                "name": "🎙️ Laura Voice", "type": "custom", "sound_key": "ai_voice_sample",
                "vol_str": "95%", "volume": 0.95, "muted": False, "color": "#00985D",
                "steps": [True, False, False, False, True, False, False, False, True, False, False, False, True, False, False, False]
            },
            {"name": "Kick 808",    "type": "kick",     "vol_str": "60%", "volume": 0.60, "muted": False, "color": "#D32F2F", "steps": [True, False, False, False, True, False, False, False, True, False, False, False, True, False, False, False]},
            {"name": "Snare Pro",   "type": "snare",    "vol_str": "55%", "volume": 0.55, "muted": False, "color": "#388E3C", "steps": [False, False, False, False, True, False, False, False, False, False, False, False, True, False, False, False]},
            {"name": "Closed Hat",  "type": "hihat",    "vol_str": "45%", "volume": 0.45, "muted": False, "color": "#F57C00", "steps": [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]},
            {"name": "Tin Whistle", "type": "tin_whistle","vol_str": "50%", "volume": 0.50, "muted": False, "color": "#00ACC1", "steps": [False, False, True, False, False, False, True, False, False, False, True, False, False, False, True, False]},
            {"name": "Steel Drum",  "type": "steel_drum", "vol_str": "55%", "volume": 0.55, "muted": False, "color": "#5E35B1", "steps": [True, False, False, True, False, False, True, False, True, False, False, True, False, False, True, False]},
            {"name": "Marimba",     "type": "marimba",  "vol_str": "50%", "volume": 0.50, "muted": False, "color": "#D81B60", "steps": [False, True, False, False, False, True, False, False, False, True, False, False, False, True, False, False]},
            {"name": "Pipe Organ",  "type": "organ",    "vol_str": "45%", "volume": 0.45, "muted": False, "color": "#8E24AA", "steps": [True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False]},
            {"name": "Strings Pad", "type": "strings",  "vol_str": "40%", "volume": 0.40, "muted": False, "color": "#3949AB", "steps": [True, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False]},
            {"name": "Ac. Guitar",  "type": "guitar",   "vol_str": "50%", "volume": 0.50, "muted": False, "color": "#00897B", "steps": [False, False, True, False, True, False, False, True, False, False, True, False, True, False, False, True]},
            {"name": "Synth Brass", "type": "brass",    "vol_str": "45%", "volume": 0.45, "muted": False, "color": "#FB8C00", "steps": [False, True, False, False, True, False, False, True, False, True, False, False, True, False, False, True]},
            {"name": "Class. Flute","type": "flute",    "vol_str": "50%", "volume": 0.50, "muted": False, "color": "#43A047", "steps": [False, False, False, True, False, False, False, True, False, False, False, True, False, False, False, True]},
            {"name": "808 Cowbell", "type": "cowbell",  "vol_str": "55%", "volume": 0.55, "muted": False, "color": "#E53935", "steps": [False, False, True, False, False, False, True, False, False, False, True, False, False, False, True, False]},
            {"name": "Tambourine",  "type": "tambourine","vol_str": "45%", "volume": 0.45, "muted": False, "color": "#FDD835", "steps": [False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True]},
            {"name": "Conga Drum",  "type": "conga",    "vol_str": "60%", "volume": 0.60, "muted": False, "color": "#6D4C41", "steps": [True, False, False, False, True, False, False, True, False, False, True, False, True, False, False, False]},
            {"name": "Shaker FX",   "type": "shaker",   "vol_str": "40%", "volume": 0.40, "muted": False, "color": "#78909C", "steps": [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]},
        ]

        self.piano_roll_tracks = [
            {"name": "C5 (High)", "midi": 72, "color": "#C2185B", "vol_str": "50%", "volume": 0.50, "muted": False, "steps": [False, False, False, True,  False, False, False, True,  False, False, False, True,  False, False, True,  False]},
            {"name": "A4",        "midi": 69, "color": "#F57C00", "vol_str": "45%", "volume": 0.45, "muted": False, "steps": [False, False, True,  False, False, False, True,  False, False, False, True,  False, False, True,  False, False]},
            {"name": "G4",        "midi": 67, "color": "#388E3C", "vol_str": "45%", "volume": 0.45, "muted": False, "steps": [False, True,  False, False, False, True,  False, False, False, True,  False, False, True,  False, False, False]},
            {"name": "E4",        "midi": 64, "color": "#455A64", "vol_str": "45%", "volume": 0.45, "muted": False, "steps": [True,  False, False, False, True,  False, False, False, True,  False, False, False, True,  False, False, False]},
            {"name": "C4 (Base)", "midi": 60, "color": "#D32F2F", "vol_str": "55%", "volume": 0.55, "muted": False, "steps": [True,  False, False, False, True,  False, False, False, True,  False, False, False, True,  False, False, True]},
        ]

        self.arrangement_tracks = [
            {"name": "Vocals / Voiceover", "color": "#00985D", "clips": [(1, 8, "Verse 1"), (17, 24, "Verse 2")]},
            {"name": "Drum Machine 808",   "color": "#D32F2F", "clips": [(5, 16, "Beat Drop"), (17, 32, "Chorus Groove")]},
            {"name": "Acoustic Melody",    "color": "#00ACC1", "clips": [(9, 16, "Whistle Hook"), (25, 32, "Outro Lead")]},
            {"name": "Orchestral Strings", "color": "#3949AB", "clips": [(5, 32, "Full Pad Harmony")]},
            {"name": "Percussion & FX",    "color": "#FDD835", "clips": [(1, 4, "Intro Shaker"), (29, 32, "Outro Sweep")]}
        ]

        self.sequencer_thread = threading.Thread(target=self._sequencer_loop, daemon=True)
        self.sequencer_thread.start()

    def _load_ai_voice_sample(self):
        sound_key = "ai_voice_sample"
        if os.path.exists(self.target_voice_filename):
            try:
                self.sound_cache[sound_key] = pygame.mixer.Sound(self.target_voice_filename)
                return
            except Exception as e:
                print(f"Error loading uploaded voice file: {e}")
        self.sound_cache[sound_key] = self._generate_synth_sound(440, duration_ms=800)

    def _wav_buffer_to_sound(self, raw_bytes):
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(raw_bytes)
        wav_buffer.seek(0)
        return pygame.mixer.Sound(file=wav_buffer)

    # --- Procedural Sound Generators ---
    def _generate_tin_whistle_sound(self, duration_ms=400):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 1046.50
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = min(1.0, i / (SAMPLE_RATE * 0.02)) * math.exp(-3.5 * t)
            sample_val = math.sin(2 * math.pi * freq * t) * env
            sample = int(max(-32768, min(32767, sample_val * 11000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_steel_drum_sound(self, duration_ms=500):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 523.25
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = math.exp(-6.0 * t)
            val = (math.sin(2 * math.pi * freq * t) + 0.5 * math.sin(2 * math.pi * freq * 2.76 * t)) * env
            sample = int(max(-32768, min(32767, val * 12000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_marimba_sound(self, duration_ms=300):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 440.0
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = math.exp(-12.0 * t)
            val = (math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * freq * 4.0 * t)) * env
            sample = int(max(-32768, min(32767, val * 13000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_organ_sound(self, duration_ms=500):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 329.63
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = min(1.0, i / (SAMPLE_RATE * 0.01)) * math.exp(-2.0 * t)
            val = (math.sin(2 * math.pi * freq * t) + 0.5 * math.sin(2 * math.pi * freq * 2 * t)) * env
            sample = int(max(-32768, min(32767, val * 10000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_strings_sound(self, duration_ms=650):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 220.0
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = min(1.0, i / (SAMPLE_RATE * 0.08)) * math.exp(-3.0 * t)
            val = (math.sin(2 * math.pi * freq * t) + 0.6 * math.sin(2 * math.pi * freq * 2.0 * t)) * env
            sample = int(max(-32768, min(32767, val * 11000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_guitar_sound(self, duration_ms=450):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 196.0
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = math.exp(-7.0 * t)
            val = (math.sin(2 * math.pi * freq * t) + 0.7 * math.sin(2 * math.pi * freq * 2.0 * t)) * env
            sample = int(max(-32768, min(32767, val * 12000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_brass_sound(self, duration_ms=400):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 261.63
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = min(1.0, i / (SAMPLE_RATE * 0.03)) * math.exp(-4.0 * t)
            val = (math.sin(2 * math.pi * freq * t) + 0.8 * math.sin(2 * math.pi * freq * 3.0 * t)) * env
            sample = int(max(-32768, min(32767, val * 12000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_flute_sound(self, duration_ms=450):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        freq = 587.33
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = min(1.0, i / (SAMPLE_RATE * 0.05)) * math.exp(-3.0 * t)
            val = math.sin(2 * math.pi * freq * t + 0.4 * math.sin(2 * math.pi * 6 * t)) * env
            sample = int(max(-32768, min(32767, val * 11000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_cowbell_sound(self, duration_ms=200):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = math.exp(-15.0 * t)
            val = (math.sin(2 * math.pi * 560 * t) + math.sin(2 * math.pi * 840 * t)) * env
            sample = int(max(-32768, min(32767, val * 13000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_tambourine_sound(self, duration_ms=120):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = math.exp(-30.0 * t)
            val = random.uniform(-1.0, 1.0) * env
            sample = int(max(-32768, min(32767, val * 9000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_conga_sound(self, duration_ms=250):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            freq = 180.0 * math.exp(-20.0 * t)
            env = math.exp(-12.0 * t)
            val = math.sin(2 * math.pi * freq * t) * env
            sample = int(max(-32768, min(32767, val * 15000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_shaker_sound(self, duration_ms=100):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = math.exp(-40.0 * t)
            val = random.uniform(-1.0, 1.0) * env
            sample = int(max(-32768, min(32767, val * 7000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_piano_sound(self, freq, duration_ms=650):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            env = min(1.0, i / (SAMPLE_RATE * 0.005)) * math.exp(-3.2 * t)
            sample_val = math.sin(2 * math.pi * freq * t) * env
            sample = int(max(-32768, min(32767, sample_val * 8000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_kick_sound(self, duration_ms=280):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            freq = 42.0 + (160.0 - 42.0) * math.exp(-32.0 * t)
            sample_val = math.sin(2 * math.pi * freq * t) * math.exp(-10.0 * t)
            sample = int(max(-32768, min(32767, sample_val * 16000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_snare_sound(self, duration_ms=220):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            tone = math.sin(2 * math.pi * 180 * t) * math.exp(-22.0 * t)
            noise = random.uniform(-1.0, 1.0) * math.exp(-14.0 * t)
            sample_val = (tone * 0.45 + noise * 0.55)
            sample = int(max(-32768, min(32767, sample_val * 13000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_hihat_sound(self, duration_ms=90):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            sample_val = random.uniform(-1.0, 1.0) * math.exp(-55.0 * t)
            sample = int(max(-32768, min(32767, sample_val * 9000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _generate_synth_sound(self, freq, duration_ms=400):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        data = bytearray()
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            sample_val = math.sin(2 * math.pi * freq * t) * math.exp(-5.0 * t)
            sample = int(max(-32768, min(32767, sample_val * 12000)))
            data.extend(struct.pack('<h', sample))
        return self._wav_buffer_to_sound(data)

    def _init_instrument_cache(self):
        self.sound_cache["kick"] = self._generate_kick_sound()
        self.sound_cache["snare"] = self._generate_snare_sound()
        self.sound_cache["hihat"] = self._generate_hihat_sound()
        self.sound_cache["tin_whistle"] = self._generate_tin_whistle_sound()
        self.sound_cache["steel_drum"] = self._generate_steel_drum_sound()
        self.sound_cache["marimba"] = self._generate_marimba_sound()
        self.sound_cache["organ"] = self._generate_organ_sound()
        self.sound_cache["strings"] = self._generate_strings_sound()
        self.sound_cache["guitar"] = self._generate_guitar_sound()
        self.sound_cache["brass"] = self._generate_brass_sound()
        self.sound_cache["flute"] = self._generate_flute_sound()
        self.sound_cache["cowbell"] = self._generate_cowbell_sound()
        self.sound_cache["tambourine"] = self._generate_tambourine_sound()
        self.sound_cache["conga"] = self._generate_conga_sound()
        self.sound_cache["shaker"] = self._generate_shaker_sound()

        for midi_note, freq in self.piano_frequencies.items():
            self.sound_cache[f"piano_{midi_note}"] = self._generate_piano_sound(freq)

    def export_to_wav(self, filepath, num_loops=4):
        steps_per_loop = 16
        total_steps = steps_per_loop * num_loops
        step_duration = 60.0 / (self.bpm * 4)
        samples_per_step = int(SAMPLE_RATE * step_duration)
        total_samples = samples_per_step * total_steps
        
        master_mix = [0.0] * total_samples

        def mix_sound_bytes(raw_bytes, start_sample, volume):
            if not raw_bytes:
                return
            sample_size = 2
            num_s = len(raw_bytes) // sample_size
            for i in range(num_s):
                target_idx = start_sample + i
                if target_idx < total_samples:
                    val = struct.unpack_from('<h', raw_bytes, i * sample_size)[0]
                    master_mix[target_idx] += float(val) * volume * self.master_volume

        for step_idx in range(total_steps):
            pattern_step = step_idx % steps_per_loop
            start_sample = step_idx * samples_per_step
            
            for ch in self.channels:
                if ch["muted"]:
                    continue
                if ch["steps"][pattern_step]:
                    ch_type = ch["type"]
                    vol = ch["volume"]
                    sound_key = ch.get("sound_key")
                    
                    raw_bytes = None
                    if ch_type == "custom" and sound_key and sound_key in self.sound_cache:
                        try:
                            raw_bytes = self.sound_cache[sound_key].get_raw()
                        except:
                            pass
                    elif ch_type in self.sound_cache:
                        try:
                            raw_bytes = self.sound_cache[ch_type].get_raw()
                        except:
                            pass
                    if raw_bytes:
                        mix_sound_bytes(raw_bytes, start_sample, vol)

        output_data = bytearray()
        for sample in master_mix:
            clamped = max(-32768.0, min(32767.0, sample))
            output_data.extend(struct.pack('<h', int(clamped)))

        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(output_data)

    def play_channel_sound(self, ch_type, volume=1.0, sound_key=None):
        if self.master_volume <= 0:
            return
        sound = self.sound_cache.get(sound_key) if (ch_type == "custom" and sound_key) else self.sound_cache.get(ch_type)
        if sound:
            sound.set_volume(min(1.0, self.master_volume * volume))
            sound.play()

    def play_ai_voice_sample(self):
        sound = self.sound_cache.get("ai_voice_sample")
        if sound:
            sound.set_volume(min(1.0, self.master_volume * 1.0))
            sound.play()

    def load_custom_voice_file(self, filepath):
        try:
            custom_sound = pygame.mixer.Sound(filepath)
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            sound_key = f"voice_sample_{len(self.channels)}"
            self.sound_cache[sound_key] = custom_sound
            self.loaded_filename = os.path.basename(filepath)

            new_channel = {
                "name": f"🎙️ {base_name[:7]}", "type": "custom", "sound_key": sound_key,
                "vol_str": "95%", "volume": 0.95, "muted": False, "color": "#00985D",
                "steps": [True, False, False, False, True, False, False, False, True, False, False, False, True, False, False, False]
            }
            self.channels.insert(0, new_channel)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def record_live_hit(self, channel_index):
        if self.is_recording and 0 <= channel_index < len(self.channels):
            self.channels[channel_index]["steps"][self.current_step] = True

    def stop_engine(self):
        self.running = False

    def _sequencer_loop(self):
        while self.running:
            loop_start = time.perf_counter()
            if self.is_playing:
                step = self.current_step
                for ch in self.channels:
                    if ch["steps"][step] and not ch["muted"]:
                        self.play_channel_sound(ch["type"], volume=ch["volume"], sound_key=ch.get("sound_key"))

                self.current_step = (self.current_step + 1) % 16
                self.smooth_progress = float(self.current_step)

            step_duration = (60.0 / (self.bpm * 4)) / self.playback_speed
            elapsed = time.perf_counter() - loop_start
            sleep_interval = step_duration - elapsed if self.is_playing else 0.04
            if sleep_interval > 0:
                time.sleep(sleep_interval)


# ==============================================================================
# 4. GUI APPLICATION WORKSTATION
# ==============================================================================

class MelodiProApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MELODI PRO - HD Multitrack DAW with Interactive Instrument Workstations")
        self.root.geometry("1520x860")
        self.root.minsize(1200, 720)

        self.engine = AudioEngine()
        self.current_theme_name = "dark"
        self.theme = THEMES[self.current_theme_name]
        self.last_anim_time = time.perf_counter()

        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.root.update_idletasks()
        self.redraw_all_canvases()
        self.run_ui_loop()

    def _build_interface(self):
        self.root.configure(bg=self.theme["bg"])

        # Top Control Bar
        self.top_bar = tk.Frame(self.root, bg=self.theme["panel"], height=60)
        self.top_bar.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.logo_lbl = tk.Label(self.top_bar, text="MELODI PRO", font=("Segoe UI", 15, "bold"), fg=self.theme["accent"], bg=self.theme["panel"])
        self.logo_lbl.pack(side=tk.LEFT, padx=15)

        trans_frame = tk.Frame(self.top_bar, bg=self.theme["panel"])
        trans_frame.pack(side=tk.LEFT, padx=10)

        self.play_btn = RoundedButton(trans_frame, text="▶ PLAY", command=self.toggle_playback, bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["accent"], width=75, height=30)
        self.play_btn.pack(side=tk.LEFT, padx=2)

        self.stop_btn = RoundedButton(trans_frame, text="■ STOP", command=self.stop_playback, bg=self.theme["card"], fg=self.theme["text"], hover_bg="#D32F2F", width=75, height=30)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        self.rec_btn = RoundedButton(trans_frame, text="● REC", command=self.toggle_record, bg=self.theme["card"], fg=self.theme["text"], hover_bg="#D32F2F", width=70, height=30)
        self.rec_btn.pack(side=tk.LEFT, padx=2)

        self.save_btn = RoundedButton(trans_frame, text="💾 SAVE", command=self.save_music_dialog, bg=self.theme["accent"], fg="#FFFFFF", hover_bg=self.theme["accent_hover"], width=80, height=30)
        self.save_btn.pack(side=tk.LEFT, padx=6)

        self.btn_back = RoundedButton(trans_frame, text="◄-", command=lambda: self.jump_step(-1), bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"], width=35, height=30)
        self.btn_back.pack(side=tk.LEFT, padx=2)

        self.btn_fwd = RoundedButton(trans_frame, text="-►", command=lambda: self.jump_step(1), bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"], width=35, height=30)
        self.btn_fwd.pack(side=tk.LEFT, padx=2)

        bpm_box = tk.Frame(self.top_bar, bg=self.theme["panel"])
        bpm_box.pack(side=tk.LEFT, padx=10)
        
        self.btn_bpm_minus = RoundedButton(bpm_box, text="-", command=lambda: self.adjust_bpm(-2), bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"], width=28, height=30)
        self.btn_bpm_minus.pack(side=tk.LEFT, padx=2)

        self.bpm_lbl = tk.Label(bpm_box, text=f"BPM: {self.engine.bpm}", font=("Segoe UI", 9, "bold"), fg=self.theme["text"], bg=self.theme["panel"], width=9)
        self.bpm_lbl.pack(side=tk.LEFT, padx=2)

        self.btn_bpm_plus = RoundedButton(bpm_box, text="+", command=lambda: self.adjust_bpm(2), bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"], width=28, height=30)
        self.btn_bpm_plus.pack(side=tk.LEFT, padx=2)

        speed_box = tk.Frame(self.top_bar, bg=self.theme["panel"])
        speed_box.pack(side=tk.LEFT, padx=10)
        self.speed_label = tk.Label(speed_box, text="SPEED:", font=("Segoe UI", 8, "bold"), fg=self.theme["subtext"], bg=self.theme["panel"])
        self.speed_label.pack(side=tk.LEFT, padx=2)
        
        self.speed_var = tk.StringVar(value="1.0x")
        self.speed_cb = ttk.Combobox(speed_box, textvariable=self.speed_var, values=["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"], width=6, state="readonly")
        self.speed_cb.pack(side=tk.LEFT, padx=2)
        self.speed_cb.bind("<<ComboboxSelected>>", self.on_speed_change)

        self.theme_btn = RoundedButton(
            self.top_bar, text="☀️ Light Theme", command=self.toggle_theme,
            bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"], width=115, height=30
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=15, pady=12)

        vol_box = tk.Frame(self.top_bar, bg=self.theme["panel"])
        vol_box.pack(side=tk.RIGHT, padx=15)
        self.master_label = tk.Label(vol_box, text="MASTER", font=("Segoe UI", 8, "bold"), fg=self.theme["subtext"], bg=self.theme["panel"])
        self.master_label.pack(side=tk.LEFT, padx=5)
        self.vol_slider = tk.Scale(
            vol_box, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
            bg=self.theme["panel"], fg=self.theme["text"], highlightthickness=0, troughcolor=self.theme["card"], length=90, command=self.on_master_vol
        )
        self.vol_slider.set(self.engine.master_volume)
        self.vol_slider.pack(side=tk.LEFT)

        main_container = tk.Frame(self.root, bg=self.theme["bg"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left Sidebar (Track List)
        self.left_sidebar = tk.Frame(main_container, bg=self.theme["panel"], width=250, bd=0)
        self.left_sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.left_sidebar.pack_propagate(False)

        self.tracklist_title = tk.Label(self.left_sidebar, text="SOUNDTRACKS (CLICK FOR WORKSTATION)", font=("Segoe UI", 9, "bold"), fg=self.theme["text"], bg=self.theme["panel"])
        self.tracklist_title.pack(anchor="w", padx=12, pady=12)
        
        self.sidebar_canvas = tk.Canvas(self.left_sidebar, bg=self.theme["panel"], highlightthickness=0, cursor="hand2")
        self.sidebar_canvas.pack(fill=tk.BOTH, expand=True, padx=6)
        self.sidebar_canvas.bind("<Button-1>", self.on_sidebar_click)
        self.render_sidebar()

        # Center Workspace
        center_container = tk.Frame(main_container, bg=self.theme["bg"])
        center_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.update_ttk_styles()

        self.notebook = ttk.Notebook(center_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.tab_timeline = tk.Frame(self.notebook, bg=self.theme["panel"])
        self.notebook.add(self.tab_timeline, text=" 🎬 Arrangement Playlist ")
        self.timeline_canvas = tk.Canvas(self.tab_timeline, bg=self.theme["panel"], highlightthickness=0)
        self.timeline_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)

        self.tab_seq = tk.Frame(self.notebook, bg=self.theme["panel"])
        self.notebook.add(self.tab_seq, text=" 🎛️ Step Sequencer ")
        self.seq_canvas = tk.Canvas(self.tab_seq, bg=self.theme["panel"], highlightthickness=0)
        self.seq_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.seq_canvas.bind("<Button-1>", self.on_seq_click)

        self.tab_roll = tk.Frame(self.notebook, bg=self.theme["panel"])
        self.notebook.add(self.tab_roll, text=" 🎼 Piano Roll ")
        self.roll_canvas = tk.Canvas(self.tab_roll, bg=self.theme["panel"], highlightthickness=0)
        self.roll_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.roll_canvas.bind("<Button-1>", self.on_roll_click)

        self.tab_loader = tk.Frame(self.notebook, bg=self.theme["panel"])
        self.notebook.add(self.tab_loader, text=" 🎙️ AI Voice & Samples ")
        self._build_loader_tab()

        # Live Trigger Pads
        self.pads_frame = tk.Frame(center_container, bg=self.theme["panel"], height=135, bd=0)
        self.pads_frame.pack(fill=tk.X, pady=(5, 0))
        self.pads_frame.pack_propagate(False)

        self.pads_lbl = tk.Label(self.pads_frame, text="LIVE TRIGGER & INSTRUMENT PADS", font=("Segoe UI", 8, "bold"), fg=self.theme["subtext"], bg=self.theme["panel"])
        self.pads_lbl.pack(anchor="w", padx=10, pady=(4, 0))
        
        self.pads_grid_inner = tk.Frame(self.pads_frame, bg=self.theme["panel"])
        self.pads_grid_inner.pack(pady=4)
        
        self.pad_buttons = []
        pad_colors = ["#00985D", "#D32F2F", "#388E3C", "#F57C00", "#00ACC1", "#5E35B1", "#D81B60", "#8E24AA", "#3949AB", "#00897B", "#FB8C00", "#43A047", "#E53935", "#FDD835", "#6D4C41", "#78909C"]
        pad_labels = ["🎙️ LAURA", "Kick 808", "Snare Pro", "Closed Hat", "Tin Whistle", "Steel Drum", "Marimba", "Pipe Organ", "Strings Pad", "Ac. Guitar", "Synth Brass", "Class. Flute", "808 Cowbell", "Tambourine", "Conga Drum", "Shaker FX"]

        for i in range(16):
            def make_pad_command(idx):
                def pad_action():
                    ch = self.engine.channels[idx]
                    if idx == 0:
                        self.engine.play_ai_voice_sample()
                    else:
                        self.engine.play_channel_sound(ch["type"], volume=ch["volume"], sound_key=ch.get("sound_key"))
                    self.engine.record_live_hit(idx)
                    self.redraw_all_canvases()
                return pad_action

            r_row = i // 8
            r_col = i % 8
            p_btn = RoundedButton(self.pads_grid_inner, text=pad_labels[i], command=make_pad_command(i), bg=pad_colors[i], fg="#FFFFFF", hover_bg=self.theme["card_hover"], width=135, height=32, radius=10)
            p_btn.grid(row=r_row, column=r_col, padx=3, pady=2)
            self.pad_buttons.append(p_btn)

        # Right Sidebar (Mixer Console)
        self.right_sidebar = tk.Frame(main_container, bg=self.theme["panel"], width=290, bd=0)
        self.right_sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        self.right_sidebar.pack_propagate(False)

        self.mixer_title = tk.Label(self.right_sidebar, text="MIXER CONSOLE", font=("Segoe UI", 10, "bold"), fg=self.theme["text"], bg=self.theme["panel"])
        self.mixer_title.pack(anchor="w", padx=10, pady=10)
        self._build_mixer_strips()

    # ==========================================================================
    # INTERACTIVE CLICKABLE INSTRUMENT WORKSTATION POP-UP WINDOW
    # ==========================================================================
    def on_sidebar_click(self, event):
        y = event.y
        clicked_idx = (y - 10) // 40
        if 0 <= clicked_idx < len(self.engine.channels):
            ch = self.engine.channels[clicked_idx]
            self.open_instrument_workstation_modal(ch, clicked_idx)

    def open_instrument_workstation_modal(self, ch, idx):
        t = self.theme
        modal = tk.Toplevel(self.root)
        modal.title(f"Workstation: {ch['name']}")
        modal.geometry("520x600")
        modal.configure(bg=t["panel"])
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text=f"🎛️ Instrument Workstation: {ch['name']}", font=("Segoe UI", 13, "bold"), fg=t["text"], bg=t["panel"]).pack(pady=10)
        tk.Label(modal, text="Click directly on the instrument parts below to test-play & configure notes!", font=("Segoe UI", 8), fg=t["subtext"], bg=t["panel"]).pack()

        # Canvas for Interactive Instrument Illustration
        canvas_w = 460
        canvas_h = 240
        inst_canvas = tk.Canvas(modal, width=canvas_w, height=canvas_h, bg="#181818", highlightthickness=1, highlightbackground=t["border"])
        inst_canvas.pack(pady=10)

        info_lbl = tk.Label(modal, text="Status: Ready. Click instrument parts.", font=("Segoe UI", 9, "bold"), fg=t["accent"], bg=t["panel"])
        info_lbl.pack(pady=5)

        # Draw Realistic Instrument Schematics with Click Hotspots
        ch_type = ch["type"]

        if ch_type in ["kick", "snare", "hihat", "conga", "cowbell"]:
            # --- DRUM KIT SCHEMATIC ---
            inst_canvas.create_oval(180, 70, 280, 170, fill="#3A3A3A", outline="#D32F2F", width=3) # Kick
            inst_canvas.create_text(230, 120, text="KICK DRUM", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

            inst_canvas.create_oval(60, 90, 140, 170, fill="#3A3A3A", outline="#388E3C", width=3) # Snare
            inst_canvas.create_text(100, 130, text="SNARE", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

            inst_canvas.create_oval(320, 90, 400, 170, fill="#3A3A3A", outline="#F57C00", width=3) # Hi-Hat / Tom
            inst_canvas.create_text(360, 130, text="HI-HAT", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

            inst_canvas.create_oval(200, 10, 260, 50, fill="#3A3A3A", outline="#00ACC1", width=3) # Cymbal
            inst_canvas.create_text(230, 30, text="CYMBAL", fill="#FFFFFF", font=("Segoe UI", 7, "bold"))

            def on_inst_click(e):
                ex, ey = e.x, e.y
                if 180 <= ex <= 280 and 70 <= ey <= 170:
                    self.engine.play_channel_sound("kick", volume=ch["volume"])
                    info_lbl.config(text="Hit: Kick Drum! (Triggered)")
                elif 60 <= ex <= 140 and 90 <= ey <= 170:
                    self.engine.play_channel_sound("snare", volume=ch["volume"])
                    info_lbl.config(text="Hit: Snare Pro! (Triggered)")
                elif 320 <= ex <= 400 and 90 <= ey <= 170:
                    self.engine.play_channel_sound("hihat", volume=ch["volume"])
                    info_lbl.config(text="Hit: Hi-Hat / Cymbal! (Triggered)")
                else:
                    self.engine.play_channel_sound(ch_type, volume=ch["volume"], sound_key=ch.get("sound_key"))
                    info_lbl.config(text=f"Hit: {ch['name']}! (Triggered)")
                self.engine.record_live_hit(idx)

            inst_canvas.bind("<Button-1>", on_inst_click)

        elif ch_type in ["guitar", "strings"]:
            # --- GUITAR / STRINGS SCHEMATIC ---
            inst_canvas.create_rectangle(40, 100, 420, 140, fill="#5D4037", outline="#8D6E63", width=2) # Neck
            for s_idx in range(6):
                sy = 108 + s_idx * 6
                inst_canvas.create_line(40, sy, 420, sy, fill="#E0E0E0", width=2)
            
            inst_canvas.create_text(230, 60, text="GUITAR FRETBOARD (Click strings to strum)", fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

            def on_guitar_click(e):
                self.engine.play_channel_sound(ch_type, volume=ch["volume"], sound_key=ch.get("sound_key"))
                info_lbl.config(text=f"Strummed: {ch['name']} strings! (Triggered)")
                self.engine.record_live_hit(idx)

            inst_canvas.bind("<Button-1>", on_guitar_click)

        elif ch_type in ["tin_whistle", "flute"]:
            # --- WHISTLE / FLUTE SCHEMATIC ---
            inst_canvas.create_rectangle(60, 100, 400, 130, fill="#00838F", outline="#00ACC1", width=2) # Tube
            for h_i in range(5):
                hx = 120 + h_i * 55
                inst_canvas.create_oval(hx, 110, hx + 18, 120, fill="#121212", outline="#FFFFFF", width=2)

            inst_canvas.create_text(230, 60, text="WOODWIND TUBE (Click tone holes)", fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

            def on_whistle_click(e):
                self.engine.play_channel_sound(ch_type, volume=ch["volume"], sound_key=ch.get("sound_key"))
                info_lbl.config(text=f"Blown: {ch['name']} tone hole! (Triggered)")
                self.engine.record_live_hit(idx)

            inst_canvas.bind("<Button-1>", on_whistle_click)

        else:
            # --- DEFAULT KEYBOARD / SYNTH SCHEMATIC ---
            for k in range(10):
                kx = 40 + k * 38
                inst_canvas.create_rectangle(kx, 70, kx + 34, 170, fill="#FFFFFF", outline="#000000")
            inst_canvas.create_text(230, 40, text="SYNTHESIZER KEYBOARD", fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

            def on_synth_click(e):
                self.engine.play_channel_sound(ch_type, volume=ch["volume"], sound_key=ch.get("sound_key"))
                info_lbl.config(text=f"Key Played: {ch['name']}! (Triggered)")
                self.engine.record_live_hit(idx)

            inst_canvas.bind("<Button-1>", on_synth_click)

        # Volume & Note Pattern Grid
        vol_box = tk.Frame(modal, bg=t["panel"])
        vol_box.pack(pady=10, fill=tk.X, padx=30)
        tk.Label(vol_box, text="Volume:", font=("Segoe UI", 9, "bold"), fg=t["subtext"], bg=t["panel"]).pack(side=tk.LEFT)
        
        def update_modal_vol(val):
            ch["volume"] = float(val)
            ch["vol_str"] = f"{int(float(val)*100)}%"
            self.render_sidebar()
            self._build_mixer_strips()

        v_scale = tk.Scale(vol_box, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL, bg=t["panel"], fg=t["text"], highlightthickness=0, troughcolor=t["card"], length=220, command=update_modal_vol)
        v_scale.set(ch["volume"])
        v_scale.pack(side=tk.RIGHT)

        # Step Activator Toggles
        tk.Label(modal, text="Quick Step Pattern Toggles:", font=("Segoe UI", 9, "bold"), fg=t["text"], bg=t["panel"]).pack(pady=(5, 2))
        step_frame = tk.Frame(modal, bg=t["panel"])
        step_frame.pack(pady=5)

        for s_i in range(8):
            def make_step_toggle(step_num):
                return lambda: self.toggle_modal_step(ch, step_num)
            
            btn_bg = t["accent"] if ch["steps"][s_i] else t["card"]
            RoundedButton(
                step_frame, text=f"S{s_i+1}", command=make_step_toggle(s_i),
                bg=btn_bg, fg="#FFFFFF", hover_bg=t["accent_hover"], width=48, height=28, radius=6
            ).grid(row=0, column=s_i, padx=3)

        RoundedButton(
            modal, text="Apply & Close", command=modal.destroy,
            bg=t["accent"], fg="#FFFFFF", hover_bg=t["accent_hover"], width=150, height=36, radius=10
        ).pack(pady=15)

    def toggle_modal_step(self, ch, step_idx):
        ch["steps"][step_idx] = not ch["steps"][step_idx]
        self.redraw_all_canvases()

    def update_ttk_styles(self):
        t = self.theme
        self.style.configure("TNotebook", background=t["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=t["card"], foreground=t["text"], font=("Segoe UI", 9, "bold"), padding=[12, 6])
        self.style.map("TNotebook.Tab", background=[("selected", t["accent"])], foreground=[("selected", "#FFFFFF")])

    def _build_loader_tab(self):
        self.loader_container = tk.Frame(self.tab_loader, bg=self.theme["panel"])
        self.loader_container.pack(expand=True, fill=tk.BOTH, padx=25, pady=25)

        self.loader_title = tk.Label(self.loader_container, text="AI Narration Voice Sample Loaded", font=("Segoe UI", 14, "bold"), fg=self.theme["text"], bg=self.theme["panel"])
        self.loader_title.pack(anchor="w", pady=(0, 10))

        self.loader_desc = tk.Label(
            self.loader_container, 
            text=f"Active File: {self.engine.loaded_filename}\nIntegrated into Channel 1 of the multitrack workstation.", 
            font=("Segoe UI", 10), fg=self.theme["subtext"], bg=self.theme["panel"], justify=tk.LEFT
        )
        self.loader_desc.pack(anchor="w", pady=(0, 20))

        self.btn_load_custom = RoundedButton(
            self.loader_container, text="📂 Load Different Audio File...", command=self.load_custom_audio_dialog,
            bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["accent"], width=220, height=38
        )
        self.btn_load_custom.pack(anchor="w", pady=5)

        self.btn_test_voice = RoundedButton(
            self.loader_container, text="▶ Test Play Voice Sample", command=self.engine.play_ai_voice_sample,
            bg=self.theme["accent"], fg="#FFFFFF", hover_bg=self.theme["accent_hover"], width=200, height=38
        )
        self.btn_test_voice.pack(anchor="w", pady=5)

    def load_custom_audio_dialog(self):
        filetypes = [("Audio Files", "*.wav *.mp3 *.ogg *.flac"), ("All Files", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            success = self.engine.load_custom_voice_file(filepath)
            if success:
                self.loader_desc.config(text=f"Active File: {self.engine.loaded_filename}\nSuccessfully imported!")
                self.render_sidebar()
                self._build_mixer_strips()
                self.redraw_all_canvases()
                messagebox.showinfo("Success", f"Loaded audio successfully:\n{os.path.basename(filepath)}")
            else:
                messagebox.showerror("Error", "Could not load audio file.")

    def save_music_dialog(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Audio File", "*.wav")])
        if filepath:
            try:
                self.engine.export_to_wav(filepath, num_loops=4)
                messagebox.showinfo("Export Successful", f"Project exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed:\n{e}")

    def toggle_playback(self):
        self.engine.is_playing = not self.engine.is_playing
        if self.engine.is_playing:
            self.play_btn.update_style(bg=self.theme["accent"], fg="#FFFFFF", hover_bg=self.theme["accent_hover"])
            self.play_btn.text = "⏸ PAUSE"
            self.play_btn.draw(self.theme["accent"])
        else:
            self.play_btn.update_style(bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"])
            self.play_btn.text = "▶ PLAY"
            self.play_btn.draw(self.theme["card"])

    def stop_playback(self):
        self.engine.is_playing = False
        self.engine.is_recording = False
        self.engine.current_step = 0
        self.play_btn.update_style(bg=self.theme["card"], fg=self.theme["text"], hover_bg=self.theme["card_hover"])
        self.play_btn.text = "▶ PLAY"
        self.play_btn.draw(self.theme["card"])
        self.rec_btn.update_style(bg=self.theme["card"], fg=self.theme["text"], hover_bg="#D32F2F")
        self.rec_btn.text = "● REC"
        self.rec_btn.draw(self.theme["card"])
        self.redraw_all_canvases()

    def toggle_record(self):
        self.engine.is_recording = not self.engine.is_recording
        if self.engine.is_recording:
            self.rec_btn.update_style(bg="#D32F2F", fg="#FFFFFF", hover_bg="#B71C1C")
            self.rec_btn.text = "🔴 REC ON"
            self.rec_btn.draw("#D32F2F")
            if not self.engine.is_playing:
                self.toggle_playback()
        else:
            self.rec_btn.update_style(bg=self.theme["card"], fg=self.theme["text"], hover_bg="#D32F2F")
            self.rec_btn.text = "● REC"
            self.rec_btn.draw(self.theme["card"])

    def jump_step(self, delta):
        self.engine.current_step = (self.engine.current_step + delta) % 16
        self.redraw_all_canvases()

    def adjust_bpm(self, amount):
        self.engine.bpm = max(40, min(240, self.engine.bpm + amount))
        self.bpm_lbl.config(text=f"BPM: {self.engine.bpm}")

    def on_speed_change(self, event):
        try:
            self.engine.playback_speed = float(self.speed_var.get().replace("x", ""))
        except ValueError:
            pass

    def on_master_vol(self, val):
        self.engine.master_volume = float(val)

    def toggle_theme(self):
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self.theme = THEMES[self.current_theme_name]
        self.root.configure(bg=self.theme["bg"])
        self._rebuild_ui_theme()

    def _rebuild_ui_theme(self):
        t = self.theme
        self.top_bar.configure(bg=t["panel"])
        self.logo_lbl.configure(bg=t["panel"], fg=t["accent"])
        self.bpm_lbl.configure(bg=t["panel"], fg=t["text"])
        self.speed_label.configure(bg=t["panel"], fg=t["subtext"])
        self.left_sidebar.configure(bg=t["panel"])
        self.tracklist_title.configure(bg=t["panel"], fg=t["text"])
        self.sidebar_canvas.configure(bg=t["panel"])
        self.right_sidebar.configure(bg=t["panel"])
        self.mixer_title.configure(bg=t["panel"], fg=t["text"])
        self.pads_frame.configure(bg=t["panel"])
        self.pads_lbl.configure(bg=t["panel"], fg=t["subtext"])
        self.pads_grid_inner.configure(bg=t["panel"])
        
        for w in [self.tab_timeline, self.tab_seq, self.tab_roll, self.tab_loader]:
            w.configure(bg=t["panel"])
        for c in [self.timeline_canvas, self.seq_canvas, self.roll_canvas]:
            c.configure(bg=t["panel"])

        self.update_ttk_styles()
        self.play_btn.update_style(bg=t["card"], fg=t["text"], hover_bg=t["accent"], parent_bg=t["panel"])
        self.stop_btn.update_style(bg=t["card"], fg=t["text"], hover_bg="#D32F2F", parent_bg=t["panel"])
        self.rec_btn.update_style(bg=t["card"], fg=t["text"], hover_bg="#D32F2F", parent_bg=t["panel"])
        self.save_btn.update_style(bg=t["accent"], fg="#FFFFFF", hover_bg=t["accent_hover"], parent_bg=t["panel"])
        self.btn_back.update_style(bg=t["card"], fg=t["text"], hover_bg=t["card_hover"], parent_bg=t["panel"])
        self.btn_fwd.update_style(bg=t["card"], fg=t["text"], hover_bg=t["card_hover"], parent_bg=t["panel"])
        self.btn_bpm_minus.update_style(bg=t["card"], fg=t["text"], hover_bg=t["card_hover"], parent_bg=t["panel"])
        self.btn_bpm_plus.update_style(bg=t["card"], fg=t["text"], hover_bg=t["card_hover"], parent_bg=t["panel"])
        self.theme_btn.update_style(bg=t["card"], fg=t["text"], hover_bg=t["card_hover"], parent_bg=t["panel"])

        self.theme_btn.text = "🌙 Dark Theme" if self.current_theme_name == "dark" else "☀️ Light Theme"
        self.theme_btn.draw(t["card"])

        self.render_sidebar()
        self._build_mixer_strips()
        self._build_loader_tab_contents()
        self.redraw_all_canvases()

    def _build_loader_tab_contents(self):
        for widget in self.tab_loader.winfo_children():
            widget.destroy()
        self._build_loader_tab()

    def render_sidebar(self):
        self.sidebar_canvas.delete("all")
        y = 10
        for ch in self.engine.channels:
            bg_col = self.theme["card"] if not ch["muted"] else self.theme["border"]
            create_rounded_rect(self.sidebar_canvas, 5, y, 235, y + 36, radius=6, fill=bg_col, outline="")
            self.sidebar_canvas.create_rectangle(5, y, 10, y + 36, fill=ch["color"], outline="")
            self.sidebar_canvas.create_text(16, y + 12, text=ch["name"], anchor="w", fill=self.theme["text"], font=("Segoe UI", 8, "bold"))
            self.sidebar_canvas.create_text(16, y + 26, text=f"Vol: {ch['vol_str']} | {'Muted' if ch['muted'] else 'Active'}", anchor="w", fill=self.theme["subtext"], font=("Segoe UI", 6))
            y += 40

    def _build_mixer_strips(self):
        for widget in self.right_sidebar.winfo_children():
            if widget != self.mixer_title:
                widget.destroy()

        mixer_container = tk.Canvas(self.right_sidebar, bg=self.theme["panel"], highlightthickness=0)
        mixer_scroll = ttk.Scrollbar(self.right_sidebar, orient="vertical", command=mixer_container.yview)
        mixer_inner = tk.Frame(mixer_container, bg=self.theme["panel"])

        mixer_inner.bind("<Configure>", lambda e: mixer_container.configure(scrollregion=mixer_container.bbox("all")))
        mixer_container.create_window((0, 0), window=mixer_inner, anchor="nw")
        mixer_container.configure(yscrollcommand=mixer_scroll.set)

        mixer_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=5)
        mixer_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for ch in self.engine.channels:
            strip = tk.Frame(mixer_inner, bg=self.theme["card"], bd=0)
            strip.pack(fill=tk.X, pady=2, ipady=2)

            tk.Label(strip, text=ch["name"], font=("Segoe UI", 8, "bold"), fg=self.theme["text"], bg=self.theme["card"]).pack(side=tk.TOP, anchor="w", padx=6, pady=1)
            controls_frame = tk.Frame(strip, bg=self.theme["card"])
            controls_frame.pack(fill=tk.X, padx=6)

            mute_text = "M" if ch["muted"] else "A"
            mute_bg = "#D32F2F" if ch["muted"] else self.theme["card_hover"]
            RoundedButton(
                controls_frame, text=mute_text, command=lambda c=ch: self.toggle_mute_channel(c),
                bg=mute_bg, fg="#FFFFFF", hover_bg="#D32F2F", width=24, height=20, radius=5
            ).pack(side=tk.LEFT, padx=1)

            vol_slider = tk.Scale(
                controls_frame, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                bg=self.theme["card"], fg=self.theme["text"], highlightthickness=0, troughcolor=self.theme["border"], length=110,
                command=lambda val, c=ch: self.on_channel_vol(c, val)
            )
            vol_slider.set(ch["volume"])
            vol_slider.pack(side=tk.RIGHT, padx=1)

    def toggle_mute_channel(self, ch):
        ch["muted"] = not ch["muted"]
        self.render_sidebar()
        self._build_mixer_strips()

    def on_channel_vol(self, ch, val):
        ch["volume"] = float(val)
        ch["vol_str"] = f"{int(float(val)*100)}%"
        self.render_sidebar()

    def _update_scrub_position(self, x):
        tw = self.timeline_canvas.winfo_width() or 800
        grid_w = tw - 140
        if grid_w > 0 and x >= 140:
            ratio = max(0.0, min(1.0, (x - 140) / grid_w))
            self.engine.current_step = min(15, int(ratio * 16))
            self.redraw_all_canvases()

    def on_timeline_click(self, event):
        if event.y < 35:
            self._update_scrub_position(event.x)
            return
        row_idx = (event.y - 35) // 42
        total_w = self.timeline_canvas.winfo_width() - 140
        bar_w = total_w / 32.0
        if 0 <= row_idx < len(self.engine.arrangement_tracks) and event.x >= 140:
            clicked_bar = int((event.x - 140) // bar_w) + 1
            track = self.engine.arrangement_tracks[row_idx]
            found = False
            for clip in track["clips"]:
                if clip[0] <= clicked_bar <= clip[1]:
                    track["clips"].remove(clip)
                    found = True
                    break
            if not found:
                track["clips"].append((clicked_bar, min(32, clicked_bar + 3), f"Clip {clicked_bar}"))
            self.redraw_all_canvases()

    def on_timeline_drag(self, event):
        if event.y < 35:
            self._update_scrub_position(event.x)

    def on_seq_click(self, event):
        if event.y >= 30:
            row_idx = (event.y - 30) // 28
            col_width = (self.seq_canvas.winfo_width() - 120) // 16
            if 0 <= row_idx < len(self.engine.channels) and event.x >= 120:
                step_idx = (event.x - 120) // col_width
                if 0 <= step_idx < 16:
                    ch = self.engine.channels[row_idx]
                    ch["steps"][step_idx] = not ch["steps"][step_idx]
                    self.redraw_all_canvases()

    def on_roll_click(self, event):
        if event.y >= 30:
            row_idx = (event.y - 30) // 35
            col_width = (self.roll_canvas.winfo_width() - 120) // 16
            if 0 <= row_idx < len(self.engine.piano_roll_tracks) and event.x >= 120:
                step_idx = (event.x - 120) // col_width
                if 0 <= step_idx < 16:
                    pt = self.engine.piano_roll_tracks[row_idx]
                    pt["steps"][step_idx] = not pt["steps"][step_idx]
                    self.redraw_all_canvases()

    def redraw_all_canvases(self):
        # 1. Timeline Canvas
        self.timeline_canvas.delete("all")
        tw = self.timeline_canvas.winfo_width() or 800
        th = self.timeline_canvas.winfo_height() or 300
        grid_w = tw - 140
        bar_w = grid_w / 32.0
        row_h = 42

        self.timeline_canvas.create_text(10, 18, text="ARRANGEMENT TRACKS", anchor="w", fill=self.theme["subtext"], font=("Segoe UI", 8, "bold"))
        for b in range(1, 33):
            bx = 140 + (b - 1) * bar_w
            is_major = (b % 4 == 1)
            self.timeline_canvas.create_line(bx, 30, bx, th, fill=self.theme["card"] if is_major else self.theme["border"])
            if is_major:
                self.timeline_canvas.create_text(bx + 3, 18, text=f"Bar {b}", anchor="w", fill=self.theme["subtext"], font=("Segoe UI", 7, "bold"))

        for r_idx, track in enumerate(self.engine.arrangement_tracks):
            y = 35 + r_idx * row_h
            create_rounded_rect(self.timeline_canvas, 5, y + 2, 135, y + row_h - 4, radius=6, fill=self.theme["card"], outline="")
            self.timeline_canvas.create_rectangle(5, y + 2, 10, y + row_h - 4, fill=track["color"], outline="")
            self.timeline_canvas.create_text(16, y + row_h/2, text=track["name"], anchor="w", fill=self.theme["text"], font=("Segoe UI", 8, "bold"))

            for clip in track["clips"]:
                cx1 = 140 + (clip[0] - 1) * bar_w
                cx2 = 140 + clip[1] * bar_w
                create_rounded_rect(self.timeline_canvas, cx1 + 1, y + 5, cx2 - 1, y + row_h - 6, radius=6, fill=track["color"], outline="")
                self.timeline_canvas.create_text(cx1 + 8, y + row_h/2, text=clip[2], anchor="w", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

        current_bar = (self.engine.current_step // 4) + 1
        play_x = 140 + (current_bar - 1) * (bar_w * 4) + (self.engine.current_step % 4) * bar_w
        self.timeline_canvas.create_line(play_x, 25, play_x, th, fill=self.theme["accent"], width=2)

        # 2. Step Sequencer Canvas
        self.seq_canvas.delete("all")
        sw = self.seq_canvas.winfo_width() or 800
        col_w_seq = (sw - 120) / 16.0
        row_h_seq = 28

        for i in range(16):
            self.seq_canvas.create_text(120 + i * col_w_seq + col_w_seq/2, 15, text=str(i+1), fill=self.theme["subtext"], font=("Segoe UI", 8, "bold"))

        for r_idx, ch in enumerate(self.engine.channels):
            y = 30 + r_idx * row_h_seq
            self.seq_canvas.create_text(5, y + row_h_seq/2, text=ch["name"], anchor="w", fill=self.theme["text"], font=("Segoe UI", 7, "bold"))
            for s_idx in range(16):
                x = 120 + s_idx * col_w_seq
                is_active = ch["steps"][s_idx]
                fill_col = self.theme["active_step"] if is_active else self.theme["inactive_step"]
                if s_idx == self.engine.current_step:
                    fill_col = self.theme["accent_hover"] if not is_active else "#FFFFFF"
                create_rounded_rect(self.seq_canvas, x + 2, y + 3, x + col_w_seq - 2, y + row_h_seq - 3, radius=3, fill=fill_col, outline="")

        # 3. Piano Roll Canvas
        self.roll_canvas.delete("all")
        rw = self.roll_canvas.winfo_width() or 800
        col_w_roll = (rw - 120) / 16.0
        row_h_roll = 35

        for i in range(16):
            self.roll_canvas.create_text(120 + i * col_w_roll + col_w_roll/2, 15, text=str(i+1), fill=self.theme["subtext"], font=("Segoe UI", 8, "bold"))

        for r_idx, pt in enumerate(self.engine.piano_roll_tracks):
            y = 30 + r_idx * row_h_roll
            self.roll_canvas.create_text(5, y + row_h_roll/2, text=pt["name"], anchor="w", fill=self.theme["text"], font=("Segoe UI", 8, "bold"))
            for s_idx in range(16):
                x = 120 + s_idx * col_w_roll
                is_active = pt["steps"][s_idx]
                fill_col = pt["color"] if is_active else self.theme["inactive_step"]
                if s_idx == self.engine.current_step:
                    fill_col = "#FFFFFF" if is_active else self.theme["card_hover"]
                create_rounded_rect(self.roll_canvas, x + 2, y + 4, x + col_w_roll - 2, y + row_h_roll - 4, radius=4, fill=fill_col, outline="")

    def run_ui_loop(self):
        if self.engine.running:
            now = time.perf_counter()
            if now - self.last_anim_time > 0.05:
                self.last_anim_time = now
                self.redraw_all_canvases()
            self.root.after(20, self.run_ui_loop)

    def _on_close(self):
        self.engine.stop_engine()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MelodiProApp(root)
    root.mainloop()