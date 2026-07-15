# optimized_lights.py
# Componente de iluminação otimizada para postes (Range Engine / Blender Game Engine / UPBGE)

try:
    import Range as bge
except ImportError:
    import bge

from collections import OrderedDict
import heapq
import random
from mathutils import Vector

class OptimizedLightManager(bge.types.KX_PythonComponent):
    args = OrderedDict([
        ("C_Icons", "LAMP_DATA"),

        ("C_Header/Configuração do Pool/EMPTY_DATA", True),
        ("Player Name", "Player"),
        ("Light Prefix", "MoveLamp"),
        ("Empty Prefix", "Empty"),
        ("Enable Debug Mode", False),
        
        ("C_Header/Otimizações de Distância/TIME", True),
        ("Update Interval (frames)", 6),
        ("Distance Threshold (meters)", 2.0),
        ("Max Light Distance (meters)", 60.0),
        
        ("C_Header/Transições e Efeitos/COLOR", True),
        ("Fade Speed", 0.08),
    ])

    def start(self, args):
        self.player_name = args["Player Name"]
        self.light_prefix = args["Light Prefix"]
        self.empty_prefix = args["Empty Prefix"]
        self.enable_debug = args.get("Enable Debug Mode", False)
        self.update_interval = args["Update Interval (frames)"]
        self.dist_threshold = args["Distance Threshold (meters)"]
        self.max_light_dist = args.get("Max Light Distance (meters)", 60.0)
        
        self.fade_speed = args["Fade Speed"]

        self.scene = self.object.scene
        
        # Variáveis de controle de frequência e cache
        self.frame_counter = 0
        self.last_player_pos = None

        # 2. Inicializa o pool de luzes dinâmicas
        self.init_dynamic_pool()

        # 3. Informações de depuração na inicialização
        if self.enable_debug:
            print("[LightManager DEBUG] --- INICIALIZADO COM DEBUG ---")
            print("[LightManager DEBUG] Jogador Alvo: '{}'".format(self.player_name))
            matching_objs = [obj.name for obj in self.scene.objects if self.light_prefix.lower() in obj.name.lower()]
            print("[LightManager DEBUG] Objetos contendo '{}' na cena: {}".format(self.light_prefix, matching_objs))
            if not matching_objs:
                all_names = [obj.name for obj in self.scene.objects][:60]
                print("[LightManager DEBUG] AVISO: Nenhum objeto contem o prefixo '{}' na cena!".format(self.light_prefix))
                print("[LightManager DEBUG] Primeiros 60 objetos na cena: {}".format(all_names))
            
            overlap_count = 0
            for obj in self.scene.objects:
                if self.light_prefix.lower() in obj.name.lower() and self.empty_prefix.lower() in obj.name.lower():
                    print("[LightManager DEBUG] AVISO CRITICO: O objeto '{}' coincide com o prefixo de lampada e de empty ao mesmo tempo!".format(obj.name))
                    overlap_count += 1
            if overlap_count > 0:
                print("[LightManager DEBUG] Dica: Altere os nomes na cena de forma que a lampada nao contenha a palavra do Empty (ex: use 'LampPoste' e 'EmptyPoste').")

    def init_dynamic_pool(self):
        """
        Inicializa o pool de luzes dinâmicas reais (que afetam os carros)
        e a lista de posições dos postes (Empties).
        """
        self.pool_lights = []
        for obj in self.scene.objects:
            if self.light_prefix.lower() in obj.name.lower() and self.empty_prefix.lower() not in obj.name.lower():
                base_energy = getattr(obj, "energy", 1.0)

                has_shadow = False
                try:
                    has_shadow = bool(obj.blenderObject.data.use_shadow)
                except Exception:
                    pass
                if not has_shadow:
                    has_shadow = "shadow" in obj.name.lower() or bool(obj.get("shadow", False))

                self.pool_lights.append({
                    "obj": obj,
                    "state": "IDLE",            # IDLE, FADING_OUT, FADING_IN, ACTIVE
                    "current_empty": None,
                    "target_empty": None,
                    "fade_factor": 0.0,
                    "base_energy": base_energy,
                    "target_color": [1.0, 1.0, 1.0],
                    "flicker": False,
                    "shadow": has_shadow,
                })
                self.update_light_visuals(self.pool_lights[-1])

        self.empties = []
        for obj in self.scene.objects:
            if self.empty_prefix.lower() in obj.name.lower():
                color = [1.0, 1.0, 1.0]
                
                group_obj = getattr(obj, "groupObject", None)
                if group_obj and "r" in group_obj and "g" in group_obj and "b" in group_obj:
                    color = [group_obj["r"], group_obj["g"], group_obj["b"]]
                elif "r" in obj and "g" in obj and "b" in obj:
                    color = [obj["r"], obj["g"], obj["b"]]
                elif hasattr(obj, "color"):
                    color = list(obj.color[:3])
                
                self.empties.append({
                    "obj": obj,
                    "color": color
                })

        print("[LightManager] Pool de Luzes Dinamicas: {} luzes e {} postes configurados.".format(
            len(self.pool_lights), len(self.empties)
        ))

    def get_empty_color(self, empty_obj):
        if not empty_obj or empty_obj.invalid:
            return [1.0, 1.0, 1.0]

        color = [1.0, 1.0, 1.0]

        group_obj = getattr(empty_obj, "groupObject", None)
        if group_obj:
            if "r" in group_obj and "g" in group_obj and "b" in group_obj:
                return [group_obj["r"], group_obj["g"], group_obj["b"]]
            elif hasattr(group_obj, "color"):
                return list(group_obj.color[:3])

        if "r" in empty_obj and "g" in empty_obj and "b" in empty_obj:
            return [empty_obj["r"], empty_obj["g"], empty_obj["b"]]
        elif hasattr(empty_obj, "color"):
            return list(empty_obj.color[:3])

        return color

    def update_light_visuals(self, light):
        """
        Atualiza a intensidade física da luz dinâmica e sua cor com base no fade_factor.
        """
        factor = light["fade_factor"]
        color = light["target_color"]
        light_obj = light["obj"]

        if light_obj.invalid:
            return

        flicker_factor = 1.0
        if light.get("flicker", False) and light["state"] == "ACTIVE":
            rnd = random.random()
            if rnd < 0.015:
                flicker_factor = 0.05
            elif rnd < 0.12:
                flicker_factor = random.uniform(0.6, 0.9)
            else:
                flicker_factor = random.uniform(0.95, 1.05)
        
        factor *= flicker_factor

        if hasattr(light_obj, "energy"):
            light_obj.energy = light["base_energy"] * factor

        alpha = 1.0
        if hasattr(light_obj, "color") and len(light_obj.color) == 4:
            alpha = light_obj.color[3]
        
        try:
            light_obj.color = [color[0] * factor, color[1] * factor, color[2] * factor, alpha]
        except AttributeError:
            light_obj.color = [color[0] * factor, color[1] * factor, color[2] * factor]
        except Exception:
            pass

    def update(self):
        # 1. Processa a transição suave de fade todo frame (essencial para evitar flickering/pops)
        self.process_fading()

        # Encontra o jogador ativo na cena
        player = self.scene.objects.get(self.player_name)
        
        # Se o debug estiver ativo, desenha as linhas de sensor em todo frame
        if self.enable_debug:
            self.draw_debug_lines(player)

        # 2. Executa a checagem de distância de forma amortizada (Time-slicing)
        self.frame_counter += 1
        if self.frame_counter < self.update_interval:
            return
        
        self.frame_counter = 0

        if not player or player.invalid:
            if self.enable_debug:
                print("[LightManager DEBUG] Erro: Jogador '{}' nao encontrado na cena ou e invalido!".format(self.player_name))
            return

        player_pos = player.worldPosition
        if self.last_player_pos is not None:
            dist_moved = (player_pos - self.last_player_pos).length
            if dist_moved < self.dist_threshold:
                if self.enable_debug:
                    print("[LightManager DEBUG] Jogador movido {:.2f}m (limite: {}m). Ignorando recalculo.".format(dist_moved, self.dist_threshold))
                return

        self.last_player_pos = player_pos.copy()

        # 3. Atualiza a atribuição dos postes mais próximos
        if self.enable_debug:
            print("[LightManager DEBUG] Atualizando luzes mais proximas em: {}".format(player_pos))
        self.update_closest_lights(player_pos)

    def draw_debug_lines(self, player):
        if not player or player.invalid:
            return
            
        player_pos = player.worldPosition
        
        for empty in self.empties:
            empty_obj = empty["obj"]
            if empty_obj.invalid:
                continue
            
            empty_pos = empty_obj.worldPosition
            dist = (empty_pos - player_pos).length
            
            if dist <= self.max_light_dist:
                color = [0.0, 1.0, 0.0]
            else:
                color = [1.0, 0.0, 0.0]
                
            is_active = False
            for light in self.pool_lights:
                if light["current_empty"] == empty or light["target_empty"] == empty:
                    is_active = True
                    break
            if is_active:
                color = [0.0, 0.8, 1.0]
                
            bge.render.drawLine(empty_pos, player_pos, color)
            
            to_pos = empty_pos + Vector((0.0, 0.0, -50.0))
            try:
                hit_obj, hit_pos, hit_norm = empty_obj.rayCast(to_pos, empty_pos, 50.0)
                if hit_pos:
                    ground_pos = hit_pos
                else:
                    ground_pos = empty_pos + Vector((0.0, 0.0, -15.0))
            except Exception:
                ground_pos = empty_pos + Vector((0.0, 0.0, -15.0))
                
            bge.render.drawLine(empty_pos, ground_pos, [1.0, 0.6, 0.0])

    def update_closest_lights(self, player_pos):
        if not self.empties or not self.pool_lights:
            return

        num_lights = len(self.pool_lights)

        closest_empties_data = heapq.nsmallest(
            num_lights,
            [((empty["obj"].worldPosition - player_pos).length, i) for i, empty in enumerate(self.empties)]
        )

        closest_empties = [
            self.empties[item[1]] 
            for item in closest_empties_data 
            if item[0] <= self.max_light_dist
        ]

        shadow_pool = [l for l in self.pool_lights if l.get("shadow", False)]
        normal_pool = [l for l in self.pool_lights if not l.get("shadow", False)]

        if not shadow_pool:
            self._update_pool_assignment(self.pool_lights, closest_empties)
        else:
            num_shadows = len(shadow_pool)
            shadow_empties = closest_empties[:num_shadows]
            normal_empties = closest_empties[num_shadows:]
            
            self._update_pool_assignment(shadow_pool, shadow_empties)
            self._update_pool_assignment(normal_pool, normal_empties)

    def _update_pool_assignment(self, pool, target_empties):
        assigned_empties = []
        lights_to_reassign = []

        for light in pool:
            if light["state"] in ("ACTIVE", "FADING_IN"):
                if light["current_empty"] in target_empties:
                    assigned_empties.append(light["current_empty"])
                else:
                    lights_to_reassign.append(light)
            elif light["state"] == "FADING_OUT":
                if light["target_empty"] in target_empties:
                    assigned_empties.append(light["target_empty"])
                else:
                    lights_to_reassign.append(light)
            else:
                lights_to_reassign.append(light)

        needed_empties = [e for e in target_empties if e not in assigned_empties]

        for new_empty in needed_empties:
            if not lights_to_reassign:
                break
            
            light = lights_to_reassign.pop(0)
            light["target_empty"] = new_empty
            
            old_name = light["current_empty"]["obj"].name if light["current_empty"] else "IDLE"
            print("[LightManager] Realocando {} de '{}' para '{}' (Sombra: {})".format(
                light["obj"].name, old_name, new_empty["obj"].name, light.get("shadow", False)
            ))
            
            empty_obj = new_empty["obj"]
            light["flicker"] = empty_obj.get("flicker", False) or "flicker" in empty_obj.name.lower()

            if light["state"] in ("ACTIVE", "FADING_IN"):
                light["state"] = "FADING_OUT"
            elif light["state"] == "IDLE":
                light["obj"].worldPosition = empty_obj.worldPosition
                light["current_empty"] = new_empty
                light["target_color"] = self.get_empty_color(empty_obj)
                light["state"] = "FADING_IN"
            elif light["state"] == "FADING_OUT":
                pass

    def process_fading(self):
        for light in self.pool_lights:
            state = light["state"]
            
            if state == "FADING_OUT":
                light["fade_factor"] -= self.fade_speed
                if light["fade_factor"] <= 0.0:
                    light["fade_factor"] = 0.0
                    
                    target = light["target_empty"]
                    if target and not target["obj"].invalid:
                        light["obj"].worldPosition = target["obj"].worldPosition
                        light["current_empty"] = target
                        light["target_color"] = self.get_empty_color(target["obj"])
                        light["flicker"] = target["obj"].get("flicker", False) or "flicker" in target["obj"].name.lower()
                        light["state"] = "FADING_IN"
                    else:
                        light["state"] = "IDLE"
                
                self.update_light_visuals(light)
                
            elif state == "FADING_IN":
                light["fade_factor"] += self.fade_speed
                if light["fade_factor"] >= 1.0:
                    light["fade_factor"] = 1.0
                    light["state"] = "ACTIVE"
                
                self.update_light_visuals(light)
                
            elif state == "ACTIVE":
                if light["fade_factor"] != 1.0:
                    light["fade_factor"] = 1.0
                    self.update_light_visuals(light)
            
            elif state == "IDLE":
                if light["fade_factor"] != 0.0:
                    light["fade_factor"] = 0.0
                    self.update_light_visuals(light)
