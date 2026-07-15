# Range Engine / UPBGE Optimization & Utilities Toolbox

Este repositório contém uma coleção de componentes Python estruturados e otimizados para jogos desenvolvidos na **Range Engine** ou **UPBGE (Blender Game Engine)**. 

Os componentes inclusos são focados em performance, automação de posicionamento de decalques e gerenciamento inteligente de iluminação em tempo real.

---

## 💡 Componentes Inclusos

1. **[Optimized Light Manager (`optimized_lights.py`)](#-optimized-light-manager-optimized_lightspy)**: Sistema de LOD (Level of Detail) e pool de luzes dinâmicas por proximidade para otimizar a renderização de iluminação urbana ou de pistas.
2. **[Decal Projector (`decal_projector.py`)](#-decal-projector-decal_projectorpy)**: Projetor geométrico instantâneo para projetar e alinhar decalques (como marcas de frenagem, óleo ou placas) à inclinação e normal de superfícies e pistas.

---

## 🔦 Optimized Light Manager (`optimized_lights.py`)

Gerenciador projetado para resolver a perda de performance decorrente do uso de múltiplas luzes dinâmicas (como postes de luz em uma pista ou cidade). Em vez de manter dezenas de fontes de luz ativas ao mesmo tempo, ele mantém apenas um pool pequeno de luzes em tempo real que "seguem" o jogador, teleportando-se suavemente entre os postes próximos com transições de fade-in e fade-out.

### ⚙️ Parâmetros do Componente (`args`)

| Campo | Tipo | Valor Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| **Player Name** | `String` | `"Player"` | Nome do objeto que representa o jogador na cena (centro do cálculo de LOD). |
| **Light Prefix** | `String` | `"MoveLamp"` | Prefixo do nome dos objetos de luz dinâmica real no pool (ex: `MoveLamp.001`). |
| **Empty Prefix** | `String` | `"Empty"` | Prefixo do nome dos objetos vazios (*Empties*) posicionados nos postes de iluminação. |
| **Enable Debug Mode** | `Boolean` | `False` | Desenha linhas de depuração 3D ligando os postes ao jogador e imprime logs no console. |
| **Update Interval (frames)** | `Integer` | `6` | Frequência de quadros para checar a distância do jogador (reduz o uso de CPU). |
| **Distance Threshold (meters)** | `Float` | `2.0` | Distância mínima que o jogador deve andar para recalcular as luzes ativas. |
| **Max Light Distance (meters)** | `Float` | `60.0` | Distância máxima de corte para ativar uma luz dinâmica real no poste. |
| **Fade Speed** | `Float` | `0.08` | Velocidade de transição fade das intensidades e cores durante o teleporte. |

### 🛠️ Como Configurar

1. **Luzes Dinâmicas (Pool):** Crie algumas luzes de tempo real (tipo Point ou Spot, ex: 3 a 5 luzes). Nomeie-as com o prefixo (ex: `MoveLamp.001`, `MoveLamp.002`). Elas serão movidas pelo script automaticamente.
2. **Postes (Empties):** Coloque objetos vazios (*Empties*) na posição de cada poste de luz. Nomeie-os com o prefixo (ex: `Empty.Poste.001`, `Empty.Poste.002`).
   * **Cores Individuais:** Mude a cor do Empty (ou use propriedades de jogo `r`, `g`, `b`) para que a luz dinâmica assuma essa cor ao se aproximar.
   * **Efeito Flicker (Mau Contato):** Adicione uma propriedade booleana `flicker = True` ou coloque `flicker` no nome do Empty para fazer o poste cintilar.
3. **Gerenciador:** Crie um Empty central na cena chamado `LightManager`, anexe o script `optimized_lights.py` como Componente e preencha os parâmetros.

---

## 🎨 Decal Projector (`decal_projector.py`)

Componente utilitário que automatiza o posicionamento geométrico de decalques sobre superfícies irregulares. Ele dispara um raio no eixo local `-Z` do decalque, reposiciona o objeto sobre o ponto de colisão com um offset ajustável (para evitar *Z-fighting*) e o alinha perfeitamente com a inclinação e a normal da superfície.

### ⚙️ Parâmetros do Componente (`args`)

| Campo | Tipo | Valor Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| **Normal Offset (meters)** | `Float` | `0.002` | Pequeno deslocamento na direção normal para evitar cintilação/sobreposição visual. |
| **Max Ray Distance** | `Float` | `5.0` | Alcance máximo do raio disparado para baixo para detectar o solo. |
| **Align to Surface Normal** | `Boolean` | `True` | Rotaciona o decalque para alinhar seu eixo Z local com a inclinação exata da pista. |
| **Parent to Hit Object** | `Boolean` | `True` | Torna o decalque filho da superfície atingida (essencial se a pista/plataforma se mover). |

### 🛠️ Como Configurar

1. Crie uma malha plana para representar o decalque (ex: marca de pneu, sujeira ou sinalização na pista).
2. Posicione o plano logo acima da pista, garantindo que o seu **eixo local -Z esteja apontando para baixo** (direção da projeção).
3. Anexe o script `decal_projector.py` como um **Python Component** neste objeto.
4. Ao iniciar o jogo, o script executará a projeção instantaneamente na primeira inicialização e liberará o loop de processamento (`update` livre), garantindo custo zero de CPU durante o gameplay.

---

## 📈 Benefícios Gerais de Performance

* **LOD Inteligente para Luzes:** Elimina o gargalo de draw calls gerado por iluminação dinâmica múltipla na BGE/Range Engine, simulando centenas de pontos de luz usando apenas de 3 a 5 luzes reais.
* **Transições Sem Pops:** As lâmpadas apagam e acendem gradativamente durante o teleporte de proximidade, impedindo transições bruscas visíveis ao jogador.
* **Projeção Estática Eficiente:** O decalque calcula sua posição exata no frame inicial (`start`) e cessa qualquer processamento subsequente, evitando chamadas repetitivas de raycast a cada frame.
* **Amortização de CPU:** O gerenciador de luzes realiza checagens temporizadas (Time-slicing) com base no deslocamento do jogador, evitando gargalos de lógica.
