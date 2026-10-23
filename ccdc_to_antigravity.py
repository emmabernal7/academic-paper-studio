#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CCDC to Antigravity Integration Script
Extracts crystallographic, chemical and structural information from CSD
and formats/integrates it with the Antigravity workflow.
"""

import sys
from ccdc import io
# Nota: Reemplaza 'antigravity' por el nombre del módulo exacto de tu toolkit
try:
    import antigravity as ag 
except ImportError:
    # Simulación de fallback en caso de interactuar mediante archivos
    ag = None 

def extract_and_connect_structure(refcode):
    print(f"[+] Conectando a la base de datos central de CCDC...")
    csd_reader = io.EntryReader('CSD')
    
    if refcode not in csd_reader:
        print(f"[-] Error: El Refcode '{refcode}' no existe en la CSD.")
        return None
        
    print(f"[+] Extrayendo datos para: {refcode}")
    
    # 1. API de Entrada (Metadatos/Contexto Científico)
    entry = csd_reader.entry(refcode)
    
    # 2. API de Cristal (Red cristalina y Simetría)
    crystal = csd_reader.crystal(refcode)
    
    # 3. API de Molécula (Átomos, Enlaces y Coordenadas 3D)
    molecule = csd_reader.molecule(refcode)
    
    print("\n--- [CCDC DATA EXTRACTED] ---")
    print(f"Fórmula Química : {entry.formula}")
    print(f"Grupo Espacial  : {crystal.spacegroup}")
    print(f"Átomos Activos  : {len(molecule.atoms)}")
    print("-------------------------------\n")
    
    # Estructurar los datos unificados para el Toolkit Antigravity
    payload_estructura = {
        "metadata": {
            "refcode": entry.identifier,
            "formula": entry.formula,
            "doi": entry.doi if entry.doi else "N/A"
        },
        "crystal_lattice": {
            "lengths": crystal.cell_lengths,   # (a, b, c)
            "angles": crystal.cell_angles,     # (alpha, beta, gamma)
            "volume": crystal.cell_volume,
            "space_group": crystal.spacegroup
        },
        "atomic_geometry": [
            {
                "element": atom.element_symbol,
                "coordinates": (atom.coordinates.x, atom.coordinates.y, atom.coordinates.z),
                "charge": atom.partial_charge if atom.partial_charge else 0.0
            } for atom in molecule.atoms
        ]
    }
    
    # Enviar o Inicializar en Antigravity
    if ag is not None:
        print("[+] Conectando y cargando estructura en Antigravity...")
        # Flujo A: Carga nativa mediante API del objeto integrado
        antigravity_crystal = ag.CrystalSystem(
            lattice=payload_estructura["crystal_lattice"],
            geometry=payload_estructura["atomic_geometry"]
        )
        print("[+] Estructura vinculada con éxito en Antigravity.")
        return antigravity_crystal
    else:
        # Flujo B: Exportación intermedia (si la integración es vía archivo externo)
        output_filename = f"{refcode}_antigravity_input.cif"
        with io.MoleculeWriter(output_filename) as writer:
            writer.write(molecule)
        print(f"[!] Módulo 'antigravity' no detectado en el entorno.")
        print(f"[➔] Estructura guardada de forma intermedia en: {output_filename}")
        return payload_estructura

if __name__ == "__main__":
    # Refcode de prueba: ABEBUF (Estructura molecular orgánica estándar)
    target_refcode = "ABEBUF"
    
    # Si se pasa un argumento por consola, usarlo como Refcode
    if len(sys.argv) > 1:
        target_refcode = sys.argv[1]
        
    resultado = extract_and_connect_structure(target_refcode)
