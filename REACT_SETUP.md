# Configuration React et shadcn/ui

Ce projet utilise maintenant React avec shadcn/ui pour les composants de l'interface, notamment les checkboxes dans l'onglet Diagram.

## Installation

1. Installer les dépendances Node.js :
```bash
npm install
```

## Développement

Pour le développement avec hot-reload :
```bash
npm run dev
```

Cela lancera Vite en mode développement. Notez que vous devrez peut-être configurer un proxy ou modifier la configuration Flask pour servir les fichiers React en développement.

## Build de production

Avant de lancer Flask, vous devez builder les composants React :

```bash
npm run build
```

Cela générera les fichiers compilés dans `static/react/`.

## Structure

- `src/` : Code source React/TypeScript
- `src/components/ui/` : Composants shadcn/ui (checkbox, label, etc.)
- `src/components/` : Composants React personnalisés
- `static/react/` : Fichiers compilés (générés par le build)
- `tailwind.config.js` : Configuration Tailwind CSS (utilisée par shadcn/ui)
- `components.json` : Configuration shadcn/ui

## Notes

- Tailwind CSS est maintenant géré via npm (pas de CDN)
- Les styles sont définis dans `src/index.css`
- Les composants React communiquent avec le code vanilla JS via `window.mountDiagramCheckboxes`

