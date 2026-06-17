---
name: Digit-AI SaaS Forge
version: 0.1.0
colors:
  primary: "#2563eb"
  ink: "#0f172a"
  ink-soft: "#334155"
  accent: "#5b21b6"
  surface: "#ffffff"
  surface-soft: "#f7f8fa"
  success: "#0f766e"
  danger: "#b91c1c"
typography:
  heading: "Roboto"
  body: "DM Sans"
  mono: "JetBrains Mono"
spacing:
  xs: 4
  sm: 8
  md: 16
  lg: 24
  xl: 40
rounded:
  sm: 6
  card: 12
  pill: 999
---

# Digit-AI SaaS Forge — Design System

Charte de référence (paramétrable, décision 08). Lintable par `design.md` ; exportable
en tokens Tailwind / DTCG (charte → code sans ressaisie).

## Principes

La référence spécifique prime sur l'adjectif : on décrit des valeurs exactes (couleurs,
familles, espacements) plutôt que des intentions vagues. Sobriété, lisibilité, accessibilité
AA par défaut.

## Couleurs

Le bleu `primary` (#2563eb) porte les actions ; l'accent violet (#5b21b6) signale l'IA et
les états BMAD. Le texte `ink` (#0f172a) sur `surface` (#ffffff) offre un contraste élevé,
conforme WCAG 2.2 AA.

## Typographie

Titres en **Roboto**, corps en **DM Sans**, code et libellés techniques en **JetBrains Mono**.

## Composants

### button-primary

Fond `primary`, texte `surface` : ratio de contraste conforme WCAG AA pour le texte de bouton.

### card

Fond `surface`, rayon `card` (12px), bordure discrète. Conteneur de base du tableau de bord.

## Spacing

Échelle d'espacement (en px) : `xs` 4, `sm` 8, `md` 16, `lg` 24, `xl` 40. Toutes les marges
et paddings dérivent de cette échelle — pas de valeurs arbitraires.

## Rounded

Rayons de coin : `sm` 6, `card` 12, `pill` 999. Les cartes utilisent `card`, les boutons
pleins `sm`, les badges `pill`.
