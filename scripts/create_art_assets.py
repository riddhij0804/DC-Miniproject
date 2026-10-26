#!/usr/bin/env python3
"""
Creates elegant SVG artworks for the demo art auction catalog.
Each SVG is custom-styled with our palette to fit the editorial aesthetic.
"""
import os

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend", "assets", "images"
)

ARTWORKS = {
    "artwork_001.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <defs>
    <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#C5BDB0" />
      <stop offset="60%" stop-color="#EAE5D8" />
      <stop offset="100%" stop-color="#E5C79E" />
    </linearGradient>
    <linearGradient id="hillGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#4F523E" />
      <stop offset="100%" stop-color="#2D3121" />
    </linearGradient>
    <filter id="canvasTexture">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise"/>
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.05 0" />
      <feBlend mode="multiply" in="SourceGraphic"/>
    </filter>
  </defs>
  <rect width="800" height="600" fill="url(#skyGrad)" filter="url(#canvasTexture)" />
  <circle cx="560" cy="280" r="45" fill="#F04432" opacity="0.8" />
  <path d="M0 450 Q220 380 440 430 T800 400 L800 600 L0 600 Z" fill="url(#hillGrad)" />
  <path d="M0 500 Q300 460 600 510 T800 490 L800 600 L0 600 Z" fill="#1C1F16" />
  <!-- Pine silhouettes -->
  <g fill="#17160F">
    <path d="M220 540 L220 320 L205 350 L220 300 L200 340 L220 270 L195 320 L220 220 L245 320 L220 270 L240 340 L220 300 L235 350 Z" />
    <path d="M270 550 L270 360 L258 390 L270 340 L252 380 L270 310 L250 350 L270 260 L290 350 L270 310 L288 380 L270 340 L282 390 Z" />
    <path d="M170 560 L170 390 L160 410 L170 370 L155 400 L170 340 L185 400 L170 370 L180 410 Z" />
  </g>
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#DCD7CA" stroke-width="1.5" opacity="0.6"/>
</svg>""",

    "artwork_002.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#201E1B" />
  <radialGradient id="spotlight" cx="50%" cy="45%" r="50%">
    <stop offset="0%" stop-color="#4A443A" />
    <stop offset="60%" stop-color="#24211D" />
    <stop offset="100%" stop-color="#141311" />
  </radialGradient>
  <rect width="800" height="600" fill="url(#spotlight)" />
  <!-- Pedestal -->
  <polygon points="260,490 540,490 560,530 240,530" fill="#3A3631" stroke="#524D46" stroke-width="2"/>
  <rect x="240" y="530" width="320" height="30" fill="#292622" />
  <!-- Bronze Sculpture Silhouette & Chisels -->
  <g fill="#A8947C" stroke="#70614E" stroke-width="2">
    <!-- Torso and horns -->
    <path d="M380 230 C340 180 300 190 280 210 C310 230 330 250 340 280 C310 290 290 320 300 360 C320 390 350 410 380 420 L400 490 L440 490 L430 420 C460 400 480 370 480 330 C480 280 450 250 420 240 C430 210 460 200 490 210 C470 190 430 180 390 230 Z" />
    <!-- Dramatic highlights -->
    <path d="M350 290 Q380 300 390 340 T390 410" fill="none" stroke="#D1BEA8" stroke-width="4" stroke-linecap="round"/>
    <path d="M420 280 Q430 320 440 370" fill="none" stroke="#D1BEA8" stroke-width="3" stroke-linecap="round"/>
  </g>
  <text x="400" y="580" fill="#777468" font-family="'Inter', sans-serif" font-size="12" letter-spacing="3" text-anchor="middle">FOUNDRY CAST • BARYE ATELIER</text>
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#3F3A33" stroke-width="1"/>
</svg>""",

    "artwork_003.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#17160F" />
  <!-- Art Deco Geometric Background -->
  <g stroke="#33312B" stroke-width="1" fill="none">
    <circle cx="400" cy="300" r="240" />
    <circle cx="400" cy="300" r="200" stroke="#777468" stroke-width="1.5"/>
    <circle cx="400" cy="300" r="160" />
    <line x1="160" y1="300" x2="640" y2="300" stroke="#44413A" />
    <line x1="400" y1="60" x2="400" y2="540" stroke="#44413A" />
  </g>
  <!-- Watch Case in Gold -->
  <circle cx="400" cy="300" r="130" fill="#DDBA76" stroke="#9E8043" stroke-width="6"/>
  <circle cx="400" cy="300" r="115" fill="#F7F4EA" stroke="#7A6335" stroke-width="1"/>
  <!-- Dial Details -->
  <circle cx="400" cy="300" r="95" fill="none" stroke="#17160F" stroke-width="1" stroke-dasharray="2 4"/>
  <!-- Numerals (Roman XII, III, VI, IX) -->
  <text x="400" y="222" font-family="'Playfair Display', serif" font-size="18" font-weight="700" fill="#17160F" text-anchor="middle">XII</text>
  <text x="480" y="306" font-family="'Playfair Display', serif" font-size="16" font-weight="700" fill="#17160F" text-anchor="middle">III</text>
  <text x="400" y="388" font-family="'Playfair Display', serif" font-size="16" font-weight="700" fill="#17160F" text-anchor="middle">VI</text>
  <text x="320" y="306" font-family="'Playfair Display', serif" font-size="16" font-weight="700" fill="#17160F" text-anchor="middle">IX</text>
  <!-- Hands -->
  <line x1="400" y1="300" x2="445" y2="250" stroke="#17160F" stroke-width="4" stroke-linecap="round"/>
  <line x1="400" y1="300" x2="365" y2="335" stroke="#F04432" stroke-width="2" stroke-linecap="round"/>
  <circle cx="400" cy="300" r="5" fill="#F04432" />
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#2B2822" stroke-width="1"/>
</svg>""",

    "artwork_004.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#EAE5D8" />
  <circle cx="400" cy="300" r="260" fill="#E3DDD0" />
  <!-- Ceramic Vase Shape -->
  <g filter="drop-shadow(0px 15px 25px rgba(23,22,15,0.18))">
    <!-- Neck, Body, Base -->
    <path d="M360 140 L440 140 L450 180 C500 240 520 320 480 410 C460 450 435 480 430 490 L370 490 C365 480 340 450 320 410 C280 320 300 240 350 180 Z" 
          fill="#35424A" stroke="#212C33" stroke-width="3"/>
    <!-- Glaze runs / drips -->
    <path d="M370 180 C400 220 380 280 395 350 C410 410 420 440 400 480" fill="none" stroke="#8CA0A8" stroke-width="12" stroke-linecap="round" opacity="0.6"/>
    <path d="M430 200 C450 250 440 330 450 390 C455 420 450 460 435 485" fill="none" stroke="#D2A26C" stroke-width="6" stroke-linecap="round" opacity="0.8"/>
    <!-- Rim -->
    <ellipse cx="400" cy="140" rx="40" ry="8" fill="#1F282D" stroke="#4B5E6B" stroke-width="2"/>
  </g>
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#DCD7CA" stroke-width="1.5"/>
</svg>""",

    "artwork_005.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#F7F4EA" />
  <!-- Suprematist / Constructivist Abstract Composition -->
  <polygon points="120,80 340,40 280,240 100,200" fill="#17160F" />
  <polygon points="260,180 620,120 580,320 220,380" fill="#F04432" opacity="0.95"/>
  <polygon points="400,260 720,350 670,510 350,420" fill="#DDBA76" opacity="0.9"/>
  <circle cx="280" cy="420" r="70" fill="#2D3A4B" />
  <circle cx="560" cy="220" r="35" fill="#17160F" />
  <line x1="80" y1="480" x2="720" y2="160" stroke="#17160F" stroke-width="5" />
  <line x1="160" y1="520" x2="480" y2="520" stroke="#777468" stroke-width="3" />
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#DCD7CA" stroke-width="1"/>
</svg>""",

    "artwork_006.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#0E1218" />
  <!-- Cloisonné Vase with Enamel Florals -->
  <g filter="drop-shadow(0px 10px 20px rgba(0,0,0,0.5))">
    <ellipse cx="400" cy="480" rx="90" ry="18" fill="#1B222C" />
    <path d="M370 120 L430 120 L440 190 C490 260 510 350 460 440 L340 440 C290 350 310 260 360 190 Z" 
          fill="#0B1C28" stroke="#DDBA76" stroke-width="3" />
    <!-- Silver wire chrysanthemums -->
    <circle cx="400" cy="300" r="36" fill="none" stroke="#EAE5D8" stroke-width="2"/>
    <circle cx="400" cy="300" r="16" fill="#F04432" stroke="#EAE5D8" stroke-width="1"/>
    <!-- Petals -->
    <path d="M400 250 Q410 280 400 300 Q390 280 400 250 Z" fill="#F7F4EA" stroke="#DDBA76" stroke-width="1"/>
    <path d="M400 350 Q410 320 400 300 Q390 320 400 350 Z" fill="#F7F4EA" stroke="#DDBA76" stroke-width="1"/>
    <path d="M350 300 Q380 310 400 300 Q380 290 350 300 Z" fill="#F7F4EA" stroke="#DDBA76" stroke-width="1"/>
    <path d="M450 300 Q420 310 400 300 Q420 290 450 300 Z" fill="#F7F4EA" stroke="#DDBA76" stroke-width="1"/>
  </g>
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#252F3C" stroke-width="1"/>
</svg>""",

    "artwork_007.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <!-- Charcoal Toned Paper -->
  <rect width="800" height="600" fill="#D3CABE" />
  <!-- Drapery and Study Lines -->
  <g stroke="#3C3731" stroke-width="2.5" fill="none" stroke-linecap="round">
    <path d="M220 80 Q240 220 260 380 Q280 480 320 540" />
    <path d="M310 90 Q340 240 330 390 Q320 490 360 550" />
    <path d="M420 85 Q400 260 410 400 Q420 490 440 545" />
    <path d="M520 100 Q490 250 480 380 Q470 480 500 550" />
    <!-- Cross hatch shading -->
    <path d="M270 200 L330 250 M260 220 L320 270 M250 240 L310 290" stroke-width="1.2" opacity="0.6"/>
    <path d="M390 220 L440 270 M380 240 L430 290 M375 260 L420 310" stroke-width="1.2" opacity="0.6"/>
  </g>
  <!-- White chalk highlights -->
  <g stroke="#FFFDF8" stroke-width="3" fill="none" opacity="0.8" stroke-linecap="round">
    <path d="M240 140 Q255 240 270 340" />
    <path d="M340 160 Q345 260 335 360" />
    <path d="M425 150 Q415 250 420 350" />
  </g>
  <!-- Monogram -->
  <text x="680" y="540" font-family="'Playfair Display', serif" font-size="20" font-style="italic" fill="#5A534B">J.S.S.</text>
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#B8AF9F" stroke-width="1.5"/>
</svg>""",

    "artwork_008.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#1C1B18" />
  <radialGradient id="marbleGlow" cx="50%" cy="45%" r="45%">
    <stop offset="0%" stop-color="#46423A" />
    <stop offset="100%" stop-color="#1C1B18" />
  </radialGradient>
  <rect width="800" height="600" fill="url(#marbleGlow)" />
  <!-- Honed Marble Base -->
  <polygon points="300,500 500,500 520,530 280,530" fill="#2E2B26" stroke="#48443D" stroke-width="2"/>
  <rect x="280" y="530" width="240" height="25" fill="#181715" />
  <!-- Classical Marble Torso in Pure White/Ivory tones -->
  <g fill="#F2ECE1" stroke="#C4BAA9" stroke-width="1">
    <path d="M370 160 C340 180 330 220 335 270 C340 310 325 360 340 420 C350 460 370 490 380 500 L420 500 C430 490 450 460 460 420 C475 360 460 310 465 270 C470 220 460 180 430 160 Z" />
    <!-- Sculptural shadow contours -->
    <path d="M375 250 C385 270 395 285 400 320 C405 350 400 390 390 430" fill="none" stroke="#ABA08E" stroke-width="3" stroke-linecap="round"/>
    <path d="M430 260 C420 280 415 300 415 330" fill="none" stroke="#D6CDC0" stroke-width="3" stroke-linecap="round"/>
  </g>
  <rect x="20" y="20" width="760" height="560" fill="none" stroke="#33302A" stroke-width="1"/>
</svg>"""
}

def generate_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    for filename, svg_content in ARTWORKS.items():
        filepath = os.path.join(ASSETS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content.strip())
        print(f"Generated asset: {filepath}")

if __name__ == "__main__":
    generate_assets()
