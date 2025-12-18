# 📦 Script de Backup - CobranzaV22

## Uso del Script

### Ejecución Básica

```powershell
.\backup.ps1
```

### Con Descripción Personalizada

```powershell
.\backup.ps1 -Descripcion "Mejoras de navegacion"
```

---

## ¿Qué hace el script?

1. **Backup Completo** → Copia todos los archivos del proyecto (excepto archivos temporales)
2. **Backup Automático** → Copia solo los archivos modificados desde el último commit
3. **Git Commit** → Hace commit de los cambios
4. **Git Push** → Sube los cambios a GitHub

---

## Archivos Excluidos del Backup

El script **NO** respalda:
- ❌ Carpeta `venv/` (entorno virtual)
- ❌ Carpeta `__pycache__/` (archivos compilados Python)
- ❌ Carpeta `.git/` (control de versiones)
- ❌ Carpeta `staticfiles/` (archivos estáticos recopilados)
- ❌ Archivo `db.sqlite3` (base de datos - se respalda por separado)
- ❌ Archivo `.env` (credenciales sensibles)
- ❌ Archivos `.pyc`, `.pyo`, `.log`

---

## Estructura de Backups

```
backups/
├── 2024-12-18_14-30_COMPLETO_Mejoras-navegacion/
│   ├── clientes/
│   ├── cobros/
│   ├── documentos/
│   └── ...
│
└── 2024-12-18_14-30_AUTO_Mejoras-navegacion/
    ├── base.html
    ├── cobros/views.py
    └── ...
```

---

## Ejemplos de Uso

### Ejemplo 1: Backup antes de cambios importantes

```powershell
.\backup.ps1 -Descripcion "Antes de implementar nuevo menu"
```

### Ejemplo 2: Backup diario

```powershell
.\backup.ps1 -Descripcion "Backup diario"
```

### Ejemplo 3: Backup después de correcciones

```powershell
.\backup.ps1 -Descripcion "Correccion de bugs en reportes"
```

---

## Salida del Script

```
========================================
  BACKUP COMPLETO + AUTO + GIT PUSH
  Sistema: CobranzaV22
========================================

[1/5] Creando backup completo...
  Copiando 245 archivos...
  Progreso: 50 / 245 archivos (20%)...
  Progreso: 100 / 245 archivos (41%)...
  ...
  ✓ Backup completo: 245 archivos copiados
  ✓ Ubicacion: backups\2024-12-18_14-30_COMPLETO_...

[2/5] Creando backup automatico (solo modificados)...
  Copiando 5 archivos modificados...
    ✓ templates/base.html
    ✓ cobros/views.py
    ...
  ✓ Backup automatico: 5 archivos copiados

[3/5] Verificando estado de Git...
  Archivos modificados detectados:
    M templates/base.html
    M cobros/views.py
    ...

[4/5] Agregando archivos a Git...
  Mensaje de commit: ✨ Mejoras navegacion - 2024-12-18_14-30
  ✓ Commit realizado exitosamente

[5/5] Subiendo cambios a GitHub...
  Rama actual: desarrollo
  Ejecutando push...
  ✓ Push completado exitosamente

========================================
  ✓ PROCESO COMPLETADO EXITOSAMENTE
========================================

Resumen:
  • Backup completo: backups\2024-12-18_14-30_COMPLETO_...
  • Archivos en backup completo: 245
  • Backup automatico: backups\2024-12-18_14-30_AUTO_...
  • Archivos en backup auto: 5
  • Commit: ✨ Mejoras navegacion - 2024-12-18_14-30
  • Rama: desarrollo
  • Estado: ✓ Subido a GitHub

🎉 Todo listo!
```

---

## Notas Importantes

> [!IMPORTANT]
> - El script **NO** respalda el archivo `.env` por seguridad
> - El script **NO** respalda la base de datos `db.sqlite3`
> - Si necesitas respaldar la BD, hazlo manualmente o usa otro script

> [!TIP]
> **Recomendación:** Ejecuta este script antes de hacer cambios importantes en el sistema

> [!WARNING]
> Si el script falla al hacer push, verifica:
> - Tu conexión a internet
> - Tus credenciales de Git (token de acceso)
> - Que la rama exista en GitHub

---

## Restaurar desde Backup

Para restaurar archivos desde un backup:

```powershell
# Ver backups disponibles
ls backups

# Copiar archivos específicos
Copy-Item "backups\2024-12-18_14-30_COMPLETO_...\templates\base.html" -Destination "templates\base.html"

# O restaurar todo (¡cuidado!)
Copy-Item "backups\2024-12-18_14-30_COMPLETO_...\*" -Destination "." -Recurse -Force
```

---

**¡Listo para usar!** 🚀
