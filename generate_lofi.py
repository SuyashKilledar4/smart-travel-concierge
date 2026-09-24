import math
import numpy as np
import scipy.io.wavfile as wav

sample_rate = 44100
duration = 35.0  # seconds
num_samples = int(sample_rate * duration)

# Time array
t = np.linspace(0, duration, num_samples, endpoint=False)

bpm = 85.0
beat_dur = 60.0 / bpm  # ~0.7058 s
bar_dur = beat_dur * 4  # ~2.8235 s

# Frequencies for 7th chords
# Cmaj7, Am7, Dm7, G7
chords = [
    [261.63, 329.63, 392.00, 493.88],  # Cmaj7 (C4, E4, G4, B4)
    [220.00, 261.63, 329.63, 392.00],  # Am7 (A3, C4, E4, G4)
    [293.66, 349.23, 440.00, 523.25],  # Dm7 (D4, F4, A4, C5)
    [196.00, 246.94, 293.66, 349.23],  # G7 (G3, B3, D4, F4)
]
bass_freqs = [130.81, 110.00, 146.83, 98.00]  # C3, A2, D3, G2

audio = np.zeros(num_samples)

# 1. Generate Rhodes-like Keys & Sub Bass
for i in range(num_samples):
    time_sec = t[i]
    bar_idx = int(time_sec / bar_dur) % 4
    beat_in_bar = (time_sec % bar_dur) / beat_dur
    beat_phase = (time_sec % beat_dur) / beat_dur
    
    # Envelope per beat for keys (gentle attack & decay)
    env_keys = np.exp(-1.8 * beat_phase)
    
    # Keys chords
    chord = chords[bar_idx]
    keys_sample = 0.0
    for f in chord:
        # Sine + subtle 2nd harmonic
        keys_sample += 0.25 * math.sin(2 * math.pi * f * time_sec)
        keys_sample += 0.08 * math.sin(2 * math.pi * f * 2 * time_sec)
    
    # Sub Bass
    b_freq = bass_freqs[bar_idx]
    bass_env = np.exp(-1.0 * (beat_in_bar % 2))
    bass_sample = 0.4 * math.sin(2 * math.pi * b_freq * time_sec) * bass_env

    audio[i] += (keys_sample * env_keys * 0.35) + (bass_sample * 0.4)

# 2. Drums & Hi-Hats
for sample_idx in range(num_samples):
    time_sec = t[sample_idx]
    beat_pos = (time_sec / beat_dur) % 4
    sub_beat = (time_sec / (beat_dur / 2)) % 2
    beat_offset = (time_sec % beat_dur)

    # Kick drum on beat 0 and 2.5
    if (beat_pos < 0.15) or (beat_pos >= 2.5 and beat_pos < 2.65):
        k_time = beat_offset if beat_pos < 0.15 else (time_sec % (beat_dur / 2))
        k_freq = 110 * np.exp(-30 * k_time) + 40
        kick = np.sin(2 * np.pi * k_freq * k_time) * np.exp(-10 * k_time)
        audio[sample_idx] += kick * 0.5

    # Snare on beat 1 and 3
    if (1.0 <= beat_pos < 1.15) or (3.0 <= beat_pos < 3.15):
        s_time = beat_offset
        noise = (np.random.rand() * 2 - 1)
        snare = (np.sin(2 * np.pi * 180 * s_time) * 0.3 + noise * 0.7) * np.exp(-15 * s_time)
        audio[sample_idx] += snare * 0.3

    # Hi-hat on 8th notes
    hat_time = time_sec % (beat_dur / 2)
    if hat_time < 0.05:
        hat = (np.random.rand() * 2 - 1) * np.exp(-60 * hat_time)
        audio[sample_idx] += hat * 0.12

# 3. Vinyl Crackle Noise
crackle = (np.random.rand(num_samples) * 2 - 1) * 0.015
audio += crackle

# Normalize audio
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = audio / max_val * 0.85

# Convert to 16-bit PCM WAV
audio_int16 = (audio * 32767).astype(np.int16)
wav.write("lofi_music.wav", sample_rate, audio_int16)
print("Generated lofi_music.wav successfully!")
