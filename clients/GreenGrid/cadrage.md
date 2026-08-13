# Cadrage — GreenGrid

> Livrable de la phase de cadrage, consolidé depuis `matrice.xlsx` (rempli avec le client). Complémentaire de la maquette HTML : il documente **l'ensemble** des indicateurs (y compris hors maquette), leurs priorités, sources et fiabilités.

- **Date** : 13/08/2026
- **Périmètre maquette retenu** : Hautes + Moyennes
- **Indicateurs cadrés** : 11

## Synthèse

**Par priorité**

| Priorité | Indicateurs | Dans la maquette ? |
|---|---:|:---:|
| Haute | 5 | Oui |
| Moyenne | 4 | Oui |
| Basse | 2 | — |

**Par fiabilité**

| Fiabilité | Indicateurs | Marqueur maquette |
|---|---:|:---:|
| Fiable | 7 | — |
| Partielle | 2 | `*` orange |
| Inconnue | 2 | `◆` rouge |

## Détail par thème

> Les **Thèmes** et **Sujets** structurent le cadrage métier — ils ne correspondent pas nécessairement aux pages/sous-pages de la maquette (regroupées pour la lisibilité).

### Sessions

| Sujet | Indicateur | Priorité | Système source | Source données | Fiabilité | Formule | Commentaires |
|---|---|---|---|---|---|---|---|
| Volumes | Nombre de sessions de recharge | Haute | CSMS | FACT_SESSIONS | Fiable | COUNT(ID_SESSION) | — |
| Volumes | Énergie délivrée (kWh) | Haute | CSMS | FACT_SESSIONS | Fiable | SUM(KWH) | — |
| Revenus | Chiffre d'affaires recharge | Haute | Billing | FACT_FACTURATION | Fiable | SUM(MONTANT_HT) | — |
| Revenus | Prix moyen par kWh | Moyenne | Billing | FACT_FACTURATION | Partielle | MONTANT_HT / KWH | Grille tarifaire en cours d'homogénéisation |

- **Nombre de sessions de recharge** — axes d'analyse : par mois, par zone, par puissance
- **Énergie délivrée (kWh)** — axes d'analyse : par mois, par zone, par opérateur
- **Chiffre d'affaires recharge** — axes d'analyse : par mois, par zone
- **Prix moyen par kWh** — axes d'analyse : par offre, par zone

### Réseau

| Sujet | Indicateur | Priorité | Système source | Source données | Fiabilité | Formule | Commentaires |
|---|---|---|---|---|---|---|---|
| Couverture | Bornes en service | Haute | CMDB | DIM_BORNE | Fiable | COUNT(STATUT='EN_SERVICE') | — |
| Couverture | Taux de disponibilité | Haute | SCADA | FACT_UPTIME | Fiable | AVG(UP_TIME_FLAG) | — |
| Couverture | Taux d'occupation | Moyenne | CSMS | FACT_SESSIONS | Partielle | SESSIONS / CAPACITE | Capacité théorique à confirmer |
| Déploiement | Nouvelles bornes déployées | Basse | CMDB | DIM_BORNE | Fiable | COUNT(DATE_MISE_EN_SERVICE) | — |
| Déploiement | Couverture territoriale | Basse | — | — | Inconnue | COUNT(BORNE) / OBJECTIF | Référentiel géo à définir |

- **Bornes en service** — axes d'analyse : par zone, par opérateur
- **Taux de disponibilité** — axes d'analyse : par zone, par mois
- **Taux d'occupation** — axes d'analyse : par zone, par heure
- **Nouvelles bornes déployées** — axes d'analyse : par zone, par mois
- **Couverture territoriale** — axes d'analyse : par région

### Qualité de service

| Sujet | Indicateur | Priorité | Système source | Source données | Fiabilité | Formule | Commentaires |
|---|---|---|---|---|---|---|---|
| Expérience client | Clients actifs | Moyenne | CRM | DIM_CLIENT | Fiable | DISTINCT(ID_CLIENT) | — |
| Expérience client | Taux de sessions interrompues | Moyenne | SCADA | — | Inconnue | SUM(ERREUR_FLAG) / COUNT | Cause non systématiquement renseignée |

- **Clients actifs** — axes d'analyse : par zone, par offre
- **Taux de sessions interrompues** — axes d'analyse : par zone, par cause

## Périmètre maquette (Hautes + Moyennes)

9 indicateurs retenus pour la maquette.

| Thème | Sujet | Indicateur | Priorité | Fiabilité |
|---|---|---|---|---|
| Sessions | Volumes | Nombre de sessions de recharge | Haute | Fiable |
| Sessions | Volumes | Énergie délivrée (kWh) | Haute | Fiable |
| Sessions | Revenus | Chiffre d'affaires recharge | Haute | Fiable |
| Sessions | Revenus | Prix moyen par kWh | Moyenne | Partielle |
| Réseau | Couverture | Bornes en service | Haute | Fiable |
| Réseau | Couverture | Taux de disponibilité | Haute | Fiable |
| Réseau | Couverture | Taux d'occupation | Moyenne | Partielle |
| Qualité de service | Expérience client | Clients actifs | Moyenne | Fiable |
| Qualité de service | Expérience client | Taux de sessions interrompues | Moyenne | Inconnue |

## Alertes fiabilité

Indicateurs à fiabilité partielle ou source non identifiée — signalés par un marqueur (`*`/`◆`) sur la maquette :

| Indicateur | Fiabilité | Système source | Source données | Raison |
|---|---|---|---|---|
| Prix moyen par kWh | Partielle (ATTENTION) | Billing | FACT_FACTURATION | Fiabilité partielle / à valider |
| Taux d'occupation | Partielle (ATTENTION) | CSMS | FACT_SESSIONS | Fiabilité partielle / à valider |
| Couverture territoriale | Inconnue (RISQUE) | — | — | Source non identifiée |
| Taux de sessions interrompues | Inconnue (RISQUE) | SCADA | — | Source non identifiée |

---
*Document généré par `generate-cadrage.py` — ne pas éditer à la main.*
