"""48 kHz periodic-loop weighting helpers; not gated programme loudness or SPL.

K: ITU-R BS.1770-1 Annex 1, Tables 1/2 (48 kHz biquads).
https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-1-200709-S!!PDF-E.pdf
FFT evaluation gives the two filters' periodic steady state, with no startup transient.
A: analog A curve, normalised to 0 dB at 1 kHz, evaluated at FFT frequencies.
"""

import numpy as np


def levels(samples, rate=48000):
    if rate != 48000:
        raise ValueError("weighting coefficients require 48000 Hz")
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or not len(x) or not np.all(np.isfinite(x)):
        raise ValueError("expected finite mono samples")
    frequency = np.fft.rfftfreq(len(x), 1 / rate)
    z = np.exp(-2j * np.pi * frequency / rate)
    shelf = (1.53512485958697 - 2.69169618940638 * z + 1.19839281085285 * z * z) / (
        1 - 1.69065929318241 * z + 0.73248077421585 * z * z
    )
    highpass = (1 - 2 * z + z * z) / (1 - 1.99004745483398 * z + 0.99007225036621 * z * z)

    def a_curve(f):
        f2 = f * f
        return (
            12194**2
            * f2
            * f2
            / ((f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194**2))
        )

    spectrum = np.fft.rfft(x)
    result = {}
    for name, response in (("RMS", 1), ("K", shelf * highpass), ("A", a_curve(frequency) / a_curve(1000))):
        filtered = np.fft.irfft(spectrum * response, n=len(x))
        power = np.mean(filtered**2)
        result[name] = float(10 * np.log10(power)) if power > 0 else float("-inf")
    result["K"] -= 0.691  # BS.1770 mono calibration; no gating/channel aggregation.
    return result
