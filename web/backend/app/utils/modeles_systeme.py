"""Modèles HTML de base pour les documents systémiques.

Ces modèles sont utilisés lors du seed initial d'un nouveau tenant :
chaque type de document métier courant (facture, devis, bon de
livraison, avoir) reçoit un modèle par défaut, marqué `est_defaut=True`.

Les modèles utilisent les balises `{{variable}}` qui seront
remplacées à la génération du document.
"""

FACTURE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Facture {{reference}}</title>
</head>
<body>
  <header>
    <h1>{{tenant_nom}}</h1>
    <p>{{tenant_adresse}}<br>{{tenant_ville}} {{tenant_code_postal}}<br>{{tenant_pays}}</p>
    <p>Tél : {{tenant_telephone}}<br>Email : {{tenant_email}}</p>
  </header>
  <hr>
  <h2>FACTURE N° {{reference}}</h2>
  <p>Date : {{date_emission}}<br>Échéance : {{date_echeance}}</p>
  <h3>Facturé à :</h3>
  <p>{{client_nom}}<br>{{client_adresse}}<br>{{client_ville}} {{client_code_postal}}</p>
  <table border="1" cellspacing="0" cellpadding="6">
    <thead>
      <tr>
        <th>Désignation</th>
        <th>Quantité</th>
        <th>Prix unitaire</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
      {{lignes}}
    </tbody>
  </table>
  <p style="text-align:right">
    Sous-total HT : {{sous_total}} {{devise}}<br>
    TVA : {{montant_tva}} {{devise}}<br>
    <strong>Total TTC : {{total_ttc}} {{devise}}</strong>
  </p>
  <footer>
    <p>{{conditions_generales}}</p>
    <p>{{mention_legales}}</p>
  </footer>
</body>
</html>
"""

DEVIS_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Devis {{reference}}</title>
</head>
<body>
  <header>
    <h1>{{tenant_nom}}</h1>
    <p>{{tenant_adresse}}<br>{{tenant_ville}} {{tenant_code_postal}}<br>{{tenant_pays}}</p>
    <p>Tél : {{tenant_telephone}}<br>Email : {{tenant_email}}</p>
  </header>
  <hr>
  <h2>DEVIS N° {{reference}}</h2>
  <p>Date : {{date_emission}}<br>Validité : {{validite_jours}} jours</p>
  <h3>Destinataire :</h3>
  <p>{{client_nom}}<br>{{client_adresse}}<br>{{client_ville}} {{client_code_postal}}</p>
  <table border="1" cellspacing="0" cellpadding="6">
    <thead>
      <tr>
        <th>Désignation</th>
        <th>Quantité</th>
        <th>Prix unitaire</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
      {{lignes}}
    </tbody>
  </table>
  <p style="text-align:right">
    Sous-total HT : {{sous_total}} {{devise}}<br>
    TVA : {{montant_tva}} {{devise}}<br>
    <strong>Total TTC : {{total_ttc}} {{devise}}</strong>
  </p>
  <footer>
    <p>{{conditions_generales}}</p>
    <p>{{mention_legales}}</p>
  </footer>
</body>
</html>
"""

BON_LIVRAISON_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Bon de livraison {{reference}}</title>
</head>
<body>
  <header>
    <h1>{{tenant_nom}}</h1>
    <p>{{tenant_adresse}}<br>{{tenant_ville}} {{tenant_code_postal}}<br>{{tenant_pays}}</p>
    <p>Tél : {{tenant_telephone}}<br>Email : {{tenant_email}}</p>
  </header>
  <hr>
  <h2>BON DE LIVRAISON N° {{reference}}</h2>
  <p>Date de livraison : {{date_emission}}</p>
  <h3>Livré à :</h3>
  <p>{{client_nom}}<br>{{client_adresse}}<br>{{client_ville}} {{client_code_postal}}</p>
  <table border="1" cellspacing="0" cellpadding="6">
    <thead>
      <tr>
        <th>Désignation</th>
        <th>Quantité livrée</th>
      </tr>
    </thead>
    <tbody>
      {{lignes}}
    </tbody>
  </table>
  <p>Reçu par : ____________________ &nbsp;&nbsp; Signature : ____________________</p>
  <footer>
    <p>{{mention_legales}}</p>
  </footer>
</body>
</html>
"""

AVOIR_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Avoir {{reference}}</title>
</head>
<body>
  <header>
    <h1>{{tenant_nom}}</h1>
    <p>{{tenant_adresse}}<br>{{tenant_ville}} {{tenant_code_postal}}<br>{{tenant_pays}}</p>
    <p>Tél : {{tenant_telephone}}<br>Email : {{tenant_email}}</p>
  </header>
  <hr>
  <h2>AVOIR N° {{reference}}</h2>
  <p>Date : {{date_emission}}<br>Réf. facture d'origine : {{facture_reference}}</p>
  <h3>Client :</h3>
  <p>{{client_nom}}<br>{{client_adresse}}<br>{{client_ville}} {{client_code_postal}}</p>
  <table border="1" cellspacing="0" cellpadding="6">
    <thead>
      <tr>
        <th>Désignation</th>
        <th>Quantité</th>
        <th>Prix unitaire</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
      {{lignes}}
    </tbody>
  </table>
  <p style="text-align:right">
    <strong>Montant de l'avoir : {{total_ttc}} {{devise}}</strong>
  </p>
  <p>Motif : {{motif}}</p>
  <footer>
    <p>{{conditions_generales}}</p>
    <p>{{mention_legales}}</p>
  </footer>
</body>
</html>
"""


SYSTEM_MODELES_DOCUMENTS = [
    {
        'nom': 'Facture — Modèle standard',
        'type_document': 'facture',
        'contenu_modele': FACTURE_TEMPLATE,
        'est_defaut': True,
    },
    {
        'nom': 'Devis — Modèle standard',
        'type_document': 'devis',
        'contenu_modele': DEVIS_TEMPLATE,
        'est_defaut': True,
    },
    {
        'nom': 'Bon de livraison — Modèle standard',
        'type_document': 'bon_livraison',
        'contenu_modele': BON_LIVRAISON_TEMPLATE,
        'est_defaut': True,
    },
    {
        'nom': 'Avoir — Modèle standard',
        'type_document': 'avoir',
        'contenu_modele': AVOIR_TEMPLATE,
        'est_defaut': True,
    },
]


MENTIONS_LEGALES_DEFAUT = (
    "Document généré par MIHAJA ERP — Conforme à la réglementation en vigueur."
)

CONDITIONS_GENERALES_DEFAUT = (
    "Conditions générales : paiement à 30 jours. "
    "En cas de retard, pénalités applicables selon la législation en vigueur."
)
