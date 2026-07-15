# decal_projector.py
# Componente auxiliar para gerenciar e alinhar decalques (Range Engine / UPBGE)

try:
    import Range as bge
except ImportError:
    import bge

from collections import OrderedDict
from mathutils import Vector

class DecalProjector(bge.types.KX_PythonComponent):
    args = OrderedDict([
        ("C_Icons", "MOD_SHRINKWRAP"),
        
        ("C_Header/Configuração do Decal/MOD_SHRINKWRAP", True),
        ("Normal Offset (meters)", 0.002),
        
        ("C_Header/Projeção e Alinhamento/SNAP_SURFACE", True),
        ("Max Ray Distance", 5.0),
        ("Align to Surface Normal", True),
        ("Parent to Hit Object", True),
    ])

    def start(self, args):
        self.normal_offset = args.get("Normal Offset (meters)", 0.002)
        self.max_ray_dist = args["Max Ray Distance"]
        self.align_to_normal = args["Align to Surface Normal"]
        self.parent_to_hit = args["Parent to Hit Object"]
        
        # Executa a projeção e alinhamento geométrico imediatamente
        self.perform_snap()

    def perform_snap(self):
        """
        Lança um raio ao longo do eixo local -Z do objeto, reposiciona-o
        no ponto de colisão com um offset normal e alinha-o à normal da pista.
        """
        # Direção local -Z do objeto (direção de projeção)
        direction = self.object.getAxisVect(Vector((0.0, 0.0, -1.0)))
        
        start_pos = self.object.worldPosition.copy()
        end_pos = start_pos + (direction * self.max_ray_dist)

        # Executa o raycast na cena (retorna: hit_obj, hit_pos, hit_norm)
        hit_obj, hit_pos, hit_norm = self.object.rayCast(end_pos, start_pos, self.max_ray_dist)

        if hit_obj:
            # Calcula o deslocamento ao longo da normal para evitar Z-fighting
            offset_vec = Vector((0.0, 0.0, 0.0))
            if hit_norm:
                normal = hit_norm.normalized()
                offset_vec = normal * self.normal_offset
                
            # Reposiciona o objeto no ponto de impacto + offset
            self.object.worldPosition = hit_pos + offset_vec
            
            # Alinha o eixo Z local do objeto com a normal da superfície usando lookAt
            if self.align_to_normal and hit_norm:
                normal = hit_norm.normalized()
                # lookAt(vetor, axis_index, factor) -> Eixo 2 é o Z local
                self.object.lookAt(normal, 2, 1.0)
                    
            # Conecta o decalque ao objeto atingido (ex: pistas móveis ou outros objetos)
            if self.parent_to_hit:
                self.object.setParent(hit_obj)
                    
            # Força o motor a atualizar a matriz e os limites de frustum culling do objeto imediatamente se disponível
            if hasattr(self.object, 'update'):
                self.object.update()

    def update(self):
        # Como o snapping é executado no start, não precisamos de lógica em todo frame.
        pass
