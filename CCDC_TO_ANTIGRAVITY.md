# Integración CSD Python API (CCDC) ➔ Antigravity Workflow

Este documento técnico detalla la arquitectura y el código necesario para automatizar un script en Python que interactúe con los tres módulos principales del ecosistema **CCDC** (`Entry`, `Crystal`, `Molecule`) y exporte/conecte la estructura geométrica procesada directamente hacia la plataforma **Antigravity**.

## 📊 Arquitectura de la Conexión

Para mapear de forma correcta la estructura tridimensional antes de enviarla a Antigravity, el script consume de forma coordinada las tres capas lógicas de la CSD:

```text
┌────────────────────────────────────────┐
│          CSD Python API (CCDC)         │
└───────────────────┬────────────────────┘
                    │
┌───────────────────┼────────────────────┐
▼                   ▼                    ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐
│  ccdc.entry      ││  ccdc.crystal    ││  ccdc.molecule   │
│  (Metadatos y    ││  (Celda unidad,  ││  (Coordenadas 3D,│
│  Publicaciones)  ││  Simetría, Grupo)││  Átomos, Enlaces)│
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
┌────────────────────────────────────────┐
│        Fusión e Integración 3D         │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│       Antigravity Toolkit/API          │
│   (Simulación, Gravedad Química, etc.) │
└────────────────────────────────────────┘
```

---

## 🛠️ Requisitos e Instalación

Asegúrate de contar con el entorno de la CCDC configurado con tu licencia institucional o comercial.

```bash
# Instalación del Toolkit de CCDC mediante Conda (recomendado)
conda install -c ccdc csd-python-api

# Instalar librería auxiliar para manipulación de matrices si Antigravity lo requiere
pip install numpy
```

---

## 🐍 Código del Script: `ccdc_to_antigravity.py`

Este script realiza la búsqueda (mediante el identificador único o *Refcode* de la base de datos), extrae la información de las tres APIs esenciales de la CCDC, unifica los datos químicos/espaciales y los inicializa en el entorno de **Antigravity**.

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
        # (Ajustar según los métodos nativos de inicialización de Antigravity)
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
```

---

## 🚀 Ejecución del Flujo

Puedes correr el script directamente desde la terminal pasando el **Refcode** del cristal deseado como argumento:

```bash
python ccdc_to_antigravity.py ABEBUF
```

### Notas de Personalización para Antigravity
* **Si la carga es por API:** Modifica la sección `if ag is not None:` para acoplarla exactamente a las clases de inicialización tridimensional del framework Antigravity.
* **Si la carga es por archivo:** El script generará un archivo `.cif` limpio y estandarizado con la información de las 3 APIs de la CCDC listo para ser importado por el backend de Antigravity.
