# Astronyx Mini Forge V3.1 — GPU PBR Preview

## O que muda
A partir da V3.1, a prévia texturizada tenta usar OpenGL 3.3 com ModernGL. A malha é enviada à GPU e a renderização PBR aproximada usa shader GLSL e z-buffer para ocultação, com texturas Albedo/MAES e, quando disponível, Normal. O resultado é lido de um framebuffer; a interface Tk mostra a imagem pronta. O renderizador CPU permanece como reserva.

## Controles do Painting Studio
- **GPU / PBR**: tenta OpenGL 3.3; se o driver não suportar, usa a prévia CPU automaticamente.
- **Luz**: intensidade de iluminação 0 a 300%, apenas na prévia.
- **Emissão**: intensidade luminosa 0 a 300%, apenas na prévia.
- A aparência no TaleSpire pode diferir, pois o jogo usa shaders, ambiente e efeito paint-wash próprios.

## Recursos do shader
Normais geométricas, mapa de normais opcional, Fresnel Schlick, distribuição GGX, Albedo e canais MAES (R=metal, G=AO, B=emissão, A=suavidade), com uma luz direcional e tone mapping.

## Performance e segurança
- Contexto ModernGL vive exclusivamente na thread dedicada ao render; nunca no thread Tk.
- Reutilização da geometria e texturas, atualizadas somente quando a miniatura ou a pintura mudar.
- O frontend opera offline e não precisa de conta externa.
- Prévia de até 150 mil triângulos e 900x900 pixels. FPS depende do computador e da cópia GPU->Tk; não há garantia de 30/60 FPS.
- Drivers sem OpenGL 3.3, RDP ou VMs podem utilizar somente CPU.

## Como testar
1. Instale o executável V3.1.
2. Abra uma miniatura convertida e entre em Pintura 3D.
3. Confirme o texto do viewport: GPU OpenGL 3.3 ou CPU (reserva).
4. Selecione armadura e aplique Ouro polido; mude Luz e Emissão.
5. Exporte novamente .tsMod e compare as texturas dentro do TaleSpire.

## Limites
Não há HDRI/IBL, ray tracing ou sombras projetadas. O preview GPU acelera desenho da miniatura, mas a seleção do pincel/UV ainda roda em CPU. O .tsMod não é alterado automaticamente; escala 1x1 e movimentação exigem teste dentro do TaleSpire. Não é o motor proprietário do Basecoat.

Referências:
- https://moderngl.readthedocs.io/en/latest/topics/context.html
- https://talespire.com/taleweaverlite-guide
