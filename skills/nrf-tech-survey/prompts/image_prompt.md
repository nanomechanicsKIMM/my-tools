---
title: "기술수요조사서 기술 설명 그림 프롬프트"
created: 2026-04-04
tags: [NRF, 이미지프롬프트, 오리가미, 메타물질, 초음파프로브]
---

# 기술 설명 그림 생성 프롬프트

## Prompt 1: 전체 개념도 (메인 그림)

```
A clean scientific illustration showing the concept of a minimally invasive origami metamaterial ultrasound probe for brain imaging. The illustration shows three sequential stages from left to right:

Stage 1 (LEFT): A thin, folded origami structure (diameter ~6mm) being inserted through a small burr hole in the human skull. The skull is shown in cross-section with bone tissue visible. The folded probe looks like a compact cylinder with visible crease patterns.

Stage 2 (CENTER): The origami structure in mid-deployment, partially unfolding in the subdural space between the inner surface of the skull and the brain surface (dura mater). Arrows indicate the expansion direction.

Stage 3 (RIGHT): The fully deployed flat circular probe (diameter ~60mm, shown 10x larger than the insertion state) conforming to the curved brain surface. Small ultrasound transducer elements are visible as an array pattern on the probe surface. Blue ultrasound wave beams are shown penetrating into the brain tissue below.

Style: Technical medical illustration, cross-sectional anatomical view, soft neutral background, labeled with clean sans-serif annotations. Color palette: skull in warm beige, brain in soft pink/coral, probe in metallic blue/teal, ultrasound waves in translucent blue gradient. No text labels in the image. Professional, publication-quality.
```

## Prompt 2: 접힘→전개 메커니즘 상세 (보조 그림)

```
A top-down technical diagram showing the folding-to-deployment transformation of an origami metamaterial ultrasound probe. The diagram shows four states arranged in a 2x2 grid:

Top-left: Fully folded state - a small compact disc (6mm diameter) with visible origami crease lines forming a radial pattern. Shown from above.

Top-right: Partially unfolded state - the structure begins to open, revealing triangular facets with thin-film piezoelectric transducer elements (small gold/copper squares) on each facet. About 30% deployed.

Bottom-left: Nearly deployed state - the structure is mostly flat with some remaining curvature. The array of transducer elements is clearly visible in a regular pattern. About 70% deployed.

Bottom-right: Fully deployed state - a flat circular disc (60mm diameter) with a grid of ultrasound transducer elements. Flexible circuit traces (thin golden lines) connect the elements in a serpentine pattern across the fold lines.

Curved arrows between each state indicate the transformation sequence. A scale bar shows 6mm and 60mm for size comparison. Style: Clean engineering schematic, white background, isometric perspective, thin line art with subtle color fills. Metallic blue for the substrate, gold for electrodes, green for circuit traces.
```

## Prompt 3: 임상 적용 시나리오 (개념적)

```
A conceptual medical illustration showing a patient's head in semi-transparent view, revealing the brain inside the skull. A small origami metamaterial ultrasound probe is shown deployed on the surface of the brain, visible through the translucent skull.

The probe is a thin, flat disc glowing in soft teal/cyan, conforming to the curvature of the brain. Concentric ultrasound wave rings emanate from the probe downward into the brain tissue, visualized as subtle blue ripple patterns. A tiny insertion point on the skull (marked with a small circle) shows where the folded probe was inserted.

On a connected display screen nearby, a real-time brain ultrasound image is shown, depicting internal brain structures.

Style: Modern medical concept art, soft volumetric lighting, dark background with the head illuminated. Semi-realistic anatomical rendering. The probe and ultrasound waves are the visual focal point with a gentle glow effect. Cinematic, futuristic medical technology aesthetic.
```

## Prompt 4: State-of-Art 비교 다이어그램 (비교 그림)

```
A comparison diagram showing three approaches to brain ultrasound, arranged as three panels side by side:

Panel 1 (LEFT) - "Transcranial": An ultrasound probe placed on the outside of the skull. Red X marks and wavy distorted lines show the ultrasound waves being scattered and attenuated by the thick skull bone. Label area shows "Transmission: ~2%".

Panel 2 (CENTER) - "Metaskull replacement": A section of skull is replaced with a honeycomb metamaterial implant. Ultrasound waves pass through more easily but the approach requires removing a large piece of skull. Partial green checkmark.

Panel 3 (RIGHT) - "Origami deployable probe (This work)": A small hole in the skull with a deployed origami probe underneath, directly on the brain surface. Clean, undistorted ultrasound waves penetrate the brain. Full green checkmark. The small insertion hole is highlighted to emphasize minimal invasiveness.

Style: Clean infographic style, three equal panels with thin dividing lines, consistent color coding (red for problems, green for solutions, blue for ultrasound). Simple anatomical cross-sections, not photorealistic. White background, modern flat design with subtle shadows.
```

## 권장 사용

| 프롬프트 | 용도 | 수요조사서 위치 |
|---------|------|--------------|
| Prompt 1 | **메인 개념도** — 기술의 핵심 원리를 한 눈에 보여줌 | 표지 또는 기술 개요 |
| Prompt 2 | 접힘→전개 메커니즘 상세 | 핵심기술내용 |
| Prompt 3 | 임상 비전 — 비전문가도 이해 가능 | 제안취지 또는 파급효과 |
| Prompt 4 | 기존 기술 대비 차별점 비교 | 국내외 동향 또는 제안취지 |

> [!tip] 수요조사서에는 Prompt 1 (전체 개념도) 또는 Prompt 4 (비교 다이어그램)을 권장.
> 5페이지 제한이므로 그림 1개가 적절하며, 기술의 핵심 원리가 직관적으로 전달되는 것이 중요.
