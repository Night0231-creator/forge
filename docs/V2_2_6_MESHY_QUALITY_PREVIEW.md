# Mini Forge — Preview 1x1 e fidelidade Meshy (PR de desenvolvimento)

## Preview visual 1x1

Na pagina Studio 3D, em Texturas, use Humanoide 1x1: ligado/desligado.
O boneco e a regua usam a mesma unidade vertical visual do OBJ preparado
(Y-up), com referencia humanoide provisoria de 1,75 unidade. A previa
recentraliza o personagem para mostrar o comparador no lado direito,
e utiliza filtragem bilinear na amostragem do albedo.

**Atencao:** a silhueta e desenhada em 2D e permanece voltada a camera;
nao e um segundo modelo 3D. Nao mede collider ou escala fisica dentro
do TaleSpire. O angulo de camera altera a altura projetada igualmente
para o modelo e para o comparador. O botao Diagnosticar escala 1x1
na aba Gerar .tsMod fornece auditoria numerica sem alterar OBJ.

## Texturas mais fieis ao Meshy

- Se a miniatura tem somente um material, UV original e albedo
  ligado diretamente a um PNG sRGB de ate 2048px, o pipeline tenta
  copiar bytes do PNG original sem recompressao. Texturas PNG embutidas
  no GLB sao aceitas quando seus bytes possuem assinatura PNG.
- Se a textura usa efeitos, transformacao UV, varios materiais, arquivo
  nao PNG, imagens grandes ou caso incerto, mantemos Cycles bake.
- O atlas UV automatico usa margem de 0,008; o bake passou para
  quatro amostras e margem de 8-12 pixels.
- O thumbnail utiliza altura efetiva apos limite de largura, evitando
  enquadramento com personagem muito pequeno.
- O relatorio conversao.json inclui albedo_method,
  triangle_retention_percent, bake_samples, bake_margin_px e resolucao.
  O log explica a perda potencial de detalhes e atlas reorganizado.

## Limites verificaveis

A documentacao oficial TaleWeaverLite limita ate 60 mil vertices e
texturas ate 2048x2048. A resolucao superior do perfil Ultra ainda
e reduzida na copia enviada ao TaleWeaverCmd.

- Guia TaleSpire: https://talespire.com/taleweaverlite-guide
- Baking Blender: https://docs.blender.org/manual/en/4.4/render/cycles/baking.html

## Validacao

Os testes automaticos validam codigo Python, relatorios e comparacao de
altura projetada. Nao garantem, sem teste real Blender + TaleWeaverCmd +
TaleSpire, que pele, cabelo, armadura, brilho e escala de gameplay
ficarao identicos ao Meshy. As alteracoes permanecem no PR ate serem
revisadas; a versao publica e 2.2.5.
