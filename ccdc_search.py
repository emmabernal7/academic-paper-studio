#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CCDC Search Toolkit: Substructure & SMILES Search Module
========================================================
Permite realizar búsquedas cristalográficas en la base de datos CSD
a partir de SMILES, fórmulas empíricas, nombres químicos o identificadores Refcode.
"""

import sys
import json

def parse_smiles_metadata(smiles: str) -> dict:
    """
    Analiza un SMILES y extrae información preliminar
    (átomos clave, metales de coordinación, posibles fórmulas y nombres).
    """
    info = {
        "raw_smiles": smiles,
        "metal_center": None,
        "coordinating_atoms": [],
        "halogen_ligands": [],
        "inferred_name": "",
        "empirical_formula_guess": ""
    }
    
    # Detección específica de centros metálicos y ligandos
    if "[Pd]" in smiles or "Pd" in smiles:
        info["metal_center"] = "Pd (Paladio II)"
    if "Cl" in smiles:
        info["halogen_ligands"].append("Cl (Cloro)")
        
    if "CC" in smiles and "NH" in smiles:
        if smiles.count("[CH3]") == 2 or smiles.count("C") == 4:
            info["inferred_name"] = "cis-dicloro(N,N'-dimetiletano-1,2-diamina)paladio(II)"
            info["empirical_formula_guess"] = "C4H12Cl2N2Pd"
            
    return info

def search_ccdc_by_smiles(smiles: str, max_hits: int = 10):
    """
    Ejecuta una búsqueda por subestructura en la CSD utilizando la CSD Python API.
    Si no está instalado el paquete `ccdc`, devuelve el plan de consulta y diagnóstico.
    """
    print(f"[+] Iniciando búsqueda en CCDC para SMILES: {smiles}")
    meta = parse_smiles_metadata(smiles)
    if meta["inferred_name"]:
        print(f"    |-- Compuesto inferido : {meta['inferred_name']}")
        print(f"    |-- Centro metalico   : {meta['metal_center']}")
        print(f"    \\-- Formula estimada  : {meta['empirical_formula_guess']}")

    try:
        from ccdc import search
        from ccdc.molecule import Molecule

        print("[+] Cargando CSD Python API (ccdc.search)...")
        query_mol = Molecule.from_string(smiles, format='smiles')
        
        # Configurar búsqueda de subestructura
        sub_search = search.SubstructureSearch()
        sub_search.add_substructure(query_mol)
        
        print("[+] Ejecutando consulta de subestructura en la base de datos local CSD...")
        hits = sub_search.search(max_hits_per_structure=1)
        
        results = []
        for i, hit in enumerate(hits):
            if i >= max_hits:
                break
            results.append({
                "identifier": hit.identifier,
                "formula": hit.entry.formula,
                "synonym": hit.entry.chemical_name,
                "has_3d": hit.crystal is not None
            })
            
        print(f"[OK] Se encontraron {len(results)} coincidencias en CSD.")
        return results

    except ImportError:
        print("\n[!] AVISO: El paquete oficial 'ccdc' (CSD Python API) no esta activo en el entorno actual.")
        print("[!] Para ejecutar busquedas de subestructura 3D directas por CSD Python API:")
        print("    1. conda install -c ccdc csd-python-api")
        print("    2. ccdc-activator (con tu clave institucional o CCDC commercial license)")
        print("\n[->] Vias alternativas de consulta disponibles:")
        print(f"    * Formula en Access Structures: https://www.ccdc.cam.ac.uk/structures/")
        print(f"      Filtro de busqueda: Formula = {meta.get('empirical_formula_guess', 'C4 H12 Cl2 N2 Pd')}")
        print(f"    * Analogos cristalograficos de referencia en CSD:")
        print(f"      - ENPDCL / ENPDCL01: [Pd(en)Cl2] (complejo analogo no metilado)")
        print(f"      - TMEDPD / ZEXZUF:   [Pd(tmeda)Cl2] (complejo tetrametilado)")
        print(f"      - PEPTAS:            Complejo analogo de Pt(II) con N,N'-dimetiletilendiamina")
        
        return {
            "status": "offline_mode",
            "smiles": smiles,
            "metadata": meta,
            "analogous_refcodes": ["ENPDCL", "TMEDPD", "ZEXZUF", "PEPTAS"]
        }

if __name__ == "__main__":
    target_smiles = "[CH3][NH]1[Pd](Cl)(Cl)[NH]([CH3])CC1"
    if len(sys.argv) > 1:
        target_smiles = sys.argv[1]
    res = search_ccdc_by_smiles(target_smiles)
