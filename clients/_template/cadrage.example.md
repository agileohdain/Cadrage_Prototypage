# Cadrage — demo

> Livrable de la phase de cadrage, consolidé depuis `matrice.xlsx` (rempli avec le client). Complémentaire de la maquette HTML : il documente **l'ensemble** des indicateurs (y compris hors maquette), leurs priorités, sources et fiabilités.

- **Date** : 12/08/2026
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
| Partielle | 3 | `*` orange |
| Inconnue | 1 | `*` rouge |

## Détail par thème

> Les **Thèmes** et **Sujets** structurent le cadrage métier — ils ne correspondent pas nécessairement aux pages/sous-pages de la maquette (regroupées pour la lisibilité).

### Ventes

| Sujet | Indicateur | Priorité | Système source | Source données | Fiabilité | Formule | Commentaires |
|---|---|---|---|---|---|---|---|
| Performance commerciale | Chiffre d'affaires | Haute | ERP SAP | DWH.FACT_VENTES | Fiable | SUM(MONTANT_HT) | — |
| Performance commerciale | Panier moyen | Moyenne | ERP SAP | DWH.FACT_VENTES | Fiable | MONTANT / NB_VENTES | — |
| Performance commerciale | Taux de conversion | Basse | CRM Salesforce | vue v_leads | Partielle | LEADS_GAGNES / LEADS | Estimation manuelle |
| Clients | Clients actifs | Haute | CRM Salesforce | DIM_CLIENT | Fiable | DISTINCT(ID_CLIENT) | — |
| Clients | Nouveaux clients | Moyenne | CRM Salesforce | vue v_newclients | Partielle | COUNT(first_order_date) | Référentiel à valider |

- **Chiffre d'affaires** — axes d'analyse : par région, par segment
- **Panier moyen** — axes d'analyse : par segment
- **Taux de conversion** — axes d'analyse : par canal
- **Clients actifs** — axes d'analyse : par région
- **Nouveaux clients** — axes d'analyse : par mois

### Logistique

| Sujet | Indicateur | Priorité | Système source | Source données | Fiabilité | Formule | Commentaires |
|---|---|---|---|---|---|---|---|
| Livraisons | Livraisons à temps | Haute | TMS | FACT_LIVRAISONS | Fiable | SUM(A_TEMPS) / COUNT | — |
| Livraisons | Coût transport | Haute | TMS | FACT_LIVRAISONS | Fiable | SUM(COUT_TRANSPORT) | — |
| Livraisons | Délai moyen | Moyenne | TMS | FACT_LIVRAISONS | Fiable | AVG(DELAI_HEURES) | — |
| Livraisons | Taux d'incidents | Basse | — | — | Inconnue | COUNT(incident) / COUNT | Source non identifiée |

- **Livraisons à temps** — axes d'analyse : par zone, par mode
- **Coût transport** — axes d'analyse : par mode
- **Délai moyen** — axes d'analyse : par zone
- **Taux d'incidents** — axes d'analyse : par type

### Qualité

| Sujet | Indicateur | Priorité | Système source | Source données | Fiabilité | Formule | Commentaires |
|---|---|---|---|---|---|---|---|
| Incidents | Tickets ouverts | Haute | Helpdesk | FACT_INCIDENT | Fiable | COUNT(ID_TICKET) | — |
| Incidents | Délai de résolution | Moyenne | Helpdesk | FACT_INCIDENT | Partielle | AVG(DELAI_RESO) | Saisie manuelle partielle |

- **Tickets ouverts** — axes d'analyse : par statut
- **Délai de résolution** — axes d'analyse : par gravité

## Périmètre maquette (Hautes + Moyennes)

9 indicateurs retenus pour la maquette.

| Thème | Sujet | Indicateur | Priorité | Fiabilité |
|---|---|---|---|---|
| Ventes | Performance commerciale | Chiffre d'affaires | Haute | Fiable |
| Ventes | Performance commerciale | Panier moyen | Moyenne | Fiable |
| Ventes | Clients | Clients actifs | Haute | Fiable |
| Ventes | Clients | Nouveaux clients | Moyenne | Partielle |
| Logistique | Livraisons | Livraisons à temps | Haute | Fiable |
| Logistique | Livraisons | Coût transport | Haute | Fiable |
| Logistique | Livraisons | Délai moyen | Moyenne | Fiable |
| Qualité | Incidents | Tickets ouverts | Haute | Fiable |
| Qualité | Incidents | Délai de résolution | Moyenne | Partielle |

## Alertes fiabilité

Indicateurs à fiabilité partielle ou source non identifiée — signalés par un `*` sur la maquette :

| Indicateur | Fiabilité | Système source | Source données | Raison |
|---|---|---|---|---|
| Taux de conversion | Partielle (ATTENTION) | CRM Salesforce | vue v_leads | Fiabilité partielle / à valider |
| Nouveaux clients | Partielle (ATTENTION) | CRM Salesforce | vue v_newclients | Fiabilité partielle / à valider |
| Taux d'incidents | Inconnue (RISQUE) | — | — | Source non identifiée |
| Délai de résolution | Partielle (ATTENTION) | Helpdesk | FACT_INCIDENT | Fiabilité partielle / à valider |

---
*Document généré par `generate-cadrage.py` — ne pas éditer à la main.*
