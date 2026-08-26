"""Dump proposal_packet schema structure for conformance checking."""
import json

s = json.load(open("schemas/artifacts/proposal_packet.schema.json"))
pp = s["properties"]["production_plan"]
ce = s["properties"]["cost_estimate"]

print("savings_options:", ce["properties"]["savings_options"])
print()
ap = pp["properties"]["alternative_paths"]["items"]
print("alternative_paths item:", {k: (p.get("type") or p.get("enum"))
      for k, p in ap.get("properties", {}).items()})
print("alternative_paths required:", ap.get("required"))
print()
print("composition_mode enum:", pp["properties"]["composition_mode"].get("enum"))
print("render_runtime:", pp["properties"]["render_runtime"])
print("renderer_family:", pp["properties"]["renderer_family"])
print("playbook:", pp["properties"].get("playbook"))
print("stages:", pp["properties"]["stages"])
print()
print("delivery_promise:", pp["properties"].get("delivery_promise"))
print("music_source:", pp["properties"].get("music_source"))
print("voice_selection:", pp["properties"].get("voice_selection"))
print("art_direction:", pp["properties"].get("art_direction"))
print("decision_log_ref:", pp["properties"].get("decision_log_ref"))
