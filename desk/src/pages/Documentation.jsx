import React from 'react';
import './Pages.css';

const Documentation = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Manuel d'utilisation — Module Documents (de A à Z)</h1>
          <p>Boky fampiasana — Modily antontan-taratasy (manomboka A hatramin'ny Z)</p>
        </div>
      </div>

      <div className="card">
        <h3>📄 1. Présentation — Fampahafantarana</h3>
        <p><strong>Français :</strong> Le module Documents permet de créer, gérer et générer des documents professionnels (factures, devis, contrats, bons de livraison, avoirs) à partir de modèles personnalisés. Vous pouvez pré-remplir les données depuis une vente ou une facture existante.</p>
        <p><strong>Malgache :</strong> Ny modily Antontan-taratasy dia ahafahana mamorona, mitantana ary manomboka antontan-taratasy matihanina (faktiora, devis, fifanarahana, taratasy fandefasana, avoir) avy amin'ny modely azo ovaina. Afaka mamerina ny angona avy amin'ny varotra na faktiora misy.</p>
      </div>

      <div className="card">
        <h3>📄 2. Navigation — Fandehanana</h3>
        <p><strong>Français :</strong> Depuis le menu, cliquez sur <em>Documents</em>. Vous y trouvez deux onglets : <strong>Modèles</strong> (création/édition) et <strong>Documents</strong> (génération et historique).</p>
        <p><strong>Malgache :</strong> Avy amin'ny menu, kitiho ny <em>Antontan-taratasy</em>. Misy tabilao roa : <strong>Modely</strong> (famoronana/fanitsiana) sy <strong>Antontan-taratasy</strong> (famoronana sy tantara).</p>
      </div>

      <div className="card">
        <h3>📄 3. Créer un modèle — Mamorona modely</h3>
        <p><strong>Français :</strong> Dans l'onglet <em>Modèles</em>, remplissez le nom, le type (facture, devis, contrat, bon de livraison, avoir), le contenu HTML avec des placeholders (ex : <code>{{client_nom}}</code>, <code>{{total_ttc}}</code>), le logo (URL), les mentions légales et les conditions générales. Cochez <em>Défaut</em> si ce modèle doit être proposé par défaut. Cliquez sur <em>Créer</em> ou <em>Modifier</em>.</p>
        <p><strong>Malgache :</strong> Ao amin'ny tabilao <em>Modely</em>, fenoy ny anarana, ny karazana (faktiora, devis, fifanarahana, taratasy fandefasana, avoir), ny votoaty HTML misy placeholders (ohatra : <code>{{client_nom}}</code>, <code>{{total_ttc}}</code>), ny sary famantarana (URL), ny fanambarana ara-dalàna ary ny fepetra. Tsindrio ny <em>Défaut</em> raha io no modely ho atolotra voalohany. Kitiho ny <em>Mamorona</em> na <em>Manitsy</em>.</p>
      </div>

      <div className="card">
        <h3>📄 4. Générer un document — Mamorona antontan-taratasy</h3>
        <p><strong>Français :</strong> Dans l'onglet <em>Documents</em>, sélectionnez un modèle, donnez une référence, choisissez le type de document, l'entité liée (vente, facture, commande, abonnement) et son ID. Remplissez les données JSON (ex : client, total, articles). Cliquez sur <em>Générer le PDF</em>. Le document apparaît dans la liste avec les actions : prévisualiser, télécharger, imprimer, supprimer.</p>
        <p><strong>Malgache :</strong> Ao amin'ny tabilao <em>Antontan-taratasy</em>, safidio ny modely, omeo anarana (référence), safidio ny karazana, ny orinasa mifandraika (varotra, faktiora, baiko, fandraisana) sy ny ID-ny. Fenoy ny angona JSON (ohatra : mpanjifa, total, entana). Kitiho ny <em>Mamorona PDF</em>. Miseho ao amin'ny lisitra ny antontan-taratasy miaraka amin'ny asa : jereo, alaina, atao pirinty, fafana.</p>
      </div>

      <div className="card">
        <h3>📄 5. Prévisualisation, téléchargement et impression — Fijerena, fakana ary fanontana</h3>
        <p><strong>Français :</strong> Cliquez sur l'icône œil (👁) pour prévisualiser le PDF dans une fenêtre modale. Utilisez <em>Télécharger</em> (↓) pour sauvegarder le fichier et <em>Imprimer</em> (🖨) pour lancer l'impression directement depuis le navigateur.</p>
        <p><strong>Malgache :</strong> Kitiho ny sary maso (👁) hijerena ny PDF ao anaty varavarankely. Ampiasao ny <em>Fakana</em> (↓) hitehirizana ny rakitra ary ny <em>Fanontana</em> (🖨) hanontana mivantana avy amin'ny navigateur.</p>
      </div>

      <div className="card">
        <h3>📄 6. Supprimer — Fafana</h3>
        <p><strong>Français :</strong> Cliquez sur la croix (✕) pour supprimer un modèle ou un document généré. Une confirmation est demandée.</p>
        <p><strong>Malgache :</strong> Kitiho ny lakroa (✕) hanesorana modely na antontan-taratasy namorona. Misy fanamafisana angatahina.</p>
      </div>

      <div className="card">
        <h3>📄 7. Liens utiles — Rohy ilaina</h3>
        <ul>
          <li><a href="/documents">Module Documents</a> — <em>Modily Antontan-taratasy</em></li>
          <li><a href="/documentation">Manuel complet</a> — <em>Boky feno</em></li>
        </ul>
      </div>

      <div className="card">
        <h3>📄 8. Support — Fanohanana</h3>
        <p><strong>Français :</strong> Si vous avez besoin d'aide, consultez la documentation technique du projet dans le dossier <code>docs/</code> ou contactez le support.</p>
        <p><strong>Malgache :</strong> Raha mila fanampiana ianao, jereo ny boky teknika ao amin'ny dossier <code>docs/</code> na mifandraisa amin'ny fanohanana.</p>
      </div>
    </div>
  );
};

export default Documentation;
