# Sistema de Sincronización Berkeley

Este proyecto implementa el algoritmo de Berkeley para sincronizar los relojes de 3 computadoras.

## Estructura
- **Coordinator**: Nodo maestro que coordina la sincronización
- **Node**: Nodos esclavos que se sincronizan con el coordinador

## Cómo ejecutar

1. **Iniciar el Coordinador**:
```bash
python coordinator.py
```
2. **Iniciar nodos (en consolas distintas)**:
```bash
python node.py 1
```
```bash
python node.py 2
```