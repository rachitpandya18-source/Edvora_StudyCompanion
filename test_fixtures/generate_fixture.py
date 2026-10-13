"""
Deterministic Test Fixture Generator for Edvora E2E Test Suite.
Generates an isolated, self-contained educational PDF about
piezoelectricity and ultrasonic wave mechanics.
"""

from pathlib import Path
import pymupdf  # PyMuPDF


def generate_educational_pdf(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()

    # Page 1: Foundations of Ultrasonics & The Piezoelectric Effect
    page1 = doc.new_page(width=595, height=842)  # Standard A4
    text_p1 = (
        "Fundamentals of Ultrasonics and Piezoelectric Waves\n\n"
        "Chapter 1: Introduction to Ultrasonic Acoustics\n"
        "Ultrasonic waves are mechanical acoustic vibrations whose frequencies exceed "
        "the limit of human hearing, typically defined as frequencies above 20 kHz (20,000 Hertz). "
        "Unlike electromagnetic radiation, ultrasound requires a material medium (such as a solid, "
        "liquid, or gas) for propagation. The propagation velocity of ultrasonic waves depends "
        "fundamentally on the density and elastic modulus of the transmitting medium. Ultrasonic waves "
        "carry higher energy compared to audible sound waves due to their shorter wavelength and higher frequency.\n\n"
        "Chapter 2: The Piezoelectric Effect\n"
        "The piezoelectric effect is the fundamental principle used to produce high-frequency ultrasonic waves. "
        "Certain anisotropic crystalline materials—such as quartz crystals, tourmaline, Rochelle salt, and synthetic "
        "barium titanate—exhibit both direct and inverse piezoelectric behavior.\n"
        "In the direct piezoelectric effect, when mechanical stress or compressive pressure is applied across specific "
        "crystal faces, electric charges accumulate on opposite faces, producing a measurable electric potential difference (voltage).\n"
        "In the inverse piezoelectric effect, when an alternating electric potential or voltage is applied across opposite "
        "crystal faces, the crystal undergoes mechanical contraction and expansion, producing continuous high-frequency vibrations."
    )
    page1.insert_text((50, 60), text_p1, fontsize=11, lineheight=1.4)

    # Page 2: Transducer Generation & Practical Applications
    page2 = doc.new_page(width=595, height=842)  # Standard A4
    text_p2 = (
        "Chapter 3: Generation of Ultrasonic Waves\n"
        "Piezoelectric generators (transducers) exploit the inverse piezoelectric effect to generate ultrasonic sound waves. "
        "A quartz crystal slice is mounted between two metal electrode plates connected to a high-frequency alternating current circuit.\n"
        "When the frequency of the applied alternating electric field matches the natural fundamental frequency of the quartz crystal, "
        "mechanical resonance occurs. At resonance, the crystal vibrates with maximum amplitude, generating powerful ultrasonic waves.\n"
        "The fundamental frequency of vibration for a quartz crystal of thickness t, Young's modulus Y, and density rho is given by:\n"
        "f = (1 / (2 * t)) * sqrt(Y / rho).\n\n"
        "Chapter 4: Applications of Ultrasonics\n"
        "1. Non-Destructive Testing (NDT): Ultrasonic pulse-echo inspection detects hidden internal flaws, cracks, and voids "
        "in structural metals, aerospace components, and pipelines.\n"
        "2. Medical Sonography: High-frequency ultrasound penetrates human tissue and reflects at tissue boundaries, "
        "providing non-invasive diagnostic imaging.\n"
        "3. Industrial Cleaning: High-energy acoustic cavitation produces micro-bubbles that scrub precision instruments."
    )
    page2.insert_text((50, 60), text_p2, fontsize=11, lineheight=1.4)

    doc.save(str(output_path))
    doc.close()
    return output_path


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "piezoelectric_ultrasonics.pdf"
    generate_educational_pdf(target)
    print(f"Generated {target} ({target.stat().st_size} bytes)")

